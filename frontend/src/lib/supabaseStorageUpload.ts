import { supabaseAdmin } from "./supabaseClient";

const BUCKET_NAME = "project-files";

/**
 * Fetches a file from a URL (typically backend) and uploads it to Supabase storage.
 * Returns the public URL of the uploaded file.
 */
export async function fetchAndUploadToSupabase(
  sourceUrl: string,
  projectId: string,
  category: string,
  filename?: string
): Promise<string | null> {
  try {
    // Fetch the file from the source URL (backend)
    const response = await fetch(sourceUrl);
    if (!response.ok) {
      console.error(`Failed to fetch file from ${sourceUrl}: ${response.statusText}`);
      return null;
    }

    // Get the file as a blob
    const blob = await response.blob();

    // Determine filename from URL if not provided
    const finalFilename = filename || sourceUrl.split("/").pop() || `file-${Date.now()}`;

    // Build the storage path (matching PDF upload pattern)
    const timestamp = Date.now();
    const sanitizedFilename = finalFilename.replace(/[^a-zA-Z0-9._-]/g, "_");
    const objectPath = `${projectId}/${category}/${timestamp}_${sanitizedFilename}`;

    // Determine content type from blob or filename
    let contentType = blob.type;
    if (!contentType || contentType === "application/octet-stream") {
      // Try to infer from filename extension
      const ext = finalFilename.split(".").pop()?.toLowerCase();
      const mimeTypes: Record<string, string> = {
        glb: "model/gltf-binary",
        gltf: "model/gltf+json",
        png: "image/png",
        jpg: "image/jpeg",
        jpeg: "image/jpeg",
        dxf: "application/dxf",
        pdf: "application/pdf",
        json: "application/json",
      };
      contentType = mimeTypes[ext || ""] || "application/octet-stream";
    }

    // Upload to Supabase using supabaseAdmin (like PDF upload)
    const { error: uploadError } = await supabaseAdmin.storage
      .from(BUCKET_NAME)
      .upload(objectPath, blob, {
        cacheControl: "3600",
        upsert: true,
        contentType,
      });

    if (uploadError) {
      console.error("Supabase upload error:", uploadError);
      return null;
    }

    // Get the public URL
    const { data: urlData } = supabaseAdmin.storage
      .from(BUCKET_NAME)
      .getPublicUrl(objectPath);

    return urlData?.publicUrl || null;
  } catch (error) {
    console.error("Error in fetchAndUploadToSupabase:", error);
    return null;
  }
}

/**
 * Batch upload layout files from backend to Supabase.
 * Returns an object with the Supabase URLs.
 */
export async function uploadLayoutFilesToSupabase(
  projectId: string,
  layoutData: {
    layout_2d_url?: string;
    layout_3d_url?: string;
    layout_dxf_url?: string;
    layout_realistic_url?: string;
    layout_realistic_clean_url?: string;
  }
): Promise<{
  layout_2d_supabase_url?: string;
  layout_3d_supabase_url?: string;
  layout_dxf_supabase_url?: string;
  layout_realistic_supabase_url?: string;
  layout_realistic_clean_supabase_url?: string;
}> {
  const result: Record<string, string | undefined> = {};

  // Upload files in parallel
  const uploads = [
    {
      key: "layout_2d_supabase_url",
      sourceUrl: layoutData.layout_2d_url,
      category: "layout-2d",
    },
    {
      key: "layout_3d_supabase_url",
      sourceUrl: layoutData.layout_3d_url,
      category: "layout-3d",
    },
    {
      key: "layout_dxf_supabase_url",
      sourceUrl: layoutData.layout_dxf_url,
      category: "layout-dxf",
    },
    {
      key: "layout_realistic_supabase_url",
      sourceUrl: layoutData.layout_realistic_url,
      category: "layout-realistic",
    },
    {
      key: "layout_realistic_clean_supabase_url",
      sourceUrl: layoutData.layout_realistic_clean_url,
      category: "layout-realistic-clean",
    },
  ];

  await Promise.all(
    uploads.map(async ({ key, sourceUrl, category }) => {
      if (sourceUrl) {
        const supabaseUrl = await fetchAndUploadToSupabase(
          sourceUrl,
          projectId,
          category
        );
        if (supabaseUrl) {
          result[key] = supabaseUrl;
        }
      }
    })
  );

  return result;
}

