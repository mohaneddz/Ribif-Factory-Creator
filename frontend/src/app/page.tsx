"use client";

import { useRouter } from "next/navigation";
import { LogIn } from "lucide-react";

import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { goToCreateProject, goToLogin, goToRegister, goToSettings, goToTwin, goToWorkflowId } from "@/functions/navigation";
import { useDashboardProjects } from "@/hooks/useDashboardProjects";

export default function Dashboard() {
  const router = useRouter();
  const { projects, loading, signedIn, error, emptyState } = useDashboardProjects();

  if (!signedIn) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--surface-0)] text-[var(--text-1)] px-6">
        <div className="max-w-lg text-center space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-xs uppercase tracking-[0.3em] text-emerald-300">
            <LogIn size={14} /> Authentication required
          </div>
          <h1 className="text-4xl font-black">RIBIF Projects</h1>
          <p className="text-[var(--text-2)]">
            Vos projets résident dans Supabase. Connectez-vous pour charger les données.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={() => goToLogin(router)}
              className="rounded-full bg-emerald-500 px-6 py-3 text-sm font-bold text-slate-950 hover:bg-emerald-400"
            >
              Se connecter
            </button>
            <button
              onClick={() => goToRegister(router)}
              className="rounded-full border border-slate-700 px-6 py-3 text-sm font-bold text-[var(--text-1)] hover:border-emerald-400"
            >
              Créer un compte
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <DashboardShell
      projects={projects}
      onOpenTwin={(id) => goToTwin(router)}
      onOpenProject={(id) => goToWorkflowId(router, id)}
      onCreateProject={() => goToCreateProject(router)}
      onOpenSettings={() => goToSettings(router)}
    />
  );
}
