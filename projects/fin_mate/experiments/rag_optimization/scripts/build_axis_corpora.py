"""Corpus builder for fair OpenViking redo (D8) — chunk/vis/cmb axis corpora.

Builds flat seed dirs that OpenViking ingests server-side (nomic-embed-text via
Ollama), mirroring exactly how the D4 baselines were seeded:

  data/kb_chunk/    — 8 analyst txts pre-chunked @ 256/50 (doc subfolders)
  data/kb_vis/seed  — 8 txts + text-extracted vis sources (csv/caption/scan/html)
  data/kb_cmb/      — chunked 8 txts + vis-extracted sources (Axes 1+2)

use_* flags skip already-built dirs. Chunking uses the same llama-index
SentenceSplitter(chunk_size, overlap) as D7 so the chunk axis is byte-fair.

Usage: python scripts/build_axis_corpora.py [--chunk-size 256] [--overlap 50]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAG_OPT = Path(__file__).resolve().parents[1]   # experiments/rag_optimization/
PROJ = RAG_OPT.parents[1]                        # projects/fin_mate
if str(PROJ) not in sys.path:
    sys.path.insert(0, str(PROJ))

TEXT_DIR = PROJ / "data" / "kb" / "msft_txt"
VIS_DIR = PROJ / "data" / "kb_vis"
OUT = RAG_OPT / "datasets"
CHUNK_DIR = OUT / "kb_chunk"
VIS_SEED = OUT / "kb_vis_seed"
CMB_DIR = OUT / "kb_cmb"

TEXTS = sorted(TEXT_DIR.glob("*.txt"))


def short_name(p: Path, n: int = 40) -> str:
    """Folder-safe doc id: filename sans ext, truncated to n chars (server til～45)."""
    s = p.name.rsplit(".", 1)[0]
    s = re.sub(r"[^A-Za-z0-9._-]", "_", s)
    return s[:n]


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    from llama_index.core import Document
    from llama_index.core.node_parser import SentenceSplitter

    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    nodes = splitter.get_nodes_from_documents([Document(text=text)])
    return [n.text for n in nodes]


def extract_vis_text(src: Path) -> str:
    if src.suffix == ".txt":
        return src.read_text(encoding="utf-8")
    if src.suffix == ".csv":
        return src.read_text(encoding="utf-8")
    if src.suffix == ".pdf":
        import fitz  # PyMuPDF

        doc = fitz.open(str(src))
        return "\n".join(page.get_text() for page in doc) or ""
    if src.suffix == ".html":
        from bs4 import BeautifulSoup

        return BeautifulSoup(src.read_text(encoding="utf-8"), "html.parser").get_text(" ", strip=True)
    return ""


def build_chunk(chunk_size: int, overlap: int):
    if CHUNK_DIR.exists():
        print(f"[skip] {CHUNK_DIR} exists")
        return
    CHUNK_DIR.mkdir(parents=True)
    n_parts = 0
    for p in TEXTS:
        short = short_name(p)
        parts = chunk_text(p.read_text(encoding="utf-8"), chunk_size, overlap)
        for i, part in enumerate(parts):
            (CHUNK_DIR / f"{short}_{i:04d}.txt").write_text(part, encoding="utf-8")
            n_parts += 1
    print(f"[chunk] {len(TEXTS)} docs -> {n_parts} parts @ {chunk_size}/{overlap} -> {CHUNK_DIR}")


def build_vis():
    if VIS_SEED.exists():
        print(f"[skip] {VIS_SEED} exists")
        return
    VIS_SEED.mkdir(parents=True)
    n = 0
    for p in TEXTS:
        (VIS_SEED / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        n += 1
    for src in sorted(VIS_DIR.glob("*")):
        if src.suffix == ".png":
            continue
        txt = extract_vis_text(src)
        if not txt.strip():
            print(f"[warn] {src.name} extracted empty text — skip")
            continue
        # 統一 .txt（保證 OpenViking TextParser 食到；gold 映射用 stem）
        (VIS_SEED / (src.stem + ".txt")).write_text(txt, encoding="utf-8")
        n += 1
    print(f"[vis] {n} sources (8 txt + vis text) -> {VIS_SEED}")


def build_cmb(chunk_size: int, overlap: int):
    if CMB_DIR.exists():
        print(f"[skip] {CMB_DIR} exists")
        return
    CMB_DIR.mkdir(parents=True)
    n = 0
    for p in TEXTS:
        short = short_name(p)
        for i, part in enumerate(chunk_text(p.read_text(encoding="utf-8"), chunk_size, overlap)):
            (CMB_DIR / f"{short}_{i:04d}.txt").write_text(part, encoding="utf-8")
            n += 1
    for src in sorted(VIS_SEED.glob("*")):
        (CMB_DIR / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        n += 1
    print(f"[cmb] {n} files (chunked txt + vis) -> {CMB_DIR}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk-size", type=int, default=256)
    ap.add_argument("--overlap", type=int, default=50)
    args = ap.parse_args()
    build_chunk(args.chunk_size, args.overlap)
    build_vis()
    build_cmb(args.chunk_size, args.overlap)


if __name__ == "__main__":
    main()