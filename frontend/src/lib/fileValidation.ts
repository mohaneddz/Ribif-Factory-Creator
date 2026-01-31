import { supabase, supabaseAdmin } from "@/lib/supabaseClient";
import { VALIDATION_CONFIG } from "@/config/validation";

/**
 * Compute SHA-256 hash of a file
 */
export async function computeFileHash(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
  return hashHex;
}

/**
 * Check if a project with the same filename and hash already exists
 */
export async function checkDuplicateProject(
  filename: string,
  hash: string
): Promise<{ exists: boolean; projectId?: string; projectName?: string }> {
  const { data, error } = await supabase
    .from("projects")
    .select("id, name")
    .eq("source_filename", filename)
    .eq("source_file_hash", hash)
    .limit(1);

  if (error) {
    console.error("Error checking duplicate:", error);
    return { exists: false };
  }

  if (data && data.length > 0) {
    return { exists: true, projectId: data[0].id, projectName: data[0].name };
  }

  return { exists: false };
}

/**
 * Validate PDF content meets minimum character requirement
 */
export function validatePdfCharacterCount(
  text: string,
  minChars: number = VALIDATION_CONFIG.MIN_PDF_CHARACTERS
): { valid: boolean; charCount: number; minRequired: number } {
  const charCount = text.trim().length;
  return {
    valid: charCount >= minChars,
    charCount,
    minRequired: minChars,
  };
}

/**
 * Extract text from PDF using backend API
 */
export async function extractPdfText(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);

  const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5000";
  
  try {
    const response = await fetch(`${API_BASE}/api/extract-text`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error("Failed to extract PDF text");
    }

    const data = await response.json();
    return data.text || "";
  } catch (error) {
    console.error("PDF extraction error:", error);
    // Fallback: return empty string if extraction fails
    return "";
  }
}

/**
 * Validate PDF content with LLM
 */
export async function validateWithLlm(
  file: File
): Promise<{ valid: boolean; error?: string; message?: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5000";

  try {
    const response = await fetch(`${API_BASE}${VALIDATION_CONFIG.LLM_VALIDATION_ENDPOINT}`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        valid: false,
        error: errorData.error || "Validation service unavailable",
      };
    }

    const data = await response.json();
    return {
      valid: data.valid !== false,
      message: data.message,
      error: data.error,
    };
  } catch (error) {
    console.error("LLM validation error:", error);
    return {
      valid: false,
      error: "Unable to validate document. Please try again.",
    };
  }
}

/**
 * Upload file to Supabase storage
 */
export async function uploadFileToStorage(
  file: File,
  projectId: string,
  onProgress?: (progress: number) => void
): Promise<{ path: string; error?: string }> {
  const fileExt = file.name.split(".").pop();
  const filePath = `${projectId}/${Date.now()}.${fileExt}`;

  // Note: Supabase JS client doesn't support progress events directly
  // We simulate progress for UX
  onProgress?.(10);

  const { data, error } = await supabaseAdmin.storage
    .from("project-files")
    .upload(filePath, file, {
      cacheControl: "3600",
      upsert: false,
    });

  onProgress?.(100);

  if (error) {
    return { path: "", error: error.message };
  }

  return { path: data.path };
}

/**
 * Create a new project record in the database
 */
export async function createProjectRecord(
  name: string,
  filename: string,
  fileHash: string,
  filePath: string
): Promise<{ id: string; error?: string }> {
  const { data: sessionData } = await supabase.auth.getSession();
  const userId = sessionData?.session?.user?.id;

  const { data, error } = await supabaseAdmin.from("projects").insert({
    name,
    source_filename: filename,
    source_file_hash: fileHash,
    source_file_path: filePath,
    owner_id: userId || null,
    status: "draft",
  }).select("id").single();

  if (error) {
    return { id: "", error: error.message };
  }

  return { id: data.id };
}

/**
 * Delete a project record (used when validation fails)
 */
export async function deleteProjectRecord(projectId: string): Promise<void> {
  await supabaseAdmin.from("projects").delete().eq("id", projectId);
}

/**
 * Validate file type and size
 */
export function validateFileBasics(file: File): { valid: boolean; error?: string } {
  if (!VALIDATION_CONFIG.ALLOWED_FILE_TYPES.includes(file.type)) {
    return { valid: false, error: "Seuls les fichiers PDF sont acceptés" };
  }

  const maxSizeBytes = VALIDATION_CONFIG.MAX_FILE_SIZE_MB * 1024 * 1024;
  if (file.size > maxSizeBytes) {
    return { valid: false, error: `Le fichier dépasse la taille maximale de ${VALIDATION_CONFIG.MAX_FILE_SIZE_MB}MB` };
  }

  return { valid: true };
}
