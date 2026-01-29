import { Loader2 } from "lucide-react";
import clsx from "clsx";

import { MODULE_LOADING_META } from "./constants";

export const ModuleLoadingView = ({ module, progress }: { module: any; progress: number }) => {
    const meta = MODULE_LOADING_META[module.type] || {
        kicker: "Traitement en cours",
        description: "Préparation des livrables, veuillez patienter.",
        bullets: ["Analyse", "Génération", "Vérification"],
        accent: "from-indigo-600 via-violet-600 to-fuchsia-600",
        glow: "bg-fuchsia-500",
    };
    const Icon = module.icon;
    const safeProgress = Math.min(100, Math.max(0, progress));

    return (
        <div className="h-full w-full flex items-center justify-center p-10 bg-slate-50">
            <div className="w-full max-w-3xl bg-white border border-slate-200 rounded-[32px] overflow-hidden shadow-xl shadow-slate-200/50">
                <div className={clsx("p-10 text-white relative overflow-hidden bg-gradient-to-br", meta.accent)}>
                    <div className={clsx("absolute -top-20 -right-20 w-48 h-48 rounded-full blur-[80px] opacity-40", meta.glow)} />
                    <div className="relative z-10 flex items-start gap-5">
                        <div className="w-14 h-14 bg-white/15 rounded-2xl flex items-center justify-center border border-white/20">
                            <Icon size={28} />
                        </div>
                        <div>
                            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/70 mb-2">{meta.kicker}</div>
                            <h3 className="text-2xl font-black tracking-tight">{module.title}</h3>
                            <p className="text-white/90 mt-2 max-w-xl">{meta.description}</p>
                        </div>
                    </div>
                </div>
                <div className="p-8">
                    <div className="flex items-center gap-3 mb-6">
                        <Loader2 className="animate-spin text-indigo-600" size={20} />
                        <span className="text-sm font-bold text-slate-700">{module.statusText}</span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden mb-6">
                        <div className="h-full bg-indigo-600 animate-[progress_1.2s_ease-in-out_infinite]" style={{ width: "35%" }} />
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                        {meta.bullets.map((item) => (
                            <div key={item} className="bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 text-xs font-bold text-slate-600 text-center">
                                {item}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
