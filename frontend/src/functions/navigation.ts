import { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";

import { ROUTES } from "@/config/routes";

export const goToWorkflow = (router: AppRouterInstance) => {
  router.push(ROUTES.workflow);
};

export const goToWorkflowId = (router: AppRouterInstance, id: string) => {
  router.push(`${ROUTES.workflow}/${id}`);
};

export const goToCreateProject = (router: AppRouterInstance) => {
  router.push(ROUTES.createProject);
};

export const goToTwin = (router: AppRouterInstance, id?: string) => {
  if (id) {
    router.push(`${ROUTES.workflow}/${id}/twin`);
  } else {
    router.push(ROUTES.twin);
  }
};

export const goToSettings = (router: AppRouterInstance) => {
  router.push(ROUTES.settings);
};

export const goToLogin = (router: AppRouterInstance) => {
  router.push(ROUTES.login);
};

export const goToRegister = (router: AppRouterInstance) => {
  router.push(ROUTES.register);
};

export const goToDashboard = (router: AppRouterInstance) => {
  router.push(ROUTES.dashboard);
};
