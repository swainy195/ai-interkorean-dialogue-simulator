-- Phase 5 exact pgvector retrieval function. No approximate index is required for PoC scale.
create or replace function public.match_document_chunks(
    query_embedding vector(2048),
    match_count integer default 10,
    source_types text[] default null,
    theme_filter text default null
)
returns table (
    id uuid,
    document_id text,
    content text,
    title text,
    source_type text,
    source_url text,
    metadata jsonb,
    similarity double precision
)
language sql
stable
as $$
    select
        dc.id,
        dc.document_id,
        dc.content,
        dc.title,
        dc.source_type,
        dc.source_url,
        dc.metadata,
        (1 - (dc.embedding <=> query_embedding))::double precision as similarity
    from public.document_chunks dc
    where dc.embedding is not null
      and (source_types is null or dc.source_type = any(source_types))
      and (theme_filter is null or dc.theme = theme_filter)
    order by dc.embedding <=> query_embedding
    limit greatest(match_count, 0);
$$;
