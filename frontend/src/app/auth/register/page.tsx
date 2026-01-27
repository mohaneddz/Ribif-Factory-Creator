"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Mail, Lock, User, ArrowRight, AlertTriangle } from "lucide-react";

import { supabase } from "@/lib/supabaseClient";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const { error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
          },
        },
      });

      if (signUpError) {
        setError(signUpError.message);
        return;
      }

      setSuccess(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[radial-gradient(circle_at_top,_#14272f_0%,_#0b0c10_60%)] text-slate-900 dark:text-slate-100 flex items-center justify-center px-6 py-12 transition-colors">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-16 left-12 h-72 w-72 rounded-full bg-amber-500/10 blur-[110px]" />
        <div className="absolute bottom-10 right-10 h-96 w-96 rounded-full bg-sky-500/10 blur-[140px]" />
      </div>

      <div className="relative w-full max-w-md">
        <div className="bg-white dark:glass-panel rounded-3xl border border-slate-200 dark:border-white/10 p-8 shadow-2xl shadow-indigo-500/10 dark:shadow-[0_30px_80px_rgba(0,0,0,0.45)]">
          <div className="mb-8">
            <p className="text-xs uppercase tracking-[0.3em] text-indigo-600 dark:text-amber-300/80 font-semibold">
              RIBIF ACCESS
            </p>
            <h1 className="text-3xl font-black text-slate-900 dark:text-white mt-3">
              Create your account
            </h1>
            <p className="text-slate-500 dark:text-slate-300 mt-2">
              Start building industrial projects with Supabase-backed storage.
            </p>
          </div>

          {success ? (
            <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-5 text-sm text-emerald-800 dark:text-emerald-100">
              Account created. Check your email to confirm and then sign in.
            </div>
          ) : (
            <form onSubmit={handleRegister} className="space-y-5">
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                  Full name
                </label>
                <div className="flex items-center gap-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/30 px-4 py-3">
                  <User size={18} className="text-indigo-500 dark:text-amber-300" />
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full bg-transparent text-sm text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none transition-colors"
                    placeholder="Operations Lead"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                  Email
                </label>
                <div className="flex items-center gap-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/30 px-4 py-3">
                  <Mail size={18} className="text-indigo-500 dark:text-amber-300" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-transparent text-sm text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none transition-colors"
                    placeholder="you@company.com"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                  Password
                </label>
                <div className="flex items-center gap-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/30 px-4 py-3">
                  <Lock size={18} className="text-indigo-500 dark:text-amber-300" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-transparent text-sm text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none transition-colors"
                    placeholder="Minimum 6 characters"
                    required
                  />
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-200">
                  <AlertTriangle size={16} />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-2xl bg-indigo-600 dark:bg-amber-500/90 py-3 text-sm font-bold uppercase tracking-widest text-white dark:text-slate-950 transition hover:bg-indigo-700 dark:hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-60 shadow-lg shadow-indigo-500/20 dark:shadow-amber-500/20"
              >
                {loading ? "Creating account..." : "Create account"}
              </button>
            </form>
          )}

          <div className="mt-8 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Already have an account?</span>
            <button
              onClick={() => router.push("/auth/login")}
              className="inline-flex items-center gap-2 text-indigo-600 dark:text-amber-300 hover:text-indigo-500 dark:hover:text-amber-200"
            >
              Sign in <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

