"use client";

import { ProjectsList } from "./ProjectsList";
import { ActionPanel } from "./ActionPanel";
import { Project } from "@/types/dashboard";

interface DashboardShellProps {
  projects: Project[];
  onOpenTwin: (id: string) => void;
  onCreateProject: () => void;
  onOpenSettings: () => void;
  onOpenProject: (id: string) => void;
  onDeleteProject?: (id: string) => void;
}

export const DashboardShell = ({
  projects,
  onOpenTwin,
  onCreateProject,
  onOpenSettings,
  onOpenProject,
  onDeleteProject,
}: DashboardShellProps) => {
  return (
    <div className="flex h-screen w-full bg-slate-50 dark:bg-[#0b0c10] text-slate-900 dark:text-white overflow-hidden selection:bg-indigo-500/30">
      <ProjectsList
        projects={projects}
        onOpenTwin={onOpenTwin}
        onOpenProject={onOpenProject}
        onDeleteProject={onDeleteProject}
      />
      <ActionPanel onCreateProject={onCreateProject} onOpenSettings={onOpenSettings} />
    </div>
  );
};
