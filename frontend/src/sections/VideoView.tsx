import { Film, Loader2, Play, Sparkles } from "lucide-react";

export const VideoView = ({ progress, videoUrl }: { progress: number; videoUrl?: string | null }) => {
    const hasVideo = Boolean(videoUrl);

    const renderContent = () => {
        if (hasVideo) {
            return (
                <video
                    className="h-full w-full object-cover"
                    src={videoUrl as string}
                    controls
                    playsInline
                />
            );
        }

        return (
            <div className="relative h-full w-full flex items-center justify-center">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-slate-800 to-indigo-900" />
                <div className="absolute inset-0 opacity-30" style={{ backgroundImage: "radial-gradient(circle at 20% 20%, rgba(99,102,241,0.6) 0, transparent 45%), radial-gradient(circle at 80% 0%, rgba(244,114,182,0.4) 0, transparent 40%)" }} />
                <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.08)_1px,transparent_1px),linear-gradient(180deg,rgba(255,255,255,0.06)_1px,transparent_1px)] bg-[length:32px_32px] opacity-20" />
                <div className="relative z-10 flex flex-col items-center gap-4 text-center">
                    <div className="w-20 h-20 bg-white/10 rounded-2xl flex items-center justify-center text-white border border-white/20 backdrop-blur">
                        {progress < 100 ? <Loader2 className="animate-spin" size={32} /> : <Play className="ml-1" size={32} />}
                    </div>
                    <div>
                        <div className="text-sm font-bold text-white">Simulation Extérieure 3D</div>
                        <div className="text-xs text-slate-200/80">Placeholder rendu architectural</div>
                    </div>
                </div>
            </div>
        );
    };

    const renderSecondaryContent = () => {
        if (hasVideo) {
            return (
                <video
                    className="h-full w-full object-cover"
                    src={videoUrl as string}
                    controls
                    playsInline
                />
            );
        }

        return (
            <div className="relative h-full w-full flex items-center justify-center">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-slate-100 to-indigo-50" />
                <div className="absolute inset-0 opacity-50" style={{ backgroundImage: "radial-gradient(circle at 20% 80%, rgba(99,102,241,0.18) 0, transparent 45%), radial-gradient(circle at 80% 20%, rgba(14,165,233,0.18) 0, transparent 40%)" }} />
                <div className="absolute inset-0 border border-dashed border-indigo-200/60 rounded-4xl" />
                <div className="relative z-10 flex flex-col items-center gap-4 text-center">
                    <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center text-indigo-500 border border-indigo-100 shadow-sm">
                        {progress < 100 ? <Loader2 className="animate-spin" size={28} /> : <Play className="ml-1" size={28} />}
                    </div>
                    <div>
                        <div className="text-sm font-bold text-slate-700">Visite Virtuelle Usine</div>
                        <div className="text-xs text-slate-500">Storyboard intérieur (placeholder)</div>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="h-full p-4 flex flex-col gap-4">
            <div className="h-full bg-white rounded-4xl relative overflow-hidden flex items-center justify-center group cursor-pointer border border-slate-200 hover:border-indigo-300 transition-all">
                <div className="absolute top-6 left-6 bg-white/90 text-slate-800 px-4 py-2 rounded-full text-xs font-bold z-10 border border-slate-200 shadow-sm flex items-center gap-2">
                    <Film size={12} className="text-indigo-600" />
                    SIMULATION CINÉMATIQUE
                </div>
                {renderContent()}
                {!hasVideo && (
                    <div className="absolute bottom-6 left-6 right-6">
                        <div className="flex items-center justify-between text-[10px] font-semibold text-white/80 mb-2">
                            <span>Génération de la vidéo</span>
                            <span>{Math.min(100, Math.round(progress))}%</span>
                        </div>
                        <div className="h-1.5 bg-white/20 rounded-full overflow-hidden">
                            <div className="h-full bg-white/80 rounded-full" style={{ width: `${Math.min(100, Math.max(12, progress))}%` }} />
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
