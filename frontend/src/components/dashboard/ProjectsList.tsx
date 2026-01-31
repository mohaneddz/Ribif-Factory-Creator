"use client";

import { useState, useMemo } from "react";
import { Search, SlidersHorizontal, FolderOpen, Trash2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { Project } from "@/types/dashboard";
import { ProjectCard } from "./ProjectCard";

interface ProjectsListProps {
  projects: Project[];
  onOpenTwin: (id: string) => void;
  onOpenProject: (id: string) => void;
  onDeleteProject?: (id: string) => void;
}

type SortOption = "date-desc" | "date-asc" | "name-asc" | "name-desc";
type FilterStatus = "all" | "live" | "draft" | "study" | "archived";

const sortOptions: { value: SortOption; label: string }[] = [
  { value: "date-desc", label: "Plus récent" },
  { value: "date-asc", label: "Plus ancien" },
  { value: "name-asc", label: "Nom A-Z" },
  { value: "name-desc", label: "Nom Z-A" },
];

const filterOptions: { value: FilterStatus; label: string; color: string }[] = [
  { value: "all", label: "Tous", color: "bg-slate-100" },
  { value: "live", label: "En ligne", color: "bg-emerald-100" },
  { value: "draft", label: "Brouillon", color: "bg-slate-100" },
  { value: "study", label: "Étude", color: "bg-indigo-100" },
  { value: "archived", label: "Archivé", color: "bg-slate-100" },
];



export const ProjectsList = ({ projects, onOpenTwin, onOpenProject, onDeleteProject }: ProjectsListProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("date-desc");
  const [filterStatus, setFilterStatus] = useState<FilterStatus>("all");
  const [showFilters, setShowFilters] = useState(false);
  
  // Delete modal state
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!projectToDelete || !onDeleteProject) return;
    
    setIsDeleting(true);
    try {
      await onDeleteProject(projectToDelete.id);
      setProjectToDelete(null); // Close modal on success
    } catch (error) {
      alert("Échec de la suppression du projet. Veuillez réessayer.");
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredAndSortedProjects = useMemo(() => {
    // ... existing filtering logic (unchanged)
    let result = [...projects];

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(query) ||
          (p.source_filename && p.source_filename.toLowerCase().includes(query))
      );
    }

    // Filter by status
    if (filterStatus !== "all") {
      result = result.filter((p) => p.status === filterStatus);
    }

    // Sort
    result.sort((a, b) => {
      switch (sortBy) {
        case "date-desc":
          return new Date(b.date).getTime() - new Date(a.date).getTime();
        case "date-asc":
          return new Date(a.date).getTime() - new Date(b.date).getTime();
        case "name-asc":
          return a.name.localeCompare(b.name);
        case "name-desc":
          return b.name.localeCompare(a.name);
        default:
          return 0;
      }
    });

    return result;
  }, [projects, searchQuery, sortBy, filterStatus]);

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { all: projects.length };
    projects.forEach((p) => {
      counts[p.status] = (counts[p.status] || 0) + 1;
    });
    return counts;
  }, [projects]);

  return (
    <div className="flex-1 flex flex-col relative z-10 border-r border-slate-200 dark:border-white/5">
      {/* Header */}
      <header className="px-8 py-8 bg-white/80 dark:bg-[#0b0c10]/50 backdrop-blur-md border-b border-slate-200 dark:border-white/5 transition-colors">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">Projets</h1>
            <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">
              {projects.length} projet{projects.length > 1 ? "s" : ""} au total
            </p>
          </div>

          {/* Sort dropdown */}
          <div className="flex items-center gap-3">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="px-4 py-2.5 bg-slate-100 dark:bg-white/5 rounded-xl border border-slate-200 dark:border-white/10 focus:border-indigo-500 focus:outline-none text-sm font-medium text-slate-700 dark:text-white cursor-pointer hover:bg-slate-200 dark:hover:bg-white/10 transition-colors"
            >
              {sortOptions.map((option) => (
                <option key={option.value} value={option.value} className="bg-white dark:bg-[#0b0c10] text-slate-900 dark:text-white">
                  {option.label}
                </option>
              ))}
            </select>

            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`p-2.5 rounded-xl transition-colors ${
                showFilters
                  ? "bg-indigo-500/10 text-indigo-600 dark:text-indigo-300 border border-indigo-500/20"
                  : "bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-white/10 hover:bg-slate-200 dark:hover:bg-white/10 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <SlidersHorizontal size={20} />
            </button>
          </div>
        </div>

        {/* Search bar */}
        <div className="flex items-center gap-3 bg-slate-100 dark:bg-white/5 h-12 rounded-2xl px-5 border border-slate-200 dark:border-white/5 focus-within:border-indigo-500/50 focus-within:bg-white focus-within:dark:bg-white/10 focus-within:ring-4 focus-within:ring-indigo-500/10 transition-all">
          <Search size={20} className="text-slate-400 dark:text-slate-500" />
          <input
            type="text"
            placeholder="Rechercher un projet..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-transparent border-none outline-none w-full text-sm font-medium placeholder-slate-400 dark:placeholder-slate-500 text-slate-900 dark:text-white"
          />
        </div>

        {/* Filter chips */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="flex flex-wrap gap-2 pt-4">
                {filterOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setFilterStatus(option.value)}
                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                      filterStatus === option.value
                        ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                        : "bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10 hover:text-slate-900 dark:hover:text-white"
                    }`}
                  >
                    {option.label}
                    {statusCounts[option.value] !== undefined && (
                      <span className={`ml-1.5 ${filterStatus === option.value ? "text-indigo-200" : "text-slate-400 dark:text-slate-500"}`}>
                        ({statusCounts[option.value] || 0})
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      {/* Projects grid */}
      <div className="flex-1 overflow-y-auto p-8 bg-slate-50 dark:bg-[#0b0c10] custom-scrollbar transition-colors">
        {filteredAndSortedProjects.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center h-64 text-center"
          >
            <div className="w-20 h-20 rounded-3xl bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/5 flex items-center justify-center mb-6">
              <FolderOpen size={32} className="text-slate-400 dark:text-slate-600" />
            </div>
            <p className="text-lg font-semibold text-slate-900 dark:text-white">Aucun projet trouvé</p>
            <p className="text-sm text-slate-500 mt-2 max-w-xs mx-auto">
              {searchQuery
                ? "Essayez une autre recherche ou modifiez les filtres"
                : filterStatus !== "all"
                ? "Aucun projet ne correspond à ce statut"
                : "Commencez par créer votre premier projet industriel"}
            </p>
          </motion.div>
        ) : (
          <div className="space-y-5">
            {filteredAndSortedProjects.map((project, index) => (
              <ProjectCard
                key={project.id}
                project={project}
                index={index}
                onOpenTwin={onOpenTwin}
                onOpenProject={onOpenProject}
                onRequestDelete={(p) => setProjectToDelete(p)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {projectToDelete && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-slate-900/50 dark:bg-black/80 backdrop-blur-sm flex items-center justify-center z-[100]"
            onClick={() => !isDeleting && setProjectToDelete(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white dark:bg-[#13141c] border border-slate-200 dark:border-white/10 rounded-3xl p-8 max-w-md w-full mx-4 shadow-2xl relative"
            >
              <div className="flex items-center gap-4 mb-6">
                <div className="w-14 h-14 rounded-2xl bg-red-500/10 flex items-center justify-center border border-red-500/20">
                  <Trash2 size={24} className="text-red-500" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-900 dark:text-white">Supprimer le projet</h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Cette action est irréversible</p>
                </div>
              </div>
              
              <p className="text-slate-600 dark:text-slate-400 mb-8 leading-relaxed">
                Êtes-vous sûr de vouloir supprimer <strong className="text-slate-900 dark:text-white">{projectToDelete.name}</strong> ? 
                Tous les fichiers et données associés seront définitivement perdus.
              </p>

              <div className="flex gap-4">
                <button
                  onClick={() => setProjectToDelete(null)}
                  disabled={isDeleting}
                  className="flex-1 px-6 py-3.5 rounded-xl border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300 font-semibold hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-900 dark:hover:text-white transition-colors disabled:opacity-50"
                >
                  Annuler
                </button>
                <button
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="flex-1 px-6 py-3.5 rounded-xl bg-red-600 text-white font-semibold hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg shadow-red-900/20"
                >
                  {isDeleting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    </>
                  ) : (
                    <>
                      <Trash2 size={18} />
                      Supprimer
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
