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
    <div className="flex h-screen w-full bg-[var(--surface-0)] text-[var(--text-1)] overflow-hidden selection:bg-indigo-100">
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
