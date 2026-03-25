-- Per-tenant label overrides for i18n
create table tenant_locales (
  tenant_id text not null references tenant_registry(id) on delete cascade,
  key text not null,
  value text not null,
  primary key (tenant_id, key)
);

-- Index for fast lookup by tenant
create index idx_tenant_locales_tenant on tenant_locales(tenant_id);
