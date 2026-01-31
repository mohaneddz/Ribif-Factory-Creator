"use client";

import Simple3DViewer from "@/components/Simple3DViewer";
import SimpleDxfViewer from "@/components/SimpleDxfViewer";

const Layout2DPanel = ({
    heightClass = "h-1/2",
    imageUrl,
}: {
    heightClass?: string;
    imageUrl?: string | null;
}) => (
    <div className={`${heightClass} relative bg-[#f8fafc] rounded-4xl overflow-hidden border border-slate-200`}>
        <div className="absolute top-6 left-6 bg-indigo-600 text-white px-4 py-2 rounded-full text-xs font-bold z-10 shadow-lg shadow-indigo-200">
            VUE 2D (PLAN D'IMPLANTATION)
        </div>
        <div className="h-full w-full flex items-center justify-center bg-[#f8fafc]">
            {imageUrl ? (
                imageUrl.toLowerCase().endsWith(".dxf") || imageUrl.toLowerCase().endsWith(".dwg") ? (
                    <SimpleDxfViewer url={imageUrl} />
                ) : (
                    <img
                        src={imageUrl}
                        alt="Plan 2D"
                        className="w-full h-full object-contain p-10"
                    />
                )
            ) : (
                <SimpleDxfViewer url="/deliverables/layout_square.dxf" />
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

interface Model3DPanelProps {
    heightClass?: string;
    pipelineModelUrl?: string | null;
}

const Model3DPanel = ({ heightClass = "h-1/2", pipelineModelUrl }: Model3DPanelProps) => {
    // Pipeline model URL from Supabase - no local fallback since it's dynamically generated
    const modelUrl = pipelineModelUrl || undefined;
    const modelName = pipelineModelUrl 
        ? pipelineModelUrl.split('/').pop() || "pipeline.glb"
        : null;
    
    return (
        <div className={`${heightClass} relative rounded-4xl overflow-hidden border border-slate-200 bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900`}>
            <div className="absolute inset-0 opacity-40" style={{ backgroundImage: "radial-gradient(circle at 20% 20%, rgba(148,163,184,0.35) 0, transparent 45%), radial-gradient(circle at 80% 10%, rgba(99,102,241,0.3) 0, transparent 40%)" }} />
            <div className="absolute top-6 left-6 bg-white/90 backdrop-blur text-slate-800 px-4 py-2 rounded-full text-xs font-bold z-10 border border-slate-200 shadow-sm">
                VUE 3D ISOMÉTRIQUE (GLB)
            </div>
            <div className="h-full w-full relative">
                <Simple3DViewer
                    boundingboxStart={{ x: -5, y: 0, z: -5 }}
                    boundingboxEnd={{ x: 5, y: 5, z: 0 }}
                    factoryModel="/models/factory1.glb"
                    pipelineModel={modelUrl}
                />
                <div className="absolute bottom-6 left-6 bg-slate-900/80 text-white px-3 py-1.5 rounded-lg text-[10px] font-semibold border border-white/10">
                    {modelName 
                        ? `factory1.glb + ${modelName}`
                        : "factory1.glb (awaiting pipeline model...)"
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
    <div className="h-full flex flex-col gap-4 p-4">
        <Layout2DPanel imageUrl={imageUrl} />
        <Model3DPanel pipelineModelUrl={pipelineModelUrl} />
    </div>
);

export const Layout2DView = ({ imageUrl }: { imageUrl?: string | null }) => (
    <div className="h-full p-4">
        <Layout2DPanel heightClass="h-full" imageUrl={imageUrl} />
    </div>
);

interface Model3DViewProps {
    pipelineModelUrl?: string | null;
}

export const Model3DView = ({ pipelineModelUrl }: Model3DViewProps) => (
    <div className="h-full p-4">
        <Model3DPanel heightClass="h-full" pipelineModelUrl={pipelineModelUrl} />
    </div>
);
