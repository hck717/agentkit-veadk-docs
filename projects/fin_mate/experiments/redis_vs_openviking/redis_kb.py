"""Redis Vector+FT KB：nomic-embed-text 768d via Ollama（同 OpenViking 一致）。

Build 階段：讀 data/kb/msft_txt/*.txt → split → embed → FT index（HNSW vector + TEXT）。
Search 階段：embed query → FT.SEARCH KNN → hydrate to read_limit → KnowledgeEntry。
Grep 階段：FT.SEARCH text match → [{uri, content}]（sparse channel 等價）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments._lib import load_env  # noqa: E402

TXT = "viking://resources/fin_kb/"

# ── Ollama embedding ────────────────────────────────────────────────────────
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768


@dataclass
class Entry:
    """Lightweight knowledge entry (mirrors veadk KnowledgebaseEntry interface)."""
    content: str
    metadata: dict = field(default_factory=dict)


def _embed_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed a list of texts via Ollama nomic-embed-text (batched, with retries)."""
    import httpx
    all_vecs: list[list[float]] = []
    for i, t in enumerate(texts):
        body = {"model": EMBED_MODEL, "prompt": t}
        for attempt in range(3):
            try:
                with httpx.Client(timeout=60) as c:
                    r = c.post(OLLAMA_EMBED_URL, json=body)
                    r.raise_for_status()
                    all_vecs.append(r.json()["embedding"])
                break
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(1.0 * (attempt + 1))
        if (i + 1) % 10 == 0:
            print(f"  Embedded {i+1}/{len(texts)} chunks...")
        if len(texts) > 1:  # only sleep during bulk KB builds, not per-query embeds
            time.sleep(0.1)
    return all_vecs


def _embed_one(text: str) -> list[float]:
    return _embed_batch([text])[0]


# ── Chunking ────────────────────────────────────────────────────────────────

_MAX_CHUNK = 1500  # nomic-embed-text context ~2048 tokens → cap at ~1500 chars


def _chunk_by_sentences(text: str, max_len: int = _MAX_CHUNK) -> list[str]:
    """Split text into chunks never exceeding max_len chars, on sentence/paragraph
    boundaries (nomic-embed-text raises on overly long input)."""
    units = re.split(r"(?<=[。.!?；;])\s*|\n{2,}", text)
    chunks: list[str] = []
    buf = ""
    for u in units:
        u = u.strip()
        if not u:
            continue
        while len(u) > max_len:  # hard-split pathological long units
            chunks.append(u[:max_len])
            u = u[max_len:]
        if buf and len(buf) + len(u) + 1 > max_len:
            chunks.append(buf)
            buf = u
        else:
            buf = f"{buf} {u}" if buf else u
    if buf:
        chunks.append(buf)
    return chunks if chunks else [text[:max_len]]


# ── Redis KB ────────────────────────────────────────────────────────────────

