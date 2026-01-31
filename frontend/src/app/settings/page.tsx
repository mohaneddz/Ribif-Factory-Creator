"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  SlidersHorizontal,
  Database,
  PackageOpen,
  RotateCcw,
  User,
  LogOut,
  Moon,
  Sun,
  Shield,
  Settings,
  ChevronRight,
  Mail,
  AlertTriangle,
} from "lucide-react";

import { supabase } from "@/lib/supabaseClient";
import {
  DEFAULT_PIPELINE_SETTINGS,
  PipelineSettings,
  loadPipelineSettings,
  savePipelineSettings,
} from "@/utils/pipelineSettings";
import { getTheme, setTheme, ThemeMode } from "@/utils/theme";

// ========================================
// COMPONENTS
// ========================================

const Toggle = ({
  checked,
  onChange,
  label,
  description,
  disabled = false,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
  description: string;
  disabled?: boolean;
}) => (
  <button
    onClick={onChange}
    disabled={disabled}
    className={`w-full rounded-2xl border px-5 py-4 text-left transition ${
      disabled
        ? "border-slate-200 bg-slate-50 opacity-60 cursor-not-allowed"
        : "border-slate-200 bg-white hover:border-indigo-300 hover:shadow-sm"
    }`}
  >
    <div className="flex items-center justify-between gap-4">
      <div>
        <div className="text-sm font-semibold text-slate-900">{label}</div>
        <p className="text-xs text-slate-500 mt-1">{description}</p>
      </div>
      <div
        className={`h-6 w-11 rounded-full transition flex-shrink-0 ${
          checked ? "bg-indigo-600" : "bg-slate-300"
        }`}
      >
        <div
          className={`h-5 w-5 mt-0.5 rounded-full bg-white shadow transition ${
            checked ? "translate-x-5 ml-0.5" : "translate-x-0.5"
          }`}
        />
      </div>
    </div>
  </button>
);

const SettingsCard = ({
  icon: Icon,
  title,
  subtitle,
  children,
  accentColor = "indigo",
}: {
  icon: React.ElementType;
  title: string;
  subtitle: string;
  children: React.ReactNode;
  accentColor?: "indigo" | "emerald" | "red" | "amber";
}) => {
  const colorClasses = {
    indigo: "bg-indigo-100 text-indigo-600",
    emerald: "bg-emerald-100 text-emerald-600",
    red: "bg-red-100 text-red-600",
    amber: "bg-amber-100 text-amber-600",
  };

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3 mb-5">
        <div className={`rounded-xl p-2.5 ${colorClasses[accentColor]}`}>
          <Icon size={20} />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-900">{title}</h2>
          <p className="text-xs text-slate-500">{subtitle}</p>
        </div>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
};

// ========================================
// MAIN COMPONENT
// ========================================

