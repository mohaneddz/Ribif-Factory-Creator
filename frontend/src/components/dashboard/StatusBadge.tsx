import clsx from "clsx";

import { ProjectStatus } from "@/types/dashboard";

interface StatusBadgeProps {
  status: ProjectStatus;
}

export const StatusBadge = ({ status }: StatusBadgeProps) => {
  const isLive = status === "live";

  return (
    <div
      className={clsx(
        "px-4 py-2 rounded-full text-xs font-bold border flex items-center gap-2",
        isLive
          ? "bg-emerald-50 text-emerald-700 border-emerald-100"
          : "bg-indigo-50 text-indigo-700 border-indigo-100"
      )}
    >
      <div
        className={clsx(
          "w-2 h-2 rounded-full",
          isLive ? "bg-emerald-500 animate-pulse" : "bg-indigo-500"
        )}
      />
      {isLive ? "OPÉRATIONNEL" : "EN ÉTUDE"}
    </div>
  );
};
