-- ============================================================
-- SIMPLIFIED RIBIF SCHEMA
-- Single-table approach for project workflow data
-- Generated: 2026-01-30
-- ============================================================

-- Drop all existing tables and policies (clean slate)
drop policy if exists "projects_select_members" on public.projects;
drop policy if exists "projects_insert_owner" on public.projects;
drop policy if exists "projects_update_owner" on public.projects;
drop policy if exists "projects_delete_owner" on public.projects;

drop table if exists public.tco_annual cascade;
drop table if exists public.tco_raw_materials cascade;
drop table if exists public.tco_products cascade;
drop table if exists public.tco_machines cascade;
drop table if exists public.tco_runs cascade;
drop table if exists public.catalogs cascade;
drop table if exists public.pitch_decks cascade;
drop table if exists public.business_plans cascade;
drop table if exists public.videos cascade;
drop table if exists public.layouts cascade;
drop table if exists public.pipelines cascade;
drop table if exists public.machine_suppliers cascade;
drop table if exists public.suppliers cascade;
drop table if exists public.module4_sourcing cascade;
drop table if exists public.machine_assets cascade;
drop table if exists public.machines cascade;
drop table if exists public.module1_extractions cascade;
drop table if exists public.project_files cascade;
drop table if exists public.project_settings cascade;
drop table if exists public.project_members cascade;
drop table if exists public.projects cascade;
drop table if exists public.profiles cascade;

-- ============================================================
-- SINGLE UNIFIED PROJECTS TABLE
-- All workflow data stored as JSONB for flexibility
-- ============================================================

create table if not exists public.projects (
    id uuid primary key default gen_random_uuid(),
    
    -- Basic info
    owner_id uuid,  -- Optional: link to auth.users if needed
    name text not null,
    status text not null default 'draft',
    
    -- Source file info
    source_filename text,
    source_file_path text,  -- Path in storage bucket
    
    -- Module outputs (all stored as JSONB for flexibility)
    module1_data jsonb,     -- Specs/extraction
    module4_data jsonb,     -- Sourcing
    module6_data jsonb,     -- TCO
    module7_business jsonb, -- Business plan
    module7_pitch jsonb,    -- Pitch deck
    module9_data jsonb,     -- Catalog
    module2_data jsonb,     -- Layout
    module3_data jsonb,     -- Video
    
    -- Workflow state
    completed_modules text[] default '{}',  -- Array of completed module names
    current_module text,                    -- Currently processing module
    
    -- Metadata
    settings jsonb default '{}'::jsonb,     -- Pipeline settings
    metadata jsonb default '{}'::jsonb,     -- Any additional data
    
    -- Timestamps
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Auto-update timestamp trigger
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger projects_set_updated_at
before update on public.projects
for each row execute function public.set_updated_at();

-- Indexes for common queries
create index if not exists projects_owner_id_idx on public.projects(owner_id);
create index if not exists projects_status_idx on public.projects(status);
create index if not exists projects_created_at_idx on public.projects(created_at desc);

-- ============================================================
-- STORAGE BUCKET (for uploaded files)
-- ============================================================

insert into storage.buckets (id, name, public)
values ('project-files', 'project-files', true)
on conflict (id) do update set public = true;

-- ============================================================
-- SIMPLE RLS POLICIES
-- For development: allow all operations with service role
-- For production: add proper user-based policies
-- ============================================================

alter table public.projects enable row level security;

-- Allow all operations (use service role key to bypass RLS anyway)
create policy "allow_all_projects" on public.projects
    for all using (true) with check (true);

-- Storage: allow public access for simplicity
create policy "allow_all_storage" on storage.objects
    for all using (bucket_id = 'project-files') with check (bucket_id = 'project-files');
