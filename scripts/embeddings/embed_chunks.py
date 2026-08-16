"""Create and cache OpenRouter embeddings for deterministic chunk JSONL."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
CHUNKS = ROOT / "data" / "processed" / "chunks"
CACHE = CHUNKS / "embedded_chunks.jsonl"
REPORT = CHUNKS / "embedding_report.json"
MODEL_DIMENSION = 2048
BATCH_SIZE = 16
load_dotenv(ROOT / ".env")


def content_hash(content: str) -> str:
    return hashlib.sha256(" ".join(content.split()).encode("utf-8")).hexdigest()


def load_cache(model: str) -> dict[str, list[float]]:
    if not CACHE.exists():
        return {}
    result = {}
    for line in CACHE.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("embedding_model") == model and row.get("content_hash") and len(row.get("embedding", [])) == MODEL_DIMENSION:
            result[row["content_hash"]] = row["embedding"]
    return result


def main() -> None:
    model = os.environ["OPENROUTER_EMBEDDING_MODEL"]
    source_rows = [json.loads(line) for line in (CHUNKS / "all_chunks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    cached = load_cache(model)
    embedded: dict[str, list[float]] = dict(cached)
    pending = []
    for row in source_rows:
        row["content_hash"] = content_hash(row["content"])
        row["embedding_model"] = model
        if row["content_hash"] not in embedded:
            pending.append(row)
    requests = 0
    failed: list[dict[str, Any]] = []
    tokens = 0
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json", "HTTP-Referer": "http://localhost:5173", "X-Title": "AI Inter-Korean Dialogue"}
    with httpx.Client(timeout=90, headers=headers) as client:
        for start in range(0, len(pending), BATCH_SIZE):
            group = pending[start:start + BATCH_SIZE]
            success = False
            last_error = ""
            for attempt in range(3):
                try:
                    response = client.post("https://openrouter.ai/api/v1/embeddings", json={"model": model, "input": [row["content"] for row in group]})
                    requests += 1
                    response.raise_for_status()
                    payload = response.json()
                    data = payload.get("data") or []
                    if len(data) != len(group):
                        raise RuntimeError(f"embedding count mismatch: expected {len(group)}, got {len(data)}")
                    ordered_data = sorted(data, key=lambda value: int(value.get("index", 0)))
                    for position, item in enumerate(ordered_data):
                        vector = item.get("embedding")
                        if not isinstance(vector, list) or len(vector) != MODEL_DIMENSION or any(not isinstance(value, (int, float)) for value in vector):
                            raise RuntimeError(f"invalid vector at batch index {position}")
                        embedded[group[position]["content_hash"]] = vector
                    usage = payload.get("usage") or {}
                    tokens += int(usage.get("prompt_tokens") or usage.get("total_tokens") or 0)
                    success = True
                    break
                except (httpx.HTTPError, ValueError, RuntimeError) as exc:
                    last_error = str(exc)
                    if attempt < 2:
                        time.sleep(2 ** attempt)
            if not success:
                failed.extend({"content_hash": row["content_hash"], "document_id": row["document_id"], "error": last_error} for row in group)
            if start and start % (BATCH_SIZE * 10) == 0:
                print(f"embedded={len(embedded)} pending={len(pending)} requests={requests}")
            time.sleep(0.15)
    output_rows = []
    for row in source_rows:
        vector = embedded.get(row["content_hash"])
        if vector is not None:
            row["embedding"] = vector
            output_rows.append(row)
    with CACHE.open("w", encoding="utf-8") as handle:
        for row in output_rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    report = {"model": model, "dimension": MODEL_DIMENSION, "source_chunks": len(source_rows), "embedded": len(output_rows), "skipped_cached": len(source_rows) - len(pending), "failed": len(failed), "requests": requests, "tokens": tokens, "failures": failed[:20]}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
