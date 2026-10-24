"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
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
import { getTheme, setTheme, ThemeMode } from "@/utils/theme";

// ========================================
// COMPONENTS
// ========================================

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
    indigo: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20",
    emerald: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20",
    red: "bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20",
    amber: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20",
  };

  return (
    <div className="rounded-3xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#13141c] p-6 shadow-xl shadow-slate-200/50 dark:shadow-black/20">
      <div className="flex items-center gap-4 mb-6">
        <div className={`rounded-xl p-3 ${colorClasses[accentColor]}`}>
          <Icon size={22} />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">{title}</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">{subtitle}</p>
        </div>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
};

// ... existing code ...

export default function SettingsPage() {
  const router = useRouter();
  const [theme, setThemeState] = useState<ThemeMode>(() => getTheme());
  const [user, setUser] = useState<{ email: string; name?: string } | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  // ... existing logic ...

  // Load user info and listen to changes
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

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
       if (session?.user) {
        setUser({
          email: session.user.email || "",
          name: session.user.user_metadata?.full_name,
        });
      } else {
        setUser(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const updateTheme = (mode: ThemeMode) => {
    setThemeState(mode);
    setTheme(mode);
    // Instant update
    if (typeof document !== "undefined") {
      document.documentElement.classList.remove("light", "dark");
      document.documentElement.classList.add(mode);
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

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0b0c10] text-slate-900 dark:text-white transition-colors">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 dark:bg-[#0b0c10]/80 backdrop-blur-lg border-b border-slate-200 dark:border-white/5 transition-colors">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
          >
            <ArrowLeft size={20} />
            <span className="font-medium">Retour</span>
          </button>
          <h1 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Settings size={20} className="text-indigo-600 dark:text-indigo-400" />
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
                <div className="rounded-2xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-white/5 p-4">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg shadow-lg">
                      {user.name?.[0] || user.email[0].toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      {user.name && (
                        <p className="font-semibold text-slate-900 dark:text-white truncate">{user.name}</p>
                      )}
                      <p className="text-sm text-slate-500 dark:text-slate-400 truncate flex items-center gap-1.5">
                        <Mail size={14} />
                        {user.email}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-semibold">
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
                    className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4"
                  >
                    <div className="flex items-start gap-3">
                      <AlertTriangle size={20} className="text-red-600 dark:text-red-400 mt-0.5" />
                      <div className="flex-1">
                        <p className="font-semibold text-red-700 dark:text-red-200">Confirmer la déconnexion</p>
                        <p className="text-sm text-red-600/70 dark:text-red-300/70 mt-1">
                          Vous serez redirigé vers la page d&apos;accueil.
                        </p>
                        <div className="flex gap-2 mt-4">
                          <button
                            onClick={handleLogout}
                            disabled={loggingOut}
                            className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700 disabled:opacity-60 transition-colors shadow-lg shadow-red-900/20"
                          >
                            {loggingOut ? "Déconnexion..." : "Confirmer"}
                          </button>
                          <button
                            onClick={() => setShowLogoutConfirm(false)}
                            className="px-4 py-2 bg-transparent border border-red-200 dark:border-white/10 text-red-700 dark:text-slate-300 rounded-lg text-sm font-semibold hover:bg-red-50 dark:hover:bg-white/5 transition-colors"
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
                    className="w-full flex items-center justify-between px-5 py-4 rounded-2xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-white/5 hover:border-red-500/30 hover:bg-red-500/5 group transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <LogOut size={18} className="text-slate-400 dark:text-slate-400 group-hover:text-red-500 dark:group-hover:text-red-400" />
                      <span className="font-medium text-slate-600 dark:text-slate-300 group-hover:text-red-500 dark:group-hover:text-red-400">
                        Se déconnecter
                      </span>
                    </div>
                    <ChevronRight size={18} className="text-slate-400 dark:text-slate-500 group-hover:text-red-500 dark:group-hover:text-red-400" />
                  </button>
                )}
              </>
            ) : (
              <div className="text-center py-8">
                <p className="text-slate-500 mb-4">Vous n&apos;êtes pas connecté</p>
                <button
                  onClick={() => router.push("/auth/login")}
                  className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-500/20"
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
                    ? "border-indigo-500 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400"
                    : "border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-white/5 text-slate-500 dark:text-slate-400 hover:border-slate-300 dark:hover:border-white/10 hover:bg-slate-100 dark:hover:bg-white/10"
                }`}
              >
                <Sun size={20} />
                <span className="font-semibold">Clair</span>
              </button>
              <button
                onClick={() => updateTheme("dark")}
                className={`flex items-center justify-center gap-2 px-4 py-4 rounded-2xl border-2 transition-all ${
                  theme === "dark"
                    ? "border-indigo-500 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400"
                    : "border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-white/5 text-slate-500 dark:text-slate-400 hover:border-slate-300 dark:hover:border-white/10 hover:bg-slate-100 dark:hover:bg-white/10"
                }`}
              >
                <Moon size={20} />
                <span className="font-semibold">Sombre</span>
              </button>
            </div>
          </SettingsCard>
        </motion.div>
      </main>
    </div>
  );
}
