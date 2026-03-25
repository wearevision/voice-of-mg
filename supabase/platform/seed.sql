-- Seed: MG Motor as first tenant
insert into tenant_registry (id, name, status, domain)
values ('mg-motor', 'MG Motor Chile', 'active', 'intelligence.mgmotor.cl');

insert into tenant_configs (tenant_id, brand, features, pipeline, locale)
values (
  'mg-motor',
  '{
    "name": "MG Motor Chile",
    "logo": "/tenants/mg-motor/logo.svg",
    "logoSmall": "/tenants/mg-motor/logo-small.svg",
    "favicon": "/tenants/mg-motor/favicon.ico",
    "colors": {
      "primary": "oklch(0.345 0.183 14.7)",
      "primaryForeground": "oklch(0.966 0.008 60)",
      "secondary": "oklch(0.127 0.088 348)",
      "secondaryForeground": "oklch(0.966 0.008 60)",
      "background": "oklch(0.097 0.015 270)",
      "foreground": "oklch(0.966 0.008 60)",
      "card": "oklch(0.13 0.015 270)",
      "cardForeground": "oklch(0.966 0.008 60)",
      "muted": "oklch(0.18 0.012 270)",
      "mutedForeground": "oklch(0.60 0.01 270)",
      "accent": "oklch(0.576 0.243 24.5)",
      "accentForeground": "oklch(1 0 0)",
      "destructive": "oklch(0.704 0.191 22.216)",
      "border": "oklch(1 0 0 / 12%)",
      "input": "oklch(1 0 0 / 15%)",
      "ring": "oklch(0.345 0.183 14.7)"
    },
    "fonts": {
      "sans": "Geist Sans",
      "mono": "Geist Mono"
    }
  }'::jsonb,
  '{
    "video360": true,
    "videoDslr": true,
    "audioTracks": true,
    "semanticSearch": true,
    "ragQA": true,
    "pdfExport": true,
    "csvExport": true,
    "trends": true
  }'::jsonb,
  '{
    "transcriptionProvider": "elevenlabs",
    "videoSources": ["360", "dslr"],
    "audioTrackCount": 13,
    "aiModel": "anthropic/claude-sonnet-4.6"
  }'::jsonb,
  'es-CL'
);

-- Seed: WAV super admin
insert into wav_admin_users (email, name, role)
values ('federico@wearevision.cl', 'Federico Elgueta', 'wav_super_admin');
