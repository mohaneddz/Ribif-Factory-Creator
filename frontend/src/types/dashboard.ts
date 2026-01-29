export type ProjectStatus = "draft" | "live" | "study" | "archived" | string;

export type ProjectType = string;

export interface Project {
  id: string;
  name: string;
  client: string;
  location: string;
  date: string;
  status: ProjectStatus;
  type: ProjectType;
}
