-- Tenant configuration: brand, features, pipeline settings
create table tenant_configs (
  tenant_id text primary key references tenant_registry(id) on delete cascade,
  brand jsonb not null,
  features jsonb not null,
  pipeline jsonb not null,
  locale text not null default 'es-CL',
  updated_at timestamptz not null default now()
);

create trigger tenant_configs_updated_at
  before update on tenant_configs
  for each row execute function update_updated_at();
