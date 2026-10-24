import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import HTMLFlipBook from "react-pageflip";
import { BookOpen, ChevronLeft, ChevronRight, Download, Loader2, CheckCircle2, Sparkles, FileText } from "lucide-react";
import clsx from "clsx";
import { ErrorDisplay } from "@/components/ErrorDisplay";

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "";

const Page = React.forwardRef<HTMLDivElement, { pageNum: number; pdfDoc: any; scale: number }>(
    ({ pageNum, pdfDoc, scale }, ref) => {
        const canvasRef = useRef<HTMLCanvasElement>(null);
        const renderTaskRef = useRef<any>(null);
        const [rendered, setRendered] = useState(false);
        const renderQueueRef = useRef<Promise<void>>(Promise.resolve());
        const isUnmountedRef = useRef<boolean>(false);

        useEffect(() => {
            if (!pdfDoc || !canvasRef.current) return;

            isUnmountedRef.current = false;
            // Reset the loaded flag before re-rendering a new page onto the canvas
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setRendered(false);

            const renderPage = async () => {
                try {
                    // If a render is in progress, cancel and await it before starting a new one
                    if (renderTaskRef.current) {
                        try {
                            renderTaskRef.current.cancel();
                            await renderTaskRef.current.promise;
                        } catch (e) {
                            // Ignore cancel errors
                        }
                        renderTaskRef.current = null;
                    }

                    if (isUnmountedRef.current) return;

                    const page = await pdfDoc.getPage(pageNum);
                    if (isUnmountedRef.current) return;

                    const viewport = page.getViewport({ scale });
                    const canvas = canvasRef.current;
                    if (!canvas) return;

                    const context = canvas.getContext('2d');
                    if (!context) return;

                    canvas.height = viewport.height;
                    canvas.width = viewport.width;
                    context.clearRect(0, 0, canvas.width, canvas.height);

                    const renderTask = page.render({
                        canvasContext: context,
                        viewport: viewport
                    });
                    renderTaskRef.current = renderTask;

                    await renderTask.promise;
                    if (!isUnmountedRef.current) {
                        setRendered(true);
                    }
                } catch (err: any) {
                    if (err?.name !== 'RenderingCancelledException') {
                        console.error('Error rendering page:', err);
                    }
                }
            };

            renderQueueRef.current = renderQueueRef.current
                .then(renderPage)
                .catch(() => {
                    // Swallow queue errors to keep chain alive
                });

            // Cleanup: cancel render task on unmount
            return () => {
                isUnmountedRef.current = true;
                if (renderTaskRef.current) {
                    try {
                        renderTaskRef.current.cancel();
                    } catch (e) {
                        // Ignore cancel errors
                    }
                    renderTaskRef.current = null;
                }
            };
        }, [pdfDoc, pageNum, scale]);

        return (
            <div ref={ref} className="bg-white shadow-lg" style={{ width: '100%', height: '100%' }}>
                <canvas
                    key={`canvas-${pageNum}`}
                    ref={canvasRef}
                    className="w-full h-full object-contain"
                    style={{ display: rendered ? 'block' : 'none' }}
                />
                {!rendered && (
                    <div className="w-full h-full flex items-center justify-center bg-slate-50">
                        <Loader2 className="animate-spin text-indigo-500" size={24} />
                    </div>
                )}
            </div>
        );
    }
);
Page.displayName = 'Page';