class RedisKB:
    """Redis vector + text index for fin_mate KB (nomic-embed-text 768d)."""

    def __init__(self, read_limit: int = 200, kb_root: Path | None = None,
                 redis_url: str = "redis://localhost:6379/0"):
        self.read_limit = read_limit
        self.kb_root = kb_root or (ROOT / "data" / "kb")
        self.index_name = "fin_kb_redis"
        self._url = redis_url
        self._client = None
        self._connected = False

    def _ensure_client(self):
        if self._client is None:
            from redis import Redis
            self._client = Redis.from_url(self._url, decode_responses=True)
            self._connected = True
        return self._client

    def _connect(self, url: str = "redis://localhost:6379/0"):
        self._url = url
        self._ensure_client()

    def build(self, force: bool = False):
        """Index all KB files into Redis (FT index + vector embeddings)."""
        self._connect()
        client = self._client

        # drop old index if force
        try:
            client.ft(self.index_name).dropindex(delete_documents=True)
        except Exception:
            pass

        # create FT index
        from redis.commands.search.field import VectorField, TextField, TagField
        from redis.commands.search.indexDefinition import IndexDefinition, IndexType

        schema = [
            TextField("uri", sortable=False),
            TextField("content", sortable=False),
            TagField("file"),
            TagField("folder"),
            VectorField("vector",
                        "HNSW",
                        {"TYPE": "FLOAT32", "DIM": EMBED_DIM,
                         "DISTANCE_METRIC": "COSINE", "INITIAL_CAP": 256}),
        ]
        client.ft(self.index_name).create_index(
            schema,
            definition=IndexDefinition(prefix=["fin_kb:"], index_type=IndexType.HASH),
        )

        # index all txt files
        txt_dir = self.kb_root / "msft_txt"
        if not txt_dir.exists():
            txt_dir = self.kb_root  # fallback
        files = sorted(txt_dir.glob("*.txt"))
        total_chunks = 0
        for fp in files:
            text = fp.read_text(encoding="utf-8", errors="replace")
            file_name = fp.name
            folder = file_name.rsplit(".", 1)[0]  # folder prefix in URI
            chunks = _chunk_by_sentences(text)
            vecs = _embed_batch(chunks)
            for idx, (chunk, vec) in enumerate(zip(chunks, vecs)):
                uri = f"{TXT}{folder}/{idx:04d}"
                key = f"fin_kb:{folder}:{idx:04d}"
                client.hset(key, mapping={
                    "uri": uri,
                    "content": chunk,
                    "file": file_name,
                    "folder": folder,
                    "vector": _vec_to_bytes(vec),
                })
                total_chunks += 1

        # Also index the overview if it exists
        overview = self.kb_root / "msft_overview.md"
        if overview.exists():
            text = overview.read_text(encoding="utf-8", errors="replace")
            chunks = _chunk_by_sentences(text)
            vecs = _embed_batch(chunks)
            for idx, (chunk, vec) in enumerate(zip(chunks, vecs)):
                uri = f"{TXT}msft_overview/{idx:04d}"
                key = f"fin_kb:msft_overview:{idx:04d}"
                client.hset(key, mapping={
                    "uri": uri,
                    "content": chunk,
                    "file": "msft_overview.md",
                    "folder": "msft_overview",
                    "vector": _vec_to_bytes(vec),
                })
                total_chunks += 1

        # verify
        info = client.ft(self.index_name).info()
        print(f"RedisKB built: {total_chunks} chunks indexed, "
              f"index={info.get('index_name', self.index_name)}")
        return total_chunks

    def search(self, query: str, top_k: int = 5) -> list[Entry]:
        """Dense search: embed query → KNN → hydrate content to read_limit."""
        client = self._ensure_client()
        qvec = _embed_one(query)
        qbytes = _vec_to_bytes(qvec)

        from redis.commands.search.query import Query
        q = (
            Query(f"*=>[KNN {top_k} @vector $vec AS score]")
            .sort_by("score")
            .return_fields("uri", "content", "file", "folder", "score")
            .dialect(2)
        )
        result = client.ft(self.index_name).search(q, query_params={"vec": qbytes})
        entries = []
        for doc in result.docs:
            c = str(getattr(doc, "content", "") or "")[:self.read_limit]
            dist = float(getattr(doc, "score", 0) or 0)
            entries.append(Entry(
                content=c,
                metadata={
                    "uri": str(getattr(doc, "uri", "") or ""),
                    "score": round(1.0 - dist, 4),   # COSINE distance → similarity (higher=better, ~OpenViking)
                    "dist": round(dist, 4),
                    "file": str(getattr(doc, "file", "") or ""),
                },
            ))
        return entries

    def grep(self, pattern: str, limit: int = 64, uri_prefix: str | None = None) -> list[dict]:
        """Sparse search: FT.SEARCH text match → [{uri, content}].
        pattern uses Redis full-text query syntax (| = OR, * = prefix)."""
        client = self._ensure_client()
        from redis.commands.search.query import Query

        # Build FT query: match pattern in content field
        ft_query = f"@content:({pattern})" if pattern else "*"
        q = (
            Query(ft_query)
            .return_fields("uri", "content")
            .paging(0, limit)
            .dialect(2)
        )
        result = client.ft(self.index_name).search(q)
        matches = []
        for doc in result.docs:
            uri = getattr(doc, "uri", "") or (doc.get("uri") if callable(getattr(doc, "get", None)) else "")
            if uri_prefix and not str(uri).startswith(uri_prefix):
                continue
            content = getattr(doc, "content", "") or (doc.get("content") if callable(getattr(doc, "get", None)) else "")
            matches.append({"uri": str(uri), "content": str(content)})
        return matches

    def doc_uris(self) -> dict[str, str]:
        """Map source filename → doc-level URI prefix (same as eval_set.all_doc_uris)."""
        txt_dir = self.kb_root / "msft_txt"
        if not txt_dir.exists():
            txt_dir = self.kb_root
        files = sorted(txt_dir.glob("*.txt"))
        out: dict[str, str] = {}
        for fp in files:
            folder = fp.name.rsplit(".", 1)[0]
            # strip trailing hash: _XXXXXXXX
            stripped = re.sub(r"_[0-9a-f]{8}$", "", folder)
            for d in _LOCAL_DOCS:
                if d not in out and d.startswith(stripped):
                    out[d] = f"{TXT}{folder}/"
        return out

    def close(self):
        if self._client:
            self._client.close()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _vec_to_bytes(vec: list[float]) -> bytes:
    """Convert float vector to raw bytes for Redis VECTOR field."""
    import struct
    return struct.pack(f"{len(vec)}f", *vec)


