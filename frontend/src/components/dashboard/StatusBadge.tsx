"use client";

import { motion } from "framer-motion";
import clsx from "clsx";

interface StatusBadgeProps {
  status: string;
}

const statusConfig: Record<string, { label: string; bgClass: string; textClass: string; dotClass: string }> = {
  live: {
    label: "En ligne",
    bgClass: "bg-emerald-500/10",
    textClass: "text-emerald-600",
    dotClass: "bg-emerald-500",
  },
  draft: {
    label: "Brouillon",
    bgClass: "bg-slate-500/10",
    textClass: "text-slate-600",
    dotClass: "bg-slate-400",
  },
  study: {
    label: "Étude",
    bgClass: "bg-indigo-500/10",
    textClass: "text-indigo-600",
    dotClass: "bg-indigo-500",
  },
  archived: {
    label: "Archivé",
    bgClass: "bg-slate-400/10",
    textClass: "text-slate-500",
    dotClass: "bg-slate-400",
  },
  processing: {
    label: "Traitement",
    bgClass: "bg-amber-500/10",
    textClass: "text-amber-600",
    dotClass: "bg-amber-500",
  },
};

export const StatusBadge = ({ status }: StatusBadgeProps) => {
  const config = statusConfig[status] || statusConfig.draft;

  return (
    <div
      className={clsx(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wide",
        config.bgClass,
        config.textClass
      )}
    >
      {status === "live" ? (
        <motion.span
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          className={clsx("w-2 h-2 rounded-full", config.dotClass)}
        />
      ) : (
        <span className={clsx("w-2 h-2 rounded-full", config.dotClass)} />
      )}
      {config.label}
    </div>
  );
};
