import { useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { Project } from "@/types/dashboard";

export function useDashboardProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [signedIn, setSignedIn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
        
        if (sessionError) {
          console.error("Session error:", sessionError);
          setSignedIn(false);
          setProjects([]);
          setLoading(false);
          return;
        }
        
        const session = sessionData?.session;
        if (!session) {
          console.log("No active session");
          setSignedIn(false);
          setProjects([]);
          setLoading(false);
          return;
        }
        
        setSignedIn(true);
        const userId = session.user.id;
        console.log("Loading projects for user:", userId);

        // Query projects owned by the current user
        // Note: Using simplified schema columns only
        const { data, error: fetchError } = await supabase
          .from("projects")
          .select("id,name,status,created_at,owner_id,source_filename")
          .eq("owner_id", userId)
          .order("created_at", { ascending: false });

        console.log("Query result:", { data, fetchError, userId });

        if (fetchError) {
          console.error("Failed to load projects:", fetchError);
          setError(fetchError.message || "Erreur de chargement");
          setProjects([]);
          setLoading(false);
          return;
        }

        const formatted = (data || []).map((row) => {
          const date = row.created_at
            ? new Date(row.created_at).toLocaleDateString("fr-FR", { month: "short", year: "numeric" })
            : "—";
          return {
            id: row.id,
            name: row.name || row.source_filename || "Projet sans nom",
            client: "—",
            location: "—",
            date,
            status: row.status || "draft",
            type: "Industrial",
          } as Project;
        });
        setProjects(formatted);
        setLoading(false);
        console.log("Loaded projects:", formatted);
      } catch (err) {
        console.error("Unexpected error loading projects:", err);
        setError("Erreur inattendue");
        setProjects([]);
        setLoading(false);
      }
    };

    load();
    const { data: sub } = supabase.auth.onAuthStateChange(() => load());
    return () => {
      sub.subscription.unsubscribe();
    };
  }, []);

  const emptyState = useMemo(() => {
    if (loading) return "Chargement des projets...";
    if (error) return `Erreur: ${error}`;
    if (!signedIn) return "Connectez-vous pour accéder à vos projets.";
    return "Aucun projet pour le moment. Créez votre premier projet.";
  }, [loading, error, signedIn]);

  const handleDeleteProject = async (projectId: string): Promise<boolean> => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5000";
      const response = await fetch(`${backendUrl}/api/projects/${projectId}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        console.error("Failed to delete project:", data.error);
        setError(data.error || "Failed to delete project");
        return false;
      }

      // Remove the project from local state
      setProjects((prev) => prev.filter((p) => p.id !== projectId));
      console.log("Project deleted successfully:", data);
      return true;
    } catch (err) {
      console.error("Error deleting project:", err);
      setError("Failed to delete project");
      return false;
    }
  };

  return { projects, loading, signedIn, error, emptyState, deleteProject: handleDeleteProject };
}
