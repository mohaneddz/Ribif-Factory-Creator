import { supabase, supabaseAdmin } from "./supabaseClient";

// ============================================================
// TYPES
// ============================================================

export interface ProjectRecord {
    id: string;
    owner_id: string | null;
    name: string;
    status: string;
    source_filename: string | null;
    source_file_path: string | null;
    module1_data: Record<string, unknown> | null;
    module4_data: Record<string, unknown> | null;
    module6_data: Record<string, unknown> | null;
    module7_business: Record<string, unknown> | null;
    module7_pitch: Record<string, unknown> | null;
    module9_data: Record<string, unknown> | null;
    module2_data: Record<string, unknown> | null;
    module3_data: Record<string, unknown> | null;
    completed_modules: string[];
    current_module: string | null;
    settings: Record<string, unknown>;
    metadata: Record<string, unknown>;
    created_at: string;
    updated_at: string;
}

// ============================================================
// PROJECT CRUD
// ============================================================

export async function createProject(
    userId: string | null,
    name: string,
    sourceFilename?: string
): Promise<{ data: ProjectRecord | null; error: Error | null }> {
    const { data, error } = await supabaseAdmin
        .from("projects")
        .insert({
            owner_id: userId,
            name,
            status: "draft",
            source_filename: sourceFilename || null,
            completed_modules: [],
        })
        .select()
        .single();

    return { data, error: error ? new Error(error.message) : null };
}

export async function getProject(
    projectId: string
): Promise<{ data: ProjectRecord | null; error: Error | null }> {
    const { data, error } = await supabaseAdmin
        .from("projects")
        .select("*")
        .eq("id", projectId)
        .single();

    return { data, error: error ? new Error(error.message) : null };
}

export async function updateProject(
    projectId: string,
    updates: Partial<Omit<ProjectRecord, "id" | "created_at" | "updated_at">>
): Promise<{ data: ProjectRecord | null; error: Error | null }> {
    const { data, error } = await supabaseAdmin
        .from("projects")
        .update(updates)
        .eq("id", projectId)
        .select()
        .single();

    return { data, error: error ? new Error(error.message) : null };
}

export async function deleteProject(
    projectId: string
): Promise<{ error: Error | null }> {
    const { error } = await supabaseAdmin
        .from("projects")
        .delete()
        .eq("id", projectId);

    return { error: error ? new Error(error.message) : null };
}

// ============================================================
// FILE UPLOAD TO STORAGE BUCKET
// ============================================================

export async function uploadFileToBucket(
    projectId: string,
    file: File
): Promise<{ path: string | null; error: Error | null }> {
    const timestamp = Date.now();
    const sanitizedFilename = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
    const objectPath = `${projectId}/${timestamp}_${sanitizedFilename}`;

    const { error: uploadError } = await supabaseAdmin.storage
        .from("project-files")
        .upload(objectPath, file, {
            cacheControl: "3600",
            upsert: true,
            contentType: file.type,
        });

    if (uploadError) {
        return { path: null, error: new Error(uploadError.message) };
    }

    // Update project with file path
    await updateProject(projectId, { source_file_path: objectPath });

    return { path: objectPath, error: null };
}

export function getPublicFileUrl(objectPath: string): string {
    const { data } = supabaseAdmin.storage
        .from("project-files")
        .getPublicUrl(objectPath);

    return data?.publicUrl || "";
}

// ============================================================
// MODULE DATA HELPERS
// ============================================================

export async function saveModule1Data(
    projectId: string,
    data: Record<string, unknown>
): Promise<{ error: Error | null }> {
    const { error } = await supabaseAdmin
        .from("projects")
        .update({
            module1_data: data,
            completed_modules: supabaseAdmin.rpc ? undefined : undefined, // Will append below
            current_module: null,
        })
        .eq("id", projectId);

    if (!error) {
        // Append to completed_modules
        await supabaseAdmin.rpc("array_append_unique", {
            table_name: "projects",
            id: projectId,
            column_name: "completed_modules",
            value: "specs",
        }).catch(() => {
            // Fallback: just update directly
            supabaseAdmin
                .from("projects")
                .update({ completed_modules: ["specs"] })
                .eq("id", projectId);
        });
    }

    return { error: error ? new Error(error.message) : null };
}

