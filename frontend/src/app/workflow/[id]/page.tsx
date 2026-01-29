"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
    BrainCircuit,
    Building2,
    Check,
    Download,
    Eye,
    Info,
    Loader2,
    RefreshCw,
    Sparkles,
    Upload,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import clsx from "clsx";

import { BusinessPlanView } from "@/sections/BusinessPlanView";
import { CatalogueTechniqueView } from "@/sections/CatalogueTechniqueView";
import { ModuleLoadingView } from "@/sections/ModuleLoadingView";
import { PlansView } from "@/sections/PlansView";
import { SpecsView } from "@/sections/SpecsView";
import { SourcingView } from "@/sections/SourcingView";
import { TcoView } from "@/sections/TcoView";
import { VideoView } from "@/sections/VideoView";
import { API_BASE, MODULES, fontStyle } from "@/sections/constants";
import { supabase } from "@/lib/supabaseClient";
import { loadPipelineSettings } from "@/utils/pipelineSettings";

export default function FactoryCopilot() {
    const router = useRouter();
    const params = useParams();
    const routeProjectId = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : null;
    const [status, setStatus] = useState<'idle' | 'uploading' | 'processing' | 'finished'>('idle');
    const [currentModule, setCurrentModule] = useState(0);
    const [selectedModule, setSelectedModule] = useState(0);
    const [subStep, setSubStep] = useState(0);
    const [artifacts, setArtifacts] = useState<number[]>([]);

    // THIS HOLDS THE REAL BACKEND DATA
    const [extractedData, setExtractedData] = useState<any>(null);
    const [module4Data, setModule4Data] = useState<any>(null);
    const [module4Loading, setModule4Loading] = useState(false);
    const [tcoData, setTcoData] = useState<any>(null);
    const [tcoLoading, setTcoLoading] = useState(false);
    const [businessPlanData, setBusinessPlanData] = useState<any>(null);
    const [pitchDeckData, setPitchDeckData] = useState<any>(null);
    const [businessPlanLoading, setBusinessPlanLoading] = useState(false);
    const [catalogData, setCatalogData] = useState<any>(null);
    const [catalogLoading, setCatalogLoading] = useState(false);
    const [projectId, setProjectId] = useState<string | null>(
        routeProjectId && routeProjectId !== "new" ? routeProjectId : null
    );

    useEffect(() => {
        if (routeProjectId && routeProjectId !== projectId) {
            setProjectId(routeProjectId);
        }
    }, [routeProjectId, projectId]);

    // Animate loading progress while a module is running
    useEffect(() => {
        if (status === 'processing' && !artifacts.includes(currentModule)) {
            const timer = setTimeout(() => {
                setSubStep(s => (s + 1) % 5);
            }, 800);
            return () => clearTimeout(timer);
        }
    }, [status, currentModule, subStep, artifacts]);

    // ----------------------------------------------------
    // REAL FILE UPLOAD HANDLER
    // ----------------------------------------------------
    const handleStart = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;
        const { data: authData } = await supabase.auth.getSession();
        if (!authData?.session) {
            router.push("/auth/login");
            return;
        }

        const file = e.target.files[0];
        const activeSettings = loadPipelineSettings();

        setStatus('processing');
        setArtifacts([]);
        setCurrentModule(0);
        setSelectedModule(0);
        setSubStep(0);
        setExtractedData(null);
        setModule4Data(null);
        setTcoData(null);
        setBusinessPlanData(null);
        setPitchDeckData(null);
        setCatalogData(null);

        try {
            const { data: authUser } = await supabase.auth.getUser();
            const userId = authUser?.user?.id || null;

            const baseHeaders: HeadersInit = {};
            if (userId) baseHeaders["x-user-id"] = userId;
            if (projectId) baseHeaders["x-project-id"] = projectId;

            const formData = new FormData();
            formData.append('file', file);
            formData.append('settings', JSON.stringify(activeSettings));
            if (projectId) {
                formData.append('project_id', projectId);
            }

            const module1Res = await fetch(`${API_BASE}/api/module1/process`, {
                method: 'POST',
                headers: baseHeaders,
                body: formData
            });
            const module1Json = await module1Res.json();
            if (!module1Res.ok) throw new Error(module1Json?.error || 'Module 1 failed');

            const module1Data = module1Json?.data || module1Json;
            setExtractedData(module1Data);
            setArtifacts(prev => [...new Set([...prev, 0])]);

            const newProjectId =
                module1Data?.project_id ||
                module1Data?.ribif_metadata?.project_id ||
                module1Json?.project_id ||
                projectId;
            if (newProjectId) setProjectId(newProjectId);
            if (newProjectId && (!routeProjectId || routeProjectId === "new")) {
                router.replace(`/workflow/${newProjectId}`);
            }

            const jsonHeaders: HeadersInit = {
                "Content-Type": "application/json",
                ...baseHeaders,
                ...(newProjectId ? { "x-project-id": newProjectId } : {})
            };

            setStatus('processing');
            setCurrentModule(1);
            setSelectedModule(1);
            setSubStep(0);

            let module4Json: any = null;
            if (activeSettings.enableSourcing) {
                setModule4Loading(true);
                const module4Res = await fetch(`${API_BASE}/api/module4/enrich`, {
                    method: 'POST',
                    headers: jsonHeaders,
                    body: JSON.stringify({
                        ...module1Data,
                        project_id: newProjectId,
                        pipeline_settings: activeSettings,
                    })
                });
                module4Json = await module4Res.json();
                if (!module4Res.ok) throw new Error(module4Json?.error || 'Module 4 failed');
                setModule4Data(module4Json);
                setModule4Loading(false);
                setArtifacts(prev => [...new Set([...prev, 1])]);
            } else {
                setModule4Loading(false);
                setModule4Data(null);
            }

            setCurrentModule(2);
            setSelectedModule(2);
            setSubStep(0);

            let module6Json: any = null;
            if (activeSettings.enableTco && module4Json) {
                setTcoLoading(true);
                const module6Payload = { ...module1Data, ...module4Json, project_id: newProjectId };
                const module6Res = await fetch(`${API_BASE}/api/module6/tco-from-sourcing`, {
                    method: 'POST',
                    headers: jsonHeaders,
                    body: JSON.stringify(module6Payload)
                });
                module6Json = await module6Res.json();
                if (!module6Res.ok) throw new Error(module6Json?.error || 'Module 6 failed');
                setTcoData(module6Json);
                setTcoLoading(false);
                setArtifacts(prev => [...new Set([...prev, 2])]);
            } else {
                setTcoLoading(false);
                setTcoData(null);
            }

            setCurrentModule(3);
            setSelectedModule(3);
            setSubStep(0);

            if (module6Json && (activeSettings.enableBusinessPlan || activeSettings.enablePitchDeck)) {
                setBusinessPlanLoading(true);

                if (activeSettings.enableBusinessPlan) {
                    const businessPlanRes = await fetch(`${API_BASE}/api/module7/business-plan`, {
                        method: 'POST',
                        headers: jsonHeaders,
                        body: JSON.stringify(module6Json)
                    });
                    const businessPlanJson = await businessPlanRes.json();
                    if (!businessPlanRes.ok) throw new Error(businessPlanJson?.error || 'Business Plan failed');
                    setBusinessPlanData(businessPlanJson);
                }

                if (activeSettings.enablePitchDeck) {
                    const pitchDeckRes = await fetch(`${API_BASE}/api/module7/pitch-deck`, {
                        method: 'POST',
                        headers: jsonHeaders,
                        body: JSON.stringify(module6Json)
                    });
                    const pitchDeckJson = await pitchDeckRes.json();
                    if (!pitchDeckRes.ok) throw new Error(pitchDeckJson?.error || 'Pitch Deck failed');
                    setPitchDeckData(pitchDeckJson);
                }

                setBusinessPlanLoading(false);
                setArtifacts(prev => [...new Set([...prev, 3])]);
            } else {
                setBusinessPlanLoading(false);
                setBusinessPlanData(null);
                setPitchDeckData(null);
            }

            setCurrentModule(4);
            setSelectedModule(4);
            setSubStep(0);

            if (activeSettings.enableCatalog) {
                setCatalogLoading(true);
                const module9Res = await fetch(`${API_BASE}/api/module9/catalog`, {
                    method: 'POST',
                    headers: jsonHeaders,
                    body: JSON.stringify({
                        module1_data: module1Data,
                        module4_data: module4Json || undefined,
                        output_format: activeSettings.catalogFormat,
                        project_id: newProjectId,
                        module1_id: module1Data?.module1_id,
                    })
                });
                const module9Json = await module9Res.json();
                if (!module9Res.ok) throw new Error(module9Json?.error || 'Module 9 failed');
                setCatalogData(module9Json);
                setCatalogLoading(false);
                setArtifacts(prev => [...new Set([...prev, 4])]);
            } else {
                setCatalogLoading(false);
                setCatalogData(null);
            }

            setStatus('finished');
        } catch (error) {
            console.error("❌ Workflow error:", error);
            setModule4Loading(false);
            setTcoLoading(false);
            setBusinessPlanLoading(false);
            setCatalogLoading(false);
            setStatus('idle');
        }
    };

    const regenerateOne = (idx: number) => {
        setArtifacts(prev => prev.filter(i => i !== idx));
        setCurrentModule(idx);
        setSelectedModule(idx);
        setSubStep(0);
        setStatus('processing');
    };

    const regenerateAll = () => {
        setArtifacts([]);
        setCurrentModule(0);
        setSelectedModule(0);
        setSubStep(0);
        setStatus('processing');
    };

    const handleModuleClick = (idx: number) => {
        if (artifacts.includes(idx) || status === 'finished' || idx === currentModule) {
            setSelectedModule(idx);
        }
    };

    const handleArtifactDownload = (idx: number) => {
        const moduleType = MODULES[idx]?.type;
        if (moduleType === 'businessplan') {
            const url = businessPlanData?.download_url;
            if (url) window.open(url, '_blank', 'noopener,noreferrer');
            return;
        }
        if (moduleType === 'catalogue') {
            const url = catalogData?.data?.pdf_download_url || catalogData?.data?.html_download_url;
            if (url) window.open(url, '_blank', 'noopener,noreferrer');
            return;
        }
    };

    const handleDownloadAll = () => {
        const urls = [
            businessPlanData?.download_url,
            catalogData?.data?.pdf_download_url || catalogData?.data?.html_download_url
        ];
        urls.forEach((url) => {
            if (url) window.open(url, '_blank', 'noopener,noreferrer');
        });
    };

    const downloadableArtifacts = artifacts.filter((idx) => {
        const type = MODULES[idx]?.type;
        return type === 'businessplan' || type === 'catalogue';
    });

    const selectedModuleItem = MODULES[selectedModule];
    const activeStagePrimary = MODULES[currentModule];
    const completedPhases = Math.max(artifacts.length, status === 'finished' ? MODULES.length : 0);
    const overallProgress = Math.round((completedPhases / MODULES.length) * 100);
    const isSelectedProcessing = status === 'processing' && selectedModule === currentModule && !artifacts.includes(currentModule);
    const isSelectedDone = artifacts.includes(selectedModule) || status === 'finished' || selectedModule < currentModule;
    const selectedProgress = isSelectedProcessing ? (subStep / 4) * 100 : isSelectedDone ? 100 : 0;

    return (
        <>
            <style>{fontStyle}</style>

            <div className="flex h-screen bg-[#F8FAFC] overflow-hidden font-sans text-slate-900 selection:bg-indigo-100">

                {/* LEFT SIDEBAR */}
                <aside className="w-80 bg-white border-r border-slate-200 flex flex-col z-20 shadow-[4px_0_24px_rgba(0,0,0,0.02)]">
                    <div className="p-8 h-24 border-b border-slate-100 flex items-center gap-4">
                        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-200">
                            <Building2 size={20} />
                        </div>
                        <div>
                            <span className="font-extrabold text-lg text-slate-900 tracking-tight block">RIBIF IA</span>
                            <div className="text-[10px] text-indigo-600 font-bold uppercase tracking-wider">Manager v5.0</div>
                        </div>
                    </div>
                    <div className="flex-1 overflow-y-auto p-6 space-y-2">
                        <div className="px-2 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest flex justify-between">
                            Étapes du Workflow
                            {status === 'finished' && <RefreshCw size={12} className="cursor-pointer hover:text-indigo-600 transition-colors" onClick={regenerateAll} />}
                        </div>
                        {MODULES.map((m, idx) => {
                            const isDone = artifacts.includes(idx);
                            const isActive = selectedModule === idx;
                            const isAvailable = isDone || status === 'finished' || idx === currentModule;
                            return (
                                <button
                                    key={m.id}
                                    onClick={() => handleModuleClick(idx)}
                                    disabled={!isAvailable}
                                    className={clsx(
                                        "w-full flex items-center gap-4 p-4 rounded-[16px] transition-all text-left relative overflow-hidden group",
                                        isActive ? "bg-indigo-50 border border-indigo-100" : "hover:bg-slate-50 border border-transparent",
                                        !isAvailable && "opacity-50 cursor-not-allowed"
                                    )}
                                >
                                    {isActive && <div className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-600" />}
                                    <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border",
                                        isDone ? "bg-emerald-50 text-emerald-600 border-emerald-100" :
                                            isActive ? "bg-indigo-600 text-white border-indigo-600" :
                                                "bg-white text-slate-400 border-slate-200"
                                    )}>
                                        {isDone ? <Check size={16} strokeWidth={3} /> : <m.icon size={16} />}
                                    </div>
                                    <div className={clsx("text-sm font-bold truncate", isActive ? "text-indigo-900" : "text-slate-600 group-hover:text-slate-900")}>{m.title}</div>
                                </button>
                            );
                        })}
                    </div>
                    {status === 'processing' && (
                        <div className="p-6 border-t border-slate-100 bg-white">
                            <motion.div initial={{ y: 12, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="bg-slate-900 text-white px-5 py-4 rounded-2xl flex items-center gap-4 shadow-lg shadow-slate-300/40">
                                <div className="relative">
                                    <div className="absolute inset-0 bg-indigo-500 rounded-full animate-ping opacity-75"></div>
                                    <div className="relative w-9 h-9 bg-indigo-600 rounded-full flex items-center justify-center text-white border border-indigo-400">
                                        <Sparkles size={14} />
                                    </div>
                                </div>
                                <div className="flex-1">
                                    <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest leading-none mb-1">Progression globale</div>
                                    <div className="text-sm font-bold text-white">{activeStagePrimary?.statusText || "Traitement en cours"}</div>
                                    <div className="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                        <div className="h-full bg-indigo-500" style={{ width: `${Math.max(overallProgress, 6)}%` }} />
                                    </div>
                                </div>
                                <div className="text-base font-black text-indigo-300 font-mono">
                                    {overallProgress}%
                                </div>
                            </motion.div>
                        </div>
                    )}
                </aside>

                {/* CENTER PANEL */}
                <main className="flex-1 flex flex-col relative overflow-hidden bg-[#F8FAFC]">
                    <header className="h-24 border-b border-slate-200 flex items-center justify-between px-10 z-10 bg-white/80 backdrop-blur-md">
                        <div className="flex items-center gap-4">
                            <div className={`h-2.5 w-2.5 rounded-full ring-4 ring-opacity-20 ${status === 'processing' || status === 'uploading' ? 'bg-indigo-500 ring-indigo-500 animate-pulse' : 'bg-slate-300 ring-slate-300'}`} />
                            <h2 className="text-xs font-extrabold text-slate-500 uppercase tracking-widest">
                                {status === 'idle' ? "Prêt" : status === 'uploading' ? "Téléchargement & Analyse..." : status === 'finished' ? "Terminé" : "Traitement IA en cours"}
                            </h2>
                        </div>
                        <div className="flex gap-4">
                            {status === 'finished' && (
                                <button onClick={regenerateAll} className="bg-white border border-slate-200 hover:border-indigo-300 text-slate-600 px-6 py-2.5 rounded-full text-xs font-bold flex items-center gap-2 transition-all shadow-sm">
                                    <RefreshCw size={14} /> Relancer
                                </button>
                            )}
                            <button onClick={() => router.push('/twin')} className="bg-slate-900 hover:bg-indigo-600 text-white px-6 py-2.5 rounded-full text-xs font-bold flex items-center gap-2 transition-all shadow-lg shadow-indigo-200/50">
                                <BrainCircuit size={16} className="text-indigo-300" /> Jumeau Numérique
                            </button>
                        </div>
                    </header>

                    <div className="flex-1 p-6 relative overflow-y-auto">
                        {status === 'idle' ? (
                            <div className="h-full flex items-center justify-center p-10">
                                <label className="w-full max-w-4xl aspect-[16/9] bg-white border-2 border-dashed border-slate-300 rounded-[32px] flex flex-col items-center justify-center gap-8 cursor-pointer hover:border-indigo-500 hover:bg-indigo-50/30 transition-all group relative overflow-hidden">
                                    <input type="file" className="hidden" accept=".pdf" onChange={handleStart} />

                                    <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(#4f46e5 1px, transparent 1px)', backgroundSize: '24px 24px' }} />

                                    <div className="w-24 h-24 bg-indigo-50 rounded-[2rem] flex items-center justify-center text-indigo-600 group-hover:scale-110 group-hover:bg-indigo-600 group-hover:text-white transition-all duration-300 shadow-sm z-10">
                                        <Upload size={32} />
                                    </div>
                                    <div className="text-center z-10 max-w-md">
                                        <h3 className="text-2xl font-black text-slate-800 mb-3">Initialiser le Projet</h3>
                                        <p className="text-slate-500 font-medium leading-relaxed">Glissez votre cahier des charges (PDF) pour lancer l'analyse IA.</p>
                                    </div>
                                    <div className="px-8 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold z-10 group-hover:bg-indigo-600 transition-colors shadow-lg shadow-slate-200">
                                        Sélectionner un fichier
                                    </div>
                                </label>
                            </div>
                        ) : status === 'uploading' ? (
                            <div className="h-full w-full flex flex-col items-center justify-center">
                                <Loader2 size={48} className="text-indigo-600 animate-spin mb-4" />
                                <h3 className="text-xl font-bold text-slate-800">Analyse du PDF par IA</h3>
                                <p className="text-slate-500">Cela peut prendre quelques secondes.</p>
                            </div>
                        ) : (
                            <div className="h-full w-full bg-white rounded-[32px] border border-slate-200 shadow-sm overflow-auto relative">
                                <AnimatePresence mode="wait">
                                    <motion.div key={selectedModule} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full w-full">
                                        {isSelectedProcessing ? (
                                            <ModuleLoadingView module={selectedModuleItem} progress={selectedProgress} />
                                        ) : (
                                            <>
                                                {selectedModuleItem.type === 'specs' && <SpecsView data={extractedData} />}
                                                {selectedModuleItem.type === 'plans' && <PlansView />}
                                                {selectedModuleItem.type === 'video' && <VideoView progress={selectedProgress} />}
                                                {selectedModuleItem.type === 'sourcing' && <SourcingView progress={selectedProgress} data={extractedData} module4Data={module4Data} loading={module4Loading} />}
                                                {selectedModuleItem.type === 'tco' && <TcoView data={tcoData} loading={tcoLoading} />}
                                                {selectedModuleItem.type === 'businessplan' && <BusinessPlanView businessPlanData={businessPlanData} pitchDeckData={pitchDeckData} loading={businessPlanLoading} />}
                                                {selectedModuleItem.type === 'catalogue' && (
                                                    <CatalogueTechniqueView
                                                        pdfUrl={catalogData?.data?.pdf_download_url}
                                                        htmlUrl={catalogData?.data?.html_download_url}
                                                    />
                                                )}
                                            </>
                                        )}
                                    </motion.div>
                                </AnimatePresence>

                            </div>
                        )}
                    </div>
                </main>

                {/* RIGHT SIDEBAR (Artifacts) */}
                <aside className="w-80 bg-white border-l border-slate-200 flex flex-col z-20 shadow-[-4px_0_24px_rgba(0,0,0,0.02)]">
                    <div className="h-24 p-8 border-b border-slate-100 flex items-center justify-between">
                        <h2 className="text-xs font-extrabold text-slate-500 uppercase tracking-widest">Livrables</h2>
                        <span className="bg-slate-100 text-slate-600 px-2 py-1 rounded-md text-[10px] font-bold">{downloadableArtifacts.length} fichiers</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50/50">
                        <AnimatePresence>
                            {downloadableArtifacts.length === 0 && (
                                <div className="h-40 border-2 border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center p-6 text-center">
                                    <Info size={24} className="mb-2 text-slate-300" />
                                    <p className="text-xs font-bold text-slate-400">En attente de génération...</p>
                                </div>
                            )}
                            {downloadableArtifacts.slice().reverse().map((idx) => (
                                <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                    className={clsx("bg-white rounded-[20px] border p-4 transition-all group shadow-sm hover:shadow-md", selectedModule === idx ? "border-indigo-400 ring-4 ring-indigo-50" : "border-slate-200")}>
                                    <div className="flex justify-between items-start mb-3">
                                        <div onClick={() => handleModuleClick(idx)} className="w-10 h-10 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors cursor-pointer">
                                            <Eye size={18} />
                                        </div>
                                        <div className="flex gap-1">
                                            <button onClick={() => regenerateOne(idx)} className="w-8 h-8 flex items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-indigo-600 transition-colors">
                                                <RefreshCw size={14} />
                                            </button>
                                            <button
                                                onClick={() => handleArtifactDownload(idx)}
                                                className="w-8 h-8 flex items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-indigo-600 transition-colors"
                                            >
                                                <Download size={14} />
                                            </button>
                                        </div>
                                    </div>
                                    <div className="text-xs font-extrabold text-slate-800 truncate mb-2">{MODULES[idx].file}</div>
                                    <div className="flex items-center gap-1.5">
                                        <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Prêt à l'envoi</span>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                    {status === 'finished' && (
                        <div className="p-6 border-t border-slate-100 bg-white">
                            <button
                                onClick={handleDownloadAll}
                                className="w-full bg-indigo-600 text-white py-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200"
                            >
                                <Download size={16} /> TOUT TÉLÉCHARGER
                            </button>
                        </div>
                    )}
                </aside>
            </div>
        </>
    );
}
