"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

interface Vector3Tuple {
    x: number;
    y: number;
    z: number;
}

interface Simple3DViewerProps {
    boundingboxStart: Vector3Tuple;
    boundingboxEnd: Vector3Tuple;
    factoryModel?: string;
    pipelineModel?: string;
    className?: string;
}

export default function Simple3DViewer({
    boundingboxStart,
    boundingboxEnd,
    factoryModel,
    pipelineModel,
    className = ""
}: Simple3DViewerProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
    const sceneRef = useRef<THREE.Scene | null>(null);
    const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
    const controlsRef = useRef<OrbitControls | null>(null);
    const frameIdRef = useRef<number>(0);

    useEffect(() => {
        if (!containerRef.current) return;

        const container = containerRef.current;
        const width = container.clientWidth;
        const height = container.clientHeight;

        // Scene
        const scene = new THREE.Scene();
        // scene.background = null; // Transparent to let CSS background show
        sceneRef.current = scene;

        // Camera
        const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
        camera.position.set(5, 4, 8);
        cameraRef.current = camera;

        // Renderer
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(renderer.domElement);
        rendererRef.current = renderer;

        // Controls
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.minDistance = 2;
        controls.maxDistance = 50;
        controls.target.set(0, 1, 0);
        controlsRef.current = controls;

        // Grid
        const gridHelper = new THREE.GridHelper(60, 60, 0x6366f1, 0x334155);
        scene.add(gridHelper);

        // Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 1.4);
        directionalLight.position.set(10, 20, 10);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 4096;
        directionalLight.shadow.mapSize.height = 4096;
        directionalLight.shadow.camera.near = 0.5;
        directionalLight.shadow.camera.far = 500;
        directionalLight.shadow.camera.left = -100;
        directionalLight.shadow.camera.right = 100;
        directionalLight.shadow.camera.top = 100;
        directionalLight.shadow.camera.bottom = -100;
        directionalLight.shadow.bias = -0.0005;
        scene.add(directionalLight);

        // Calculate target bounding box from props
        const targetMin = new THREE.Vector3(
            Math.min(boundingboxStart.x, boundingboxEnd.x),
            Math.min(boundingboxStart.y, boundingboxEnd.y),
            Math.min(boundingboxStart.z, boundingboxEnd.z)
        );
        const targetMax = new THREE.Vector3(
            Math.max(boundingboxStart.x, boundingboxEnd.x),
            Math.max(boundingboxStart.y, boundingboxEnd.y),
            Math.max(boundingboxStart.z, boundingboxEnd.z)
        );
        const targetSize = new THREE.Vector3().subVectors(targetMax, targetMin);
        const targetCenter = new THREE.Vector3().addVectors(targetMin, targetMax).multiplyScalar(0.5);

        // Adjust camera to fit the bounding box
        const maxDim = Math.max(targetSize.x, targetSize.y, targetSize.z);
        const cameraDistance = maxDim * 2; // Arbitrary multiplier to frame the box
        camera.position.set(
            targetCenter.x + cameraDistance,
            targetCenter.y + cameraDistance * 0.8,
            targetCenter.z + cameraDistance
        );
        controls.target.copy(targetCenter);
        controls.update();

        const loader = new GLTFLoader();

        // Load Factory (Environment)
        if (factoryModel) {
            loader.load(
                factoryModel,
                (gltf) => {
                    const model = gltf.scene;
                    model.scale.set(0.2, 0.2, 0.2);

                    model.traverse((child) => {
                        if ((child as THREE.Mesh).isMesh) {
                            child.receiveShadow = true;
                            child.castShadow = true;
                        }
                    });
                    scene.add(model);
                },
                undefined,
                (error) => console.error("Error loading factory model:", error)
            );
        }

        // Load Pipeline (Stretched Content) - only if URL is provided
        if (pipelineModel) {
            loader.load(
                pipelineModel,
                (gltf) => {
                    const model = gltf.scene;

                    // Get original model bounding box
                    const originalBox = new THREE.Box3().setFromObject(model);
                    const originalSize = originalBox.getSize(new THREE.Vector3());
                    const originalCenter = originalBox.getCenter(new THREE.Vector3());

                    // Calculate scale factors to stretch model to fit target bounding box
                    const scaleX = targetSize.x / (originalSize.x || 1);
                    const scaleY = targetSize.y / (originalSize.y || 1);
                    const scaleZ = targetSize.z / (originalSize.z || 1);

                    // Apply non-uniform scale
                    model.scale.set(scaleX, scaleY, scaleZ);

                    // Position the model
                    model.position.set(
                        targetCenter.x - originalCenter.x * scaleX,
                        targetCenter.y - originalCenter.y * scaleY,
                        targetCenter.z - originalCenter.z * scaleZ
                    );

                    model.rotateX(Math.PI / 2);

                    model.traverse((child) => {
                        if ((child as THREE.Mesh).isMesh) {
                            child.castShadow = true;
                            child.receiveShadow = true;
                        }
                    });

                    scene.add(model);
                },
                undefined,
                (error) => console.error("Error loading pipeline model:", error)
            );
        }

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
            camera.aspect = w / h;
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
    }, [boundingboxStart, boundingboxEnd, factoryModel, pipelineModel]);

    return (
        <div
            ref={containerRef}
            className={`w-full h-full ${className}`}
            style={{ minHeight: "300px" }}
        />
    );
}
