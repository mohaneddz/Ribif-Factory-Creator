-- Supabase schema initialization for RIBIF
-- Generated: 2026-01-29

create extension if not exists pgcrypto;

-- Helper: updated_at trigger
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;


-- Profiles (linked to auth.users)
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique,
  full_name text,
  avatar_url text,
  company text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

-- Projects
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references auth.users(id) on delete set null,
  name text not null,
  client text,
  location_city text,
  location_country text,
  status text not null default 'draft',
  project_type text,
  description text,
  metadata jsonb not null default '{}'::jsonb,
  current_pipeline_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger projects_set_updated_at
before update on public.projects
for each row execute function public.set_updated_at();

create index if not exists projects_owner_id_idx on public.projects(owner_id);
create index if not exists projects_status_idx on public.projects(status);

-- Project members
create table if not exists public.project_members (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'member',
  created_at timestamptz not null default now(),
  unique (project_id, user_id)
);

create index if not exists project_members_project_id_idx on public.project_members(project_id);
create index if not exists project_members_user_id_idx on public.project_members(user_id);

-- Helper: project membership check (must be after table creation)
create or replace function public.is_project_member(p_project_id uuid)
returns boolean
language sql
stable
as $$
  select exists (
    select 1
    from public.project_members pm
    where pm.project_id = p_project_id
      and pm.user_id = auth.uid()
  )
  or exists (
    select 1
    from public.projects p
    where p.id = p_project_id
      and p.owner_id = auth.uid()
  );
$$;

