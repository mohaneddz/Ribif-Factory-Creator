import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
    Check,
    ChevronLeft,
    ChevronRight,
    Download,
    FileSpreadsheet,
    Loader2,
    X,
} from "lucide-react";
import clsx from "clsx";

import { BUSINESS_PLAN_TABS, API_BASE } from "./constants";

export const BusinessPlanView = ({ businessPlanData, pitchDeckData, loading }: { businessPlanData: any, pitchDeckData: any, loading: boolean }) => {
    const [activeTab, setActiveTab] = useState<string | null>(null);
    const [showOverlay, setShowOverlay] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
    const [pdfLoading, setPdfLoading] = useState(false);
    const [pdfError, setPdfError] = useState<string | null>(null);
    const lastFetchedRef = useRef<string | null>(null);
    const totalPages = pitchDeckData?.data?.n_slides || pitchDeckData?.data?.slides?.length || 10;

    // Create a unique key from pitchDeckData to detect when it changes
    const pitchDeckKey = pitchDeckData ? `${pitchDeckData.pdf_download_url || ''}_${pitchDeckData.pdf_filename || ''}_${pitchDeckData.data?.created_at || ''}` : null;

    // Get pitch deck file info - resolve relative URLs to full URLs
    const resolvePdfUrl = (url: string | undefined): string => {
        if (!url) return "";
        if (url.startsWith("http://") || url.startsWith("https://")) return url;
        if (url.startsWith("/")) return `${API_BASE}${url}`;
        return url;
    };
    
    const pitchDeckPdfUrl = resolvePdfUrl(pitchDeckData?.pdf_download_url);
    const businessPlanDownloadUrl = resolvePdfUrl(businessPlanData?.download_url);

    // Fetch PDF as blob and create object URL for iframe display
    const fetchPdfAsBlob = useCallback(async (url: string) => {
        setPdfLoading(true);
        setPdfError(null);
        try {
            // Add cache-busting parameter to ensure fresh download
            const cacheBustUrl = url.includes('?') ? `${url}&_t=${Date.now()}` : `${url}?_t=${Date.now()}`;
            const response = await fetch(cacheBustUrl, {
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache',
                }
            });
            if (!response.ok) {
                throw new Error(`Failed to fetch PDF: ${response.status}`);
            }
            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);
            setPdfBlobUrl(blobUrl);
        } catch (err) {
            console.error("Error fetching PDF:", err);
            setPdfError(err instanceof Error ? err.message : "Failed to load PDF");
        } finally {
            setPdfLoading(false);
        }
    }, []);

    // Fetch PDF when pitchDeckData changes (not just URL)
    useEffect(() => {
        if (!pitchDeckPdfUrl || !pitchDeckKey) return;
        
        // Skip if we already fetched this exact data
        if (lastFetchedRef.current === pitchDeckKey) return;
        lastFetchedRef.current = pitchDeckKey;
        
        // Revoke previous blob URL to prevent memory leaks
        if (pdfBlobUrl) {
            URL.revokeObjectURL(pdfBlobUrl);
            setPdfBlobUrl(null);
        }
        
        fetchPdfAsBlob(pitchDeckPdfUrl);
    }, [pitchDeckPdfUrl, pitchDeckKey, fetchPdfAsBlob]);

    // Cleanup blob URL on unmount
    useEffect(() => {
        return () => {
            if (pdfBlobUrl) {
                URL.revokeObjectURL(pdfBlobUrl);
            }
        };
    }, [pdfBlobUrl]);

    const handleTabClick = (tabId: string) => {
        setActiveTab(tabId);
        setShowOverlay(true);
    };

    const closeOverlay = () => {
        setShowOverlay(false);
        setActiveTab(null);
    };

    const renderOverlayContent = () => {
        if (!activeTab) return null;
        const data = businessPlanData?.data || {};
        const bmc = data.bmc_content || {};
        const capex = data.capex_data || {};
        const opex = data.opex_data || {};
        const pricing = data.pricing_data || {};
        const roi = data.financial_data || {};

        switch (activeTab) {
            case 'bmc':
                return (
                    <div className="space-y-6">
                        <h3 className="text-lg font-bold text-slate-800 mb-4">Business Model Canvas</h3>
                        <div className="grid grid-cols-3 gap-4">
                            <div className="bg-indigo-50 p-4 rounded-xl border border-indigo-100">
                                <div className="text-xs font-bold text-indigo-600 uppercase tracking-widest mb-2">Partenaires Clés</div>
                                <p className="text-sm text-slate-600">{Array.isArray(bmc.partners) ? bmc.partners.join(" • ") : bmc.partners}</p>
                            </div>
                            <div className="bg-purple-50 p-4 rounded-xl border border-purple-100">
                                <div className="text-xs font-bold text-purple-600 uppercase tracking-widest mb-2">Activités Clés</div>
                                <p className="text-sm text-slate-600">{Array.isArray(bmc.activities) ? bmc.activities.join(" • ") : bmc.activities}</p>
                            </div>
                            <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-100">
                                <div className="text-xs font-bold text-emerald-600 uppercase tracking-widest mb-2">Propositions de Valeur</div>
                                <p className="text-sm text-slate-600">{Array.isArray(bmc.value_propositions) ? bmc.value_propositions.join(" • ") : bmc.value_propositions}</p>
                            </div>
                            <div className="bg-sky-50 p-4 rounded-xl border border-sky-100">
                                <div className="text-xs font-bold text-sky-600 uppercase tracking-widest mb-2">Ressources Clés</div>
                                <p className="text-sm text-slate-600">{Array.isArray(bmc.resources) ? bmc.resources.join(" • ") : bmc.resources}</p>
                            </div>
                            <div className="bg-amber-50 p-4 rounded-xl border border-amber-100">
                                <div className="text-xs font-bold text-amber-600 uppercase tracking-widest mb-2">Relations Clients</div>
                                <p className="text-sm text-slate-600">{Array.isArray(bmc.relationships) ? bmc.relationships.join(" • ") : bmc.relationships}</p>
                            </div>
                            <div className="bg-rose-50 p-4 rounded-xl border border-rose-100">
                                <div className="text-xs font-bold text-rose-600 uppercase tracking-widest mb-2">Segments Clients</div>
                                <p className="text-sm text-slate-600">{Array.isArray(bmc.segments) ? bmc.segments.join(" • ") : bmc.segments}</p>
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4 mt-4">
                            <div className="bg-slate-800 p-4 rounded-xl text-white">
                                <div className="text-xs font-bold text-slate-300 uppercase tracking-widest mb-2">Structure de Coûts</div>
                                <p className="text-sm">{Array.isArray(bmc.cost_structure) ? bmc.cost_structure.join(" • ") : bmc.cost_structure}</p>
                            </div>
                            <div className="bg-emerald-600 p-4 rounded-xl text-white">
                                <div className="text-xs font-bold text-emerald-200 uppercase tracking-widest mb-2">Flux de Revenus</div>
                                <p className="text-sm">{Array.isArray(bmc.revenue_streams) ? bmc.revenue_streams.join(" • ") : bmc.revenue_streams}</p>
                            </div>
                        </div>
                    </div>
                );
            case 'capex':
                return (
                    <div className="space-y-4">
                        <h3 className="text-lg font-bold text-slate-800 mb-4">Capital Expenditures (CapEx)</h3>
                        <div className="space-y-3">
                            {[
                                { label: 'Équipements', value: capex?.equipment?.total },
                                { label: 'Infrastructure', value: capex?.infrastructure?.total },
                                { label: 'Véhicules', value: capex?.vehicles?.total },
                                { label: 'Licences', value: capex?.licenses?.total },
                                { label: 'Fonds de roulement', value: capex?.working_capital },
                            ].map((item, i) => (
                                <div key={i} className="flex justify-between items-center p-4 bg-slate-50 rounded-xl">
                                    <span className="font-medium text-slate-700">{item.label}</span>
                                    <span className="font-bold text-slate-900">{(item.value / 1000000).toFixed(0)} M DZD</span>
                                </div>
                            ))}
                            <div className="flex justify-between items-center p-4 bg-indigo-600 text-white rounded-xl">
                                <span className="font-bold">TOTAL CAPEX</span>
                                <span className="font-black text-xl">{((capex?.total_capex || 0) / 1000000000).toFixed(2)} Mrd DZD</span>
                            </div>
                        </div>
                    </div>
                );
            case 'opex':
                return (
                    <div className="space-y-4">
                        <h3 className="text-lg font-bold text-slate-800 mb-4">Operating Expenses (OpEx) - Annuel</h3>
                        <div className="space-y-3">
                            {[
                                { label: 'Matières Premières', value: opex?.raw_materials?.annual_cost },
                                { label: 'Énergie', value: opex?.energy?.annual_cost },
                                { label: 'Personnel', value: opex?.personnel?.annual_cost },
                                { label: 'Maintenance', value: opex?.maintenance?.annual_cost },
                                { label: 'Loyer', value: opex?.rent?.annual_cost },
                                { label: 'Assurance', value: opex?.insurance?.annual_cost },
                                { label: 'Marketing', value: opex?.marketing?.annual_cost },
                                { label: 'Administratif', value: opex?.administrative?.annual_cost },
                            ].map((item, i) => (
                                <div key={i} className="flex justify-between items-center p-3 bg-slate-50 rounded-xl">
                                    <span className="font-medium text-slate-700">{item.label}</span>
                                    <span className="font-bold text-slate-900">{(item.value / 1000000).toFixed(0)} M DZD</span>
                                </div>
                            ))}
                            <div className="flex justify-between items-center p-4 bg-slate-800 text-white rounded-xl">
                                <span className="font-bold">TOTAL OPEX ANNUEL</span>
                                <span className="font-black text-xl">{((opex?.total_annual_opex || 0) / 1000000000).toFixed(2)} Mrd DZD</span>
                            </div>
                        </div>
                    </div>
                );
            case 'pricing':
                return (
                    <div className="space-y-4">
                        <h3 className="text-lg font-bold text-slate-800 mb-4">Stratégie de Tarification</h3>
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-slate-200">
                                    <th className="text-left py-3 text-xs font-bold text-slate-400 uppercase">Produit</th>
                                    <th className="text-right py-3 text-xs font-bold text-slate-400 uppercase">Prix Unitaire</th>
                                    <th className="text-right py-3 text-xs font-bold text-slate-400 uppercase">Volume/An</th>
                                    <th className="text-right py-3 text-xs font-bold text-slate-400 uppercase">CA Annuel</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(pricing.products || []).map((p: any, i: number) => (
                                    <tr key={i} className="border-b border-slate-100">
                                        <td className="py-3 font-medium text-slate-700">{p.name}</td>
                                        <td className="py-3 text-right text-slate-600">{p.unit_price_dzd.toLocaleString()} DZD</td>
                                        <td className="py-3 text-right text-slate-600">{p.annual_volume.toLocaleString()}</td>
                                        <td className="py-3 text-right font-bold text-slate-900">{(p.annual_revenue / 1000000000).toFixed(2)} Mrd</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        <div className="mt-4 p-4 bg-emerald-600 text-white rounded-xl flex justify-between items-center">
                            <span className="font-bold">TOTAL ANNÉE 1</span>
                            <span className="font-black text-xl">{((pricing.total_annual_revenue_year1 || 0) / 1000000000).toFixed(2)} Mrd DZD</span>
                        </div>
                        <div className="mt-4 p-4 bg-slate-50 rounded-xl">
                            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Stratégie</div>
                            <p className="text-sm text-slate-700">{pricing.pricing_strategy}</p>
                        </div>
                    </div>
                );
            case 'roi':
                return (
                    <div className="space-y-4">
                        <h3 className="text-lg font-bold text-slate-800 mb-4">Analyse ROI</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="bg-emerald-50 p-6 rounded-xl border border-emerald-100">
                                <div className="text-xs font-bold text-emerald-600 uppercase tracking-widest mb-2">VAN (NPV)</div>
                                <div className="text-3xl font-black text-emerald-700">{((roi.npv || 0) / 1000000000).toFixed(2)} Mrd</div>
                                <div className="text-sm text-emerald-600 mt-1">DZD</div>
                            </div>
                            <div className="bg-indigo-50 p-6 rounded-xl border border-indigo-100">
                                <div className="text-xs font-bold text-indigo-600 uppercase tracking-widest mb-2">TRI (IRR)</div>
                                <div className="text-3xl font-black text-indigo-700">{((roi.irr || 0) * 100).toFixed(1)}%</div>
                            </div>
                            <div className="bg-amber-50 p-6 rounded-xl border border-amber-100">
                                <div className="text-xs font-bold text-amber-600 uppercase tracking-widest mb-2">Période de Récupération</div>
                                <div className="text-3xl font-black text-amber-700">{(roi.payback || 0).toFixed(1)} ans</div>
                            </div>
                            <div className="bg-slate-100 p-6 rounded-xl border border-slate-200">
                                <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Investissement Total</div>
                                <div className="text-3xl font-black text-slate-700">{((roi.total_investment || 0) / 1000000000).toFixed(2)} Mrd</div>
                                <div className="text-sm text-slate-500 mt-1">DZD</div>
                            </div>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    // Loading state
    if (loading) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-center">
                    <Loader2 size={48} className="text-indigo-600 animate-spin mx-auto mb-4" />
                    <h3 className="text-xl font-bold text-slate-800">Génération du Business Plan...</h3>
                    <p className="text-slate-500">Préparation du pitch deck et analyse financière</p>
                </div>
            </div>
        );
    }

    // Waiting state (no data yet)
    if (!businessPlanData && !pitchDeckData) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-center">
                    <FileSpreadsheet size={48} className="text-slate-300 mx-auto mb-4" />
                    <h3 className="text-xl font-bold text-slate-600">En attente du Business Plan...</h3>
                    <p className="text-slate-400">Le calcul TCO doit d'abord se terminer</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col p-6 gap-6">
            {/* TOP SECTION: 5 Tabs + Download Buttons */}
            <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-sm">
                <div className="flex justify-between items-center mb-4">
                    <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Sections du Business Plan</div>
                    <div className="flex gap-2">
                        {businessPlanDownloadUrl && (
                            <a
                                href={businessPlanDownloadUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 transition-all"
                            >
                                <Download size={14} />
                                Business Plan XLSX
                            </a>
                        )}
                        {pdfBlobUrl && (
                            <a
                                href={pdfBlobUrl}
                                download={pitchDeckData?.pdf_filename || 'Pitch_Deck.pdf'}
                                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 transition-all"
                            >
                                <Download size={14} />
                                Pitch Deck PDF
                            </a>
                        )}
                    </div>
                </div>
                <div className="flex gap-2">
                    {BUSINESS_PLAN_TABS.map((tab, index) => (
                        <button
                            key={tab.id}
                            onClick={() => handleTabClick(tab.id)}
                            className={clsx(
                                "flex-1 py-4 px-4 rounded-xl text-sm font-bold transition-all border-2 cursor-pointer",
                                "hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-700",
                                "bg-white border-slate-200 text-slate-700",
                                index === 0 && "border-l-4 border-l-emerald-500"
                            )}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
                <p className="mt-4 text-xs text-slate-400 text-center">Cliquez sur une section pour voir les détails</p>
            </div>

            {/* BOTTOM SECTION: Pitch Deck Preview */}
            <div className="flex-1 bg-slate-900 rounded-3xl relative overflow-hidden">
                {/* Status Badge */}
                <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20">
                    <div className="bg-emerald-500/90 text-white px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2">
                        <Check size={14} />
                        {pitchDeckData ? 'Pitch Deck Généré' : 'Business Plan Généré'}
                    </div>
                </div>

                {/* Navigation Arrows */}
                <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 z-20 flex items-center justify-between px-4">
                    <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage <= 1}
                        className={clsx(
                            "w-10 h-10 rounded-full flex items-center justify-center transition-all",
                            currentPage <= 1
                                ? "bg-white/10 text-slate-500 cursor-not-allowed"
                                : "bg-white/20 text-white hover:bg-white/30 cursor-pointer"
                        )}
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <button
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage >= totalPages}
                        className={clsx(
                            "w-10 h-10 rounded-full flex items-center justify-center transition-all",
                            currentPage >= totalPages
                                ? "bg-white/10 text-slate-500 cursor-not-allowed"
                                : "bg-white/20 text-white hover:bg-white/30 cursor-pointer"
                        )}
                    >
                        <ChevronRight size={20} />
                    </button>
                </div>

                {/* Page Counter */}
                <div className="absolute bottom-4 left-6 z-20">
                    <span className="text-white text-sm font-medium bg-black/40 px-3 py-1.5 rounded-lg">
                        {currentPage} / {totalPages}
                    </span>
                </div>

                {/* PDF Preview or Placeholder */}
                <div className="w-full h-full flex items-center justify-center">
                    {pdfLoading ? (
                        <div className="text-center text-white/80">
                            <Loader2 size={64} className="mx-auto mb-4 animate-spin" />
                            <p className="text-lg font-bold">Chargement du Pitch Deck...</p>
                            <p className="text-sm text-white/60">Téléchargement et préparation du PDF</p>
                        </div>
                    ) : pdfError ? (
                        <div className="text-center text-white/60">
                            <FileSpreadsheet size={64} className="mx-auto mb-4 text-red-400" />
                            <p className="text-lg font-bold text-red-400">Erreur de chargement</p>
                            <p className="text-sm">{pdfError}</p>
                            {pitchDeckPdfUrl && (
                                <button
                                    onClick={() => fetchPdfAsBlob(pitchDeckPdfUrl)}
                                    className="mt-4 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium transition-colors"
                                >
                                    Réessayer
                                </button>
                            )}
                        </div>
                    ) : pdfBlobUrl ? (
                        <iframe
                            src={`${pdfBlobUrl}#page=${currentPage}&toolbar=0&navpanes=0&scrollbar=0&view=FitH`}
                            className="w-full h-full border-0"
                            title="Pitch Deck Preview"
                        />
                    ) : (
                        <div className="text-center text-white/60">
                            <FileSpreadsheet size={64} className="mx-auto mb-4" />
                            <p className="text-lg font-bold">Pitch Deck en cours de génération...</p>
                            <p className="text-sm">Le PDF sera affiché une fois prêt</p>
                        </div>
                    )}
                </div>
            </div>

            {/* OVERLAY MODAL */}
            <AnimatePresence>
                {showOverlay && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-8"
                        onClick={closeOverlay}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-white rounded-3xl p-8 max-w-4xl w-full max-h-[80vh] overflow-y-auto shadow-2xl"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex justify-between items-center mb-6">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center text-indigo-600">
                                        <FileSpreadsheet size={20} />
                                    </div>
                                    <span className="font-bold text-slate-800">{BUSINESS_PLAN_TABS.find(t => t.id === activeTab)?.label}</span>
                                </div>
                                <button
                                    onClick={closeOverlay}
                                    className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition-colors"
                                >
                                    <X size={20} />
                                </button>
                            </div>
                            {renderOverlayContent()}
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};
