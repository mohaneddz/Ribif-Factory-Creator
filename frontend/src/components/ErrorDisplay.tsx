'use client';

import React, { useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp, RefreshCw, Sparkles, Lightbulb, Zap } from 'lucide-react';

interface ErrorDisplayProps {
    error: Error | string | unknown | null;
    errorInfo?: React.ErrorInfo | null;
    onReset?: () => void;
    onRetry?: () => void;
    title?: string;
    message?: string;
    className?: string;
    compact?: boolean;
}

const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
    error,
    errorInfo,
    onReset,
    onRetry,
    title = 'Oups ! Un petit accroc',
    message = 'Pas de panique ! Cela arrive parfois. Un simple réessai suffit généralement à résoudre le problème.',
    className = '',
    compact = false,
}) => {
    const [showDetails, setShowDetails] = useState(false);

    const handleRetry = () => {
        if (onRetry) {
            onRetry();
        } else if (onReset) {
            onReset();
        } else {
            window.location.reload();
        }
    };

    const errorMessage = typeof error === 'string' 
        ? error 
        : error instanceof Error 
            ? error.message 
            : error && typeof error === 'object' && 'message' in error
                ? String((error as any).message)
                : 'Une erreur inconnue s\'est produite';

    const errorDetails = error instanceof Error
        ? `${error.toString()}\n\n${error.stack || ''}\n\n${errorInfo?.componentStack || ''}`
        : typeof error === 'object' && error !== null
            ? JSON.stringify(error, null, 2)
            : String(error || 'Aucun détail disponible');

    if (compact) {
        return (
            <div className={`flex items-center justify-center p-6 ${className}`}>
                <div className="max-w-lg w-full bg-gradient-to-br from-white/15 to-white/5 dark:from-white/10 dark:to-white/5 backdrop-blur-lg rounded-2xl border border-white/20 dark:border-white/10 shadow-xl p-6">
                    <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-amber-500/20">
                            <Lightbulb className="w-6 h-6 text-white" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-1">
                                {title}
                            </h3>
                            <p className="text-sm text-slate-600 dark:text-slate-300 mb-4">
                                {errorMessage}
                            </p>
                            <div className="flex flex-wrap gap-2">
                                <button
                                    onClick={handleRetry}
                                    className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-sm font-bold rounded-xl flex items-center gap-2 transition-all shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 hover:scale-[1.02] active:scale-[0.98]"
                                >
                                    <RefreshCw className="w-4 h-4" />
                                    Réessayer maintenant
                                </button>
                                <button
                                    onClick={() => setShowDetails(!showDetails)}
                                    className="px-4 py-2.5 bg-slate-200/80 dark:bg-slate-700/80 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 text-sm font-medium rounded-xl transition-all"
                                >
                                    {showDetails ? 'Masquer' : 'Détails'}
                                </button>
                            </div>
                            {showDetails && (
                                <div className="mt-4 bg-slate-900/80 dark:bg-slate-950/50 rounded-xl p-4 border border-slate-700 dark:border-slate-800 max-h-48 overflow-auto">
                                    <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono">
                                        {errorDetails}
                                    </pre>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className={`min-h-screen w-full fixed inset-0 flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-purple-950 p-6 z-50 ${className}`}>
            {/* Animated background decorations */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-500/20 rounded-full blur-[120px] animate-pulse" />
                <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }} />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-500/10 rounded-full blur-[150px]" />
            </div>
            
            <div className="relative max-w-lg w-full bg-white/10 backdrop-blur-xl rounded-3xl border border-white/20 shadow-2xl p-8 overflow-hidden">
                {/* Decorative gradient border effect */}
                <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-indigo-500/20 via-transparent to-purple-500/20 pointer-events-none" />
                
                <div className="relative z-10">
                    {/* Icon and Title */}
                    <div className="flex flex-col items-center text-center mb-8">
                        {/* Animated icon container */}
                        <div className="relative mb-6">
                            <div className="absolute inset-0 w-20 h-20 bg-gradient-to-br from-amber-400 to-orange-500 rounded-2xl blur-xl opacity-40 animate-pulse" />
                            <div className="relative w-20 h-20 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-2xl shadow-amber-500/30">
                                <Sparkles className="w-10 h-10 text-white" />
                            </div>
                        </div>
                        
                        <h3 className="text-2xl font-bold text-white mb-3">
                            {title}
                        </h3>
                        <p className="text-white/70 text-base leading-relaxed max-w-sm">
                            {message}
                        </p>
                    </div>

                    {/* Encouraging tips */}
                    <div className="mb-6 bg-white/5 backdrop-blur rounded-2xl p-4 border border-white/10">
                        <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                                <Zap className="w-4 h-4 text-emerald-400" />
                            </div>
                            <div>
                                <p className="text-emerald-300 text-sm font-medium mb-1">Astuce rapide</p>
                                <p className="text-white/60 text-sm">
                                    La plupart des erreurs sont temporaires. Cliquez sur réessayer et tout devrait rentrer dans l&apos;ordre !
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Error Message (collapsed by default) */}
                    <button
                        onClick={() => setShowDetails(!showDetails)}
                        className="w-full mb-6 px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-white/80 text-sm font-medium flex items-center justify-between transition-all group"
                    >
                        <span className="flex items-center gap-2">
                            <AlertCircle className="w-4 h-4 text-white/50" />
                            Voir les détails techniques
                        </span>
                        {showDetails ? (
                            <ChevronUp className="w-4 h-4 group-hover:translate-y-[-2px] transition-transform" />
                        ) : (
                            <ChevronDown className="w-4 h-4 group-hover:translate-y-[2px] transition-transform" />
                        )}
                    </button>

                    {/* Error Details (Collapsible) */}
                    {showDetails && (
                        <div className="mb-6 space-y-3">
                            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                                <p className="text-red-200 text-sm font-medium">
                                    {errorMessage}
                                </p>
                            </div>
                            <div className="bg-slate-900/50 rounded-xl p-4 border border-white/10 max-h-48 overflow-auto">
                                <pre className="text-xs text-white/60 whitespace-pre-wrap font-mono">
                                    {errorDetails}
                                </pre>
                            </div>
                        </div>
                    )}

                    {/* Retry Button - Made more prominent */}
                    <button
                        onClick={handleRetry}
                        className="w-full px-6 py-4 bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:via-indigo-400 hover:to-purple-500 text-white font-bold rounded-xl flex items-center justify-center gap-3 transition-all shadow-xl shadow-indigo-500/30 hover:shadow-indigo-500/50 hover:scale-[1.02] active:scale-[0.98] group"
                    >
                        <RefreshCw className="w-5 h-5 group-hover:rotate-180 transition-transform duration-500" />
                        <span className="text-lg">Réessayer maintenant</span>
                    </button>

                    {/* Help Text - More encouraging */}
                    <div className="text-center mt-6 space-y-2">
                        <p className="text-white/50 text-sm">
                            Besoin d&apos;aide ? Notre équipe est là pour vous
                        </p>
                        <p className="text-indigo-400/70 text-xs font-medium">
                            support@allomaison.com
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ErrorDisplay;
export { ErrorDisplay };