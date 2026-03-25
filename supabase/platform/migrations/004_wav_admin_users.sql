-- WAV team members with portal access
create table wav_admin_users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  name text not null,
  role text not null default 'wav_admin'
    check (role in ('wav_super_admin', 'wav_admin')),
  created_at timestamptz not null default now()
);
