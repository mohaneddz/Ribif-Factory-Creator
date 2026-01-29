import { Loader2, Play } from "lucide-react";

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
            <div className="flex flex-col items-center gap-4">
                <div className="w-20 h-20 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600 border border-indigo-100 group-hover:bg-indigo-600 group-hover:text-white transition-all">
                    {progress < 100 ? <Loader2 className="animate-spin" size={32} /> : <Play className="ml-1" size={32} />}
                </div>
                <div className="text-center">
                    <div className="text-sm font-bold text-slate-700">Simulation Extérieure 3D</div>
                    <div className="text-xs text-slate-400">Rendu architectural du bâtiment</div>
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
            <div className="flex flex-col items-center gap-4">
                <div className="w-20 h-20 bg-white rounded-2xl flex items-center justify-center text-slate-400 border border-slate-200 group-hover:bg-indigo-600 group-hover:text-white group-hover:border-indigo-600 transition-all">
                    {progress < 100 ? <Loader2 className="animate-spin" size={32} /> : <Play className="ml-1" size={32} />}
                </div>
                <div className="text-center">
                    <div className="text-sm font-bold text-slate-700">Visite Virtuelle Usine</div>
                    <div className="text-xs text-slate-400">Parcours interactif des installations</div>
                </div>
            </div>
        );
    };

    return (
        <div className="h-full p-4 flex flex-col gap-4">
        {/* Top Section - Exterior View */}
        <div className="h-1/2 bg-white rounded-4xl relative overflow-hidden flex items-center justify-center group cursor-pointer border border-slate-200 hover:border-indigo-300 transition-all">
            <div className="absolute top-6 left-6 bg-slate-100 text-slate-700 px-4 py-2 rounded-full text-xs font-bold z-10 border border-slate-200">
                VUE EXTÉRIEURE
            </div>
            <div className="absolute top-6 right-6 flex gap-2 z-10">
                <button className="bg-white text-slate-600 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                    Façade Nord
                </button>
                <button className="bg-slate-50 text-slate-400 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                    Façade Sud
                </button>
            </div>
            {renderContent()}
        </div>

        {/* Bottom Section - Interior View */}
        <div className="h-1/2 bg-slate-50 rounded-4xl relative overflow-hidden flex items-center justify-center group cursor-pointer border border-slate-200 hover:border-indigo-300 transition-all">
            <div className="absolute top-6 left-6 bg-white text-slate-700 px-4 py-2 rounded-full text-xs font-bold z-10 border border-slate-200">
                VUE INTÉRIEURE
            </div>
            <div className="absolute top-6 right-6 flex gap-2 z-10">
                <button className="bg-white text-slate-600 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                    Zone Production
                </button>
                <button className="bg-slate-100 text-slate-400 px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-200 hover:border-indigo-300 transition-colors">
                    Stockage
                </button>
            </div>
            {renderSecondaryContent()}
        </div>
    </div>
    );
};
