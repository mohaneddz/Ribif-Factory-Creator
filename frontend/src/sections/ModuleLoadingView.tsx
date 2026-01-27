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

    const activeBulletIndex = meta.bullets.findIndex((_, index) => {
        const stepThreshold = ((index + 1) / meta.bullets.length) * 100;
        const prevThreshold = (index / meta.bullets.length) * 100;
        return safeProgress >= prevThreshold && safeProgress < stepThreshold;
    });
    const currentStatusText = activeBulletIndex !== -1 ? meta.bullets[activeBulletIndex] + "..." : module.statusText;

    return (
        <div className="h-full w-full flex items-center justify-center p-10 bg-slate-50 dark:bg-[#0b0c10] transition-colors">
            <div className="w-full max-w-3xl bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/10 rounded-4xl overflow-hidden shadow-xl shadow-slate-200/50 dark:shadow-black/30">
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
                        <Loader2 className="animate-spin text-indigo-600 dark:text-indigo-400" size={20} />
                        <span className="text-sm font-bold text-slate-700 dark:text-slate-200">{currentStatusText}</span>
                    </div>
                    <div className="h-2 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden mb-6">
                        <div className="h-full bg-indigo-600 dark:bg-indigo-500 transition-all duration-700 ease-out" style={{ width: `${safeProgress}%` }} />
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                        {meta.bullets.map((item, index) => {
                            const stepThreshold = ((index + 1) / meta.bullets.length) * 100;
                            const prevThreshold = (index / meta.bullets.length) * 100;
                            const isActive = safeProgress >= prevThreshold && safeProgress < stepThreshold;
                            const isCompleted = safeProgress >= stepThreshold;

                            return (
                                <div key={item} className={clsx(
                                    "border rounded-xl px-4 py-3 text-xs font-bold text-center transition-all duration-300",
                                    isActive ? "bg-indigo-50 dark:bg-indigo-500/10 border-indigo-200 dark:border-indigo-500/20 text-indigo-700 dark:text-indigo-300 shadow-sm scale-105" :
                                    isCompleted ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-300 opacity-80" :
                                    "bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/5 text-slate-400 dark:text-slate-500"
                                )}>
                                    {isCompleted && <span className="mr-1">✓</span>}
                                    {item}
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
};
