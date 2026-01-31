export type ProjectStatus = "draft" | "live" | "study" | "archived" | string;

export type ProjectType = string;

export interface Project {
  id: string;
  name: string;
  source_filename?: string;
  date: string;
  status: ProjectStatus;
  progress: number;
  completed_modules: string[];
}
