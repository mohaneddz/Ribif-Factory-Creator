import { Search } from "lucide-react";

import { Project } from "@/types/dashboard";
import { ProjectCard } from "./ProjectCard";

interface ProjectsListProps {
  projects: Project[];
  onOpenTwin: (id: string) => void;
  onOpenProject: (id: string) => void;
}

export const ProjectsList = ({ projects, onOpenTwin, onOpenProject }: ProjectsListProps) => {
  return (
    <div className="flex-1 flex flex-col relative z-10 border-r border-[var(--border-1)]">
      <header className="h-32 px-10 flex items-center justify-between bg-[var(--surface-1)] border-b border-[var(--border-1)]">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight mb-1 text-[var(--text-1)]">Projets</h1>
          <p className="text-[var(--text-2)] font-medium text-lg">Vue d'ensemble du parc</p>
        </div>

        <div className="w-80 bg-[var(--surface-2)] h-14 rounded-full flex items-center px-6 border border-transparent focus-within:border-indigo-500 focus-within:bg-[var(--surface-1)] focus-within:ring-4 focus-within:ring-indigo-50 transition-all">
          <Search size={20} className="text-[var(--text-2)]" />
          <input
            type="text"
            placeholder="Rechercher..."
            className="bg-transparent border-none outline-none w-full ml-3 text-lg font-medium placeholder-slate-400 text-[var(--text-1)]"
          />
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-10 space-y-6 bg-[var(--surface-0)]">
        {projects.map((project, index) => (
          <ProjectCard
            key={project.id}
            project={project}
            index={index}
            onOpenTwin={onOpenTwin}
            onOpenProject={onOpenProject}
          />
        ))}
      </div>
    </div>
  );
};
