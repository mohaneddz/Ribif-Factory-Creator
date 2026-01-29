import React, { useCallback, useEffect, useRef, useState } from "react";
import HTMLFlipBook from "react-pageflip";
import { BookOpen, ChevronLeft, ChevronRight, Download, Loader2 } from "lucide-react";
import clsx from "clsx";

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

export const CatalogueTechniqueView = ({ pdfUrl, htmlUrl }: { pdfUrl?: string; htmlUrl?: string }) => {
    const bookRef = useRef<any>(null);
    const [pdfDoc, setPdfDoc] = useState<any>(null);
    const [numPages, setNumPages] = useState(0);
    const [currentPage, setCurrentPage] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [pdfJsLoaded, setPdfJsLoaded] = useState(false);
    const [loadError, setLoadError] = useState<string | null>(null);
    const resolvedPdfUrl = pdfUrl;
    const resolvedHtmlUrl = htmlUrl;

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
                if (!resolvedPdfUrl) {
                    setPdfDoc(null);
                    setNumPages(0);
                    setLoadError('Catalogue non disponible');
                    setIsLoading(false);
                    return;
                }
                setLoadError(null);
                setIsLoading(true);
                const pdfjsLib = (window as any).pdfjsLib;
                const loadingTask = pdfjsLib.getDocument(resolvedPdfUrl);
                const doc = await loadingTask.promise;
                setPdfDoc(doc);
                setNumPages(doc.numPages);
                setIsLoading(false);
            } catch (err) {
                console.error('Error loading PDF:', err);
                setLoadError('Impossible de charger le catalogue');
                setIsLoading(false);
            }
        };

        loadPdf();
    }, [pdfJsLoaded, resolvedPdfUrl]);

    useEffect(() => {
        if (resolvedHtmlUrl && !resolvedPdfUrl) {
            setIsLoading(false);
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

    if (isLoading) {
        return (
            <div className="h-full flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900">
                <div className="text-center">
                    <Loader2 className="animate-spin text-indigo-400 mx-auto mb-4" size={48} />
                    <p className="text-white font-bold">Chargement du catalogue...</p>
                </div>
            </div>
        );
    }

    if (loadError) {
        return (
            <div className="h-full flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900">
                <div className="text-center">
                    <p className="text-white font-bold">{loadError}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full min-h-0 flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900 relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute inset-0 opacity-10">
                <div className="absolute top-0 left-0 w-96 h-96 bg-indigo-500 rounded-full blur-[150px]" />
                <div className="absolute bottom-0 right-0 w-96 h-96 bg-purple-500 rounded-full blur-[150px]" />
            </div>

            {/* Header with Download Button */}
            <div className="relative z-10 p-6 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-500/30">
                        <BookOpen size={24} />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">Catalogue Technique</h2>
                        <p className="text-sm text-indigo-300">{numPages} pages</p>
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
                            ? "bg-white/10 text-slate-500 cursor-not-allowed"
                            : "bg-white/20 backdrop-blur-sm text-white hover:bg-white/30 cursor-pointer hover:scale-110"
                    )}
                >
                    <ChevronLeft size={28} />
                </button>

                {/* Book */}
                {resolvedHtmlUrl && !resolvedPdfUrl ? (
                    <iframe
                        src={resolvedHtmlUrl}
                        className="w-full h-full max-w-[960px] max-h-[720px] rounded-2xl border border-white/10 bg-white"
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
                            ? "bg-white/10 text-slate-500 cursor-not-allowed"
                            : "bg-white/20 backdrop-blur-sm text-white hover:bg-white/30 cursor-pointer hover:scale-110"
                    )}
                >
                    <ChevronRight size={28} />
                </button>
            </div>

            {/* Page Counter */}
            <div className="relative z-10 p-6 flex justify-center shrink-0">
                <div className="bg-white/10 backdrop-blur-sm px-6 py-3 rounded-full flex items-center gap-4">
                    <span className="text-indigo-300 text-sm font-medium">Page</span>
                    <span className="text-white font-bold text-lg">{resolvedPdfUrl ? currentPage + 1 : 1}</span>
                    <span className="text-indigo-400">/</span>
                    <span className="text-indigo-300 font-bold text-lg">{resolvedPdfUrl ? numPages : 1}</span>
                </div>
            </div>
        </div>
    );
};
