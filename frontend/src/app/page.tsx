"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import LandingPage from "@/components/landing/LandingPage";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { useDashboardProjects } from "@/hooks/useDashboardProjects";
import { goToCreateProject, goToSettings, goToTwin, goToWorkflowId } from "@/functions/navigation";

export default function Home() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const { projects } = useDashboardProjects();

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setIsAuthenticated(!!session);
    };
    checkAuth();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_, session) => {
      setIsAuthenticated(!!session);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Loading state
  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen bg-[#0b0c10] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Show landing page for unauthenticated users
  if (!isAuthenticated) {
    return <LandingPage />;
  }

  // Show dashboard for authenticated users
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
