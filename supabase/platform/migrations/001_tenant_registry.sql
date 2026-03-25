-- Tenant registry: master list of tenants and their infrastructure
create table tenant_registry (
  id text primary key,
  name text not null,
  status text not null default 'active'
    check (status in ('active', 'suspended', 'provisioning')),
  domain text,
  supabase_url text,
  supabase_anon_key text,
  r2_bucket text,
  vercel_project_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Auto-update updated_at
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger tenant_registry_updated_at
  before update on tenant_registry
  for each row execute function update_updated_at();
