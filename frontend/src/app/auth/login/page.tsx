"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Mail, Lock, ArrowRight, AlertTriangle } from "lucide-react";

import { supabase } from "@/lib/supabaseClient";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (signInError) {
        setError(signInError.message);
        return;
      }
      router.push("/");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#162232_0%,_#0b0c10_55%)] text-slate-100 flex items-center justify-center px-6 py-12">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 -right-20 h-80 w-80 rounded-full bg-indigo-500/10 blur-[120px]" />
        <div className="absolute bottom-0 left-0 h-96 w-96 rounded-full bg-emerald-500/10 blur-[140px]" />
      </div>

      <div className="relative w-full max-w-md">
        <div className="glass-panel rounded-3xl border border-white/10 p-8 shadow-[0_30px_80px_rgba(0,0,0,0.45)]">
          <div className="mb-8">
            <p className="text-xs uppercase tracking-[0.3em] text-emerald-300/80 font-semibold">
              RIBIF ACCESS
            </p>
            <h1 className="text-3xl font-black text-white mt-3">
              Welcome back
            </h1>
            <p className="text-slate-300 mt-2">
              Sign in to continue your industrial workflow.
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5">
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                Email
              </label>
              <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-black/30 px-4 py-3">
                <Mail size={18} className="text-emerald-300" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none"
                  placeholder="you@company.com"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                Password
              </label>
              <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-black/30 px-4 py-3">
                <Lock size={18} className="text-emerald-300" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none"
                  placeholder="Enter your password"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                <AlertTriangle size={16} />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-2xl bg-emerald-500/90 py-3 text-sm font-bold uppercase tracking-widest text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <div className="mt-8 flex items-center justify-between text-xs text-slate-400">
            <span>New to RIBIF?</span>
            <button
              onClick={() => router.push("/auth/register")}
              className="inline-flex items-center gap-2 text-emerald-300 hover:text-emerald-200"
            >
              Create account <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

