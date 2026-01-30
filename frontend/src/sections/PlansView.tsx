"use client";
import { Canvas, useLoader } from "@react-three/fiber";
import { Bounds, OrbitControls } from "@react-three/drei";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import DxfParser from "dxf-parser";
import Scene1 from "@/components/three/scenes/Scene1";
import { useSceneSettings, useSceneThreeLogic } from "@/hooks/useSceneLogic";

const Layout2DPanel = ({
    heightClass = "h-1/2",
    imageUrl,
}: {
    heightClass?: string;
    imageUrl?: string | null;
}) => (
    <div className={`${heightClass} relative bg-white rounded-4xl overflow-hidden border border-slate-200`}>
        <div className="absolute top-6 left-6 bg-indigo-600 text-white px-4 py-2 rounded-full text-xs font-bold z-10 shadow-lg shadow-indigo-200">
            VUE 2D (PLAN D'IMPLANTATION)
        </div>
        <div className="absolute top-6 right-6 flex gap-2 z-10">
            <button className="bg-white/90 backdrop-blur text-slate-600 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                Étage RDC
            </button>
            <button className="bg-slate-100 text-slate-400 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                Étage 1
            </button>
        </div>
        <div className="h-full w-full flex items-center justify-center bg-slate-50">
            {imageUrl ? (
                imageUrl.toLowerCase().endsWith(".dxf") || imageUrl.toLowerCase().endsWith(".dwg") ? (
                    <DxfViewport url={imageUrl} />
                ) : (
                    <img
                        src={imageUrl}
                        alt="Plan 2D"
                        className="w-full h-full object-contain p-10"
                    />
                )
            ) : (
                <DxfViewport url="/deliverables/layout_square.dxf" />
            )}
        </div>
        {/* Scale indicator */}
        <div className="absolute bottom-6 right-6 flex items-center gap-2 bg-white/90 backdrop-blur px-3 py-1.5 rounded-lg border border-slate-200 text-[10px] text-slate-500 font-medium">
            <div className="w-12 h-0.5 bg-slate-400"></div>
            <span>10m</span>
        </div>
        <div className="absolute bottom-6 left-6 flex items-center gap-2 bg-white/90 backdrop-blur px-3 py-1.5 rounded-lg border border-slate-200 text-[10px] text-slate-500 font-medium">
            layout_square.dxf
        </div>
    </div>
);

const _buildLine = (points: THREE.Vector3[], material: THREE.LineBasicMaterial) => {
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    return new THREE.Line(geometry, material);
};

const _addPolyline = (group: THREE.Group, vertices: Array<{ x: number; y: number }>, closed: boolean, material: THREE.LineBasicMaterial) => {
    if (!vertices || vertices.length < 2) {
        return;
    }
    const points = vertices.map((v) => new THREE.Vector3(v.x, v.y, 0));
    if (closed) {
        points.push(points[0].clone());
    }
    group.add(_buildLine(points, material));
};

const _addCircle = (group: THREE.Group, center: { x: number; y: number }, radius: number, material: THREE.LineBasicMaterial) => {
    const curve = new THREE.EllipseCurve(center.x, center.y, radius, radius, 0, Math.PI * 2, false, 0);
    const points = curve.getPoints(64).map((p) => new THREE.Vector3(p.x, p.y, 0));
    group.add(_buildLine(points, material));
};

const _addArc = (
    group: THREE.Group,
    center: { x: number; y: number },
    radius: number,
    startAngleDeg: number,
    endAngleDeg: number,
    material: THREE.LineBasicMaterial
) => {
    const start = THREE.MathUtils.degToRad(startAngleDeg);
    const end = THREE.MathUtils.degToRad(endAngleDeg);
    const curve = new THREE.EllipseCurve(center.x, center.y, radius, radius, start, end, false, 0);
    const points = curve.getPoints(48).map((p) => new THREE.Vector3(p.x, p.y, 0));
    group.add(_buildLine(points, material));
};

const _buildGroupFromDxf = (dxf: any) => {
    const group = new THREE.Group();
    const material = new THREE.LineBasicMaterial({ color: "#1f2937", linewidth: 1 });
    const entities = Array.isArray(dxf?.entities) ? dxf.entities : [];

    entities.forEach((ent: any) => {
        const type = ent?.type;
        if (type === "LINE") {
            const points = [
                new THREE.Vector3(ent.start.x, ent.start.y, 0),
                new THREE.Vector3(ent.end.x, ent.end.y, 0),
            ];
            group.add(_buildLine(points, material));
        } else if (type === "LWPOLYLINE") {
            _addPolyline(group, ent.vertices || [], !!ent.closed, material);
        } else if (type === "POLYLINE") {
            const vertices = (ent.vertices || []).map((v: any) => ({ x: v.x, y: v.y }));
            _addPolyline(group, vertices, !!ent.closed, material);
        } else if (type === "CIRCLE") {
            _addCircle(group, ent.center, ent.radius, material);
        } else if (type === "ARC") {
            _addArc(group, ent.center, ent.radius, ent.startAngle, ent.endAngle, material);
        }
    });

    return group;
};

const DxfScene = ({ url }: { url: string }) => {
    const [group, setGroup] = useState<THREE.Group | null>(null);
    const ref = useRef<THREE.Group>(null);

    useEffect(() => {
        let active = true;
        const parser = new DxfParser();
        const loader = new THREE.FileLoader();
        loader.setResponseType("text");
        loader.load(
            url,
            (data) => {
                if (!active) {
                    return;
                }
                try {
                    const text = typeof data === "string" ? data : new TextDecoder().decode(data as ArrayBuffer);
                    const dxf = parser.parseSync(text);
                    const parsed = _buildGroupFromDxf(dxf);
                    setGroup(parsed);
                } catch {
                    setGroup(new THREE.Group());
                }
            },
            undefined,
            () => {
                if (active) {
                    setGroup(new THREE.Group());
                }
            }
        );
        return () => {
            active = false;
        };
    }, [url]);

    useLayoutEffect(() => {
        if (!group) {
            return;
        }
        group.traverse((child) => {
            if ((child as THREE.Line).isLine) {
                (child as THREE.Line).material = new THREE.LineBasicMaterial({
                    color: "#1f2937",
                    linewidth: 1,
                });
            }
        });
    }, [group]);

    const bounds = useMemo(() => {
        if (!group) {
            return { size: new THREE.Vector3(1, 1, 1), center: new THREE.Vector3(0, 0, 0) };
        }
        const box = new THREE.Box3().setFromObject(group);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        return { size, center };
    }, [group]);

    if (!group) {
        return null;
    }

    return (
        <group ref={ref} position={[-bounds.center.x, -bounds.center.y, 0]}>
            <primitive object={group} />
        </group>
    );
};

const DxfViewport = ({ url }: { url: string }) => (
    <div className="w-full h-full">
        <Canvas
            orthographic
            camera={{ position: [0, 0, 80], zoom: 30, near: 0.1, far: 2000 }}
            className="bg-slate-50"
        >
            <color attach="background" args={["#f8fafc"]} />
            <ambientLight intensity={0.8} />
            <gridHelper args={[200, 20, "#e2e8f0", "#e2e8f0"]} rotation={[Math.PI / 2, 0, 0]} position={[0, 0, -0.1]} />
            <Bounds fit clip observe margin={1.2}>
                <DxfScene url={url} />
            </Bounds>
            <OrbitControls enableRotate={false} enableDamping dampingFactor={0.1} />
        </Canvas>
    </div>
);

const Scene1Preview = () => {
    const settings = useSceneSettings();
    const threeLogic = useSceneThreeLogic();
    const logic = { ...settings, ...threeLogic, activeCam: 0 };
    return <Scene1 logic={logic} />;
};

const Model3DPanel = ({ heightClass = "h-1/2" }: { heightClass?: string }) => (
    <div className={`${heightClass} relative rounded-4xl overflow-hidden border border-slate-200 bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900`}>
        <div className="absolute inset-0 opacity-40" style={{ backgroundImage: "radial-gradient(circle at 20% 20%, rgba(148,163,184,0.35) 0, transparent 45%), radial-gradient(circle at 80% 10%, rgba(99,102,241,0.3) 0, transparent 40%)" }} />
        <div className="absolute top-6 left-6 bg-white/90 backdrop-blur text-slate-800 px-4 py-2 rounded-full text-xs font-bold z-10 border border-slate-200 shadow-sm">
            VUE 3D ISOMÉTRIQUE (GLB)
        </div>
        <div className="absolute top-6 right-6 flex gap-2 z-10">
            <button className="bg-white/90 backdrop-blur text-slate-600 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                Rotation
            </button>
            <button className="bg-white/90 backdrop-blur text-slate-600 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                Reset
            </button>
        </div>
        <div className="h-full w-full relative">
            <Canvas shadows camera={{ position: [0.7, 1.78, -3], fov: 45 }}>
                <Scene1Preview />
            </Canvas>
            <div className="absolute bottom-6 left-6 bg-slate-900/80 text-white px-3 py-1.5 rounded-lg text-[10px] font-semibold border border-white/10">
                factory1.glb • Scene 1
            </div>
        </div>
    </div>
);

export const PlansView = ({ imageUrl }: { imageUrl?: string | null }) => (
    <div className="h-full flex flex-col gap-4 p-4">
        <Layout2DPanel imageUrl={imageUrl} />
        <Model3DPanel />
    </div>
);

export const Layout2DView = ({ imageUrl }: { imageUrl?: string | null }) => (
    <div className="h-full p-4">
        <Layout2DPanel heightClass="h-full" imageUrl={imageUrl} />
    </div>
);

export const Model3DView = () => (
    <div className="h-full p-4">
        <Model3DPanel heightClass="h-full" />
    </div>
);