export async function saveModule4Data(
    projectId: string,
    data: Record<string, unknown>
): Promise<{ error: Error | null }> {
    const result = await updateProject(projectId, {
        module4_data: data,
        status: "sourcing_complete",
    });
    return { error: result.error };
}

export async function saveModule6Data(
    projectId: string,
    data: Record<string, unknown>
): Promise<{ error: Error | null }> {
    const result = await updateProject(projectId, {
        module6_data: data,
        status: "tco_complete",
    });
    return { error: result.error };
}

export async function saveModule7BusinessData(
    projectId: string,
    data: Record<string, unknown>
): Promise<{ error: Error | null }> {
    const result = await updateProject(projectId, {
        module7_business: data,
    });
    return { error: result.error };
}

export async function saveModule7PitchData(
    projectId: string,
    data: Record<string, unknown>
): Promise<{ error: Error | null }> {
    const result = await updateProject(projectId, {
        module7_pitch: data,
    });
    return { error: result.error };
}

export async function saveModule9Data(
    projectId: string,
    data: Record<string, unknown>
): Promise<{ error: Error | null }> {
    const result = await updateProject(projectId, {
        module9_data: data,
    });
    return { error: result.error };
}

export async function saveModule2Data(
    projectId: string,
    data: Record<string, unknown>
): Promise<{ error: Error | null }> {
    const result = await updateProject(projectId, {
        module2_data: data,
        status: "layout_complete",
    });
    return { error: result.error };
}

export async function saveModule3Data(
    projectId: string,
    data: Record<string, unknown>
): Promise<{ error: Error | null }> {
    const result = await updateProject(projectId, {
        module3_data: data,
        status: "complete",
    });
    return { error: result.error };
}

// ============================================================
// LOAD FULL PROJECT
// ============================================================

export async function loadProject(
    projectId: string
): Promise<{ data: ProjectRecord | null; error: Error | null }> {
    return getProject(projectId);
}

// ============================================================
// LIST USER PROJECTS
// ============================================================

export async function listUserProjects(
    userId?: string
): Promise<{ data: ProjectRecord[] | null; error: Error | null }> {
    let query = supabaseAdmin
        .from("projects")
        .select("*")
        .order("updated_at", { ascending: false });

    if (userId) {
        query = query.eq("owner_id", userId);
    }

    const { data, error } = await query;

    return { data, error: error ? new Error(error.message) : null };
}

// ============================================================
// CONVENIENCE: SAVE ALL MODULE DATA AT ONCE
// ============================================================

export async function saveAllModuleData(
    projectId: string,
    moduleData: {
        module1?: Record<string, unknown>;
        module4?: Record<string, unknown>;
        module6?: Record<string, unknown>;
        module7Business?: Record<string, unknown>;
        module7Pitch?: Record<string, unknown>;
        module9?: Record<string, unknown>;
        module2?: Record<string, unknown>;
        module3?: Record<string, unknown>;
    }
): Promise<{ error: Error | null }> {
    const updates: Partial<ProjectRecord> = {};

    if (moduleData.module1) updates.module1_data = moduleData.module1;
    if (moduleData.module4) updates.module4_data = moduleData.module4;
    if (moduleData.module6) updates.module6_data = moduleData.module6;
    if (moduleData.module7Business) updates.module7_business = moduleData.module7Business;
    if (moduleData.module7Pitch) updates.module7_pitch = moduleData.module7Pitch;
    if (moduleData.module9) updates.module9_data = moduleData.module9;
    if (moduleData.module2) updates.module2_data = moduleData.module2;
    if (moduleData.module3) updates.module3_data = moduleData.module3;

    const { error } = await supabaseAdmin
        .from("projects")
        .update(updates)
        .eq("id", projectId);

    return { error: error ? new Error(error.message) : null };
}
