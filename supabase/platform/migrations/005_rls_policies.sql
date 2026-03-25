-- Enable RLS on all tables
alter table tenant_registry enable row level security;
alter table tenant_configs enable row level security;
alter table tenant_locales enable row level security;
alter table wav_admin_users enable row level security;

-- Service role bypasses RLS (used by admin portal backend and tenant app server)
-- Anon/authenticated users get restricted access

-- tenant_configs: readable by authenticated (tenant apps use service role anyway)
create policy "tenant_configs_read" on tenant_configs
  for select to authenticated using (true);

create policy "tenant_configs_write" on tenant_configs
  for all to authenticated using (
    exists (
      select 1 from wav_admin_users
      where email = auth.jwt()->>'email'
      and role in ('wav_super_admin', 'wav_admin')
    )
  );

-- tenant_locales: same pattern
create policy "tenant_locales_read" on tenant_locales
  for select to authenticated using (true);

create policy "tenant_locales_write" on tenant_locales
  for all to authenticated using (
    exists (
      select 1 from wav_admin_users
      where email = auth.jwt()->>'email'
      and role in ('wav_super_admin', 'wav_admin')
    )
  );

-- tenant_registry: readable by wav_admin+
create policy "tenant_registry_read" on tenant_registry
  for select to authenticated using (
    exists (
      select 1 from wav_admin_users
      where email = auth.jwt()->>'email'
    )
  );

create policy "tenant_registry_write" on tenant_registry
  for all to authenticated using (
    exists (
      select 1 from wav_admin_users
      where email = auth.jwt()->>'email'
      and role in ('wav_super_admin', 'wav_admin')
    )
  );

-- wav_admin_users: CRUD for super_admin only
create policy "wav_admin_users_read" on wav_admin_users
  for select to authenticated using (
    exists (
      select 1 from wav_admin_users
      where email = auth.jwt()->>'email'
    )
  );

create policy "wav_admin_users_write" on wav_admin_users
  for all to authenticated using (
    exists (
      select 1 from wav_admin_users
      where email = auth.jwt()->>'email'
      and role = 'wav_super_admin'
    )
  );
