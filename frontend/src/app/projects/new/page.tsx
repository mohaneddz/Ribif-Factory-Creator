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

      // Step 2: Check for duplicates
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
    <div className="min-h-screen bg-[#0b0c10] text-white">
      {/* Background Effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-indigo-500/15 rounded-full blur-[140px]" />
        <div className="absolute bottom-1/4 left-1/4 w-[400px] h-[400px] bg-purple-500/10 rounded-full blur-[120px]" />
      </div>

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between px-8 py-6 border-b border-white/10">
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={20} />
          <span className="font-medium">Retour</span>
        </button>
        <h1 className="text-lg font-bold">Nouveau Projet</h1>
        <div className="w-24" /> {/* Spacer for centering */}
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-2xl mx-auto px-6 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h2 className="text-4xl font-black mb-4">Créer un nouveau projet</h2>
          <p className="text-slate-400 text-lg">
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
              className={`relative cursor-pointer rounded-3xl border-2 border-dashed p-16 text-center transition-all duration-300 ${
                dragActive
                  ? "border-indigo-500 bg-indigo-500/10"
                  : "border-slate-600 hover:border-indigo-500/50 hover:bg-white/5"
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
                  className={`w-20 h-20 rounded-2xl flex items-center justify-center transition-colors ${
                    dragActive ? "bg-indigo-500 text-white" : "bg-slate-800 text-slate-400"
                  }`}
                >
                  <Upload size={36} />
                </div>
                <div>
                  <p className="text-xl font-semibold mb-2">
                    {dragActive ? "Déposez votre fichier" : "Glissez-déposez votre PDF"}
                  </p>
                  <p className="text-slate-500">
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
              className="rounded-3xl border border-slate-700 bg-slate-900/50 p-8"
            >
              {/* File Preview */}
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-xl bg-indigo-500/20 flex items-center justify-center">
                    <FileText size={28} className="text-indigo-400" />
                  </div>
                  <div>
                    <p className="font-semibold text-lg">{file.name}</p>
                    <p className="text-slate-500 text-sm">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                {workflow.step === "idle" && (
                  <button
                    onClick={resetWorkflow}
                    className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
                  >
                    <X size={20} className="text-slate-400" />
                  </button>
                )}
              </div>

              {/* Project Name Input */}
              {workflow.step === "idle" && (
                <div className="mb-6">
                  <label className="block text-sm font-semibold text-slate-400 mb-2">
                    Nom du projet
                  </label>
                  <input
                    type="text"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder="Mon projet industriel"
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
              )}

              {/* Workflow Progress */}
              {workflow.step !== "idle" && workflow.step !== "error" && workflow.step !== "duplicate" && (
                <div className="mb-6">
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
                  className="mb-6 rounded-xl border border-red-500/40 bg-red-500/10 p-4"
                >
                  <div className="flex items-start gap-3">
                    <AlertTriangle size={20} className="text-red-400 mt-0.5" />
                    <div>
                      <p className="font-semibold text-red-200">{workflow.message}</p>
                      <p className="text-red-300/80 text-sm mt-1">{workflow.error}</p>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Duplicate State */}
              {workflow.step === "duplicate" && workflow.duplicateProject && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-6 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4"
                >
                  <div className="flex items-start gap-3">
                    <AlertTriangle size={20} className="text-amber-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="font-semibold text-amber-200">Projet existant détecté</p>
                      <p className="text-amber-300/80 text-sm mt-1">
                        Un projet avec ce fichier existe déjà: <strong>{workflow.duplicateProject.name}</strong>
                      </p>
                      <button
                        onClick={() => goToProject(workflow.duplicateProject!.id)}
                        className="mt-3 inline-flex items-center gap-2 text-amber-300 hover:text-amber-200 text-sm font-medium"
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
                  className="mb-6 rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-4"
                >
                  <div className="flex items-start gap-3">
                    <Check size={20} className="text-emerald-400 mt-0.5" />
                    <div>
                      <p className="font-semibold text-emerald-200">Projet créé avec succès!</p>
                      <p className="text-emerald-300/80 text-sm mt-1">
                        Votre projet est prêt pour l'analyse.
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3">
                {workflow.step === "idle" && (
                  <button
                    onClick={startWorkflow}
                    disabled={!projectName.trim()}
                    className="flex-1 py-4 px-6 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl font-bold text-lg transition-colors"
                  >
                    Créer le projet
                  </button>
                )}

                {(workflow.step === "error" || workflow.step === "duplicate") && (
                  <>
                    <button
                      onClick={resetWorkflow}
                      className="flex-1 py-4 px-6 bg-slate-800 hover:bg-slate-700 rounded-xl font-semibold flex items-center justify-center gap-2 transition-colors"
                    >
                      <RefreshCw size={18} />
                      Recommencer
                    </button>
                    {workflow.step === "duplicate" && workflow.duplicateProject && (
                      <button
                        onClick={() => goToProject(workflow.duplicateProject!.id)}
                        className="flex-1 py-4 px-6 bg-indigo-600 hover:bg-indigo-700 rounded-xl font-bold transition-colors"
                      >
                        Voir le projet
                      </button>
                    )}
                  </>
                )}

                {workflow.step === "success" && workflow.projectId && (
                  <button
                    onClick={() => goToProject(workflow.projectId!)}
                    className="flex-1 py-4 px-6 bg-indigo-600 hover:bg-indigo-700 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-colors"
                  >
                    Ouvrir le projet
                    <ExternalLink size={18} />
                  </button>
                )}

                {workflow.step !== "idle" &&
                  workflow.step !== "error" &&
                  workflow.step !== "duplicate" &&
                  workflow.step !== "success" && (
                    <div className="flex-1 py-4 px-6 bg-slate-800 rounded-xl font-semibold flex items-center justify-center gap-2 cursor-not-allowed">
                      <Loader2 size={18} className="animate-spin" />
                      Traitement...
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
          className="mt-8 p-6 rounded-2xl bg-slate-900/30 border border-slate-800"
        >
          <h3 className="font-semibold mb-3 text-slate-300">Exigences du document</h3>
          <ul className="space-y-2 text-slate-500 text-sm">
            <li className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
              Format PDF uniquement
            </li>
            <li className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
              Minimum {VALIDATION_CONFIG.MIN_PDF_CHARACTERS.toLocaleString()} caractères de contenu technique
            </li>
            <li className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
              Taille maximale: {VALIDATION_CONFIG.MAX_FILE_SIZE_MB}MB
            </li>
            <li className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
              Le document doit contenir des informations techniques suffisantes
            </li>
          </ul>
        </motion.div>
      </main>
    </div>
  );
}
