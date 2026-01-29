"use client";
import { Canvas } from "@react-three/fiber";
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
                <img
                    src={imageUrl}
                    alt="Plan 2D"
                    className="w-full h-full object-contain p-10"
                />
            ) : (
                <svg viewBox="0 0 400 300" className="w-full h-full max-w-3xl p-10">
                    {/* Background Grid */}
                    <defs>
                        <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e2e8f0" strokeWidth="0.5" />
                        </pattern>
                    </defs>
                    <rect width="400" height="300" fill="url(#grid)" />

                    {/* Main Factory Building */}
                    <rect x="40" y="40" width="200" height="150" fill="#e0e7ff" stroke="#4f46e5" strokeWidth="2" rx="4" />
                    <text x="140" y="120" textAnchor="middle" className="text-[10px] font-bold fill-indigo-700">ZONE PRODUCTION</text>

                    {/* Warehouse */}
                    <rect x="260" y="40" width="100" height="80" fill="#dcfce7" stroke="#22c55e" strokeWidth="2" rx="4" />
                    <text x="310" y="85" textAnchor="middle" className="text-[8px] font-bold fill-emerald-700">STOCKAGE</text>

                    {/* Office Area */}
                    <rect x="260" y="130" width="100" height="60" fill="#fef3c7" stroke="#f59e0b" strokeWidth="2" rx="4" />
                    <text x="310" y="165" textAnchor="middle" className="text-[8px] font-bold fill-amber-700">BUREAUX</text>

                    {/* Machines Representation */}
                    <rect x="60" y="60" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <rect x="100" y="60" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <rect x="140" y="60" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <rect x="180" y="60" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />

                    <rect x="60" y="130" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <rect x="100" y="130" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <rect x="140" y="130" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <rect x="180" y="130" width="30" height="40" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />

                    {/* Flow Arrows */}
                    <path d="M 95 80 L 95 80" stroke="#4f46e5" strokeWidth="1" markerEnd="url(#arrow)" />

                    {/* Legend */}
                    <rect x="40" y="220" width="12" height="12" fill="#818cf8" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <text x="58" y="230" className="text-[8px] fill-slate-600">Machines</text>

                    <rect x="120" y="220" width="12" height="12" fill="#e0e7ff" stroke="#4f46e5" strokeWidth="1" rx="2" />
                    <text x="138" y="230" className="text-[8px] fill-slate-600">Production</text>

                    <rect x="200" y="220" width="12" height="12" fill="#dcfce7" stroke="#22c55e" strokeWidth="1" rx="2" />
                    <text x="218" y="230" className="text-[8px] fill-slate-600">Stockage</text>

                    <rect x="280" y="220" width="12" height="12" fill="#fef3c7" stroke="#f59e0b" strokeWidth="1" rx="2" />
                    <text x="298" y="230" className="text-[8px] fill-slate-600">Bureaux</text>
                </svg>
            )}
        </div>
        {/* Scale indicator */}
        <div className="absolute bottom-6 right-6 flex items-center gap-2 bg-white/90 backdrop-blur px-3 py-1.5 rounded-lg border border-slate-200 text-[10px] text-slate-500 font-medium">
            <div className="w-12 h-0.5 bg-slate-400"></div>
            <span>10m</span>
        </div>
    </div>
);

const Scene1Preview = () => {
    const settings = useSceneSettings();
    const threeLogic = useSceneThreeLogic();
    const logic = { ...settings, ...threeLogic, activeCam: 0 };
    return <Scene1 logic={logic} />;
};

const Model3DPanel = ({ heightClass = "h-1/2" }: { heightClass?: string }) => (
    <div className={`${heightClass} relative bg-slate-100 rounded-4xl overflow-hidden border border-slate-200`}>
        <div className="absolute top-6 left-6 bg-white/90 backdrop-blur text-slate-800 px-4 py-2 rounded-full text-xs font-bold z-10 border border-slate-200 shadow-sm">
            VUE 3D ISOMÉTRIQUE (IFC)
        </div>
        <div className="absolute top-6 right-6 flex gap-2 z-10">
            <button className="bg-white/90 backdrop-blur text-slate-600 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                Rotation
            </button>
            <button className="bg-white/90 backdrop-blur text-slate-600 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                Reset
            </button>
        </div>
        <div className="h-full w-full">
            <Canvas shadows camera={{ position: [0.7, 1.78, -3], fov: 45 }}>
                <Scene1Preview />
            </Canvas>
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
