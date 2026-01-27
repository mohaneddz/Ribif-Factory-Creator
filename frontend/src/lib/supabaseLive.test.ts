import { describe, expect, it } from "vitest";
import { createClient } from "@supabase/supabase-js";

const argv = process.argv.join(" ");
const isLive = argv.includes("--live") || process.env.SUPABASE_TEST_LIVE === "1";

// Ensure trailing slash for storage endpoint
const rawUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseUrl = rawUrl ? rawUrl.replace(/\/$/, "") + "/" : "";
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_TEST_SERVICE_KEY;

const bucketName = process.env.SUPABASE_TEST_BUCKET || "project-files";
const ownerId = process.env.SUPABASE_TEST_OWNER_ID || null;

const describeFn = isLive ? describe : describe.skip;

describeFn("supabase live integration", () => {
  it("uploads file and writes project data", async () => {
    if (!supabaseUrl || !serviceKey) {
      throw new Error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
    }

    const supabase = createClient(supabaseUrl, serviceKey);
    const timestamp = Date.now();
    const projectName = `Live Test Project ${timestamp}`;

    const { data: projectRows, error: projectError } = await supabase
      .from("projects")
      .insert({ name: projectName, owner_id: ownerId, status: "testing" })
      .select("id")
      .limit(1);
    if (projectError || !projectRows?.length) {
      throw projectError || new Error("Project insert failed");
    }

    const projectId = projectRows[0].id as string;
    const objectPath = `${projectId}/tests/${timestamp}_hello.txt`;
    const payload = Buffer.from("supabase-live-test");

    const uploadRes = await supabase.storage
      .from(bucketName)
      .upload(objectPath, payload, { upsert: true, contentType: "text/plain" });
    if (uploadRes.error) {
      throw uploadRes.error;
    }

    const { data: fileRows, error: fileError } = await supabase
      .from("project_files")
      .insert({
        project_id: projectId,
        owner_id: ownerId,
        bucket: bucketName,
        object_path: objectPath,
        mime_type: "text/plain",
        size_bytes: payload.length,
        category: "tests",
        label: "hello.txt",
      })
      .select("id")
      .limit(1);
    if (fileError || !fileRows?.length) {
      throw fileError || new Error("project_files insert failed");
    }

    const fileId = fileRows[0].id as string;
    const { data: settingsRows, error: settingsError } = await supabase
      .from("project_settings")
      .upsert({ project_id: projectId, settings: { live_test: true }, updated_by: ownerId })
      .select("id")
      .limit(1);
    if (settingsError || !settingsRows?.length) {
      throw settingsError || new Error("project_settings upsert failed");
    }

    const { data: updatedRows, error: updateError } = await supabase
      .from("projects")
      .update({ status: "tested" })
      .eq("id", projectId)
      .select("status")
      .limit(1);
    if (updateError || !updatedRows?.length) {
      throw updateError || new Error("Project update failed");
    }

    expect(updatedRows[0].status).toBe("tested");

    const cleanupErrors: string[] = [];
    const removeRes = await supabase.storage.from(bucketName).remove([objectPath]);
    if (removeRes.error) cleanupErrors.push(removeRes.error.message);

    const deleteFileRes = await supabase.from("project_files").delete().eq("id", fileId);
    if (deleteFileRes.error) cleanupErrors.push(deleteFileRes.error.message);

    const deleteProjectRes = await supabase.from("projects").delete().eq("id", projectId);
    if (deleteProjectRes.error) cleanupErrors.push(deleteProjectRes.error.message);

    if (cleanupErrors.length) {
      throw new Error(`Cleanup failed: ${cleanupErrors.join(", ")}`);
    }
  });
});
