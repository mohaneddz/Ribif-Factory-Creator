import { getCookie, setCookie } from "@/utils/cookies";

export type PipelineSettings = {
  enableMachineImages: boolean;
  enableSourcing: boolean;
  enableTco: boolean;
  enableBusinessPlan: boolean;
  enablePitchDeck: boolean;
  enableCatalog: boolean;
  catalogFormat: "pdf" | "html" | "both";
  testRecipientEmail: string; // Override recipient email for testing - empty means use scraped emails
};

export const PIPELINE_SETTINGS_COOKIE = "ribif_pipeline_settings";

export const DEFAULT_PIPELINE_SETTINGS: PipelineSettings = {
  enableMachineImages: true,
  enableSourcing: true,
  enableTco: true,
  enableBusinessPlan: true,
  enablePitchDeck: true,
  enableCatalog: true,
  catalogFormat: "pdf",
  testRecipientEmail: "", // Empty = use original supplier emails from scraping
};

export const sanitizeSettings = (settings: Partial<PipelineSettings>): PipelineSettings => {
  const catalogFormat = settings.catalogFormat;
  const safeFormat =
    catalogFormat === "html" || catalogFormat === "both" || catalogFormat === "pdf"
      ? catalogFormat
      : DEFAULT_PIPELINE_SETTINGS.catalogFormat;

  return {
    enableMachineImages: settings.enableMachineImages ?? DEFAULT_PIPELINE_SETTINGS.enableMachineImages,
    enableSourcing: settings.enableSourcing ?? DEFAULT_PIPELINE_SETTINGS.enableSourcing,
    enableTco: settings.enableTco ?? DEFAULT_PIPELINE_SETTINGS.enableTco,
    enableBusinessPlan: settings.enableBusinessPlan ?? DEFAULT_PIPELINE_SETTINGS.enableBusinessPlan,
    enablePitchDeck: settings.enablePitchDeck ?? DEFAULT_PIPELINE_SETTINGS.enablePitchDeck,
    enableCatalog: settings.enableCatalog ?? DEFAULT_PIPELINE_SETTINGS.enableCatalog,
    catalogFormat: safeFormat,
    testRecipientEmail: (settings.testRecipientEmail ?? DEFAULT_PIPELINE_SETTINGS.testRecipientEmail).trim(),
  };
};

export const loadPipelineSettings = (): PipelineSettings => {
  const raw = getCookie(PIPELINE_SETTINGS_COOKIE);
  if (!raw) return DEFAULT_PIPELINE_SETTINGS;
  try {
    const parsed = JSON.parse(raw);
    return sanitizeSettings(parsed);
  } catch {
    return DEFAULT_PIPELINE_SETTINGS;
  }
};

export const savePipelineSettings = (settings: PipelineSettings) => {
  setCookie(PIPELINE_SETTINGS_COOKIE, JSON.stringify(settings), 30);
};

