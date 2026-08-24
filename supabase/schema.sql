-- ShopLens schema — run in Supabase SQL editor
-- Tables per Epic 8 Day 1 / epics.md

create extension if not exists "pgcrypto";

create table if not exists videos (
    id uuid primary key default gen_random_uuid(),
    filename text,
    storage_key text,
    status text not null default 'queued'
        check (status in ('queued', 'processing', 'done', 'failed')),
    error text,
    created_at timestamptz not null default now()
);

create table if not exists zones (
    id uuid primary key default gen_random_uuid(),
    store_id text not null default 'default',
    name text not null,
    polygon jsonb not null,
    created_at timestamptz not null default now(),
    unique (store_id, name)
);

create table if not exists analytics (
    id uuid primary key default gen_random_uuid(),
    video_id uuid not null references videos(id) on delete cascade,
    payload jsonb not null,
    created_at timestamptz not null default now(),
    unique (video_id)
);

create table if not exists anomalies (
    id uuid primary key default gen_random_uuid(),
    video_id uuid not null references videos(id) on delete cascade,
    anomaly_type text not null
        check (anomaly_type in ('loitering', 'crowd_spike', 'zone_avoidance')),
    zone_id text,
    frame int,
    details jsonb,
    created_at timestamptz not null default now()
);

create table if not exists reports (
    id uuid primary key default gen_random_uuid(),
    video_id uuid not null references videos(id) on delete cascade,
    content text not null,
    model text,
    created_at timestamptz not null default now(),
    unique (video_id)
);

create index if not exists idx_anomalies_video on anomalies(video_id);

-- TODO(epic-8 day 1): enable RLS on all five tables; backend uses the service role key,
-- frontend reads zones/anomalies with the anon key + permissive read policies only.