export const CatalogueTechniqueView = ({ pdfUrl, htmlUrl, loading = false }: { pdfUrl?: string; htmlUrl?: string; loading?: boolean }) => {
    const bookRef = useRef<any>(null);
    const [pdfDoc, setPdfDoc] = useState<any>(null);
    const [numPages, setNumPages] = useState(0);
    const [currentPage, setCurrentPage] = useState(0);
    const [isLoadingPdf, setIsLoadingPdf] = useState(false);
    const [pdfJsLoaded, setPdfJsLoaded] = useState(false);
    const [loadError, setLoadError] = useState<string | null>(null);

    // Resolve URLs - handle relative paths
    const resolvedPdfUrl = useMemo(() => {
        if (!pdfUrl) return null;
        if (pdfUrl.startsWith("http://") || pdfUrl.startsWith("https://")) return pdfUrl;
        if (pdfUrl.startsWith("/")) return `${API_BASE}${pdfUrl}`;
        const filename = pdfUrl.split(/[/\\]/).pop();
        return filename ? `${API_BASE}/download/${filename}` : null;
    }, [pdfUrl]);

    const resolvedHtmlUrl = useMemo(() => {
        if (!htmlUrl) return null;
        if (htmlUrl.startsWith("http://") || htmlUrl.startsWith("https://")) return htmlUrl;
        if (htmlUrl.startsWith("/")) return `${API_BASE}${htmlUrl}`;
        const filename = htmlUrl.split(/[/\\]/).pop();
        return filename ? `${API_BASE}/download/${filename}` : null;
    }, [htmlUrl]);

    // Load PDF.js from CDN
    useEffect(() => {
        if (typeof window !== 'undefined' && !(window as any).pdfjsLib) {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
            script.onload = () => {
                const pdfjsLib = (window as any).pdfjsLib;
                pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                setPdfJsLoaded(true);
            };
            document.head.appendChild(script);
        } else if ((window as any).pdfjsLib) {
            setPdfJsLoaded(true);
        }
    }, []);

    // Load PDF document
    useEffect(() => {
        if (!pdfJsLoaded || !resolvedPdfUrl) return;

        const loadPdf = async () => {
            try {
                setLoadError(null);
                setIsLoadingPdf(true);
                const pdfjsLib = (window as any).pdfjsLib;
                
                // For cross-origin URLs (Supabase), fetch the PDF as blob first
                let loadingTask;
                if (resolvedPdfUrl.includes('supabase') || resolvedPdfUrl.includes('storage')) {
                    try {
                        const response = await fetch(resolvedPdfUrl);
                        if (!response.ok) throw new Error(`Failed to fetch PDF: ${response.status}`);
                        const blob = await response.blob();
                        const arrayBuffer = await blob.arrayBuffer();
                        loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
                    } catch (fetchErr) {
                        console.warn('Fetch approach failed, trying direct load:', fetchErr);
                        loadingTask = pdfjsLib.getDocument(resolvedPdfUrl);
                    }
                } else {
                    loadingTask = pdfjsLib.getDocument(resolvedPdfUrl);
                }
                
                const doc = await loadingTask.promise;
                setPdfDoc(doc);
                setNumPages(doc.numPages);
                setIsLoadingPdf(false);
            } catch (err) {
                console.error('Error loading PDF:', err);
                setLoadError('Impossible de charger le catalogue');
                setIsLoadingPdf(false);
            }
        };

        loadPdf();
    }, [pdfJsLoaded, resolvedPdfUrl]);

    useEffect(() => {
        if (resolvedHtmlUrl && !resolvedPdfUrl) {
            setLoadError(null);
        }
    }, [resolvedHtmlUrl, resolvedPdfUrl]);

    const handlePageFlip = useCallback((e: any) => {
        setCurrentPage(e.data);
    }, []);

    const goToPrevPage = () => {
        if (bookRef.current) {
            bookRef.current.pageFlip().flipPrev();
        }
    };

    const goToNextPage = () => {
        if (bookRef.current) {
            bookRef.current.pageFlip().flipNext();
        }
    };

    const handleDownload = () => {
        const url = resolvedPdfUrl || resolvedHtmlUrl;
        if (!url) return;
        const link = document.createElement('a');
        link.href = url;
        link.download = resolvedPdfUrl ? 'Catalogue_Technique.pdf' : 'Catalogue_Technique.html';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    // Show generating state when backend is still working
    if (loading) {
        return (
            <div className="h-full flex items-center justify-center bg-slate-50 dark:bg-[#0b0c10] bg-none dark:bg-gradient-to-br dark:from-slate-900 dark:via-slate-800 dark:to-indigo-900 transition-colors">
                <div className="text-center">
                    <Loader2 className="animate-spin text-indigo-600 dark:text-indigo-400 mx-auto mb-4" size={48} />
                    <p className="text-slate-800 dark:text-white font-bold">Génération du catalogue en cours...</p>
                    <p className="text-indigo-600 dark:text-indigo-300 text-sm mt-2">Compilation LaTeX du document PDF</p>
                </div>
            </div>
        );
    }

    // Show loading PDF state
    if (isLoadingPdf || (!pdfDoc && resolvedPdfUrl && pdfJsLoaded)) {
        return (
            <div className="h-full flex items-center justify-center bg-slate-50 dark:bg-[#0b0c10] bg-none dark:bg-gradient-to-br dark:from-slate-900 dark:via-slate-800 dark:to-indigo-900 transition-colors">
                <div className="text-center">
                    <Loader2 className="animate-spin text-indigo-600 dark:text-indigo-400 mx-auto mb-4" size={48} />
                    <p className="text-slate-800 dark:text-white font-bold">Chargement du catalogue...</p>
                </div>
            </div>
        );
    }

    // No PDF URL available (but might have HTML)
    if (!resolvedPdfUrl && !resolvedHtmlUrl) {
        return (
            <div className="h-full flex items-center justify-center bg-gradient-to-br from-slate-50 via-indigo-50/30 to-purple-50/20 dark:from-[#0b0c10] dark:via-slate-900 dark:to-indigo-950 transition-colors relative overflow-hidden">
                {/* Animated background decorations */}
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                    <div className="absolute top-1/4 -left-20 w-72 h-72 bg-indigo-400/20 dark:bg-indigo-500/10 rounded-full blur-3xl animate-pulse" />
                    <div className="absolute bottom-1/4 -right-20 w-72 h-72 bg-purple-400/20 dark:bg-purple-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-emerald-400/10 dark:bg-emerald-500/5 rounded-full blur-3xl" />
                </div>
                
                <div className="relative z-10 text-center max-w-md mx-auto px-6">
                    {/* Success icon with animated ring */}
                    <div className="relative inline-flex items-center justify-center mb-6">
                        <div className="absolute inset-0 w-24 h-24 bg-emerald-500/20 dark:bg-emerald-400/20 rounded-full animate-ping" style={{ animationDuration: '2s' }} />
                        <div className="relative w-24 h-24 bg-gradient-to-br from-emerald-400 to-emerald-600 dark:from-emerald-500 dark:to-emerald-700 rounded-full flex items-center justify-center shadow-2xl shadow-emerald-500/30">
                            <CheckCircle2 className="text-white" size={48} strokeWidth={2.5} />
                        </div>
                    </div>
                    
                    {/* Success message */}
                    <div className="space-y-3 mb-8">
                        <div className="flex items-center justify-center gap-2">
                            <Sparkles className="text-amber-500 dark:text-amber-400" size={20} />
                            <h2 className="text-2xl font-bold bg-gradient-to-r from-slate-800 via-indigo-700 to-purple-700 dark:from-white dark:via-indigo-200 dark:to-purple-200 bg-clip-text text-transparent">
                                Catalogue Prêt !
                            </h2>
                            <Sparkles className="text-amber-500 dark:text-amber-400" size={20} />
                        </div>
                        <p className="text-slate-600 dark:text-slate-300 text-base">
                            Votre catalogue technique a été généré avec succès
                        </p>
                    </div>
                    
                    {/* Feature badges */}
                    <div className="flex flex-wrap justify-center gap-3 mb-8">
                        <div className="flex items-center gap-2 px-4 py-2 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm rounded-full shadow-lg border border-slate-200/50 dark:border-slate-700/50">
                            <FileText className="text-indigo-500 dark:text-indigo-400" size={16} />
                            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Document PDF</span>
                        </div>
                        <div className="flex items-center gap-2 px-4 py-2 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm rounded-full shadow-lg border border-slate-200/50 dark:border-slate-700/50">
                            <BookOpen className="text-purple-500 dark:text-purple-400" size={16} />
                            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Consultation interactive</span>
                        </div>
                    </div>
                    
                    {/* Info card */}
                    <div className="bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl rounded-2xl p-6 shadow-xl border border-slate-200/50 dark:border-slate-700/50">
                        <div className="flex items-start gap-4">
                            <div className="flex-shrink-0 w-10 h-10 bg-indigo-100 dark:bg-indigo-900/50 rounded-xl flex items-center justify-center">
                                <BookOpen className="text-indigo-600 dark:text-indigo-400" size={20} />
                            </div>
                            <div className="text-left">
                                <h3 className="font-semibold text-slate-800 dark:text-white mb-1">Prochaine étape</h3>
                                <p className="text-sm text-slate-600 dark:text-slate-400">
                                    Le catalogue sera disponible automatiquement une fois le traitement terminé. Vous pourrez le consulter en mode livre interactif.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (loadError) {
        return (
            <ErrorDisplay 
                error={loadError}
                title="Erreur de chargement du catalogue"
                onRetry={() => {
                    setLoadError(null);
                    setIsLoadingPdf(true);
                    // Re-trigger PDF load
                    if (resolvedPdfUrl) {
                        window.location.reload();
                    }
                }}
            />
        );
    }

    return (
        <div className="h-full min-h-0 flex flex-col bg-slate-50 dark:bg-[#0b0c10] bg-none dark:bg-gradient-to-br dark:from-slate-900 dark:via-slate-800 dark:to-indigo-900 relative overflow-hidden transition-colors">
            {/* Background decoration */}
            <div className="absolute inset-0 opacity-10 pointer-events-none">
                <div className="absolute top-0 left-0 w-96 h-96 bg-indigo-500 rounded-full blur-[150px]" />
                <div className="absolute bottom-0 right-0 w-96 h-96 bg-purple-500 rounded-full blur-[150px]" />
            </div>

            {/* Header with Download Button */}
            <div className="relative z-10 p-6 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-indigo-100 dark:bg-indigo-600 rounded-xl flex items-center justify-center text-indigo-600 dark:text-white shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/30">
                        <BookOpen size={24} />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-slate-800 dark:text-white">Catalogue Technique</h2>
                        <p className="text-sm text-slate-500 dark:text-indigo-300">{numPages} pages</p>
                    </div>
                </div>
                <button
                    onClick={handleDownload}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl text-sm font-bold flex items-center gap-2 transition-all shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/50"
                >
                    <Download size={18} />
                    Télécharger {resolvedPdfUrl ? "PDF" : "HTML"}
                </button>
            </div>

            {/* Flipbook Container */}
            <div className="flex-1 min-h-0 relative z-10 flex items-center justify-center px-8 py-4">
                {/* Left Arrow */}
                <button
                    onClick={goToPrevPage}
                    disabled={currentPage <= 0}
                    className={clsx(
                        "absolute left-6 z-20 w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-lg",
                        currentPage <= 0
                            ? "bg-slate-200 dark:bg-white/10 text-slate-400 dark:text-slate-500 cursor-not-allowed"
                            : "bg-white dark:bg-white/20 backdrop-blur-sm text-slate-700 dark:text-white hover:bg-slate-50 dark:hover:bg-white/30 cursor-pointer hover:scale-110"
                    )}
                >
                    <ChevronLeft size={28} />
                </button>

                {/* Book */}
                {resolvedHtmlUrl && !resolvedPdfUrl ? (
                    <iframe
                        src={resolvedHtmlUrl}
                        className="w-full h-full max-w-[960px] max-h-[720px] rounded-2xl border border-slate-200 dark:border-white/10 bg-white"
                        title="Catalogue HTML Preview"
                    />
                ) : null}

                {pdfDoc && numPages > 0 && (
                    <div className="w-full h-full max-w-[720px] max-h-[640px] flex items-center justify-center">
                        <HTMLFlipBook
                            ref={bookRef}
                            width={360}
                            height={520}
                            size="stretch"
                            minWidth={280}
                            maxWidth={520}
                            minHeight={360}
                            maxHeight={640}
                            showCover={true}
                            mobileScrollSupport={true}
                            onFlip={handlePageFlip}
                            className="shadow-2xl"
                            style={{}}
                            startPage={0}
                            drawShadow={true}
                            flippingTime={600}
                            usePortrait={false}
                            startZIndex={0}
                            autoSize={true}
                            maxShadowOpacity={0.5}
                            showPageCorners={true}
                            disableFlipByClick={false}
                            swipeDistance={30}
                            clickEventForward={true}
                            useMouseEvents={true}
                        >
                            {Array.from({ length: numPages }, (_, i) => (
                                <Page key={i} pageNum={i + 1} pdfDoc={pdfDoc} scale={1.4} />
                            ))}
                        </HTMLFlipBook>
                    </div>
                )}

                {/* Right Arrow */}
                <button
                    onClick={goToNextPage}
                    disabled={currentPage >= numPages - 1}
                    className={clsx(
                        "absolute right-6 z-20 w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-lg",
                        currentPage >= numPages - 1
                            ? "bg-slate-200 dark:bg-white/10 text-slate-400 dark:text-slate-500 cursor-not-allowed"
                            : "bg-white dark:bg-white/20 backdrop-blur-sm text-slate-700 dark:text-white hover:bg-slate-50 dark:hover:bg-white/30 cursor-pointer hover:scale-110"
                    )}
                >
                    <ChevronRight size={28} />
                </button>
            </div>

            {/* Page Counter */}
            <div className="relative z-10 p-6 flex justify-center shrink-0">
                <div className="bg-white dark:bg-white/10 backdrop-blur-sm border border-slate-200 dark:border-white/5 px-6 py-3 rounded-full flex items-center gap-4 shadow-sm dark:shadow-none">
                    <span className="text-slate-500 dark:text-indigo-300 text-sm font-medium">Page</span>
                    <span className="text-slate-800 dark:text-white font-bold text-lg">{resolvedPdfUrl ? currentPage + 1 : 1}</span>
                    <span className="text-slate-400 dark:text-indigo-400">/</span>
                    <span className="text-slate-500 dark:text-indigo-300 font-bold text-lg">{resolvedPdfUrl ? numPages : 1}</span>
                </div>
            </div>
        </div>
    );
};