-- Project settings (used for pipeline configuration)
create table if not exists public.project_settings (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null unique references public.projects(id) on delete cascade,
  settings jsonb not null default '{}'::jsonb,
  updated_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger project_settings_set_updated_at
before update on public.project_settings
for each row execute function public.set_updated_at();

-- Project files (Supabase storage objects)
create table if not exists public.project_files (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  owner_id uuid references auth.users(id) on delete set null,
  bucket text not null,
  object_path text not null,
  mime_type text,
  size_bytes bigint,
  category text,
  label text,
  checksum text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (bucket, object_path)
);

create index if not exists project_files_project_id_idx on public.project_files(project_id);
create index if not exists project_files_category_idx on public.project_files(category);

-- Module 1 extraction
create table if not exists public.module1_extractions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  source_file_id uuid references public.project_files(id) on delete set null,
  data jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists module1_extractions_project_id_idx on public.module1_extractions(project_id);

-- Machines
create table if not exists public.machines (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  name text not null,
  machine_type text,
  manufacturer text,
  quantity integer not null default 1,
  use text,
  specifications jsonb not null default '{}'::jsonb,
  performance jsonb not null default '{}'::jsonb,
  source_reference text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger machines_set_updated_at
before update on public.machines
for each row execute function public.set_updated_at();

create index if not exists machines_project_id_idx on public.machines(project_id);

-- Machine assets (images, datasheets, cad, models, plans)
create table if not exists public.machine_assets (
  id uuid primary key default gen_random_uuid(),
  machine_id uuid not null references public.machines(id) on delete cascade,
  file_id uuid references public.project_files(id) on delete set null,
  asset_type text not null,
  label text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists machine_assets_machine_id_idx on public.machine_assets(machine_id);

-- Suppliers (Module 4)
create table if not exists public.suppliers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  website text,
  region text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists suppliers_name_idx on public.suppliers(name);

create table if not exists public.machine_suppliers (
  id uuid primary key default gen_random_uuid(),
  machine_id uuid not null references public.machines(id) on delete cascade,
  supplier_id uuid not null references public.suppliers(id) on delete cascade,
  price_estimate text,
  price_type text,
  price_currency text,
  lead_time_days integer,
  relevance_score numeric,
  notes text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (machine_id, supplier_id)
);

create index if not exists machine_suppliers_machine_id_idx on public.machine_suppliers(machine_id);
create index if not exists machine_suppliers_supplier_id_idx on public.machine_suppliers(supplier_id);

-- Module 4 sourcing output
create table if not exists public.module4_sourcing (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  module1_id uuid references public.module1_extractions(id) on delete set null,
  data jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists module4_sourcing_project_id_idx on public.module4_sourcing(project_id);

-- Pipelines (flows between machines)
create table if not exists public.pipelines (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  generated_by uuid references auth.users(id) on delete set null,
  version integer not null default 1,
  groups jsonb,
  flows jsonb,
  layout_suggestion jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists pipelines_project_id_idx on public.pipelines(project_id);

alter table public.projects
  add constraint projects_current_pipeline_fk
  foreign key (current_pipeline_id)
  references public.pipelines(id)
  on delete set null;

-- Layout outputs (2D/3D)
create table if not exists public.layouts (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  pipeline_id uuid references public.pipelines(id) on delete set null,
  layout_2d_file_id uuid references public.project_files(id) on delete set null,
  layout_3d_file_id uuid references public.project_files(id) on delete set null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists layouts_project_id_idx on public.layouts(project_id);

-- Video outputs
create table if not exists public.videos (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  file_id uuid references public.project_files(id) on delete set null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists videos_project_id_idx on public.videos(project_id);

-- TCO runs and line items
create table if not exists public.tco_runs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  module4_id uuid references public.module4_sourcing(id) on delete set null,
  currency text not null default 'DZD',
  total_tco numeric,
  average_annual_tco numeric,
  tco_per_unit_revenue numeric,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists tco_runs_project_id_idx on public.tco_runs(project_id);

create table if not exists public.tco_machines (
  id uuid primary key default gen_random_uuid(),
  tco_run_id uuid not null references public.tco_runs(id) on delete cascade,
  machine_id uuid references public.machines(id) on delete set null,
  machine_name text,
  category text,
  manufacturer text,
  initial_cost numeric,
  operations_cost numeric,
  maintenance_cost numeric,
  downtime_cost numeric,
  resale_value numeric,
  total_tco numeric,
  annual_tco numeric,
  lifetime_years integer,
  cost_breakdown jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.tco_products (
  id uuid primary key default gen_random_uuid(),
  tco_run_id uuid not null references public.tco_runs(id) on delete cascade,
  product_name text,
  category text,
  landing_cost numeric,
  holding_cost numeric,
  quality_cost numeric,
  administrative_cost numeric,
  total_tco numeric,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.tco_raw_materials (
  id uuid primary key default gen_random_uuid(),
  tco_run_id uuid not null references public.tco_runs(id) on delete cascade,
  material_name text,
  material_type text,
  total_tco numeric,
  annual_cost numeric,
  transport_cost numeric,
  storage_cost numeric,
  wastage_cost numeric,
  estimation_confidence text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.tco_annual (
  id uuid primary key default gen_random_uuid(),
  tco_run_id uuid not null references public.tco_runs(id) on delete cascade,
  year integer,
  machines_tco numeric,
  products_tco numeric,
  raw_materials_tco numeric,
  total_tco numeric,
  cumulative_tco numeric,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- Business plans
create table if not exists public.business_plans (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  tco_run_id uuid references public.tco_runs(id) on delete set null,
  file_id uuid references public.project_files(id) on delete set null,
  filename text,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists business_plans_project_id_idx on public.business_plans(project_id);

-- Pitch decks
create table if not exists public.pitch_decks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  tco_run_id uuid references public.tco_runs(id) on delete set null,
  file_id uuid references public.project_files(id) on delete set null,
  presentation_id text,
  edit_url text,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists pitch_decks_project_id_idx on public.pitch_decks(project_id);

-- Catalogs
create table if not exists public.catalogs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  module1_id uuid references public.module1_extractions(id) on delete set null,
  pdf_file_id uuid references public.project_files(id) on delete set null,
  html_file_id uuid references public.project_files(id) on delete set null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists catalogs_project_id_idx on public.catalogs(project_id);

-- Storage buckets (safe to re-run)
insert into storage.buckets (id, name, public)
values ('project-files', 'project-files', false)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('public-assets', 'public-assets', true)
on conflict (id) do nothing;

-- RLS
alter table public.profiles enable row level security;
alter table public.projects enable row level security;
alter table public.project_members enable row level security;
alter table public.project_settings enable row level security;
alter table public.project_files enable row level security;
alter table public.module1_extractions enable row level security;
alter table public.machines enable row level security;
alter table public.machine_assets enable row level security;
alter table public.suppliers enable row level security;
alter table public.machine_suppliers enable row level security;
alter table public.module4_sourcing enable row level security;
alter table public.pipelines enable row level security;
alter table public.layouts enable row level security;
alter table public.videos enable row level security;
alter table public.tco_runs enable row level security;
alter table public.tco_machines enable row level security;
alter table public.tco_products enable row level security;
alter table public.tco_raw_materials enable row level security;
alter table public.tco_annual enable row level security;
alter table public.business_plans enable row level security;
alter table public.pitch_decks enable row level security;
alter table public.catalogs enable row level security;

-- Profiles policies
create policy "profiles_select_own" on public.profiles
  for select using (auth.uid() = id);
create policy "profiles_update_own" on public.profiles
  for update using (auth.uid() = id) with check (auth.uid() = id);
create policy "profiles_insert_own" on public.profiles
  for insert with check (auth.uid() = id);

-- Projects policies
create policy "projects_select_members" on public.projects
  for select using (public.is_project_member(id));
create policy "projects_insert_owner" on public.projects
  for insert with check (auth.uid() = owner_id);
create policy "projects_update_owner" on public.projects
  for update using (auth.uid() = owner_id) with check (auth.uid() = owner_id);
create policy "projects_delete_owner" on public.projects
  for delete using (auth.uid() = owner_id);

-- Project members policies
create policy "project_members_select" on public.project_members
  for select using (public.is_project_member(project_id));
create policy "project_members_manage_owner" on public.project_members
  for all using (
    exists (select 1 from public.projects p where p.id = project_id and p.owner_id = auth.uid())
  ) with check (
    exists (select 1 from public.projects p where p.id = project_id and p.owner_id = auth.uid())
  );

-- Project settings policies
create policy "project_settings_select" on public.project_settings
  for select using (public.is_project_member(project_id));
create policy "project_settings_upsert" on public.project_settings
  for all using (public.is_project_member(project_id))
  with check (public.is_project_member(project_id));

-- Project files policies
create policy "project_files_select" on public.project_files
  for select using (public.is_project_member(project_id));
create policy "project_files_insert" on public.project_files
  for insert with check (public.is_project_member(project_id));
create policy "project_files_update" on public.project_files
  for update using (public.is_project_member(project_id))
  with check (public.is_project_member(project_id));
create policy "project_files_delete" on public.project_files
  for delete using (public.is_project_member(project_id));

-- Module 1 extractions policies
create policy "module1_select" on public.module1_extractions
  for select using (public.is_project_member(project_id));
create policy "module1_insert" on public.module1_extractions
  for insert with check (public.is_project_member(project_id));

-- Machines policies
create policy "machines_select" on public.machines
  for select using (public.is_project_member(project_id));
create policy "machines_insert" on public.machines
  for insert with check (public.is_project_member(project_id));
create policy "machines_update" on public.machines
  for update using (public.is_project_member(project_id)) with check (public.is_project_member(project_id));
create policy "machines_delete" on public.machines
  for delete using (public.is_project_member(project_id));

-- Machine assets policies
create policy "machine_assets_select" on public.machine_assets
  for select using (exists (
    select 1 from public.machines m where m.id = machine_id and public.is_project_member(m.project_id)
  ));
create policy "machine_assets_insert" on public.machine_assets
  for insert with check (exists (
    select 1 from public.machines m where m.id = machine_id and public.is_project_member(m.project_id)
  ));
create policy "machine_assets_update" on public.machine_assets
  for update using (exists (
    select 1 from public.machines m where m.id = machine_id and public.is_project_member(m.project_id)
  )) with check (exists (
    select 1 from public.machines m where m.id = machine_id and public.is_project_member(m.project_id)
  ));
create policy "machine_assets_delete" on public.machine_assets
  for delete using (exists (
    select 1 from public.machines m where m.id = machine_id and public.is_project_member(m.project_id)
  ));

-- Suppliers policies (read-only for members)
create policy "suppliers_select" on public.suppliers
  for select using (true);

-- Machine suppliers policies
create policy "machine_suppliers_select" on public.machine_suppliers
  for select using (exists (
    select 1 from public.machines m where m.id = machine_id and public.is_project_member(m.project_id)
  ));
create policy "machine_suppliers_insert" on public.machine_suppliers
  for insert with check (exists (
    select 1 from public.machines m where m.id = machine_id and public.is_project_member(m.project_id)
  ));

-- Module 4 policies
create policy "module4_select" on public.module4_sourcing
  for select using (public.is_project_member(project_id));
create policy "module4_insert" on public.module4_sourcing
  for insert with check (public.is_project_member(project_id));

-- Pipelines policies
create policy "pipelines_select" on public.pipelines
  for select using (public.is_project_member(project_id));
create policy "pipelines_insert" on public.pipelines
  for insert with check (public.is_project_member(project_id));
create policy "pipelines_update" on public.pipelines
  for update using (public.is_project_member(project_id)) with check (public.is_project_member(project_id));

-- Layouts policies
create policy "layouts_select" on public.layouts
  for select using (public.is_project_member(project_id));
create policy "layouts_insert" on public.layouts
  for insert with check (public.is_project_member(project_id));

-- Videos policies
create policy "videos_select" on public.videos
  for select using (public.is_project_member(project_id));
create policy "videos_insert" on public.videos
  for insert with check (public.is_project_member(project_id));

-- TCO policies
create policy "tco_runs_select" on public.tco_runs
  for select using (public.is_project_member(project_id));
create policy "tco_runs_insert" on public.tco_runs
  for insert with check (public.is_project_member(project_id));

create policy "tco_machines_select" on public.tco_machines
  for select using (exists (
    select 1 from public.tco_runs tr where tr.id = tco_run_id and public.is_project_member(tr.project_id)
  ));
create policy "tco_machines_insert" on public.tco_machines
  for insert with check (exists (
    select 1 from public.tco_runs tr where tr.id = tco_run_id and public.is_project_member(tr.project_id)
  ));

create policy "tco_products_select" on public.tco_products
  for select using (exists (
    select 1 from public.tco_runs tr where tr.id = tco_run_id and public.is_project_member(tr.project_id)
  ));
create policy "tco_products_insert" on public.tco_products
  for insert with check (exists (
    select 1 from public.tco_runs tr where tr.id = tco_run_id and public.is_project_member(tr.project_id)
  ));

create policy "tco_raw_materials_select" on public.tco_raw_materials
  for select using (exists (
    select 1 from public.tco_runs tr where tr.id = tco_run_id and public.is_project_member(tr.project_id)
  ));
create policy "tco_raw_materials_insert" on public.tco_raw_materials
  for insert with check (exists (
    select 1 from public.tco_runs tr where tr.id = tco_run_id and public.is_project_member(tr.project_id)
  ));

create policy "tco_annual_select" on public.tco_annual
  for select using (exists (
    select 1 from public.tco_runs tr where tr.id = tco_run_id and public.is_project_member(tr.project_id)
  ));
create policy "tco_annual_insert" on public.tco_annual
  for insert with check (exists (
    select 1 from public.tco_runs tr where tr.id = tco_run_id and public.is_project_member(tr.project_id)
  ));

-- Business plans policies
create policy "business_plans_select" on public.business_plans
  for select using (public.is_project_member(project_id));
create policy "business_plans_insert" on public.business_plans
  for insert with check (public.is_project_member(project_id));

-- Pitch decks policies
create policy "pitch_decks_select" on public.pitch_decks
  for select using (public.is_project_member(project_id));
create policy "pitch_decks_insert" on public.pitch_decks
  for insert with check (public.is_project_member(project_id));

-- Catalogs policies
create policy "catalogs_select" on public.catalogs
  for select using (public.is_project_member(project_id));
create policy "catalogs_insert" on public.catalogs
  for insert with check (public.is_project_member(project_id));

-- Storage RLS policies for project-files bucket (private)
create policy "project_files_storage_select" on storage.objects
  for select using (bucket_id = 'project-files' and auth.uid() = owner);
create policy "project_files_storage_insert" on storage.objects
  for insert with check (bucket_id = 'project-files' and auth.uid() = owner);
create policy "project_files_storage_update" on storage.objects
  for update using (bucket_id = 'project-files' and auth.uid() = owner)
  with check (bucket_id = 'project-files' and auth.uid() = owner);

