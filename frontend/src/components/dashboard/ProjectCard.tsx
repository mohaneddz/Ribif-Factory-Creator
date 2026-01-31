import { ArrowRight, Calendar, ExternalLink, MapPin, MonitorPlay, MoreVertical, Trash2 } from "lucide-react";
import { motion } from "framer-motion";
import clsx from "clsx";
import { useState } from "react";

import { Project } from "@/types/dashboard";
import { StatusBadge } from "./StatusBadge";
import { getProjectIcon } from "@/utils/projectIcons";

interface ProjectCardProps {
  project: Project;
  index: number;
  onOpenTwin: (id: string) => void;
  onOpenProject: (id: string) => void;
  onDeleteProject?: (id: string) => void;
}

const statusGradients: Record<string, string> = {
  live: "from-emerald-500/20 via-transparent to-transparent",
  draft: "from-slate-500/20 via-transparent to-transparent",
  study: "from-indigo-500/20 via-transparent to-transparent",
  archived: "from-slate-700/20 via-transparent to-transparent",
};

export const ProjectCard = ({ project, index, onOpenTwin, onOpenProject, onDeleteProject }: ProjectCardProps) => {
  const [showMenu, setShowMenu] = useState(false);

  const gradientClass = statusGradients[project.status] || statusGradients.draft;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      whileHover={{ y: -4 }}
      className={clsx(
        "relative group bg-[var(--surface-1)] rounded-3xl overflow-hidden",
        "border border-[var(--border-1)] hover:border-indigo-300",
        "shadow-sm hover:shadow-xl hover:shadow-indigo-100/50",
        "transition-all duration-300"
      )}
    >
      {/* Gradient accent based on status */}
      <div className={clsx("absolute inset-0 bg-gradient-to-br", gradientClass, "opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none")} />
      
      {/* Animated border glow on hover */}
      <div className="absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
        <div className="absolute inset-[1px] rounded-3xl bg-gradient-to-r from-indigo-500/0 via-indigo-500/10 to-purple-500/0" />
      </div>

      <div className="relative p-8">
        {/* Header with icon and menu */}
        <div className="flex justify-between items-start mb-6">
          <div className="flex items-center gap-5">
            <motion.div
              whileHover={{ scale: 1.05, rotate: -3 }}
              className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-100 to-indigo-50 flex items-center justify-center text-indigo-600 border border-indigo-100 shadow-lg shadow-indigo-100/50"
            >
              {getProjectIcon(project.type)}
            </motion.div>
            <div>
              <h2 className="text-xl font-bold text-[var(--text-1)] group-hover:text-indigo-700 transition-colors">
                {project.name}
              </h2>
              <p className="text-sm font-medium text-[var(--text-2)] mt-0.5">
                {project.client}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <StatusBadge status={project.status} />
            
            {/* Action menu */}
            <div className="relative">
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-2 rounded-xl hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors opacity-0 group-hover:opacity-100"
              >
                <MoreVertical size={18} />
              </button>
              
              {showMenu && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="absolute right-0 top-full mt-1 w-40 bg-white rounded-xl shadow-xl border border-slate-200 py-1 z-20"
                >
                  <button
                    onClick={() => {
                      onDeleteProject?.(project.id);
                      setShowMenu(false);
                    }}
                    className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                  >
                    <Trash2 size={14} />
                    Supprimer
                  </button>
                </motion.div>
              )}
            </div>
          </div>
        </div>

        {/* Metadata */}
        <div className="flex flex-wrap items-center gap-4 text-slate-400 text-sm font-medium mb-6">
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-50">
            <MapPin size={14} className="text-indigo-400" />
            {project.location}
          </span>
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-50">
            <Calendar size={14} className="text-indigo-400" />
            {project.date}
          </span>
        </div>

        {/* Progress indicator for non-live projects */}
        {project.status !== "live" && project.status !== "archived" && (
          <div className="mb-6">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-2">
              <span>Progression</span>
              <span>En cours</span>
            </div>
            <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: project.status === "study" ? "60%" : "25%" }}
                transition={{ duration: 1, delay: index * 0.1 }}
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
              />
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3">
          <button
            onClick={() => onOpenProject(project.id)}
            className={clsx(
              "h-12 rounded-2xl bg-white border-2 border-slate-100 text-slate-600 font-bold flex items-center justify-center gap-2",
              "hover:border-indigo-200 hover:text-indigo-600 hover:bg-indigo-50",
              "transition-all active:scale-[0.98]",
              project.status === "live" ? "px-6" : "flex-1"
            )}
          >
            <ExternalLink size={18} />
            {project.status === "live" ? "Détails" : "Voir Détails"}
          </button>

          {project.status === "live" && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onOpenTwin(project.id)}
              className="flex-1 h-12 px-6 rounded-2xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold flex items-center justify-center gap-2 shadow-lg shadow-indigo-200/50 hover:shadow-indigo-300/60 transition-shadow group"
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
