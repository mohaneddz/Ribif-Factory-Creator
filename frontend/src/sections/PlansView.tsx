"use client";

import React from "react";
import Simple3DViewer from "@/components/Simple3DViewer";
import SimpleDxfViewer from "@/components/SimpleDxfViewer";
import InteractiveImageViewer from "@/components/InteractiveImageViewer";

const Layout2DPanel = ({
    heightClass = "h-1/2",
    imageUrl,
}: {
    heightClass?: string;
    imageUrl?: string | null;
}) => (
    <div className={`${heightClass} relative bg-[#f8fafc] dark:bg-[#13141c] rounded-4xl overflow-hidden border border-slate-200 dark:border-white/10 transition-colors`}>
        <div className="absolute top-6 left-6 bg-indigo-600 text-white px-4 py-2 rounded-full text-xs font-bold z-10 shadow-lg shadow-indigo-200 dark:shadow-indigo-900/40">
            VUE 2D (PLAN D'IMPLANTATION)
        </div>
        <div className="h-full w-full flex items-center justify-center bg-[#f8fafc] dark:bg-[#13141c]">
            {imageUrl ? (
                imageUrl.toLowerCase().endsWith(".dxf") || imageUrl.toLowerCase().endsWith(".dwg") ? (
                    <SimpleDxfViewer url={imageUrl} />
                ) : (
                    <InteractiveImageViewer
                        src={imageUrl}
                        alt="Plan 2D"
                        className="w-full h-full"
                    />
                )
            ) : (
                <SimpleDxfViewer url="/deliverables/layout_square.dxf" />
            )}
        </div>
        {/* Scale indicator */}
        <div className="absolute bottom-6 right-6 flex items-center gap-2 bg-white/90 dark:bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 text-[10px] text-slate-500 dark:text-slate-400 font-medium">
            <div className="w-12 h-0.5 bg-slate-400 dark:bg-slate-500"></div>
            <span>10m</span>
        </div>
        <div className="absolute bottom-6 left-6 flex items-center gap-2 bg-white/90 dark:bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 text-[10px] text-slate-500 dark:text-slate-400 font-medium">
            layout_square.dxf
        </div>
    </div>
);

interface Model3DPanelProps {
    heightClass?: string;
    pipelineModelUrl?: string | null;
}

const Model3DPanel = ({ heightClass = "h-1/2", pipelineModelUrl }: Model3DPanelProps) => {
    const [factoryVersion, setFactoryVersion] = React.useState<1 | 2>(1);
    
    // Pipeline model URL from Supabase - no local fallback since it's dynamically generated
    const modelUrl = pipelineModelUrl || undefined;
    const modelName = pipelineModelUrl!
        ? pipelineModelUrl.split('/').pop() || "pipeline.glb"
        : null;

    const factoryModel = `/models/factory${factoryVersion}.glb`;

    return (
        <div className={`${heightClass} relative rounded-4xl overflow-hidden border border-slate-200 dark:border-white/10 bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900 transition-colors`}>
            <div className="absolute inset-0 opacity-40" style={{ backgroundImage: "radial-gradient(circle at 20% 20%, rgba(148,163,184,0.35) 0, transparent 45%), radial-gradient(circle at 80% 10%, rgba(99,102,241,0.3) 0, transparent 40%)" }} />
            <div className="absolute top-6 left-6 bg-white/90 dark:bg-white/10 backdrop-blur text-slate-800 dark:text-white px-4 py-2 rounded-full text-xs font-bold z-10 border border-slate-200 dark:border-white/10 shadow-sm dark:shadow-none">
                VUE 3D ISOMÉTRIQUE (GLB)
            </div>
            <div className="absolute top-6 right-6 flex gap-2 z-10">
                <button
                    onClick={() => setFactoryVersion(1)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                        factoryVersion === 1
                            ? 'bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-500/50'
                            : 'bg-white/90 dark:bg-white/10 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-white/10 hover:bg-white dark:hover:bg-white/20'
                    }`}
                >
                    Version 1
                </button>
                <button
                    onClick={() => setFactoryVersion(2)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                        factoryVersion === 2
                            ? 'bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-500/50'
                            : 'bg-white/90 dark:bg-white/10 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-white/10 hover:bg-white dark:hover:bg-white/20'
                    }`}
                >
                    Version 2
                </button>
            </div>
            <div className="h-full w-full relative">
                <Simple3DViewer
                    boundingboxStart={{ x: -10, y: 0, z: -5 }}
                    boundingboxEnd={{ x: 10, y: 5, z: 5 }}
                    factoryModel={factoryModel}
                    pipelineModel={modelUrl}
                />
                <div className="absolute bottom-6 left-6 bg-slate-900/80 dark:bg-black/50 text-white px-3 py-1.5 rounded-lg text-[10px] font-semibold border border-white/10">
                    {modelName
                        ? `factory${factoryVersion}.glb + ${modelName}`
                        : `factory${factoryVersion}.glb (awaiting pipeline model...)`
                    }
                </div>
            </div>
        </div>
    );
};

interface PlansViewProps {
    imageUrl?: string | null;
    pipelineModelUrl?: string | null;
}

export const PlansView = ({ imageUrl, pipelineModelUrl }: PlansViewProps) => (
    <div className="h-full flex flex-col gap-4 p-4 bg-slate-50 dark:bg-[#0b0c10] transition-colors">
        <Layout2DPanel imageUrl={imageUrl} />
        <Model3DPanel pipelineModelUrl={pipelineModelUrl} />
    </div>
);

export const Layout2DView = ({ imageUrl }: { imageUrl?: string | null }) => (
    <div className="h-full p-4 bg-slate-50 dark:bg-[#0b0c10] transition-colors">
        <Layout2DPanel heightClass="h-full" imageUrl={imageUrl} />
    </div>
);

interface Model3DViewProps {
    pipelineModelUrl?: string | null;
}

export const Model3DView = ({ pipelineModelUrl }: Model3DViewProps) => (
    <div className="h-full p-4 bg-slate-50 dark:bg-[#0b0c10] transition-colors">
        <Model3DPanel heightClass="h-full" pipelineModelUrl={pipelineModelUrl} />
    </div>
);
