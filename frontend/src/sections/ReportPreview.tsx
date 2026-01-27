import { motion } from "framer-motion";
import { Download, FileSearch } from "lucide-react";

export const ReportPreview = ({ module }: { module: any }) => (
    <div className="h-full flex items-center justify-center p-12 bg-slate-50/50 dark:bg-[#0b0c10] transition-colors">
        <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="w-full max-w-lg aspect-[1/1.41] bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/10 rounded-3xl p-10 relative flex flex-col shadow-xl shadow-slate-200/50 dark:shadow-none transition-colors">
            <div className="absolute top-8 right-8 text-[9px] font-bold text-slate-300 dark:text-slate-600 uppercase tracking-widest">Ref: #RB-2025-X</div>
            <div className="flex items-center gap-5 mb-10 border-b border-slate-100 dark:border-white/10 pb-8">
                <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-200 dark:shadow-indigo-900/40">
                    <FileSearch size={24} />
                </div>
                <div>
                    <h1 className="text-xl font-black text-slate-900 dark:text-white uppercase tracking-tight">{module.title}</h1>
                    <p className="text-xs text-slate-400 dark:text-slate-500 font-bold mt-0.5">{module.file}</p>
                </div>
            </div>
            <div className="space-y-6 flex-1 opacity-50">
                <div className="h-3 bg-slate-100 dark:bg-white/10 rounded-full w-3/4" />
                <div className="h-3 bg-slate-100 dark:bg-white/10 rounded-full w-1/2" />
                <div className="py-6 space-y-4">
                    <div className="h-24 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5" />
                    <div className="h-24 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5" />
                </div>
            </div>
            <div className="mt-auto pt-8 border-t border-slate-50 dark:border-white/5 text-center">
                <button className="w-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 py-3 rounded-xl text-xs font-bold flex items-center justify-center gap-2 hover:bg-indigo-600 dark:hover:bg-slate-200 transition-colors">
                    <Download size={14} /> TÉLÉCHARGER LE PDF
                </button>
            </div>
        </motion.div>
    </div>
);
