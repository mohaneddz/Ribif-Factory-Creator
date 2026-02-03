'use client';

import React, { useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';

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
    title = 'Une erreur s\'est produite',
    message = 'Une erreur inattendue s\'est produite lors du traitement.',
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
                <div className="max-w-lg w-full bg-white/10 dark:bg-white/5 backdrop-blur-lg rounded-xl border border-white/20 dark:border-white/10 shadow-xl p-6">
                    <div className="flex items-start gap-4">
                        <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0">
                            <AlertCircle className="w-5 h-5 text-red-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-1">
                                {title}
                            </h3>
                            <p className="text-sm text-slate-600 dark:text-slate-300 mb-3">
                                {errorMessage}
                            </p>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleRetry}
                                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg flex items-center gap-2 transition-all"
                                >
                                    <RefreshCw className="w-4 h-4" />
                                    Réessayer
                                </button>
                                <button
                                    onClick={() => setShowDetails(!showDetails)}
                                    className="px-4 py-2 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 text-sm font-medium rounded-lg transition-all"
                                >
                                    Détails
                                </button>
                            </div>
                            {showDetails && (
                                <div className="mt-3 bg-slate-900/80 dark:bg-slate-950/50 rounded-lg p-3 border border-slate-700 dark:border-slate-800 max-h-48 overflow-auto">
                                    <pre className="text-xs text-slate-200 whitespace-pre-wrap font-mono">
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
        <div className={`min-h-screen w-full fixed inset-0 flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900 p-6 z-50 ${className}`}>
            <div className="max-w-lg w-full bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 shadow-2xl p-8">
                {/* Icon and Title */}
                <div className="flex flex-col items-center text-center mb-6">
                    <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mb-4">
                        <AlertCircle className="w-8 h-8 text-red-400" />
                    </div>
                    <h3 className="text-2xl font-bold text-white mb-2">
                        {title}
                    </h3>
                    <p className="text-white/60 text-sm">
                        {message}
                    </p>
                </div>

                {/* Error Message */}
                <div className="mb-6">
                    <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                        <p className="text-red-200 text-sm font-medium">
                            {errorMessage}
                        </p>
                    </div>
                </div>

                {/* Toggle Details Button */}
                <button
                    onClick={() => setShowDetails(!showDetails)}
                    className="w-full mb-4 px-4 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-white/80 text-sm font-medium flex items-center justify-between transition-all group"
                >
                    <span>Détails techniques</span>
                    {showDetails ? (
                        <ChevronUp className="w-4 h-4 group-hover:translate-y-[-2px] transition-transform" />
                    ) : (
                        <ChevronDown className="w-4 h-4 group-hover:translate-y-[2px] transition-transform" />
                    )}
                </button>

                {/* Error Details (Collapsible) */}
                {showDetails && (
                    <div className="mb-6 bg-slate-900/50 rounded-lg p-4 border border-white/10 max-h-64 overflow-auto">
                        <pre className="text-xs text-white/70 whitespace-pre-wrap font-mono">
                            {errorDetails}
                        </pre>
                    </div>
                )}

                {/* Retry Button */}
                <button
                    onClick={handleRetry}
                    className="w-full px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg flex items-center justify-center gap-2 transition-all shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98]"
                >
                    <RefreshCw className="w-4 h-4" />
                    Réessayer
                </button>

                {/* Help Text */}
                <p className="text-center text-white/40 text-xs mt-4">
                    Si le problème persiste, contactez le support technique
                </p>
            </div>
        </div>
    );
};

export default ErrorDisplay;
export { ErrorDisplay };