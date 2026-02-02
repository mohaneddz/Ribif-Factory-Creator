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
import { VoiceNegotiationView } from "@/sections/VoiceNegotiationView";
import { ModuleLoadingView } from "@/sections/ModuleLoadingView";
import { Layout2DView, Model3DView } from "@/sections/PlansView";
import { SpecsView } from "@/sections/SpecsView";
import { SourcingView } from "@/sections/SourcingView";
import { TcoView } from "@/sections/TcoView";
import { VideoView } from "@/sections/VideoView";
import { DigitalTwinView } from "@/sections/DigitalTwinView";
import { ErrorDisplay } from "@/components/ErrorDisplay";
import { API_BASE, MODULES, fontStyle } from "@/sections/constants";
import { supabase } from "@/lib/supabaseClient";
import { loadPipelineSettings } from "@/utils/pipelineSettings";
import {
    uploadFileToBucket,
    loadProject,
    updateProject,
    ProjectRecord,
} from "@/lib/projectService";

/**
 * Strip heavy image data from module1 payload before sending to module4.
 * This reduces payload from ~13MB to ~50KB by removing base64 images.
 */
function stripImagesForModule4(data: any): any {
    if (!data) return data;
    
    const stripped = JSON.parse(JSON.stringify(data)); // Deep clone
    
    // Strip from machines_production
    const machines = stripped?.stage_4_machines_equipements?.machines_production;
    if (Array.isArray(machines)) {
        stripped.stage_4_machines_equipements.machines_production = machines.map((m: any) => {
            if (!m || typeof m !== 'object') return m;
            const clean: any = {};
            for (const [key, value] of Object.entries(m)) {
                // Skip image fields with base64 data
                if (['image', 'image_url', 'image_data', 'image_base64', 'best_image_url', 'image_local_path'].includes(key)) {
                    if (typeof value === 'string' && (value.startsWith('data:image') || value.length > 10000)) {
                        continue;
                    }
                }
                // Clean assets.image_urls
                if (key === 'assets' && value && typeof value === 'object') {
                    const cleanAssets: any = {};
                    for (const [ak, av] of Object.entries(value as Record<string, unknown>)) {
                        if (ak === 'image_urls' && Array.isArray(av)) {
                            const cleanUrls = av.filter((u: any) => typeof u === 'string' && !u.startsWith('data:image') && u.length < 1000);
                            if (cleanUrls.length > 0) cleanAssets[ak] = cleanUrls;
                        } else {
                            cleanAssets[ak] = av;
                        }
                    }
                    clean[key] = cleanAssets;
                    continue;
                }
                clean[key] = value;
            }
            return clean;
        });
    }
    
    // Also strip from enriched_machines if present
    if (Array.isArray(stripped?.enriched_machines)) {
        stripped.enriched_machines = stripped.enriched_machines.map((m: any) => {
            if (!m || typeof m !== 'object') return m;
            const clean: any = {};
            for (const [key, value] of Object.entries(m)) {
                if (['image', 'image_url', 'image_data', 'image_base64', 'best_image_url', 'image_local_path'].includes(key)) {
                    if (typeof value === 'string' && (value.startsWith('data:image') || value.length > 10000)) {
                        continue;
                    }
                }
                clean[key] = value;
            }
            return clean;
        });
    }
    
    return stripped;
}

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

    // Error state
    const [error, setError] = useState<string | Error | null>(null);

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
            setError(error?.message || "Impossible de charger le projet");
            setStatus('idle');
            projectLoadedRef.current = false;
            return;
        }

        setError(null);
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
            completedArtifacts.push(getModuleIndex("pitchdeck"));
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
        // Strict check: only auto-resume if we have the actual storage path
        const hasSourceFile = !!data.source_file_path;
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
            // Reset progress when module changes (implied by dependency on currentModule)
            // But we need to handle the increment logic
            const interval = setInterval(() => {
                setSubStep(prev => {
                    if (prev >= 90) return prev; // Hold at 90% until complete
                    // Increment to reach 90% in ~15 seconds (15000ms)
                    // limit per 200ms step: 90 / (15000/200) = 90 / 75 = 1.2
                    return prev + 1.2;
                });
            }, 200);
            return () => clearInterval(interval);
        } else if (artifacts.includes(currentModule)) {
            setSubStep(100);
        } else {
            setSubStep(0);
        }
    }, [status, currentModule, artifacts]);

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
        businessplan: "/deliverables/Business_Plan.xlsx",
        pitchdeck: "/deliverables/Pitch_Deck.pdf",
        catalogue: "/deliverables/Catalogue_Produits.pdf",
        layout2d: "/deliverables/layout_square.dxf",
        model3d: "/deliverables/factory_model.glb",
        video: "/deliverables/Presentation_HD.mp4",
    };

    const getArtifactDownloadUrl = (moduleType?: string | null) => {
        if (!moduleType) return null;
        if (moduleType === "businessplan") {
            return resolveDownloadUrl(businessPlanData?.download_url) || deliverableFallbacks.businessplan;
        }
        if (moduleType === "pitchdeck") {
            return resolveDownloadUrl(pitchDeckData?.pdf_download_url) || deliverableFallbacks.pitchdeck;
        }
        if (moduleType === "catalogue") {
            return resolveDownloadUrl(catalogData?.data?.pdf_download_url || catalogData?.data?.html_download_url || catalogData?.pdf_download_url || catalogData?.html_download_url) || deliverableFallbacks.catalogue;
        }
        if (moduleType === "layout2d") {
            // Return DXF file for 2D layout, not PNG
            return resolveDownloadUrl(
                layoutData?.layout_dxf_supabase_url ||
                layoutData?.layout_dxf_url
            ) || deliverableFallbacks.layout2d;
        }
        if (moduleType === "model3d") {
            return resolveDownloadUrl(
                layoutData?.layout_3d_supabase_url ||
                layoutData?.layout_3d_url
            ) || deliverableFallbacks.model3d;
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
        const markArtifact = async (idx: number) => {
            const moduleType = MODULES[idx]?.type;
            setArtifacts(prev => {
                const next = [...new Set([...prev, idx])];
                // Persist to Supabase if project exists
                if (currentProjectId && moduleType) {
                    const completedTypes = next.map(i => MODULES[i]?.type).filter(Boolean);
                    updateProject(currentProjectId, { completed_modules: completedTypes });
                }
                return next;
            });
        };

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
                    body = JSON.stringify({
                        project_id: currentProjectId,
                        settings: activeSettings,
                        source_file_path: currentData?.source_file_path,
                        source_filename: currentData?.source_filename
                    });
                }

                let res;
                try {
                    res = await fetch(`${API_BASE}/api/module1/process`, { method: 'POST', headers, body });
                } catch (fetchError: any) {
                    console.error("❌ Network Error (Module 1):", fetchError);
                    throw new Error(`Backend connection failed: ${fetchError.message || 'Network error'}. Please ensure the backend server is running on ${API_BASE}`);
                }

                if (!res.ok) {
                    const text = await res.text();
                    console.error("❌ HTTP Error (Module 1):", res.status, res.statusText, text.substring(0, 500));
                    throw new Error(`Module 1 failed with status ${res.status}: ${text.substring(0, 200) || res.statusText}`);
                }

                const text = await res.text();
                let json;
                try {
                    json = JSON.parse(text);
                } catch (e) {
                    console.error("❌ JSON Parse Failed (Module 1). Raw response:", text.substring(0, 1000));
                    throw new Error("Server response was not valid JSON. The backend may have crashed or returned an error page.");
                }
                
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

                    let res;
                    try {
                        // Strip heavy image data before sending (reduces ~13MB to ~50KB)
                        const lightPayload = stripImagesForModule4(m1Data);
                        console.log("📦 Module 4 payload size:", JSON.stringify(lightPayload).length / 1024, "KB");
                        
                        res = await fetch(`${API_BASE}/api/module4/enrich`, {
                            method: 'POST', headers: jsonHeaders,
                            body: JSON.stringify({ ...lightPayload, project_id: currentProjectId, pipeline_settings: activeSettings })
                        });
                    } catch (fetchError: any) {
                        setModule4Loading(false);
                        console.error("❌ Network Error (Module 4):", fetchError);
                        throw new Error(`Module 4: Backend connection failed - ${fetchError.message || 'Network error'}`);
                    }
                    
                    if (!res.ok) {
                        const text = await res.text();
                        setModule4Loading(false);
                        console.error("❌ HTTP Error (Module 4):", res.status, text.substring(0, 500));
                        throw new Error(`Module 4 failed with status ${res.status}`);
                    }

                    const text = await res.text();
                    let json;
                    try {
                        json = JSON.parse(text);
                    } catch (e) {
                         setModule4Loading(false);
                         console.error("❌ JSON Parse Failed (Module 4). Raw response:", text.substring(0, 1000));
                         throw new Error("Module 4: Server response not valid JSON.");
                    }

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
                    
                    let res;
                    try {
                        // Strip images from m1Data before sending (reduces payload significantly)
                        const lightM1Data = stripImagesForModule4(m1Data);
                        console.log("📦 Module 6 payload size:", JSON.stringify({ ...lightM1Data, ...m4Data }).length / 1024, "KB");
                        
                        res = await fetch(`${API_BASE}/api/module6/tco-from-sourcing`, {
                            method: 'POST', headers: jsonHeaders,
                            body: JSON.stringify({ ...lightM1Data, ...m4Data, project_id: currentProjectId })
                        });
                    } catch (fetchError: any) {
                        setTcoLoading(false);
                        console.error("❌ Network Error (Module 6):", fetchError);
                        throw new Error(`Module 6: Backend connection failed - ${fetchError.message || 'Network error'}`);
                    }
                    
                    if (!res.ok) {
                        const text = await res.text();
                        setTcoLoading(false);
                        console.error("❌ HTTP Error (Module 6):", res.status, text.substring(0, 500));
                        throw new Error(`Module 6 failed with status ${res.status}`);
                    }

                    const text = await res.text();
                    let json;
                    try {
                        json = JSON.parse(text);
                    } catch (e) {
                        setTcoLoading(false);
                        console.error("❌ JSON Parse Failed (Module 6). Raw response:", text.substring(0, 1000));
                        throw new Error("Module 6: Server response not valid JSON.");
                    }

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
            const idxPitchDeck = getModuleIndex("pitchdeck");

            if (tcoJson && (activeSettings.enableBusinessPlan || activeSettings.enablePitchDeck) && idxBusinessPlan >= 0) {
                if ((!bpJson && activeSettings.enableBusinessPlan) || (!pitchJson && activeSettings.enablePitchDeck)) {
                    setBusinessPlanLoading(true);
                    setCurrentModule(idxBusinessPlan);
                    setSelectedModule(idxBusinessPlan);

                    if (activeSettings.enableBusinessPlan && !bpJson) {
                        const res = await fetch(`${API_BASE}/api/module7/business-plan`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify(tcoJson) });
                        // Simple robust parsing for these too
                         try {
                             bpJson = await res.json();
                             await updateProject(currentProjectId, { module7_business: bpJson });
                         } catch (e) { console.error("BP parse error", e); throw new Error("Business Plan API invalid JSON"); }
                    }
                    if (activeSettings.enablePitchDeck && !pitchJson) {
                        const res = await fetch(`${API_BASE}/api/module7/pitch-deck`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify(tcoJson) });
                         try {
                              pitchJson = await res.json();
                              await updateProject(currentProjectId, { module7_pitch: pitchJson });
                         } catch (e) { console.error("Pitch parse error", e); throw new Error("Pitch Deck API invalid JSON"); }
                    }
                    setBusinessPlanLoading(false);
                }
                setBusinessPlanData(bpJson);
                setPitchDeckData(pitchJson);
                markArtifact(idxBusinessPlan);
                if (pitchJson && idxPitchDeck >= 0) {
                    markArtifact(idxPitchDeck);
                }
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
                    try {
                         catalogJson = await res.json();
                         await updateProject(currentProjectId, { module9_data: catalogJson });
                    } catch (e) { console.error("Catalog parse error", e); throw new Error("Catalog API invalid JSON"); }
                    
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
                    
                    let res;
                    try {
                        res = await fetch(`${API_BASE}/api/module2/layout`, {
                            method: 'POST', headers: jsonHeaders,
                            body: JSON.stringify({ ...m1Data, project_id: currentProjectId, pipeline_settings: activeSettings })
                        });
                    } catch (fetchError: any) {
                        setLayoutLoading(false);
                        console.error("❌ Network Error (Module 2):", fetchError);
                        throw new Error(`Module 2: Backend connection failed - ${fetchError.message || 'Network error'}`);
                    }
                    
                    if (!res.ok) {
                        const text = await res.text();
                        setLayoutLoading(false);
                        console.error("❌ HTTP Error (Module 2):", res.status, text.substring(0, 500));
                        throw new Error(`Module 2 failed with status ${res.status}`);
                    }

                    const text = await res.text();
                    let json;
                    try {
                        json = JSON.parse(text);
                    } catch (e) {
                         setLayoutLoading(false);
                         console.error("❌ JSON Parse Failed (Module 2). Raw response:", text.substring(0, 1000));
                         throw new Error("Module 2: Server response not valid JSON.");
                    }
                    
                    layoutJson = json;

                    // Backend now handles Supabase upload and returns the URLs in layoutJson
                    console.log("✅ Layout generated and uploaded by backend:", layoutJson);

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
                    
                    let res;
                    try {
                        res = await fetch(`${API_BASE}/api/module3/video`, {
                            method: 'POST', headers: jsonHeaders,
                            body: JSON.stringify({ ...layoutJson, project_id: currentProjectId, pipeline_settings: activeSettings })
                        });
                    } catch (fetchError: any) {
                        setVideoLoading(false);
                        console.error("❌ Network Error (Module 3):", fetchError);
                        throw new Error(`Module 3: Backend connection failed - ${fetchError.message || 'Network error'}`);
                    }
                    
                    if (!res.ok) {
                        const text = await res.text();
                        setVideoLoading(false);
                        console.error("❌ HTTP Error (Module 3):", res.status, text.substring(0, 500));
                        throw new Error(`Module 3 failed with status ${res.status}`);
                    }

                    const text = await res.text();
                    let json;
                    try {
                        json = JSON.parse(text);
                    } catch (e) {
                         setVideoLoading(false);
                         console.error("❌ JSON Parse Failed (Module 3). Raw response:", text.substring(0, 1000));
                         throw new Error("Module 3: Server response not valid JSON.");
                    }
                    videoJson = json;
                    
                    await updateProject(currentProjectId, { module3_data: videoJson, status: "complete" });
                    setVideoLoading(false);
                }
                setVideoData(videoJson);
                markArtifact(idxVideo);
            }

            // =====================================================
            // MODULE: DIGITAL TWIN
            // =====================================================
            const idxTwin = getModuleIndex("twin");
            if (idxTwin >= 0 && layoutJson) {
                setCurrentModule(idxTwin);
                setSelectedModule(idxTwin);
                setSubStep(0);
                await new Promise(r => setTimeout(r, 1500)); // Simulaton de l'initialisation
                markArtifact(idxTwin);
            }

            console.log("🎉 Workflow complete / synced");
            setStatus('finished');

        } catch (e) {
            console.error("Workflow Error", e);
            setError(e instanceof Error ? e : String(e));
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

    const regenerateOne = async (idx: number) => {
        // Clear error state
        setError(null);
        
        // Clear local state for the module to trigger UI updates
        const moduleType = MODULES[idx]?.type;
        const updates: Partial<ProjectRecord> = {};

        if (moduleType === 'specs') { setExtractedData(null); updates.module1_data = null; }
        if (moduleType === 'sourcing') { setModule4Data(null); updates.module4_data = null; }
        if (moduleType === 'tco') { setTcoData(null); updates.module6_data = null; }
        if (moduleType === 'businessplan') { setBusinessPlanData(null); setPitchDeckData(null); updates.module7_business = null; updates.module7_pitch = null; }
        if (moduleType === 'pitchdeck') { setPitchDeckData(null); updates.module7_pitch = null; }
        if (moduleType === 'catalogue') { setCatalogData(null); updates.module9_data = null; }
        if (moduleType === 'layout2d') { setLayoutData(null); updates.module2_data = null; }
        if (moduleType === 'video') { setVideoData(null); updates.module3_data = null; }
        if (moduleType === 'twin') { updates.status = "layout_complete"; } // Digital twin is real-time, no persistent data but needs a status

        if (projectId && Object.keys(updates).length > 0) {
            await updateProject(projectId, updates);
        }

        setArtifacts(prev => prev.filter(i => i !== idx));
        setCurrentModule(idx);
        setSelectedModule(idx);
        setSubStep(0);
        setStatus('processing');
        runHasData.current = true;

        // Build cleaned project data and trigger workflow
        const cleanedData = {
            ...projectData,
            ...updates,
        } as ProjectRecord;

        // Trigger workflow with cleaned data
        setPendingResumeData(cleanedData);
        setShouldAutoResume(true);
    };

    const regenerateAll = async () => {
        // Clear error state
        setError(null);
        
        if (!projectId) return;

        try {
            console.log("🔄 Resetting project data...");
            setStatus('loading');

            const res = await fetch(`${API_BASE}/api/projects/${projectId}/reset`, { method: 'POST' });
            if (!res.ok) {
                const errText = await res.text();
                console.error("❌ Reset failed with status:", res.status, res.statusText, errText);
                throw new Error(`Failed to reset project: ${res.status} ${res.statusText}`);
            }

            console.log("✅ Project reset on backend. restart frontend flow...");

            // Clear all local data
            setExtractedData(null);
            setModule4Data(null);
            setTcoData(null);
            setBusinessPlanData(null);
            setPitchDeckData(null);
            setCatalogData(null);
            setLayoutData(null);
            setVideoData(null);

            setArtifacts([]);
            setCurrentModule(0);
            setSelectedModule(0);
            setSubStep(0);

            // Construct cleaned data object
            const cleanedData = {
                ...projectData,
                module1_data: null,
                module2_data: null,
                module3_data: null,
                module4_data: null,
                module6_data: null,
                module7_business: null,
                module7_pitch: null,
                module9_data: null,
                status: 'uploaded'
            } as ProjectRecord;

            setProjectData(cleanedData);

            // Trigger auto-resume
            setPendingResumeData(cleanedData);
            setShouldAutoResume(true);
            setStatus('processing');

        } catch (e) {
            console.error("Reset failed", e);
            // Even if it failed, we might be in a bad state, but let's go back to finished for safety or stay in loading
            setStatus('finished'); // Revert to finished so user can try again
            alert("Failed to reset project. Please ensure backend is running and up to date.");
        }
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
    const selectedProgress = isSelectedProcessing ? subStep : isSelectedDone ? 100 : 0;
    const displayArtifacts = status === 'finished' ? MODULES.map((_, idx) => idx) : artifacts;
    const deliverableTypes = new Set(["specs", "sourcing", "tco", "businessplan", "pitchdeck", "catalogue", "layout2d", "model3d", "video", "twin"]);
    const downloadableArtifacts = displayArtifacts.filter(idx => deliverableTypes.has(MODULES[idx]?.type));

    return (
        <>
            <style>{fontStyle}</style>
            <div className="flex h-screen bg-slate-50 dark:bg-[#0b0c10] overflow-hidden font-sans text-slate-900 dark:text-slate-100 selection:bg-indigo-100 transition-colors">
                {/* LEFT SIDEBAR */}
                <aside className="w-80 bg-white dark:bg-[#0b0c10] border-r border-slate-200 dark:border-white/5 flex flex-col z-20 shadow-[4px_0_24px_rgba(0,0,0,0.02)] transition-colors">
                    <div className="p-8 h-24 border-b border-slate-100 dark:border-white/5 flex items-center gap-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5 transition-colors" onClick={() => router.push('/')}>
                        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-200 dark:shadow-indigo-900/20">
                            <Building2 size={20} />
                        </div>
                        <div>
                            <span className="font-extrabold text-lg text-slate-900 dark:text-white tracking-tight block">RIBIF IA</span>
                            <div className="text-[10px] text-indigo-600 dark:text-indigo-400 font-bold uppercase tracking-wider">Manager v5.0</div>
                        </div>
                    </div>
                    <div className="flex-1 overflow-y-auto p-6 space-y-2">
                        <div className="px-2 py-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest flex justify-between">
                            Étapes du Workflow
                            {status === 'finished' && <RefreshCw size={12} className="cursor-pointer hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors" onClick={regenerateAll} />}
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
                                        isActive ? "bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-100 dark:border-indigo-500/20" : "hover:bg-slate-50 dark:hover:bg-white/5 border border-transparent",
                                        isAvailable ? "cursor-pointer" : "cursor-not-allowed opacity-50"
                                    )}
                                >
                                    {isActive && <div className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-600 dark:bg-indigo-500" />}
                                    <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border",
                                        isDone ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-100 dark:border-emerald-500/20" :
                                            isActive ? "bg-indigo-600 dark:bg-indigo-500 text-white border-indigo-600 dark:border-indigo-500" :
                                                "bg-white dark:bg-white/5 text-slate-400 dark:text-slate-500 border-slate-200 dark:border-white/10"
                                    )}>
                                        {isDone ? <Check size={16} strokeWidth={3} /> : <m.icon size={16} />}
                                    </div>
                                    <div className={clsx("text-sm font-bold truncate", isActive ? "text-indigo-900 dark:text-indigo-100" : "text-slate-600 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-white")}>{m.title}</div>
                                </button>
                            );
                        })}
                    </div>
                    {status === 'processing' && (
                        <div className="p-6 border-t border-slate-100 dark:border-white/5 bg-white dark:bg-[#0b0c10]">
                            <motion.div initial={{ y: 12, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="bg-slate-900 dark:bg-[#1f2937] text-white px-5 py-4 rounded-2xl flex items-center gap-4 shadow-lg shadow-slate-300/40 dark:shadow-none">
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
                <main className="flex-1 flex flex-col relative overflow-hidden bg-slate-50 dark:bg-[#0b0c10] transition-colors">
                    <header className="h-24 border-b border-slate-200 dark:border-white/5 flex items-center justify-between px-10 z-10 bg-white/80 dark:bg-[#0b0c10]/80 backdrop-blur-md transition-colors">
                        <div className="flex items-center gap-4">
                            <div className={`h-2.5 w-2.5 rounded-full ring-4 ring-opacity-20 ${['processing', 'uploading', 'loading', 'resuming'].includes(status) ? 'bg-indigo-500 ring-indigo-500 animate-pulse' : 'bg-slate-300 dark:bg-slate-600 ring-slate-300 dark:ring-slate-600'}`} />
                            <h2 className="text-xs font-extrabold text-slate-500 dark:text-slate-400 uppercase tracking-widest">
                                {status === 'idle' ? "Prêt" : status === 'uploading' ? "Téléchargement..." : status === 'loading' ? "Chargement..." : status === 'resuming' ? "Reprise en cours..." : status === 'finished' ? "Terminé" : "Traitement IA"}
                            </h2>
                        </div>
                        <div className="flex gap-4">
                            {status === 'finished' && (
                                <button onClick={regenerateAll} className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 hover:border-indigo-300 dark:hover:border-indigo-500 text-slate-600 dark:text-slate-300 px-6 py-2.5 rounded-full text-xs font-bold flex items-center gap-2 transition-all shadow-sm">
                                    <RefreshCw size={14} /> Relancer
                                </button>
                            )}
                        </div>
                    </header>

                    <div className="flex-1 p-6 relative overflow-y-auto">
                        {error ? (
                            <ErrorDisplay 
                                error={error}
                                onRetry={() => {
                                    setError(null);
                                    if (projectId) {
                                        projectLoadedRef.current = false;
                                        loadExistingProject(projectId);
                                    }
                                }}
                                compact={true}
                            />
                        ) : status === 'uploading' || status === 'loading' || status === 'resuming' || status === 'idle' ? (
                            <div className="h-full w-full flex flex-col items-center justify-center">
                                <Loader2 size={48} className="text-indigo-600 dark:text-indigo-500 animate-spin mb-4" />
                                <h3 className="text-xl font-bold text-slate-800 dark:text-white">
                                    {status === 'loading' || status === 'idle' ? 'Chargement du projet' : status === 'resuming' ? 'Reprise du traitement' : 'Analyse du PDF'}
                                </h3>
                                <p className="text-slate-500 dark:text-slate-400">
                                    {status === 'loading' || status === 'idle' ? 'Récupération depuis Supabase...' : status === 'resuming' ? 'Continuation depuis la dernière étape...' : 'Veuillez patienter...'}
                                </p>
                            </div>
                        ) : (
                            <div className="h-full w-full bg-white dark:bg-[#13141c] rounded-4xl border border-slate-200 dark:border-white/5 shadow-sm dark:shadow-none overflow-auto relative transition-colors">
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
                                                {selectedModuleItem.type === 'email' && <VoiceNegotiationView projectId={routeProjectId || ""} module4Data={module4Data} loading={module4Loading} />}
                                                {selectedModuleItem.type === 'tco' && <TcoView data={tcoData} loading={tcoLoading} />}
                                                {selectedModuleItem.type === 'businessplan' && <BusinessPlanView businessPlanData={businessPlanData} pitchDeckData={pitchDeckData} loading={businessPlanLoading} />}
                                                {selectedModuleItem.type === 'pitchdeck' && <BusinessPlanView businessPlanData={businessPlanData} pitchDeckData={pitchDeckData} loading={businessPlanLoading} />}
                                                {selectedModuleItem.type === 'catalogue' && <CatalogueTechniqueView pdfUrl={catalogData?.data?.pdf_download_url || catalogData?.pdf_download_url} htmlUrl={catalogData?.data?.html_download_url || catalogData?.html_download_url} />}
                                                {selectedModuleItem.type === 'twin' && <DigitalTwinView pipelineModelUrl={pipelineModelUrl} />}
                                            </>
                                        )}
                                    </motion.div>
                                </AnimatePresence>
                            </div>
                        )}
                    </div>
                </main>

                {/* RIGHT SIDEBAR */}
                <aside className="w-80 bg-white dark:bg-[#0b0c10] border-l border-slate-200 dark:border-white/5 flex flex-col z-20 shadow-[-4px_0_24px_rgba(0,0,0,0.02)] transition-colors">
                    <div className="h-24 p-8 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                        <h2 className="text-xs font-extrabold text-slate-500 dark:text-slate-400 uppercase tracking-widest">Livrables</h2>
                        <span className="bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-300 px-2 py-1 rounded-md text-[10px] font-bold">{downloadableArtifacts.length} fichiers</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50/50 dark:bg-[#13141c]/50">
                        <AnimatePresence>
                            {downloadableArtifacts.length === 0 && (
                                <div className="h-40 border-2 border-dashed border-slate-200 dark:border-white/10 rounded-2xl flex flex-col items-center justify-center p-6 text-center">
                                    <Info size={24} className="mb-2 text-slate-300 dark:text-slate-600" />
                                    <p className="text-xs font-bold text-slate-400 dark:text-slate-500">En attente de génération...</p>
                                </div>
                            )}
                            {downloadableArtifacts.slice().reverse().map(idx => (
                                <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                    className={clsx("bg-white dark:bg-[#1f2937] rounded-[20px] border p-4 transition-all group shadow-sm hover:shadow-md", selectedModule === idx ? "border-indigo-400 ring-4 ring-indigo-50 dark:ring-indigo-900/20" : "border-slate-200 dark:border-white/5")}>
                                    <div className="flex justify-between items-start mb-3">
                                        <div onClick={() => handleModuleClick(idx)} className="w-10 h-10 bg-indigo-50 dark:bg-indigo-500/10 rounded-full flex items-center justify-center text-indigo-600 dark:text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white transition-colors cursor-pointer">
                                            <Eye size={18} />
                                        </div>
                                        <div className="flex gap-1">
                                            <button onClick={() => regenerateOne(idx)} className="w-8 h-8 flex items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                                                <RefreshCw size={14} />
                                            </button>
                                            <button onClick={() => handleArtifactDownload(idx)} className="w-8 h-8 flex items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                                                <Download size={14} />
                                            </button>
                                        </div>
                                    </div>
                                    <div className="text-xs font-extrabold text-slate-800 dark:text-slate-200 truncate mb-2">{MODULES[idx].file}</div>
                                    <div className="flex items-center gap-1.5">
                                        <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                                        <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Prêt</span>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                    {status === 'finished' && (
                        <div className="p-6 border-t border-slate-100 dark:border-white/5 bg-white dark:bg-[#0b0c10]">
                            <button onClick={handleDownloadAll} className="w-full bg-indigo-600 text-white py-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200 dark:shadow-indigo-900/20">
                                <Download size={16} /> TOUT TÉLÉCHARGER
                            </button>
                        </div>
                    )}
                </aside>
            </div>
        </>
    );
}
