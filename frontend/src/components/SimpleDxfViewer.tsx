"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import DxfParser from "dxf-parser";

interface SimpleDxfViewerProps {
    url: string;
    className?: string;
}

const buildLine = (points: THREE.Vector3[], material: THREE.LineBasicMaterial) => {
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    return new THREE.Line(geometry, material);
};

const addPolyline = (group: THREE.Group, vertices: Array<{ x: number; y: number }>, closed: boolean, material: THREE.LineBasicMaterial) => {
    if (!vertices || vertices.length < 2) return;
    const points = vertices.map((v) => new THREE.Vector3(v.x, v.y, 0));
    if (closed) points.push(points[0].clone());
    group.add(buildLine(points, material));
};

const addCircle = (group: THREE.Group, center: { x: number; y: number }, radius: number, material: THREE.LineBasicMaterial) => {
    const curve = new THREE.EllipseCurve(center.x, center.y, radius, radius, 0, Math.PI * 2, false, 0);
    const points = curve.getPoints(64).map((p) => new THREE.Vector3(p.x, p.y, 0));
    group.add(buildLine(points, material));
};

const addArc = (group: THREE.Group, center: { x: number; y: number }, radius: number, startAngleDeg: number, endAngleDeg: number, material: THREE.LineBasicMaterial) => {
    const start = THREE.MathUtils.degToRad(startAngleDeg);
    const end = THREE.MathUtils.degToRad(endAngleDeg);
    const curve = new THREE.EllipseCurve(center.x, center.y, radius, radius, start, end, false, 0);
    const points = curve.getPoints(48).map((p) => new THREE.Vector3(p.x, p.y, 0));
    group.add(buildLine(points, material));
};

const buildGroupFromDxf = (dxf: any): THREE.Group => {
    const group = new THREE.Group();
    const material = new THREE.LineBasicMaterial({ color: "#000000", linewidth: 2 });
    const entities = Array.isArray(dxf?.entities) ? dxf.entities : [];

    entities.forEach((ent: any) => {
        const type = ent?.type;
        if (type === "LINE") {
            const points = [
                new THREE.Vector3(ent.start.x, ent.start.y, 0),
                new THREE.Vector3(ent.end.x, ent.end.y, 0),
            ];
            group.add(buildLine(points, material));
        } else if (type === "LWPOLYLINE") {
            addPolyline(group, ent.vertices || [], !!ent.closed, material);
        } else if (type === "POLYLINE") {
            const vertices = (ent.vertices || []).map((v: any) => ({ x: v.x, y: v.y }));
            addPolyline(group, vertices, !!ent.closed, material);
        } else if (type === "CIRCLE") {
            addCircle(group, ent.center, ent.radius, material);
        } else if (type === "ARC") {
            addArc(group, ent.center, ent.radius, ent.startAngle, ent.endAngle, material);
        }
    });

    // Randomly color some lines blue
    group.traverse((child) => {
        if ((child as THREE.Line).isLine && Math.random() > 0.7) {
            (child as THREE.Line).material = new THREE.LineBasicMaterial({ color: "#3b82f6", linewidth: 2 });
        }
    });

    return group;
};

export default function SimpleDxfViewer({ url, className = "" }: SimpleDxfViewerProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
    const frameIdRef = useRef<number>(0);

    useEffect(() => {
        if (!containerRef.current) return;

        const container = containerRef.current;
        const width = container.clientWidth;
        const height = container.clientHeight;

        // Scene
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf8fafc);

        // Orthographic Camera for 2D view
        const aspect = width / height;
        const frustumSize = 100;
        const camera = new THREE.OrthographicCamera(
            (frustumSize * aspect) / -2,
            (frustumSize * aspect) / 2,
            frustumSize / 2,
            frustumSize / -2,
            0.1,
            2000
        );
        camera.position.set(0, 0, 80);
        camera.zoom = 1;
        camera.updateProjectionMatrix();

        // Renderer
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        container.appendChild(renderer.domElement);
        rendererRef.current = renderer;

        // Controls - 2D pan/zoom only
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableRotate = false;
        controls.enableZoom = true;
        controls.enablePan = true;
        controls.enableDamping = true;
        controls.dampingFactor = 0.1;
        controls.screenSpacePanning = true;

        // Grid
        const gridHelper = new THREE.GridHelper(200, 20, 0xe2e8f0, 0xe2e8f0);
        gridHelper.rotation.x = Math.PI / 2;
        gridHelper.position.z = -0.1;
        scene.add(gridHelper);

        // Light
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
        scene.add(ambientLight);

        // Load DXF
        const loader = new THREE.FileLoader();
        loader.setResponseType("text");
        loader.load(
            url,
            (data) => {
                try {
                    const parser = new DxfParser();
                    const text = typeof data === "string" ? data : new TextDecoder().decode(data as ArrayBuffer);
                    const dxf = parser.parseSync(text);
                    const dxfGroup = buildGroupFromDxf(dxf);
                    
                    // Center the DXF
                    const box = new THREE.Box3().setFromObject(dxfGroup);
                    const center = box.getCenter(new THREE.Vector3());
                    dxfGroup.position.sub(center);
                    
                    // Fit to view
                    const size = box.getSize(new THREE.Vector3());
                    const maxDim = Math.max(size.x, size.y);
                    camera.zoom = (frustumSize * 0.8) / maxDim;
                    camera.updateProjectionMatrix();
                    
                    scene.add(dxfGroup);
                } catch (e) {
                    console.error("Failed to parse DXF:", e);
                }
            },
            undefined,
            (error) => {
                console.error("Error loading DXF:", error);
            }
        );

        // Animation loop
        const animate = () => {
            frameIdRef.current = requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        };
        animate();

        // Resize handler
        const handleResize = () => {
            if (!container) return;
            const w = container.clientWidth;
            const h = container.clientHeight;
            const newAspect = w / h;
            camera.left = (frustumSize * newAspect) / -2;
            camera.right = (frustumSize * newAspect) / 2;
            camera.updateProjectionMatrix();
            renderer.setSize(w, h);
        };
        window.addEventListener("resize", handleResize);

        // Cleanup
        return () => {
            window.removeEventListener("resize", handleResize);
            cancelAnimationFrame(frameIdRef.current);
            controls.dispose();
            renderer.dispose();
            if (container.contains(renderer.domElement)) {
                container.removeChild(renderer.domElement);
            }
        };
    }, [url]);

    return (
        <div
            ref={containerRef}
            className={`w-full h-full ${className}`}
            style={{ minHeight: "200px" }}
        />
    );
}