export default function SettingsPage() {
  const router = useRouter();
  const [settings, setSettings] = useState<PipelineSettings>(() => loadPipelineSettings());
  const [theme, setThemeState] = useState<ThemeMode>(() => getTheme());
  const [user, setUser] = useState<{ email: string; name?: string } | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  // Load user info
  useEffect(() => {
    const loadUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        setUser({
          email: session.user.email || "",
          name: session.user.user_metadata?.full_name,
        });
      }
    };
    loadUser();
  }, []);

  const updateSettings = (partial: Partial<PipelineSettings>) => {
    let next: PipelineSettings = { ...settings, ...partial };

    // Handle dependencies
    if (partial.enableBusinessPlan && !next.enableTco) next.enableTco = true;
    if (partial.enablePitchDeck && !next.enableTco) next.enableTco = true;
    if (partial.enableTco && !next.enableSourcing) next.enableSourcing = true;

    if (!next.enableSourcing) {
      next.enableTco = false;
      next.enableBusinessPlan = false;
      next.enablePitchDeck = false;
    }
    if (!next.enableTco) {
      next.enableBusinessPlan = false;
      next.enablePitchDeck = false;
    }

    setSettings(next);
    savePipelineSettings(next);
  };

  const updateTheme = (mode: ThemeMode) => {
    setThemeState(mode);
    setTheme(mode);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("ribif-theme-change", { detail: mode }));
    }
  };

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await supabase.auth.signOut();
      router.push("/");
    } catch (error) {
      console.error("Logout error:", error);
      setLoggingOut(false);
    }
  };

  const moduleSummary = useMemo(() => {
    const enabled = [
      settings.enableSourcing && "Sourcing",
      settings.enableTco && "TCO",
      settings.enableBusinessPlan && "Business Plan",
      settings.enablePitchDeck && "Pitch Deck",
      settings.enableCatalog && "Catalogue",
    ].filter(Boolean);
    return enabled.length ? enabled.join(" • ") : "Specs extraction uniquement";
  }, [settings]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 text-slate-600 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft size={20} />
            <span className="font-medium">Retour</span>
          </button>
          <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Settings size={20} />
            Paramètres
          </h1>
          <div className="w-24" />
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* Account Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0 }}
        >
          <SettingsCard
            icon={User}
            title="Compte"
            subtitle="Gérez votre profil et connexion"
            accentColor="indigo"
          >
            {user ? (
              <>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
                      {user.name?.[0] || user.email[0].toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      {user.name && (
                        <p className="font-semibold text-slate-900 truncate">{user.name}</p>
                      )}
                      <p className="text-sm text-slate-500 truncate flex items-center gap-1.5">
                        <Mail size={14} />
                        {user.email}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-semibold">
                      <Shield size={12} />
                      Connecté
                    </div>
                  </div>
                </div>

                {/* Logout confirmation */}
                {showLogoutConfirm ? (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    className="rounded-2xl border border-red-200 bg-red-50 p-4"
                  >
                    <div className="flex items-start gap-3">
                      <AlertTriangle size={20} className="text-red-500 mt-0.5" />
                      <div className="flex-1">
                        <p className="font-semibold text-red-900">Confirmer la déconnexion</p>
                        <p className="text-sm text-red-700 mt-1">
                          Vous serez redirigé vers la page d'accueil.
                        </p>
                        <div className="flex gap-2 mt-3">
                          <button
                            onClick={handleLogout}
                            disabled={loggingOut}
                            className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700 disabled:opacity-60 transition-colors"
                          >
                            {loggingOut ? "Déconnexion..." : "Confirmer"}
                          </button>
                          <button
                            onClick={() => setShowLogoutConfirm(false)}
                            className="px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors"
                          >
                            Annuler
                          </button>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ) : (
                  <button
                    onClick={() => setShowLogoutConfirm(true)}
                    className="w-full flex items-center justify-between px-5 py-4 rounded-2xl border border-slate-200 bg-white hover:border-red-200 hover:bg-red-50 group transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <LogOut size={18} className="text-slate-400 group-hover:text-red-500" />
                      <span className="font-medium text-slate-700 group-hover:text-red-700">
                        Se déconnecter
                      </span>
                    </div>
                    <ChevronRight size={18} className="text-slate-300 group-hover:text-red-400" />
                  </button>
                )}
              </>
            ) : (
              <div className="text-center py-8">
                <p className="text-slate-500 mb-4">Vous n'êtes pas connecté</p>
                <button
                  onClick={() => router.push("/auth/login")}
                  className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
                >
                  Se connecter
                </button>
              </div>
            )}
          </SettingsCard>
        </motion.div>

        {/* Theme Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <SettingsCard
            icon={theme === "dark" ? Moon : Sun}
            title="Apparence"
            subtitle="Personnalisez l'interface"
            accentColor="amber"
          >
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => updateTheme("light")}
                className={`flex items-center justify-center gap-2 px-4 py-4 rounded-2xl border-2 transition-all ${
                  theme === "light"
                    ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                    : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
                }`}
              >
                <Sun size={20} />
                <span className="font-semibold">Clair</span>
              </button>
              <button
                onClick={() => updateTheme("dark")}
                className={`flex items-center justify-center gap-2 px-4 py-4 rounded-2xl border-2 transition-all ${
                  theme === "dark"
                    ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                    : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
                }`}
              >
                <Moon size={20} />
                <span className="font-semibold">Sombre</span>
              </button>
            </div>
          </SettingsCard>
        </motion.div>

        {/* Divider */}
        <div className="flex items-center gap-4 py-2">
          <div className="flex-1 h-px bg-slate-200" />
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Configuration Pipeline
          </span>
          <div className="flex-1 h-px bg-slate-200" />
        </div>

        {/* Pipeline Settings */}
        <div className="grid gap-6 lg:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <SettingsCard
              icon={SlidersHorizontal}
              title="Modules d'exécution"
              subtitle="Activez ou désactivez les modules"
              accentColor="emerald"
            >
              <Toggle
                checked={settings.enableMachineImages}
                onChange={() => updateSettings({ enableMachineImages: !settings.enableMachineImages })}
                label="Génération d'images machines"
                description="Crée des images IA pour les machines extraites"
              />
              <Toggle
                checked={settings.enableSourcing}
                onChange={() => updateSettings({ enableSourcing: !settings.enableSourcing })}
                label="Enrichissement sourcing"
                description="Module 4 - Recherche fournisseurs"
              />
              <Toggle
                checked={settings.enableTco}
                onChange={() => updateSettings({ enableTco: !settings.enableTco })}
                label="Analyse TCO"
                description="Requiert sourcing. Alimente Business Plan"
                disabled={!settings.enableSourcing}
              />
              <Toggle
                checked={settings.enableBusinessPlan}
                onChange={() => updateSettings({ enableBusinessPlan: !settings.enableBusinessPlan })}
                label="Business Plan"
                description="Module 7 - Génération Excel"
                disabled={!settings.enableTco}
              />
              <Toggle
                checked={settings.enablePitchDeck}
                onChange={() => updateSettings({ enablePitchDeck: !settings.enablePitchDeck })}
                label="Pitch Deck"
                description="Génération PDF investisseurs"
                disabled={!settings.enableTco}
              />
              <Toggle
                checked={settings.enableCatalog}
                onChange={() => updateSettings({ enableCatalog: !settings.enableCatalog })}
                label="Catalogue technique"
                description="Module 9 - Génération catalogue"
              />
            </SettingsCard>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="space-y-6"
          >
            <SettingsCard
              icon={Database}
              title="Sorties & Formats"
              subtitle="Configurez les exports"
              accentColor="indigo"
            >
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
                  Format catalogue
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {(["pdf", "html", "both"] as const).map((format) => (
                    <button
                      key={format}
                      onClick={() => updateSettings({ catalogFormat: format })}
                      disabled={!settings.enableCatalog}
                      className={`rounded-xl border px-3 py-2.5 text-xs font-semibold uppercase tracking-wide transition ${
                        settings.catalogFormat === format
                          ? "border-indigo-500 bg-indigo-600 text-white"
                          : "border-slate-300 bg-white text-slate-600 hover:border-slate-400"
                      } ${!settings.enableCatalog ? "opacity-50 cursor-not-allowed" : ""}`}
                    >
                      {format}
                    </button>
                  ))}
                </div>
              </div>
            </SettingsCard>

            <SettingsCard
              icon={PackageOpen}
              title="Résumé"
              subtitle="Modules activés"
              accentColor="emerald"
            >
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                <p className="text-sm font-medium text-emerald-800">{moduleSummary}</p>
              </div>

              <button
                onClick={() => updateSettings(DEFAULT_PIPELINE_SETTINGS)}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-slate-300 text-slate-600 font-semibold hover:bg-slate-50 transition-colors"
              >
                <RotateCcw size={16} />
                Réinitialiser les paramètres
              </button>
            </SettingsCard>
          </motion.div>
        </div>
      </main>
    </div>
  );
}
