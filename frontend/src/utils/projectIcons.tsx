import { Activity, Box, Layers, Zap } from "lucide-react";

import { ProjectType } from "@/types/dashboard";

export const getProjectIcon = (type: ProjectType) => {
  switch (type) {
    case "Automobile":
      return <Box size={32} />;
    case "Pharmaceutique":
      return <Activity size={32} />;
    case "Énergie":
      return <Zap size={32} />;
    case "Logistique":
      return <Layers size={32} />;
    default:
      return <Box size={32} />;
  }
};
