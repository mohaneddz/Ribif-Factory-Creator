import { ArrowRight, Calendar, ExternalLink, MapPin, MonitorPlay } from "lucide-react";
import { motion } from "framer-motion";
import clsx from "clsx";

import { Project } from "@/types/dashboard";
import { StatusBadge } from "./StatusBadge";
import { getProjectIcon } from "@/utils/projectIcons";

interface ProjectCardProps {
  project: Project;
  index: number;
  onOpenTwin: (id: string) => void;
  onOpenProject: (id: string) => void;
}

export const ProjectCard = ({ project, index, onOpenTwin, onOpenProject }: ProjectCardProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="bg-[var(--surface-1)] rounded-4xl p-8 border border-[var(--border-1)] hover:border-indigo-300 hover:shadow-lg hover:shadow-slate-200/50 transition-all duration-300"
    >
      <div className="flex justify-between items-start mb-8">
        <div className="flex items-center gap-5">
          <div className="w-20 h-20 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600 border border-indigo-100 shadow-sm">
            {getProjectIcon(project.type)}
          </div>
          <div>
            <h2 className="text-2xl font-bold text-[var(--text-1)]">{project.name}</h2>
            <p className="text-base font-medium text-[var(--text-2)] mt-1 mb-3">{project.client}</p>

            <div className="flex items-center gap-6 text-slate-400 text-sm font-semibold">
              <span className="flex items-center gap-1.5">
                <MapPin size={16} className="text-indigo-400" /> {project.location}
              </span>
              <span className="flex items-center gap-1.5">
                <Calendar size={16} className="text-indigo-400" /> {project.date}
              </span>
            </div>
          </div>
        </div>
        <StatusBadge status={project.status} />
      </div>

      <div className="pt-6 border-t border-slate-50 flex gap-3">
        <button
          onClick={() => onOpenProject(project.id)}
          className={clsx(
            "h-14 rounded-2xl bg-white border-2 border-slate-100 text-slate-600 font-bold text-lg flex items-center justify-center hover:border-indigo-200 hover:text-indigo-600 hover:bg-indigo-50 transition-all active:scale-[0.99]",
            project.status === "live" ? "px-6 w-auto" : "w-full px-8"
          )}
        >
          {project.status === "live" ? (
            <span className="flex items-center gap-2">
              Détails <ExternalLink size={18} />
            </span>
          ) : (
            <span className="flex items-center gap-3">
              <ExternalLink size={20} /> Voir Détails
            </span>
          )}
        </button>

        {project.status === "live" && (
          <button
            onClick={() => onOpenTwin(project.id)}
            className="flex-1 h-14 px-8 rounded-2xl bg-indigo-600 text-white font-bold text-lg flex items-center justify-center gap-3 hover:bg-indigo-700 hover:shadow-lg hover:shadow-indigo-200 transition-all active:scale-[0.99] group"
          >
            <MonitorPlay size={20} />
            <span>Ouvrir Jumeau</span>
            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
          </button>
        )}
      </div>
    </motion.div>
  );
};
