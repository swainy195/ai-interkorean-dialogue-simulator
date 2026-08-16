create table if not exists public.simulation_sessions (
    id uuid primary key default gen_random_uuid(),
    scenario_id text not null,
    mode text not null default 'AI_VS_AI',
    status text not null default 'RUNNING',
    current_round integer not null default 0,
    max_rounds integer not null default 8,
    current_phase text not null default 'OPENING',
    active_agent_id text,
    negotiation_state jsonb not null default '{}'::jsonb,
    conversation_summary text not null default '',
    started_at timestamptz not null default now(),
    ended_at timestamptz,
    constraint simulation_sessions_status check (status in ('RUNNING','AGREEMENT','PARTIAL_AGREEMENT','BREAKDOWN'))
);
create table if not exists public.simulation_turns (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.simulation_sessions(id) on delete cascade,
    round integer not null,
    speaker_agent_id text not null,
    message text not null,
    intent text not null,
    phase text not null,
    structured_response jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (session_id, round)
);
create table if not exists public.simulation_evidence (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.simulation_sessions(id) on delete cascade,
    turn_id uuid not null references public.simulation_turns(id) on delete cascade,
    document_chunk_id uuid not null,
    similarity double precision,
    rank integer not null,
    created_at timestamptz not null default now(),
    unique (turn_id, document_chunk_id)
);
create table if not exists public.simulation_results (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null unique references public.simulation_sessions(id) on delete cascade,
    result_type text not null,
    summary text not null default '',
    south_position jsonb not null default '[]'::jsonb,
    north_position jsonb not null default '[]'::jsonb,
    agreements jsonb not null default '[]'::jsonb,
    unresolved_issues jsonb not null default '[]'::jsonb,
    follow_up_items jsonb not null default '[]'::jsonb,
    evaluation jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
create index if not exists simulation_turns_session_idx on public.simulation_turns(session_id, round);
create index if not exists simulation_evidence_session_idx on public.simulation_evidence(session_id);
