import { ArrowRight, Calendar, ExternalLink, MapPin, MonitorPlay, MoreVertical, Trash2, FileText } from "lucide-react";
import { motion } from "framer-motion";
import clsx from "clsx";
import { useState } from "react";

import { Project } from "@/types/dashboard";
import { StatusBadge } from "./StatusBadge";
import { getProjectIcon } from "@/utils/projectIcons";

// ... imports remain the same

interface ProjectCardProps {
  project: Project;
  index: number;
  onOpenTwin: (id: string) => void;
  onOpenProject: (id: string) => void;
  onRequestDelete?: (project: Project) => void;
}

const statusGradients: Record<string, string> = {
  live: "from-emerald-500/20 via-transparent to-transparent",
  draft: "from-slate-500/20 via-transparent to-transparent",
  study: "from-indigo-500/20 via-transparent to-transparent",
  archived: "from-slate-700/20 via-transparent to-transparent",
};

export const ProjectCard = ({ project, index, onOpenTwin, onOpenProject, onRequestDelete }: ProjectCardProps) => {
  const [showMenu, setShowMenu] = useState(false);

  const gradientClass = statusGradients[project.status] || statusGradients.draft;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      whileHover={{ y: -4 }}
      className={clsx(
        "relative group bg-white dark:bg-white/5 rounded-[2rem] overflow-hidden",
        "border border-slate-200 dark:border-white/10 hover:border-indigo-500/50 dark:hover:border-indigo-500/50",
        "shadow-lg shadow-slate-200/50 dark:shadow-black/20 hover:shadow-xl hover:shadow-indigo-500/10",
        "transition-all duration-300"
      )}
    >
      {/* Gradient accent based on status */}
      <div className={clsx("absolute inset-0 bg-gradient-to-br", gradientClass, "opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none")} />
      
      {/* Animated border glow on hover */}
      <div className="absolute inset-0 rounded-[2rem] opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
        <div className="absolute inset-[1px] rounded-[2rem] bg-gradient-to-r from-indigo-500/0 via-indigo-500/10 to-purple-500/0" />
      </div>

      <div className="relative p-8">
        {/* Header with icon and menu */}
        <div className="flex justify-between items-start mb-6">
          <div className="flex items-center gap-5">
            <motion.div
              whileHover={{ scale: 1.05, rotate: -3 }}
              className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-gradient-to-br dark:from-indigo-500/10 dark:to-purple-500/10 flex items-center justify-center text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-500/20 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-900/20"
            >
              {getProjectIcon("Default")}
            </motion.div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                {project.name}
              </h2>
              <div className="flex items-center gap-3 mt-1.5 text-sm text-slate-500 dark:text-slate-400 font-medium">
                  {project.source_filename && (
                    <span className="flex items-center gap-1.5">
                        <FileText size={14} className="text-indigo-600 dark:text-indigo-400" />
                        <span className="truncate max-w-[200px]">{project.source_filename}</span>
                    </span>
                  )}
                  <span className="flex items-center gap-1.5">
                    <Calendar size={14} className="text-indigo-600 dark:text-indigo-400" />
                    {project.date}
                  </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <StatusBadge status={project.status} />
            
            {/* Action menu */}
            <div className="relative">
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-white/10 text-slate-400 dark:text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors opacity-0 group-hover:opacity-100"
              >
                <MoreVertical size={18} />
              </button>
              
              {showMenu && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="absolute right-0 top-full mt-1 w-40 bg-white dark:bg-[#13141c] rounded-xl shadow-xl border border-slate-200 dark:border-white/10 py-1 z-20"
                >
                  <button
                    onClick={() => {
                      onRequestDelete?.(project);
                      setShowMenu(false);
                    }}
                    className="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 flex items-center gap-2 font-medium"
                  >
                    <Trash2 size={14} />
                    Supprimer
                  </button>
                </motion.div>
              )}
            </div>
          </div>
        </div>

        {/* Progress indicator */}
        <div className="mb-8">
            <div className="flex items-center justify-between text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
              <span>Progression</span>
              <span className="text-indigo-600 dark:text-indigo-400">{project.progress}%</span>
            </div>
            <div className="h-2 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden border border-slate-100 dark:border-white/5">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${project.progress}%` }}
                transition={{ duration: 1, delay: index * 0.1 }}
                className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-full shadow-[0_0_10px_rgba(99,102,241,0.5)]"
              />
            </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3">
          <button
            onClick={() => onOpenProject(project.id)}
            className={clsx(
              "h-12 rounded-xl bg-transparent border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300 font-bold flex items-center justify-center gap-2",
              "hover:border-indigo-500/50 hover:text-indigo-600 dark:hover:text-white hover:bg-indigo-50 dark:hover:bg-indigo-500/10",
              "transition-all active:scale-[0.98]",
              project.status === "live" ? "px-6" : "flex-1"
            )}
          >
            <ExternalLink size={18} />
            {project.status === "live" ? "Détails" : "Ouvrir le projet"}
          </button>

          {project.status === "live" && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onOpenTwin(project.id)}
              className="flex-1 h-12 px-6 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 hover:shadow-indigo-600/30 transition-shadow group"
            >
              <MonitorPlay size={18} />
              <span>Jumeau Digital</span>
              <ArrowRight size={18} className="opacity-0 -ml-4 group-hover:opacity-100 group-hover:ml-0 transition-all" />
            </motion.button>
          )}
        </div>
      </div>
    </motion.div>
  );
};
