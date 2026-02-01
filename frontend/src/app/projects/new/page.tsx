"use client";

import React, { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileText,
  AlertTriangle,
  Check,
  Loader2,
  ArrowLeft,
  X,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

import {
  computeFileHash,
  checkDuplicateProject,
  validateFileBasics,
  uploadFileToStorage,
  createProjectRecord,
  deleteProjectRecord,
  validateWithLlm,
} from "@/lib/fileValidation";
import { updateProject } from "@/lib/projectService";
import { UploadProgress } from "@/components/upload/UploadProgress";
import { VALIDATION_CONFIG } from "@/config/validation";

type Step =
  | "idle"
  | "hashing"
  | "checking-duplicate"
  | "uploading"
  | "validating"
  | "success"
  | "error"
  | "duplicate";

interface WorkflowState {
  step: Step;
  progress: number;
  message: string;
  error?: string;
  projectId?: string;
  duplicateProject?: { id: string; name: string };
}

export default function CreateProjectPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [projectName, setProjectName] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [workflow, setWorkflow] = useState<WorkflowState>({
    step: "idle",
    progress: 0,
    message: "",
  });

  const resetWorkflow = () => {
    setFile(null);
    setProjectName("");
    setWorkflow({ step: "idle", progress: 0, message: "" });
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  }, []);

  const handleFileSelect = (selectedFile: File) => {
    const validation = validateFileBasics(selectedFile);
    if (!validation.valid) {
      setWorkflow({
        step: "error",
        progress: 0,
        message: "Fichier invalide",
        error: validation.error,
      });
      return;
    }

    setFile(selectedFile);
    // Auto-generate project name from filename
    const baseName = selectedFile.name.replace(/\.[^/.]+$/, "");
    setProjectName(baseName);
    setWorkflow({ step: "idle", progress: 0, message: "" });
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };

  const startWorkflow = async () => {
    if (!file || !projectName.trim()) return;

    let createdProjectId: string | null = null;

    try {
      // Step 1: Compute file hash
      setWorkflow({
        step: "hashing",
        progress: 10,
        message: "Calcul de l'empreinte du fichier...",
      });
      const fileHash = await computeFileHash(file);

      // Step 2: Check for duplicates - SKIPPED per user request
      /*
      setWorkflow({
        step: "checking-duplicate",
        progress: 25,
        message: "Vérification des doublons...",
      });
      const duplicateCheck = await checkDuplicateProject(file.name, fileHash);

      if (duplicateCheck.exists) {
        setWorkflow({
          step: "duplicate",
          progress: 25,
          message: "Projet existant détecté",
          duplicateProject: {
            id: duplicateCheck.projectId!,
            name: duplicateCheck.projectName!,
          },
        });
        return;
      }
      */

      // Step 3: Create project record first (to get ID for storage path)
      setWorkflow({
        step: "uploading",
        progress: 35,
        message: "Création du projet...",
      });

      // Create a temporary record
      const createResult = await createProjectRecord(
        projectName.trim(),
        file.name,
        fileHash,
        "" // Will update after upload
      );

      if (createResult.error) {
        throw new Error(createResult.error);
      }
      createdProjectId = createResult.id;

      // Step 4: Upload file to storage
      setWorkflow({
        step: "uploading",
        progress: 50,
        message: "Upload du fichier en cours...",
      });

      const uploadResult = await uploadFileToStorage(file, createdProjectId, (progress) => {
        setWorkflow((prev) => ({
          ...prev,
          progress: 40 + progress * 0.3,
        }));
      });

      if (uploadResult.error || !uploadResult.path) {
        throw new Error(uploadResult.error || "Upload failed");
      }

      // CRITICAL FIX: Save the storage path to the project record
      await updateProject(createdProjectId, { source_file_path: uploadResult.path });

      // Step 5: Validate with LLM
      setWorkflow({
        step: "validating",
        progress: 75,
        message: "Validation IA du document...",
      });

      const validationResult = await validateWithLlm(file);

      if (!validationResult.valid) {
        // Delete the project record since validation failed
        await deleteProjectRecord(createdProjectId);
        throw new Error(
          validationResult.error ||
            "Le document ne contient pas suffisamment d'informations techniques"
        );
      }

      // Success!
      setWorkflow({
        step: "success",
        progress: 100,
        message: "Projet créé avec succès!",
        projectId: createdProjectId,
      });
    } catch (error) {
      // Clean up if we created a project
      if (createdProjectId && workflow.step !== "duplicate") {
        await deleteProjectRecord(createdProjectId).catch(() => {});
      }

      setWorkflow({
        step: "error",
        progress: 0,
        message: "Erreur lors de la création",
        error: error instanceof Error ? error.message : "Une erreur inattendue s'est produite",
      });
    }
  };

  const goToProject = (projectId: string) => {
    router.push(`/workflow/${projectId}`);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0b0c10] text-slate-900 dark:text-white transition-colors">
      {/* Background Effects */}
      <div className="fixed inset-0 pointer-events-none opacity-50 dark:opacity-100">
        <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-indigo-500/15 rounded-full blur-[140px]" />
        <div className="absolute bottom-1/4 left-1/4 w-[400px] h-[400px] bg-purple-500/10 rounded-full blur-[120px]" />
      </div>

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between px-8 py-6 border-b border-slate-200 dark:border-white/5 bg-white/80 dark:bg-[#0b0c10]/50 backdrop-blur-md transition-colors">
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
        >
          <ArrowLeft size={20} />
          <span className="font-medium">Retour</span>
        </button>
        <h1 className="text-lg font-bold text-slate-900 dark:text-white">Nouveau Projet</h1>
        <div className="w-24" /> {/* Spacer for centering */}
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-2xl mx-auto px-6 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h2 className="text-4xl font-black mb-4 tracking-tight text-slate-900 dark:text-white">Créer un nouveau projet</h2>
          <p className="text-slate-500 dark:text-slate-400 text-lg">
            Importez votre cahier des charges PDF pour démarrer l'analyse automatisée
          </p>
        </motion.div>

        {/* File Upload Zone */}
        <AnimatePresence mode="wait">
          {!file ? (
            <motion.div
              key="dropzone"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative cursor-pointer rounded-[2rem] border-2 border-dashed p-16 text-center transition-all duration-300 ${
                dragActive
                  ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-500/10 scale-[1.02]"
                  : "border-slate-300 dark:border-white/10 hover:border-indigo-500/50 hover:bg-slate-50 dark:hover:bg-white/5"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleInputChange}
                className="hidden"
              />
              <div className="flex flex-col items-center gap-4">
                <div
                  className={`w-20 h-20 rounded-2xl flex items-center justify-center transition-colors shadow-lg ${
                    dragActive ? "bg-indigo-500 text-white shadow-indigo-500/40" : "bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/10 text-slate-400 dark:text-slate-400"
                  }`}
                >
                  <Upload size={36} className={dragActive ? "text-white" : "text-slate-500 dark:text-slate-400"} />
                </div>
                <div>
                  <p className="text-xl font-bold mb-2 text-slate-900 dark:text-white">
                    {dragActive ? "Déposez votre fichier" : "Glissez-déposez votre PDF"}
                  </p>
                  <p className="text-slate-500 font-medium">
                    ou cliquez pour parcourir • PDF uniquement • Max {VALIDATION_CONFIG.MAX_FILE_SIZE_MB}MB
                  </p>
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="file-info"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-[2rem] border border-slate-200 dark:border-white/10 bg-white dark:bg-[#13141c]/80 backdrop-blur-md p-8 shadow-2xl shadow-slate-200/50 dark:shadow-black/20"
            >
              {/* File Preview */}
              <div className="flex items-start justify-between mb-8">
                <div className="flex items-center gap-5">
                  <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-lg shadow-indigo-500/10 dark:shadow-indigo-900/20">
                    <FileText size={32} className="text-indigo-600 dark:text-indigo-400" />
                  </div>
                  <div>
                    <p className="font-bold text-xl text-slate-900 dark:text-white">{file.name}</p>
                    <p className="text-slate-500 dark:text-slate-400 font-medium text-sm mt-0.5">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                {workflow.step === "idle" && (
                  <button
                    onClick={resetWorkflow}
                    className="p-3 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl transition-colors text-slate-400 hover:text-slate-900 dark:hover:text-white"
                  >
                    <X size={20} />
                  </button>
                )}
              </div>

              {/* Project Name Input */}
              {workflow.step === "idle" && (
                <div className="mb-8">
                  <label className="block text-sm font-bold text-slate-600 dark:text-slate-300 mb-3 ml-1">
                    Nom du projet
                  </label>
                  <input
                    type="text"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder="Mon projet industriel"
                    className="w-full px-5 py-4 bg-slate-50 dark:bg-[#0b0c10] border border-slate-200 dark:border-white/10 rounded-2xl text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-medium"
                  />
                </div>
              )}

              {/* Workflow Progress */}
              {workflow.step !== "idle" && workflow.step !== "error" && workflow.step !== "duplicate" && (
                <div className="mb-8">
                  <UploadProgress
                    progress={workflow.progress}
                    status={workflow.message}
                    isComplete={workflow.step === "success"}
                  />
                </div>
              )}

              {/* Error State */}
              {workflow.step === "error" && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-8 rounded-2xl border border-red-500/20 bg-red-500/10 p-5"
                >
                  <div className="flex items-start gap-4">
                    <div className="p-2 bg-red-500/20 rounded-lg">
                      <AlertTriangle size={20} className="text-red-600 dark:text-red-400" />
                    </div>
                    <div>
                      <p className="font-bold text-red-700 dark:text-red-200 text-lg">{workflow.message}</p>
                      <p className="text-red-600/70 dark:text-red-300/70 mt-1 leading-relaxed">{workflow.error}</p>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Duplicate State */}
              {workflow.step === "duplicate" && workflow.duplicateProject && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-8 rounded-2xl border border-amber-500/20 bg-amber-500/10 p-5"
                >
                  <div className="flex items-start gap-4">
                    <div className="p-2 bg-amber-500/20 rounded-lg">
                      <AlertTriangle size={20} className="text-amber-600 dark:text-amber-400" />
                    </div>
                    <div className="flex-1">
                      <p className="font-bold text-amber-700 dark:text-amber-200 text-lg">Projet existant détecté</p>
                      <p className="text-amber-600/70 dark:text-amber-300/70 mt-1 mb-4 leading-relaxed">
                        Un projet avec ce fichier existe déjà: <strong className="text-amber-700 dark:text-amber-200">{workflow.duplicateProject.name}</strong>
                      </p>
                      <button
                        onClick={() => goToProject(workflow.duplicateProject!.id)}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-700 dark:text-amber-200 text-sm font-semibold transition-colors"
                      >
                        Ouvrir le projet existant <ExternalLink size={14} />
                      </button>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Success State */}
              {workflow.step === "success" && workflow.projectId && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-8 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-5"
                >
                  <div className="flex items-start gap-4">
                     <div className="p-2 bg-emerald-500/20 rounded-lg">
                      <Check size={20} className="text-emerald-600 dark:text-emerald-400" />
                    </div>
                    <div>
                      <p className="font-bold text-emerald-700 dark:text-emerald-200 text-lg">Projet créé avec succès!</p>
                      <p className="text-emerald-600/70 dark:text-emerald-300/70 mt-1">
                        Votre projet est prêt pour l'analyse.
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-4">
                {workflow.step === "idle" && (
                  <button
                    onClick={startWorkflow}
                    disabled={!projectName.trim()}
                    className="flex-1 py-4 px-6 bg-gradient-to-r from-indigo-600 to-purple-600 hover:shadow-indigo-500/25 shadow-lg rounded-2xl font-bold text-lg text-white transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:grayscale disabled:cursor-not-allowed"
                  >
                    Créer le projet
                  </button>
                )}

                {(workflow.step === "error" || workflow.step === "duplicate") && (
                  <>
                    <button
                      onClick={resetWorkflow}
                      className="flex-1 py-4 px-6 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 border border-slate-200 dark:border-white/10 rounded-2xl font-bold text-slate-700 dark:text-white flex items-center justify-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98]"
                    >
                      <RefreshCw size={18} />
                      Recommencer
                    </button>
                    {workflow.step === "duplicate" && workflow.duplicateProject && (
                      <button
                        onClick={() => goToProject(workflow.duplicateProject!.id)}
                        className="flex-1 py-4 px-6 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl font-bold transition-all hover:scale-[1.02] active:scale-[0.98] shadow-lg shadow-indigo-600/20"
                      >
                        Voir le projet
                      </button>
                    )}
                  </>
                )}

                {workflow.step === "success" && workflow.projectId && (
                  <button
                    onClick={() => goToProject(workflow.projectId!)}
                    className="flex-1 py-4 px-6 bg-gradient-to-r from-indigo-600 to-purple-600 hover:shadow-indigo-500/25 shadow-lg rounded-2xl font-bold text-lg text-white flex items-center justify-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98]"
                  >
                    Ouvrir le projet
                    <ExternalLink size={20} />
                  </button>
                )}

                {workflow.step !== "idle" &&
                  workflow.step !== "error" &&
                  workflow.step !== "duplicate" &&
                  workflow.step !== "success" && (
                    <div className="flex-1 py-4 px-6 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-2xl font-semibold text-slate-500 dark:text-slate-300 flex items-center justify-center gap-3 cursor-not-allowed">
                      <Loader2 size={20} className="animate-spin text-indigo-600 dark:text-indigo-500" />
                      Traitement en cours...
                    </div>
                  )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Requirements Info */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-8 p-6 rounded-3xl bg-white dark:bg-[#13141c]/50 border border-slate-200 dark:border-white/5 backdrop-blur-sm shadow-lg shadow-slate-200/50 dark:shadow-none"
        >
          <h3 className="font-bold mb-4 text-slate-900 dark:text-white flex items-center gap-2">
             <div className="w-1.5 h-6 bg-indigo-500 rounded-full"/>
             Exigences du document
          </h3>
          <ul className="space-y-3 text-slate-500 dark:text-slate-400 text-sm font-medium">
            <li className="flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-600" />
              Format PDF uniquement
            </li>
            <li className="flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-600" />
              Minimum {VALIDATION_CONFIG.MIN_PDF_CHARACTERS.toLocaleString()} caractères de contenu technique
            </li>
            <li className="flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-600" />
              Taille maximale: {VALIDATION_CONFIG.MAX_FILE_SIZE_MB}MB
            </li>
            <li className="flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-600" />
              Le document doit contenir des informations techniques suffisantes
            </li>
          </ul>
        </motion.div>
      </main>
    </div>
  );
};
