-- Phase 3 initial data schema.
-- Non-destructive: this migration does not remove existing table data.

create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists public.meetings (
    id uuid primary key default gen_random_uuid(),
    source_meeting_id text,
    meeting_name text not null,
    meeting_category text,
    meeting_field text,
    start_date date,
    end_date date,
    country text,
    region text,
    facility text,
    meeting_count integer,
    visit_count integer,
    summary text,
    source_type text not null default 'meeting_csv',
    source_url text,
    source_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint meetings_date_order check (end_date is null or start_date is null or end_date >= start_date),
    constraint meetings_counts_nonnegative check ((meeting_count is null or meeting_count >= 0) and (visit_count is null or visit_count >= 0))
);

create table if not exists public.agreements (
    id uuid primary key default gen_random_uuid(),
    document_id text not null unique,
    title text,
    subject text,
    theme text,
    category text,
    agreement_date date,
    meeting_start_date date,
    meeting_end_date date,
    country text,
    region text,
    facility text,
    content text,
    original_filename text,
    download_url text,
    source_url text,
    source_type text not null default 'agreement_api',
    source_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint agreements_date_order check (meeting_end_date is null or meeting_start_date is null or meeting_end_date >= meeting_start_date)
);

create table if not exists public.meeting_documents (
    id uuid primary key default gen_random_uuid(),
    document_id text not null unique,
    document_type text not null,
    title text,
    meeting_id uuid references public.meetings(id) on delete set null,
    agreement_id uuid references public.agreements(id) on delete set null,
    meeting_name text,
    document_date date,
    category text,
    content text,
    original_filename text,
    source_url text,
    extraction_method text,
    extraction_warning text,
    source_type text not null default 'meeting_document',
    source_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.historical_events (
    id uuid primary key default gen_random_uuid(),
    event_id text not null unique,
    event_date date,
    end_date date,
    title text,
    description text,
    event_type text,
    category text,
    source_type text not null default 'historical_event_csv',
    source_url text,
    source_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint historical_events_date_order check (end_date is null or event_date is null or end_date >= event_date)
);

create table if not exists public.document_chunks (
    id uuid primary key default gen_random_uuid(),
    document_id text not null,
    source_table text not null,
    source_record_id uuid,
    chunk_index integer not null,
    content text not null,
    title text,
    source_type text,
    meeting_name text,
    meeting_date date,
    category text,
    theme text,
    agenda text[],
    section text,
    source_url text,
    original_filename text,
    metadata jsonb not null default '{}'::jsonb,
    embedding_model text,
    embedding vector(2048),
    created_at timestamptz not null default now(),
    constraint document_chunks_index_nonnegative check (chunk_index >= 0),
    constraint document_chunks_source_table check (source_table in ('meetings', 'agreements', 'meeting_documents', 'historical_events')),
    constraint document_chunks_document_index_unique unique (document_id, chunk_index)
);

create index if not exists meetings_name_idx on public.meetings (meeting_name);
create unique index if not exists meetings_source_meeting_id_uidx on public.meetings (source_meeting_id) where source_meeting_id is not null;
create index if not exists meetings_dates_idx on public.meetings (start_date, end_date);
create index if not exists meetings_field_idx on public.meetings (meeting_field);
create index if not exists agreements_date_idx on public.agreements (agreement_date);
create index if not exists agreements_theme_category_idx on public.agreements (theme, category);
create index if not exists agreements_source_type_idx on public.agreements (source_type);
create index if not exists meeting_documents_meeting_idx on public.meeting_documents (meeting_id);
create index if not exists meeting_documents_agreement_idx on public.meeting_documents (agreement_id);
create index if not exists meeting_documents_source_type_idx on public.meeting_documents (source_type);
create index if not exists historical_events_date_idx on public.historical_events (event_date);
create index if not exists document_chunks_source_idx on public.document_chunks (source_table, source_record_id);
create index if not exists document_chunks_document_idx on public.document_chunks (document_id);

create or replace function public.set_phase3_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists meetings_set_updated_at on public.meetings;
create trigger meetings_set_updated_at before update on public.meetings for each row execute function public.set_phase3_updated_at();
drop trigger if exists agreements_set_updated_at on public.agreements;
create trigger agreements_set_updated_at before update on public.agreements for each row execute function public.set_phase3_updated_at();
drop trigger if exists meeting_documents_set_updated_at on public.meeting_documents;
create trigger meeting_documents_set_updated_at before update on public.meeting_documents for each row execute function public.set_phase3_updated_at();
drop trigger if exists historical_events_set_updated_at on public.historical_events;
create trigger historical_events_set_updated_at before update on public.historical_events for each row execute function public.set_phase3_updated_at();
