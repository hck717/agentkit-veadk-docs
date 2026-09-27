"""Seed OpenViking indexes for the fair (BytePlus + local OpenViking) redo.

Creates fin_kb_chunk / fin_kb_vis / fin_kb_cmb from the axis corpora and
probes fs/tree to return the doc->URI grouping map for the runner.

Layering note: OpenViking names the folder after the file stem (sans ext) +
an 8-hex hash suffix, so part files land as `<short>_NNNN_<hash>/`. A gold doc
matches every folder whose normalized stem hashes to that doc.

Usage: python scripts/seed_fair_kbs.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

RAG_OPT = Path(__file__).resolve().parents[1]
PROJ = RAG_OPT.parents[1]
if str(PROJ) not in sys.path:
    sys.path.insert(0, str(PROJ))

from experiments import _lib  # noqa: E402
from experiments.rag_bench.eval_set import LOCAL_DOCS  # noqa: E402

DATASETS = RAG_OPT / "datasets"

INDEXES = {
    "fin_kb_chunk": DATASETS / "kb_chunk",
    "fin_kb_vis": DATASETS / "kb_vis_seed",
    "fin_kb_cmb": DATASETS / "kb_cmb",
}

VIS_GOLD = {"msft_scan": "msft_scan.pdf", "msft_azure_revenue": "msft_azure_revenue.csv",
            "msft_ai_capex": "msft_ai_capex.txt", "msft_kb_overview": "msft_kb_overview.html"}

HASH_RE = re.compile(r"_[0-9a-f]{8}$")
PART_RE = re.compile(r"_\d{4,6}$")


def norm_stem(basename: str) -> str:
    """Folder basename -> canonical stem (strip server hash + part suffix)."""
    stem = basename
    stem = HASH_RE.sub("", stem)
    stem = PART_RE.sub("", stem)
    return stem


def short(stem: str, n: int = 40) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", stem)[:n]


def gold_docs():
    """gold filename -> canonical stem used in folder names (single prefix per doc)."""
    gold = {}
    for d in sorted(LOCAL_DOCS):
        stem = d.rsplit(".", 1)[0]
        key = stem.rsplit(".", 1)[0] if stem.endswith(".pdf") else stem
        gold[d] = short(re.sub(r"[^A-Za-z0-9._-]", "_", key), 40)
    for stem, fname in sorted(VIS_GOLD.items()):
        gold[fname] = norm_stem(short(stem, 45))
    return gold


def seed(client, index: str, path: Path):
    print(f"\n=== seed {index} from {path.name} ({len(list(path.glob('*')))} files) ===")
    t0 = time.time()
    r = client.add_resource(path=str(path), to=f"viking://resources/{index}",
                            wait=True, timeout=1200, strict=False, preserve_structure=True)
    dt = time.time() - t0
    meta = r.get("meta", {}) or {}
    print(f"  done in {dt:.1f}s status={r.get('status')} processed={meta.get('file_count')} "
          f"failed={meta.get('failed_files')}")
    q = r.get("queue_status", {}) or {}
    emb = q.get("Embedding", {}) or {}
    print(f"  queue embedding processed={emb.get('processed')} errors={emb.get('errors')}")


def map_docs(client, index: str):
    """gold filename -> single doc-level prefix, verified against the live tree."""
    rows = client.tree(f"viking://resources/{index}") or []
    dirs = [e.get("uri") for e in rows if e.get("isDir")]
    stems = {u.rstrip("/").rsplit("/", 1)[-1]: u for u in dirs}
    gold = gold_docs()
    inv, warnings = {}, []
    for d, gs in gold.items():
        prefix = f"viking://resources/{index}/{gs}"
        # robustness: fall back to a live folder whose stem matches
        live = [u for st, u in stems.items() if st == gs or st.startswith(gs) or gs.startswith(st)]
        if not live:
            warnings.append(f"{d}: no live folder for stem {gs!r}")
            inv[d] = prefix
            continue
        # confirm the doc-level prefix only covers this doc's folders
        foreign = [u for st, u in stems.items() if u.startswith(prefix) and not (st == gs or st.startswith(gs))]
        if foreign:
            warnings.append(f"{d}: prefix {prefix} also covers foreign folders {foreign[:2]}")
        inv[d] = prefix
    assert len({v for v in inv.values()}) == len(inv), "non-unique doc prefixes!"
    return inv, dirs, warnings


def main():
    _lib.load_env()
    from openviking_sdk import SyncHTTPClient

    client = SyncHTTPClient(
        url=_lib.os.environ.get("DATABASE_OPENVIKING_URL", "http://localhost:1933"),
        api_key=_lib.os.environ.get("DATABASE_OPENVIKING_API_KEY"),
        timeout=300,
    )
    client.initialize()
    out = {}
    try:
        for index, path in INDEXES.items():
            seed(client, index, path)
            inv, dirs, warnings = map_docs(client, index)
            mapped = sum(1 for d in inv if any(
                u.startswith(inv[d]) for u in dirs))
            print(f"  {index}: {len(dirs)} dirs ; docs w/ live folder {mapped}/{len(inv)}")
            for w in warnings:
                print(f"    !! {w}")
            out[index] = inv
    finally:
        client.close()
    (RAG_OPT / "results" / "fair" ).mkdir(parents=True, exist_ok=True)
    out["_meta"] = {"seeded_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(RAG_OPT / "results" / "fair" / "doc_uris.json", "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("\nwrote results/fair/doc_uris.json")


if __name__ == "__main__":
    main()