"use client";

import { motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";

interface UploadProgressProps {
    progress: number;
    status: string;
    isComplete?: boolean;
    isError?: boolean;
}

export const UploadProgress = ({ progress, status, isComplete, isError }: UploadProgressProps) => {
    return (
        <div className="w-full">
            <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{status}</span>
                <span className="text-sm text-slate-500 dark:text-slate-400">{Math.round(progress)}%</span>
            </div>
            <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.3 }}
                    className={`h-full rounded-full ${isError
                            ? "bg-red-500"
                            : isComplete
                                ? "bg-emerald-500"
                                : "bg-gradient-to-r from-indigo-500 to-purple-500"
                        }`}
                />
            </div>
            {isComplete && !isError && (
                <motion.div
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-2 mt-3 text-emerald-600 dark:text-emerald-400"
                >
                    <Check size={16} />
                    <span className="text-sm font-medium">Upload terminé</span>
                </motion.div>
            )}
            {!isComplete && !isError && progress < 100 && (
                <div className="flex items-center gap-2 mt-3 text-indigo-600 dark:text-indigo-300">
                    <Loader2 size={16} className="animate-spin" />
                    <span className="text-sm">Traitement en cours...</span>
                </div>
            )}
        </div>
    );
};
