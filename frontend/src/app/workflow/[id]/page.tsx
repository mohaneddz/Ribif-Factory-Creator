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
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState, useCallback } from "react";
import clsx from "clsx";

import { BusinessPlanView } from "@/sections/BusinessPlanView";
import { CatalogueTechniqueView } from "@/sections/CatalogueTechniqueView";
import { CallsNegotiationView } from "@/sections/CallsNegotiationView";
import { EmailCenterView } from "@/sections/EmailCenterView";
import { ModuleLoadingView } from "@/sections/ModuleLoadingView";
import { Layout2DView, Model3DView } from "@/sections/PlansView";
import { SpecsView } from "@/sections/SpecsView";
import { SourcingView } from "@/sections/SourcingView";
import { TcoView } from "@/sections/TcoView";
import { VideoView } from "@/sections/VideoView";
import { API_BASE, MODULES, fontStyle } from "@/sections/constants";
import { supabase } from "@/lib/supabaseClient";
import { loadPipelineSettings } from "@/utils/pipelineSettings";
import {
    uploadFileToBucket,
    loadProject,
    updateProject,
    ProjectRecord,
} from "@/lib/projectService";

export default function FactoryCopilot() {
    const router = useRouter();
    const params = useParams();
    const routeProjectId = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : null;
    const [status, setStatus] = useState<'idle' | 'uploading' | 'processing' | 'finished' | 'loading' | 'resuming'>('idle');
    const [currentModule, setCurrentModule] = useState(0);
    const [selectedModule, setSelectedModule] = useState(0);
    const [subStep, setSubStep] = useState(0);
    const [artifacts, setArtifacts] = useState<number[]>([]);

    // Project data from Supabase
    const [projectData, setProjectData] = useState<ProjectRecord | null>(null);
    const [projectId, setProjectId] = useState<string | null>(null);  // Start null, will be set by useEffect

    // Module data (derived from projectData or fresh from API)
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
    const [layoutData, setLayoutData] = useState<any>(null);
    const [layoutLoading, setLayoutLoading] = useState(false);
    const [videoData, setVideoData] = useState<any>(null);
    const [videoLoading, setVideoLoading] = useState(false);

    // Refs for tracking workflow state
    const runHasData = useRef(false);
    const projectLoadedRef = useRef(false);

    // State-based trigger for auto-resume (state triggers re-render, refs don't)
    const [shouldAutoResume, setShouldAutoResume] = useState(false);
    const [pendingResumeData, setPendingResumeData] = useState<ProjectRecord | null>(null);

    // Helper to find module index by type
    const getModuleIndex = (type: string) => MODULES.findIndex((m) => m.type === type);

    // ============================================================
    // LOAD PROJECT FROM SUPABASE ON MOUNT
    // ============================================================
    const loadExistingProject = useCallback(async (id: string) => {
        if (projectLoadedRef.current || id === "new") return;
        projectLoadedRef.current = true;

        setStatus('loading');
        console.log("📂 Loading project from Supabase:", id);

        const { data, error } = await loadProject(id);

        if (error || !data) {
            console.warn("⚠️ Could not load project:", error?.message);
            setStatus('idle');
            projectLoadedRef.current = false;
            return;
        }

        console.log("✅ Project loaded:", data);
        setProjectData(data);

        // Restore state from project data
        const completedArtifacts: number[] = [];

        if (data.module1_data) {
            setExtractedData(data.module1_data);
            completedArtifacts.push(getModuleIndex("specs"));
        }
        if (data.module4_data) {
            setModule4Data(data.module4_data);
            completedArtifacts.push(getModuleIndex("sourcing"));
            completedArtifacts.push(getModuleIndex("email"));
            completedArtifacts.push(getModuleIndex("calls"));
        }
        if (data.module6_data) {
            setTcoData(data.module6_data);
            completedArtifacts.push(getModuleIndex("tco"));
        }
        if (data.module7_business) {
            setBusinessPlanData(data.module7_business);
            completedArtifacts.push(getModuleIndex("businessplan"));
        }
        if (data.module7_pitch) {
            setPitchDeckData(data.module7_pitch);
            if (!completedArtifacts.includes(getModuleIndex("businessplan"))) {
                completedArtifacts.push(getModuleIndex("businessplan"));
            }
        }
        if (data.module9_data) {
            setCatalogData(data.module9_data);
            completedArtifacts.push(getModuleIndex("catalogue"));
        }
        if (data.module2_data) {
            setLayoutData(data.module2_data);
            completedArtifacts.push(getModuleIndex("layout2d"));
            completedArtifacts.push(getModuleIndex("model3d"));
        }
        if (data.module3_data) {
            setVideoData(data.module3_data);
            completedArtifacts.push(getModuleIndex("video"));
        }

        const uniqueArtifacts = [...new Set(completedArtifacts.filter(i => i >= 0))];
        setArtifacts(uniqueArtifacts);

        // Determine initial status based on what data exists
        const allModulesComplete = data.module1_data && data.module2_data && data.module3_data;
        // Check both source_file_path AND source_filename since file may be uploaded but path empty
        const hasSourceFile = !!data.source_file_path || !!data.source_filename;
        const hasAnyModuleData = uniqueArtifacts.length > 0;

        if (allModulesComplete || (hasAnyModuleData && data.status === 'complete')) {
            // All modules are done
            setStatus('finished');
            setSelectedModule(0);
            setCurrentModule(MODULES.length - 1);
        } else if (hasSourceFile || hasAnyModuleData) {
            // Has source file OR some data → needs to resume processing
            console.log("🔄 Project has data/file but is incomplete, will auto-resume...");
            console.log("   - hasSourceFile:", hasSourceFile);
            console.log("   - hasAnyModuleData:", hasAnyModuleData);
            console.log("   - source_file_path:", data.source_file_path);
            setStatus('processing');  // Set to processing immediately
            setSelectedModule(0);
            if (hasAnyModuleData) {
                setCurrentModule(MODULES.length - 1);
            }
            // Trigger auto-resume via STATE (not ref) - this causes a re-render
            runHasData.current = false;
            setPendingResumeData(data);
            setShouldAutoResume(true);
        } else {
            // No file and no data - this project needs a source file
            console.log("⚠️ Project has no source file, redirecting to create new project...");
            setStatus('loading');
            setTimeout(() => {
                router.push('/projects/new');
            }, 500);
        }
    }, [router]);

    useEffect(() => {
        // Load project when we have a valid route ID and haven't loaded yet
        if (routeProjectId && routeProjectId !== "new") {
            console.log("📌 useEffect triggered - routeProjectId:", routeProjectId, "projectId:", projectId);
            if (routeProjectId !== projectId) {
                setProjectId(routeProjectId);
                loadExistingProject(routeProjectId);
            }
        }
    }, [routeProjectId, projectId, loadExistingProject]);

    useEffect(() => {
        if (status === 'processing' && !artifacts.includes(currentModule)) {
            const timer = setTimeout(() => {
                setSubStep(s => (s + 1) % 5);
            }, 800);
            return () => clearTimeout(timer);
        }
    }, [status, currentModule, subStep, artifacts]);

    const resolveDownloadUrl = (value?: string | null) => {
        if (!value) return null;
        if (value.startsWith("http://") || value.startsWith("https://")) return value;
        const filename = value.split(/[/\\]/).pop();
        return filename ? `${API_BASE}/download/${filename}` : null;
    };

    const deliverableFallbacks: Record<string, string> = {
        specs: "/deliverables/Specs_V1.pdf",
        sourcing: "/deliverables/Liste_Sourcing.xlsx",
        tco: "/deliverables/Rapport_TCO.json",
        businessplan: "/deliverables/Business_Plan.pdf",
        catalogue: "/deliverables/Catalogue_Produits.pdf",
        layout2d: "/deliverables/layout_square.png",
        model3d: "/models/factory1.glb",
        video: "/deliverables/Presentation_HD.mp4",
    };

    const getArtifactDownloadUrl = (moduleType?: string | null) => {
        if (!moduleType) return null;
        if (moduleType === "businessplan") {
            return resolveDownloadUrl(businessPlanData?.download_url) || deliverableFallbacks.businessplan;
        }
        if (moduleType === "catalogue") {
            return resolveDownloadUrl(catalogData?.pdf_download_url || catalogData?.html_download_url) || deliverableFallbacks.catalogue;
        }
        if (moduleType === "layout2d") {
            return resolveDownloadUrl(
                layoutData?.layout_realistic_clean_url ||
                layoutData?.layout_realistic_url ||
                layoutData?.layout_2d_url
            ) || deliverableFallbacks.layout2d;
        }
        if (moduleType === "video") {
            return resolveDownloadUrl(videoData?.video_url) || deliverableFallbacks.video;
        }
        return deliverableFallbacks[moduleType] || null;
    };

    // ============================================================
    // WORKFLOW ORCHESTRATION
    // ============================================================
    const processWorkflow = async (currentProjectId: string, currentData: ProjectRecord | null, file: File | null) => {
        const { data: authData } = await supabase.auth.getSession();
        const userId = authData?.session?.user?.id;
        if (!userId) return;

        const activeSettings = loadPipelineSettings();

        runHasData.current = true;
        setStatus('processing');

        // UX Helper
        const runPlaceholderStep = async (idx: number) => {
            if (idx < 0) return;
            setCurrentModule(idx);
            setSelectedModule(idx);
            setSubStep(0);
            await new Promise(r => setTimeout(r, 800));
            setArtifacts(prev => [...new Set([...prev, idx])]);
        };
        const markArtifact = (idx: number) => setArtifacts(prev => [...new Set([...prev, idx])]);

        try {
            // STEP 1: Upload (if new file)
            if (file) {
                console.log("📤 Uploading file...");
                const { error: uploadError } = await uploadFileToBucket(currentProjectId, file);
                if (uploadError) console.warn("⚠️ File upload failed:", uploadError.message);
            }

            const baseHeaders: HeadersInit = { "x-user-id": userId, "x-project-id": currentProjectId };
            const jsonHeaders: HeadersInit = { "Content-Type": "application/json", ...baseHeaders };

            // =====================================================
            // MODULE 1: EXTRACTION
            // =====================================================
            let m1Data = currentData?.module1_data;
            const idxSpecs = getModuleIndex("specs");

            if (!m1Data) {
                if (idxSpecs >= 0) {
                    setCurrentModule(idxSpecs);
                    setSelectedModule(idxSpecs);
                    setSubStep(0);
                }

                let body: any;
                let headers = { ...baseHeaders };

                if (file) {
                    const fd = new FormData();
                    fd.append('file', file);
                    fd.append('project_id', currentProjectId);
                    fd.append('settings', JSON.stringify(activeSettings));
                    body = fd;
                } else {
                    headers = { ...headers, "Content-Type": "application/json" };
                    body = JSON.stringify({ project_id: currentProjectId, settings: activeSettings });
                }

                const res = await fetch(`${API_BASE}/api/module1/process`, { method: 'POST', headers, body });
                const json = await res.json();
                if (!res.ok) throw new Error(json.error || "Module 1 failed");
                m1Data = json.data || json;

                await updateProject(currentProjectId, { module1_data: m1Data, status: "specs_complete" });
            }
            setExtractedData(m1Data);
            if (idxSpecs >= 0) markArtifact(idxSpecs);

            // =====================================================
            // MODULE 4: SOURCING
            // =====================================================
            let m4Data = currentData?.module4_data;
            const idxSourcing = getModuleIndex("sourcing");
            const idxEmail = getModuleIndex("email");
            const idxCalls = getModuleIndex("calls");

            if (activeSettings.enableSourcing && idxSourcing >= 0) {
                if (!m4Data && m1Data) {
                    setModule4Loading(true);
                    setCurrentModule(idxSourcing);
                    setSelectedModule(idxSourcing);

                    const res = await fetch(`${API_BASE}/api/module4/enrich`, {
                        method: 'POST', headers: jsonHeaders,
                        body: JSON.stringify({ ...m1Data, project_id: currentProjectId, pipeline_settings: activeSettings })
                    });
                    const json = await res.json();
                    if (!res.ok) throw new Error(json.error);
                    m4Data = json;
                    await updateProject(currentProjectId, { module4_data: m4Data, status: "sourcing_complete" });
                    setModule4Loading(false);
                }
                setModule4Data(m4Data);
                markArtifact(idxSourcing);

                if (!currentData?.module4_data) {
                    await runPlaceholderStep(idxEmail);
                    await runPlaceholderStep(idxCalls);
                } else {
                    if (idxEmail >= 0) markArtifact(idxEmail);
                    if (idxCalls >= 0) markArtifact(idxCalls);
                }
            }

            // =====================================================
            // MODULE 6: TCO
            // =====================================================
            let tcoJson = currentData?.module6_data;
            const idxTco = getModuleIndex("tco");

            if (activeSettings.enableTco && m4Data && idxTco >= 0) {
                if (!tcoJson) {
                    setTcoLoading(true);
                    setCurrentModule(idxTco);
                    setSelectedModule(idxTco);
                    const res = await fetch(`${API_BASE}/api/module6/tco-from-sourcing`, {
                        method: 'POST', headers: jsonHeaders,
                        body: JSON.stringify({ ...m1Data, ...m4Data, project_id: currentProjectId })
                    });
                    const json = await res.json();
                    tcoJson = json;
                    await updateProject(currentProjectId, { module6_data: tcoJson, status: "tco_complete" });
                    setTcoLoading(false);
                }
                setTcoData(tcoJson);
                markArtifact(idxTco);
            }

            // =====================================================
            // MODULE 7: BUSINESS PLAN & PITCH
            // =====================================================
            let bpJson = currentData?.module7_business;
            let pitchJson = currentData?.module7_pitch;
            const idxBusinessPlan = getModuleIndex("businessplan");

            if (tcoJson && (activeSettings.enableBusinessPlan || activeSettings.enablePitchDeck) && idxBusinessPlan >= 0) {
                if ((!bpJson && activeSettings.enableBusinessPlan) || (!pitchJson && activeSettings.enablePitchDeck)) {
                    setBusinessPlanLoading(true);
                    setCurrentModule(idxBusinessPlan);
                    setSelectedModule(idxBusinessPlan);

                    if (activeSettings.enableBusinessPlan && !bpJson) {
                        const res = await fetch(`${API_BASE}/api/module7/business-plan`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify(tcoJson) });
                        bpJson = await res.json();
                        await updateProject(currentProjectId, { module7_business: bpJson });
                    }
                    if (activeSettings.enablePitchDeck && !pitchJson) {
                        const res = await fetch(`${API_BASE}/api/module7/pitch-deck`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify(tcoJson) });
                        pitchJson = await res.json();
                        await updateProject(currentProjectId, { module7_pitch: pitchJson });
                    }
                    setBusinessPlanLoading(false);
                }
                setBusinessPlanData(bpJson);
                setPitchDeckData(pitchJson);
                markArtifact(idxBusinessPlan);
            }

            // =====================================================
            // MODULE 9: CATALOG
            // =====================================================
            let catalogJson = currentData?.module9_data;
            const idxCatalogue = getModuleIndex("catalogue");

            if (activeSettings.enableCatalog && idxCatalogue >= 0 && m1Data && m4Data) {
                if (!catalogJson) {
                    setCatalogLoading(true);
                    setCurrentModule(idxCatalogue);
                    setSelectedModule(idxCatalogue);
                    const res = await fetch(`${API_BASE}/api/module9/catalog`, {
                        method: 'POST', headers: jsonHeaders,
                        body: JSON.stringify({ module1_data: m1Data, module4_data: m4Data, output_format: activeSettings.catalogFormat, project_id: currentProjectId })
                    });
                    catalogJson = await res.json();
                    await updateProject(currentProjectId, { module9_data: catalogJson });
                    setCatalogLoading(false);
                }
                setCatalogData(catalogJson);
                markArtifact(idxCatalogue);
            }

            // =====================================================
            // MODULE 2: LAYOUT
            // =====================================================
            let layoutJson = currentData?.module2_data;
            const idxLayout2d = getModuleIndex("layout2d");
            const idxModel3d = getModuleIndex("model3d");

            if (idxLayout2d >= 0 && m1Data) {
                if (!layoutJson) {
                    setLayoutLoading(true);
                    setCurrentModule(idxLayout2d);
                    setSelectedModule(idxLayout2d);
                    const res = await fetch(`${API_BASE}/api/module2/layout`, {
                        method: 'POST', headers: jsonHeaders,
                        body: JSON.stringify({ ...m1Data, project_id: currentProjectId, pipeline_settings: activeSettings })
                    });
                    layoutJson = await res.json();

                    // Upload layout files to Supabase from frontend
                    if (layoutJson && currentProjectId) {
                        const { uploadLayoutFilesToSupabase } = await import("@/lib/supabaseStorageUpload");
                        try {
                            const supabaseUrls = await uploadLayoutFilesToSupabase(currentProjectId, {
                                layout_2d_url: layoutJson.layout_2d_url as string | undefined,
                                layout_3d_url: layoutJson.layout_3d_url as string | undefined,
                                layout_dxf_url: layoutJson.layout_dxf_url as string | undefined,
                                layout_realistic_url: layoutJson.layout_realistic_url as string | undefined,
                                layout_realistic_clean_url: layoutJson.layout_realistic_clean_url as string | undefined,
                            });
                            // Merge Supabase URLs into layoutJson
                            layoutJson = { ...layoutJson, ...supabaseUrls };
                            console.log("✅ Layout files uploaded to Supabase:", supabaseUrls);
                        } catch (uploadError) {
                            console.warn("⚠️ Failed to upload layout files to Supabase:", uploadError);
                        }
                    }

                    await updateProject(currentProjectId, { module2_data: layoutJson, status: "layout_complete" });
                    setLayoutLoading(false);
                }
                setLayoutData(layoutJson);
                markArtifact(idxLayout2d);

                if (!currentData?.module2_data) {
                    await runPlaceholderStep(idxModel3d);
                } else {
                    if (idxModel3d >= 0) markArtifact(idxModel3d);
                }
            }

            // =====================================================
            // MODULE 3: VIDEO
            // =====================================================
            let videoJson = currentData?.module3_data;
            const idxVideo = getModuleIndex("video");

            if (idxVideo >= 0 && layoutJson) {
                if (!videoJson) {
                    setVideoLoading(true);
                    setCurrentModule(idxVideo);
                    setSelectedModule(idxVideo);
                    const res = await fetch(`${API_BASE}/api/module3/video`, {
                        method: 'POST', headers: jsonHeaders,
                        body: JSON.stringify({ ...layoutJson, project_id: currentProjectId, pipeline_settings: activeSettings })
                    });
                    videoJson = await res.json();
                    await updateProject(currentProjectId, { module3_data: videoJson, status: "complete" });
                    setVideoLoading(false);
                }
                setVideoData(videoJson);
                markArtifact(idxVideo);
            }

            console.log("🎉 Workflow complete / synced");
            setStatus('finished');

        } catch (e) {
            console.error("Workflow Error", e);
            setStatus('idle');
            setModule4Loading(false);
            setTcoLoading(false);
            setBusinessPlanLoading(false);
            setCatalogLoading(false);
            setLayoutLoading(false);
            setVideoLoading(false);
        }
    };

    // Auto-resume workflow when shouldAutoResume state becomes true
    useEffect(() => {
        if (!shouldAutoResume || !pendingResumeData) {
            return;
        }

        console.log("🔄 Auto-resume triggered via state!");
        console.log("   - pendingResumeData.id:", pendingResumeData.id);
        console.log("   - source_file_path:", pendingResumeData.source_file_path);
        console.log("   - module1_data:", !!pendingResumeData.module1_data);

        // Clear the flags immediately to prevent re-triggering
        setShouldAutoResume(false);
        runHasData.current = true;

        // Call processWorkflow with the pending data
        console.log("🚀 Starting processWorkflow...");
        processWorkflow(pendingResumeData.id, pendingResumeData, null);

        // Clear pending data
        setPendingResumeData(null);
    }, [shouldAutoResume, pendingResumeData]);

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
        const url = getArtifactDownloadUrl(MODULES[idx]?.type);
        if (url) window.open(url, '_blank', 'noopener,noreferrer');
    };

    const handleDownloadAll = () => {
        downloadableArtifacts.forEach(idx => {
            const url = getArtifactDownloadUrl(MODULES[idx]?.type);
            if (url) window.open(url, '_blank', 'noopener,noreferrer');
        });
    };

    // 2D Layout Image URL - prefer Supabase signed URLs, fallback to backend proxy
    const layoutImageUrl = layoutLoading ? null : (
        layoutData?.layout_realistic_clean_supabase_url ||
        layoutData?.layout_realistic_supabase_url ||
        layoutData?.layout_2d_supabase_url ||
        resolveDownloadUrl(
            layoutData?.layout_realistic_clean_url ||
            layoutData?.layout_realistic_url ||
            layoutData?.layout_2d_url
        )
    ) || "/deliverables/layout_square.png";

    const videoUrl = videoLoading ? null : resolveDownloadUrl(videoData?.video_url);

    // 3D Model URL - prefer Supabase signed URL, fallback to backend proxy
    const pipelineModelUrl = layoutLoading ? null : (
        layoutData?.layout_3d_supabase_url ||
        resolveDownloadUrl(layoutData?.layout_3d_url)
    );

    const selectedModuleItem = MODULES[selectedModule];
    const activeStagePrimary = MODULES[currentModule];
    const completedPhases = Math.max(artifacts.length, status === 'finished' ? MODULES.length : 0);
    const overallProgress = Math.round((completedPhases / MODULES.length) * 100);
    const isSelectedProcessing = status === 'processing' && selectedModule === currentModule && !artifacts.includes(currentModule);
    const isSelectedDone = artifacts.includes(selectedModule) || status === 'finished' || selectedModule < currentModule;
    const selectedProgress = isSelectedProcessing ? (subStep / 4) * 100 : isSelectedDone ? 100 : 0;
    const displayArtifacts = status === 'finished' ? MODULES.map((_, idx) => idx) : artifacts;
    const deliverableTypes = new Set(["specs", "sourcing", "tco", "businessplan", "catalogue", "layout2d", "model3d", "video"]);
    const downloadableArtifacts = displayArtifacts.filter(idx => deliverableTypes.has(MODULES[idx]?.type));

    return (
        <>
            <style>{fontStyle}</style>
            <div className="flex h-screen bg-[#F8FAFC] overflow-hidden font-sans text-slate-900 selection:bg-indigo-100">
                {/* LEFT SIDEBAR */}
                <aside className="w-80 bg-white border-r border-slate-200 flex flex-col z-20 shadow-[4px_0_24px_rgba(0,0,0,0.02)]">
                    <div className="p-8 h-24 border-b border-slate-100 flex items-center gap-4 cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => router.push('/')}>
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
                            const isDone = displayArtifacts.includes(idx);
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
                                        isAvailable ? "cursor-pointer" : "cursor-not-allowed opacity-50"
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
                                    <div className="absolute inset-0 bg-indigo-500 rounded-full animate-ping opacity-75" />
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
                                <div className="text-base font-black text-indigo-300 font-mono">{overallProgress}%</div>
                            </motion.div>
                        </div>
                    )}
                </aside>

                {/* CENTER PANEL */}
                <main className="flex-1 flex flex-col relative overflow-hidden bg-[#F8FAFC]">
                    <header className="h-24 border-b border-slate-200 flex items-center justify-between px-10 z-10 bg-white/80 backdrop-blur-md">
                        <div className="flex items-center gap-4">
                            <div className={`h-2.5 w-2.5 rounded-full ring-4 ring-opacity-20 ${['processing', 'uploading', 'loading', 'resuming'].includes(status) ? 'bg-indigo-500 ring-indigo-500 animate-pulse' : 'bg-slate-300 ring-slate-300'}`} />
                            <h2 className="text-xs font-extrabold text-slate-500 uppercase tracking-widest">
                                {status === 'idle' ? "Prêt" : status === 'uploading' ? "Téléchargement..." : status === 'loading' ? "Chargement..." : status === 'resuming' ? "Reprise en cours..." : status === 'finished' ? "Terminé" : "Traitement IA"}
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
                        {status === 'uploading' || status === 'loading' || status === 'resuming' || status === 'idle' ? (
                            <div className="h-full w-full flex flex-col items-center justify-center">
                                <Loader2 size={48} className="text-indigo-600 animate-spin mb-4" />
                                <h3 className="text-xl font-bold text-slate-800">
                                    {status === 'loading' || status === 'idle' ? 'Chargement du projet' : status === 'resuming' ? 'Reprise du traitement' : 'Analyse du PDF'}
                                </h3>
                                <p className="text-slate-500">
                                    {status === 'loading' || status === 'idle' ? 'Récupération depuis Supabase...' : status === 'resuming' ? 'Continuation depuis la dernière étape...' : 'Veuillez patienter...'}
                                </p>
                            </div>
                        ) : (
                            <div className="h-full w-full bg-white rounded-4xl border border-slate-200 shadow-sm overflow-auto relative">
                                <AnimatePresence mode="wait">
                                    <motion.div key={selectedModule} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full w-full">
                                        {isSelectedProcessing ? (
                                            <ModuleLoadingView module={selectedModuleItem} progress={selectedProgress} />
                                        ) : (
                                            <>
                                                {selectedModuleItem.type === 'specs' && <SpecsView data={extractedData} />}
                                                {selectedModuleItem.type === 'layout2d' && <Layout2DView imageUrl={layoutImageUrl} />}
                                                {selectedModuleItem.type === 'model3d' && <Model3DView pipelineModelUrl={pipelineModelUrl} />}
                                                {selectedModuleItem.type === 'video' && <VideoView progress={selectedProgress} videoUrl={videoUrl} />}
                                                {selectedModuleItem.type === 'sourcing' && <SourcingView progress={selectedProgress} data={extractedData} module4Data={module4Data} loading={module4Loading} />}
                                                {selectedModuleItem.type === 'email' && <EmailCenterView />}
                                                {selectedModuleItem.type === 'calls' && <CallsNegotiationView />}
                                                {selectedModuleItem.type === 'tco' && <TcoView data={tcoData} loading={tcoLoading} />}
                                                {selectedModuleItem.type === 'businessplan' && <BusinessPlanView businessPlanData={businessPlanData} pitchDeckData={pitchDeckData} loading={businessPlanLoading} />}
                                                {selectedModuleItem.type === 'catalogue' && <CatalogueTechniqueView pdfUrl={catalogData?.pdf_download_url} htmlUrl={catalogData?.html_download_url} />}
                                            </>
                                        )}
                                    </motion.div>
                                </AnimatePresence>
                            </div>
                        )}
                    </div>
                </main>

                {/* RIGHT SIDEBAR */}
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
                            {downloadableArtifacts.slice().reverse().map(idx => (
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
                                            <button onClick={() => handleArtifactDownload(idx)} className="w-8 h-8 flex items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-indigo-600 transition-colors">
                                                <Download size={14} />
                                            </button>
                                        </div>
                                    </div>
                                    <div className="text-xs font-extrabold text-slate-800 truncate mb-2">{MODULES[idx].file}</div>
                                    <div className="flex items-center gap-1.5">
                                        <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Prêt</span>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                    {status === 'finished' && (
                        <div className="p-6 border-t border-slate-100 bg-white">
                            <button onClick={handleDownloadAll} className="w-full bg-indigo-600 text-white py-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200">
                                <Download size={16} /> TOUT TÉLÉCHARGER
                            </button>
                        </div>
                    )}
                </aside>
            </div>
        </>
    );
}
