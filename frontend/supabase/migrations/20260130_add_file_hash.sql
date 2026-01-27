-- ============================================================
-- MIGRATION: Add source_file_hash for duplicate detection
-- Generated: 2026-01-30
-- ============================================================

-- Add source_file_hash column to projects table
ALTER TABLE public.projects 
ADD COLUMN IF NOT EXISTS source_file_hash text;

-- Create index for efficient duplicate lookups
CREATE INDEX IF NOT EXISTS projects_file_hash_idx 
ON public.projects(source_filename, source_file_hash);

-- Comment for documentation
COMMENT ON COLUMN public.projects.source_file_hash IS 'SHA-256 hash of the source file for duplicate detection';
