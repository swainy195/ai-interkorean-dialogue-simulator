# Performance

## Request shape

One turn remains one frontend request. The response includes state, turn, evidence, moderator metadata, and terminal result when applicable; the frontend does not poll state or evidence during a turn.

## Streaming decision

The agent requires validated Structured JSON with Evidence IDs. Provider-level OpenRouter streaming was reviewed, but forwarding partial JSON would expose incomplete or invalid structured output and would require a second metadata path. Phase 9 keeps the validated JSON call and sends its speech in SSE chunks, with a non-streaming `/next` fallback. This preserves Evidence ID validation and the existing Agent contract.

## Retrieval

Evidence remains capped at 3 items per turn and the chunk content limit remains 750 characters. No batch embedding or extra retrieval call is introduced in the UI path.

## Measured local baseline

Run `python scripts/validation/measure_phase9.py` to record health, simulation-create, and warm-turn timings. The report separates FastAPI, RAG/embedding, OpenRouter, and total request timing when the service is running.

## Frontend

Vite production build is the bundle-size regression check. Local session recovery stores only `session_id` in localStorage; conversation content and secrets are never stored there.

## Known bottlenecks

Cold start and OpenRouter latency dominate a first turn. Supabase retrieval is executed once inside the backend turn request. Provider-level token streaming remains a later optimization because the current response contract is structured JSON.
