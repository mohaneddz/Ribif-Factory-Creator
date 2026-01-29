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
      const { data: sessionData } = await supabase.auth.getSession();
      const session = sessionData?.session;
      if (!session) {
        setSignedIn(false);
        setProjects([]);
        setLoading(false);
        return;
      }
      setSignedIn(true);

      const { data, error: fetchError } = await supabase
        .from("projects")
        .select("id,name,client,location_city,location_country,status,project_type,created_at")
        .order("created_at", { ascending: false });

      if (fetchError) {
        setError(fetchError.message);
        setProjects([]);
        setLoading(false);
        return;
      }

      const formatted = (data || []).map((row) => {
        const location = [row.location_city, row.location_country].filter(Boolean).join(", ");
        const date = row.created_at
          ? new Date(row.created_at).toLocaleDateString("fr-FR", { month: "short", year: "numeric" })
          : "—";
        return {
          id: row.id,
          name: row.name,
          client: row.client || "—",
          location: location || "—",
          date,
          status: row.status || "draft",
          type: row.project_type || "Industrial",
        } as Project;
      });
      setProjects(formatted);
      setLoading(false);
      console.log("Loaded projects:", formatted);
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

  return { projects, loading, signedIn, error, emptyState };
}