# ── Local docs (same as eval_set) ──────────────────────────────────────────

_LOCAL_DOCS = (
    "20260205_Deutsche_Bank_MSFT_Microsoft-_F2Q_Leaning_into_the_long_game.txt",
    "20260205_Mizuho_Securities_MSFT_MSFT-_Good_Overall_Execution-_Albeit_with_More_Modest_Az.txt",
    "20260212_China_Renaissance_Research_MSFT_Microsoft_Corp_F2Q26_Review-_Progresses_in_Azure_and_b.txt",
    "20260227_DeMatteo_Research_MSFT_MSFT_Long_Informal_Idea_Bberg_02.27.26.txt",
    "20260313_Barclays_MSFT_Microsoft_Corp.-_Evolving_AI_Offering_Brings_E7_to_Offic.txt",
    "20260316_Wells_Fargo_MSFT_MSFT-_Agentic_Adoption_Hinges_on_Security-_E7_SKU_Presen.txt",
    "Microsoft_Corp_Earnings_Call_20251029_DN000000003082552535.pdf.txt",
    "Microsoft_Corp_Earnings_Call_2026128_RT000000003094331726.pdf.txt",
)


# ── OpenViking wrapper (same interface as RedisKB) ──────────────────────────

class OpenVikingKB:
    """Wrapper around veadk OpenViking KB to match RedisKB interface."""

    def __init__(self, read_limit: int = 200):
        self.read_limit = read_limit
        self._kb = None

    def _ensure_loaded(self):
        if self._kb is None:
            from experiments._lib import build_kb
            os.environ["DATABASE_OPENVIKING_READ_LIMIT"] = str(self.read_limit)
            import agent_build
            agent_build._patch_openviking_hydrate()
            self._kb = agent_build.build_knowledgebase()

    def search(self, query: str, top_k: int = 5) -> list[Entry]:
        self._ensure_loaded()
        ov_entries = self._kb.search(query, top_k=top_k)
        return [Entry(
            content=e.content or "",
            metadata={
                "uri": (e.metadata or {}).get("uri", ""),
                "score": float((e.metadata or {}).get("score") or 0),
            },
        ) for e in ov_entries]

    def grep(self, pattern: str, limit: int = 64, uri_prefix: str | None = None) -> list[dict]:
        self._ensure_loaded()
        client = self._kb._backend._ensure_client()
        target = uri_prefix or TXT
        r = client.grep(uri=target, pattern=pattern, case_insensitive=True, node_limit=limit)
        if not isinstance(r, dict):
            matches = r if isinstance(r, list) else []
        else:
            matches = r.get("result", r)
            matches = matches.get("matches", []) if isinstance(matches, dict) else matches
        return [{"uri": m["uri"], "content": m.get("content", "")} for m in matches]

    def doc_uris(self) -> dict[str, str]:
        """Same as eval_set.all_doc_uris (OpenViking fs/tree probe)."""
        from experiments.rag_bench.eval_set import all_doc_uris
        return all_doc_uris()

    def close(self):
        pass
