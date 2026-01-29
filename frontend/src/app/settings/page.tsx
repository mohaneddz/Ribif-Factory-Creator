"use client";

import { useMemo, useState } from "react";
import {
  SlidersHorizontal,
  Database,
  PackageOpen,
  Sparkles,
  RotateCcw,
} from "lucide-react";

import {
  DEFAULT_PIPELINE_SETTINGS,
  PipelineSettings,
  loadPipelineSettings,
  savePipelineSettings,
} from "@/utils/pipelineSettings";
import { getTheme, setTheme, ThemeMode } from "@/utils/theme";

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
        ? "border-slate-700/40 bg-slate-900/40 opacity-60 cursor-not-allowed"
        : "border-slate-700/60 bg-slate-900/60 hover:border-emerald-500/60"
    }`}
  >
    <div className="flex items-center justify-between gap-4">
      <div>
        <div className="text-sm font-bold text-white">{label}</div>
        <p className="text-xs text-slate-400 mt-1">{description}</p>
      </div>
      <div
        className={`h-6 w-11 rounded-full border transition ${
          checked ? "bg-emerald-500/90 border-emerald-400" : "bg-slate-700/60 border-slate-600"
        }`}
      >
        <div
          className={`h-5 w-5 rounded-full bg-white transition ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </div>
    </div>
  </button>
);

export default function SettingsPage() {
  const [settings, setSettings] = useState<PipelineSettings>(() =>
    loadPipelineSettings()
  );
  const [theme, setThemeState] = useState<ThemeMode>(() => getTheme());

  const updateSettings = (partial: Partial<PipelineSettings>) => {
    let next: PipelineSettings = { ...settings, ...partial };

    if (partial.enableBusinessPlan && !next.enableTco) {
      next.enableTco = true;
    }
    if (partial.enablePitchDeck && !next.enableTco) {
      next.enableTco = true;
    }
    if (partial.enableTco && !next.enableSourcing) {
      next.enableSourcing = true;
    }

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

  const moduleSummary = useMemo(() => {
    const enabled = [
      settings.enableSourcing && "Sourcing",
      settings.enableTco && "TCO",
      settings.enableBusinessPlan && "Business Plan",
      settings.enablePitchDeck && "Pitch Deck",
      settings.enableCatalog && "Catalogue",
    ].filter(Boolean);
    return enabled.length ? enabled.join(" • ") : "Only Specs extraction";
  }, [settings]);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#131a23_0%,_#0b0c10_60%)] text-slate-100 px-6 py-12">
      <div className="mx-auto w-full max-w-5xl space-y-10">
        <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.4em] text-emerald-300/80 font-semibold">
              Pipeline Settings
            </p>
            <h1 className="text-3xl font-black text-white mt-2">
              Configure your workflow
            </h1>
            <p className="text-sm text-slate-400 mt-2 max-w-2xl">
              These controls write to cookies now, and every workflow run will read them
              to decide which modules to execute and how files are produced.
            </p>
          </div>
          <button
            onClick={() => updateSettings(DEFAULT_PIPELINE_SETTINGS)}
            className="inline-flex items-center gap-2 rounded-full border border-slate-700/60 bg-slate-900/60 px-4 py-2 text-xs font-semibold text-slate-200 hover:border-emerald-400/60"
          >
            <RotateCcw size={14} /> Reset defaults
          </button>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4 rounded-3xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-[0_30px_90px_rgba(0,0,0,0.4)]">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-emerald-500/20 p-3 text-emerald-300">
                <SlidersHorizontal size={20} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Execution Layers</h2>
                <p className="text-xs text-slate-400">Toggle modules and dependencies</p>
              </div>
            </div>

            <Toggle
              checked={settings.enableMachineImages}
              onChange={() =>
                updateSettings({ enableMachineImages: !settings.enableMachineImages })
              }
              label="Generate machine images"
              description="Controls AI image creation for extracted machines."
            />
            <Toggle
              checked={settings.enableSourcing}
              onChange={() => updateSettings({ enableSourcing: !settings.enableSourcing })}
              label="Run sourcing enrichment"
              description="Executes Module 4 supplier enrichment."
            />
            <Toggle
              checked={settings.enableTco}
              onChange={() => updateSettings({ enableTco: !settings.enableTco })}
              label="Compute TCO analysis"
              description="Requires sourcing. Feeds business plan + pitch deck."
              disabled={!settings.enableSourcing}
            />
            <Toggle
              checked={settings.enableBusinessPlan}
              onChange={() =>
                updateSettings({ enableBusinessPlan: !settings.enableBusinessPlan })
              }
              label="Generate business plan"
              description="Runs Module 7 Excel output."
              disabled={!settings.enableTco}
            />
            <Toggle
              checked={settings.enablePitchDeck}
              onChange={() =>
                updateSettings({ enablePitchDeck: !settings.enablePitchDeck })
              }
              label="Generate pitch deck"
              description="Uses Presenton to build the investor PDF."
              disabled={!settings.enableTco}
            />
            <Toggle
              checked={settings.enableCatalog}
              onChange={() => updateSettings({ enableCatalog: !settings.enableCatalog })}
              label="Generate technical catalog"
              description="Creates Module 9 catalog output."
            />
          </div>

          <div className="space-y-4 rounded-3xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-[0_30px_90px_rgba(0,0,0,0.4)]">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-indigo-500/20 p-3 text-indigo-300">
                <Database size={20} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Outputs & Storage</h2>
                <p className="text-xs text-slate-400">Control file formats</p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-700/60 bg-black/30 p-5">
              <div className="text-xs uppercase tracking-widest text-slate-400">
                Catalog format
              </div>
              <div className="mt-3 grid grid-cols-3 gap-3">
                {(["pdf", "html", "both"] as const).map((format) => (
                  <button
                    key={format}
                    onClick={() => updateSettings({ catalogFormat: format })}
                    disabled={!settings.enableCatalog}
                    className={`rounded-xl border px-3 py-2 text-xs font-semibold uppercase tracking-widest transition ${
                      settings.catalogFormat === format
                        ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-200"
                        : "border-slate-700/60 bg-slate-900/60 text-slate-400 hover:border-slate-500"
                    } ${!settings.enableCatalog ? "opacity-60 cursor-not-allowed" : ""}`}
                  >
                    {format}
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-700/60 bg-black/30 p-5">
              <div className="text-xs uppercase tracking-widest text-slate-400">
                Theme
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3">
                {(["dark", "light"] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => updateTheme(mode)}
                    className={`rounded-xl border px-3 py-2 text-xs font-semibold uppercase tracking-widest transition ${
                      theme === mode
                        ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-200"
                        : "border-slate-700/60 bg-slate-900/60 text-slate-400 hover:border-slate-500"
                    }`}
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-700/60 bg-black/30 p-5 space-y-3">
              <div className="flex items-center gap-3 text-emerald-200">
                <PackageOpen size={18} />
                <span className="text-xs uppercase tracking-widest">Active modules</span>
              </div>
              <p className="text-sm text-slate-300">{moduleSummary}</p>
            </div>

            <div className="rounded-2xl border border-slate-700/60 bg-black/30 p-5 space-y-3">
              <div className="flex items-center gap-3 text-indigo-200">
                <Sparkles size={18} />
                <span className="text-xs uppercase tracking-widest">Cookie preview</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed break-words">
                {JSON.stringify(settings)}
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
