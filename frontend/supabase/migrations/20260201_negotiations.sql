-- ============================================================
-- NEGOTIATIONS TABLE FOR MODULE 5
-- Voice-first negotiation tracking with supplier links
-- Generated: 2026-02-01
-- ============================================================

-- Add module5_data column to projects if not exists
alter table public.projects
add column if not exists module5_data jsonb;

-- ============================================================
-- NEGOTIATIONS TABLE
-- Tracks individual negotiations with suppliers
-- ============================================================

create table if not exists public.negotiations (
    id uuid primary key default gen_random_uuid(),
    
    -- Links
    project_id uuid not null references public.projects(id) on delete cascade,
    
    -- Supplier info
    supplier_name text not null,
    supplier_email text,
    supplier_phone text,
    supplier_website text,
    supplier_region text,
    
    -- Machine/product info
    machine_name text not null,
    machine_type text,
    quantity integer not null default 1,
    
    -- Price tracking
    initial_price_estimate numeric,
    final_price numeric,
    currency text default 'DZD',
    discount_achieved numeric,  -- Percentage
    total_value numeric,
    
    -- Negotiation state
    status text not null default 'pending',  -- pending, link_sent, in_progress, completed, accepted, rejected, expired
    negotiation_rounds integer default 0,
    
    -- Voice call link (secure token for supplier access)
    link_token text unique,
    link_sent_at timestamptz,
    link_expires_at timestamptz,
    
    -- Voice call results
    voice_call_completed_at timestamptz,
    voice_call_transcript jsonb,  -- Array of {role, text, timestamp}
    rounds_history jsonb,         -- Array of {round, ai_offer, supplier_response, supplier_price}
    
    -- Buyer info
    buyer_company text default 'RIBIF Algeria',
    buyer_email text,
    buyer_contact_name text,
    
    -- Email tracking
    emails_sent jsonb default '[]'::jsonb,  -- Array of sent emails
    
    -- Timestamps
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Triggers
create trigger negotiations_set_updated_at
before update on public.negotiations
for each row execute function public.set_updated_at();

-- Indexes
create index if not exists negotiations_project_id_idx on public.negotiations(project_id);
create index if not exists negotiations_status_idx on public.negotiations(status);
create index if not exists negotiations_link_token_idx on public.negotiations(link_token);
create index if not exists negotiations_supplier_email_idx on public.negotiations(supplier_email);

-- RLS
alter table public.negotiations enable row level security;

-- Allow all operations (same pattern as projects table)
create policy "allow_all_negotiations" on public.negotiations
    for all using (true) with check (true);

-- ============================================================
-- HELPER FUNCTION: Generate secure negotiation link token
-- ============================================================

create or replace function public.generate_negotiation_token()
returns text
language plpgsql
as $$
begin
    return encode(gen_random_bytes(32), 'hex');
end;
$$;

-- ============================================================
-- VIEW: Active negotiations summary per project
-- ============================================================

create or replace view public.negotiations_summary as
select
    project_id,
    count(*) as total_negotiations,
    count(*) filter (where status = 'pending') as pending_count,
    count(*) filter (where status = 'link_sent') as link_sent_count,
    count(*) filter (where status = 'in_progress') as in_progress_count,
    count(*) filter (where status = 'completed' or status = 'accepted') as completed_count,
    count(*) filter (where status = 'rejected') as rejected_count,
    sum(total_value) filter (where status = 'accepted') as total_accepted_value,
    avg(discount_achieved) filter (where status = 'accepted') as avg_discount
from public.negotiations
group by project_id;
