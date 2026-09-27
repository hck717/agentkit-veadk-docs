#!/usr/bin/env python3
"""Append the topic Parts into veadk-agentkit-comprehensive-guide.html.

Part structure comes from guide_parts.py (shared with the .md twin), so a Part
may draw on several source documents — that is how the overlapping topics were
merged. Every source keeps all of its content; its own `#` title lands as an
<h2> sub-section inside the Part.

Purely additive: every fragment is inserted immediately before `</main>`, so no
existing byte of the guide is modified. The guide's own JS builds its Part grid,
`#partnav`, TOC, progress bar and search index from `main > h1`, so appended
Parts register themselves automatically — the shell needs no edits.

Heading levels: each source doc is converted with --shift-heading-level-by=1 so
its `#` title lands as <h2> and the injected Part heading stays the only <h1>
(the guide's JS treats `main > h1` as a Part boundary). --id-prefix keeps
auto-generated heading ids unique across Parts AND across the several sources
that may make up one Part ("安裝" appears in many docs).

Usage:
  python3 references/_build/splice_tabs_into_guide.py --check   # dry run, no write
  python3 references/_build/splice_tabs_into_guide.py           # write in place
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guide_parts as G  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "references"
GUIDE = REFS / "veadk-agentkit-comprehensive-guide.html"

MARKER = 'id="part10-overview"'
ANCHOR = "</main>"

# A note in the hero so the expanded scope is visible without opening partnav.
HERO_ANCHOR = '<div class="meta">語言：'
_N_SOURCES = sum(len(s) for _n, _t, _i, s in G.PARTS)
_N_MERGED = sum(1 for _n, _t, _i, s in G.PARTS if len(s) > 1)
HERO_NOTE = (
    f'<p style="margin:10px 0 0">另加 <b>{_N_SOURCES} 篇主題參考'
    f'（Part {G.ORIGINAL_PARTS}–{G.TOTAL_PARTS - 1}）</b>，其中 <b>{_N_MERGED} 個 Part '
    f'係同類主題合併</b>（內容全部保留，每個來源變成 Part 內嘅子章節）。'
    f'原攻略 Part 0–{G.ORIGINAL_PARTS - 1} 內容保持不變。</p>\n')


def md_fragment(path: Path, prefix: str) -> str:
    r = subprocess.run(
        ["pandoc", "-f", "gfm-tex_math_dollars", "-t", "html5",
         "--no-highlight", "--shift-heading-level-by=1",
         f"--id-prefix={prefix}"],
        input=path.read_text(encoding="utf-8").encode(),
        capture_output=True)
    if r.returncode != 0:
        sys.exit(f"pandoc failed on {path.name}: {r.stderr.decode()[:400]}")
    return r.stdout.decode()


def intro_fragment(path: Path) -> str:
    h = path.read_text(encoding="utf-8").strip()
    # drop the tab-shell banner ("📘 呢頁詳細解說…"), it makes no sense in the guide
    return re.sub(r'<div class="intro-bar">.*?</div>\s*', "", h, count=1, flags=re.S)


def source_fragment(rel: str, prefix: str) -> str:
    p = (ROOT / rel[3:]) if rel.startswith("../") else (REFS / rel)
    if not p.exists():
        sys.exit(f"missing source: {p}")
    if rel.endswith(".html"):
        return intro_fragment(p)
    return md_fragment(p, prefix)


def block(pid: str, title: str, frags: list[str]) -> str:
    """One Part: the <h1> boundary, then every source's converted body.

    The guide's part cards read the first <p> after the <h1> as the card
    description, so no separate summary field is needed.
    """
    body = "\n".join(f.strip() for f in frags)
    return f'\n<h1 id="{pid}">{title}</h1>\n{body}\n'


def ids_of(h: str):
    """ids from genuine tags only (escaped markup inside code samples ignored)."""
    tags = re.findall(r"<[a-zA-Z][^>]*>", h)
    return re.findall(r'(?<![-\w])id="([^"]+)"', "\n".join(tags))


def main() -> None:
    check = "--check" in sys.argv
    src = GUIDE.read_text(encoding="utf-8")

    if MARKER in src:
        sys.exit("guide already contains the tab parts — aborting (idempotent guard).")
    if ANCHOR not in src:
        sys.exit(f"anchor {ANCHOR!r} not found — aborting.")

    before_ids = set(ids_of(src))
    frags, report = [], []

    for num, title, pid, sources in G.PARTS:
        parts = []
        for idx, rel in enumerate(sources):
            # a unique prefix per source, so heading ids never collide
            parts.append(source_fragment(rel, f"{pid}-{idx}-"))
        frag = block(pid, title, parts)
        frags.append(frag)
        tag = f"  ({len(sources)} sources merged)" if len(sources) > 1 else ""
        report.append((num, pid, len(sources), len(frag), tag))

    added = "".join(frags)
    out = src.replace(ANCHOR, added + "\n" + ANCHOR, 1)
    if out == src:
        sys.exit(f"insertion anchor {ANCHOR!r} did not apply.")
    if HERO_ANCHOR not in out:
        sys.exit("hero anchor not found — aborting.")
    out = out.replace(HERO_ANCHOR, HERO_NOTE + HERO_ANCHOR, 1)

    # additive-only assertion: reverting both insertions must reproduce the original
    if out.replace(added + "\n", "", 1).replace(HERO_NOTE, "", 1) != src:
        sys.exit("NOT additive — aborting.")

    # the new parts must not reuse an existing id, nor collide with each other
    new_ids = ids_of(added)
    dups = sorted({x for x in new_ids if new_ids.count(x) > 1})
    clash = sorted(set(new_ids) & before_ids)
    if dups:
        sys.exit(f"duplicate ids inside the appended parts: {dups[:10]}")
    if clash:
        sys.exit(f"id collision with the existing guide: {clash[:10]}")

    # the Part headings themselves must be exactly the configured set
    h1s = re.findall(r'<h1[^>]*id="([^"]+)"', added)
    expect = [p[2] for p in G.PARTS]
    if h1s != expect:
        sys.exit(f"Part <h1> mismatch\n  got:    {h1s}\n  expect: {expect}")

    print(f"  guide {len(src):,} -> {len(out):,} chars  (+{len(out)-len(src):,})")
    for num, pid, nsrc, n, tag in report:
        print(f"    + P{num:<3} {pid:<20} {n:>9,} chars{tag}")
    print(f"  parts appended : {len(frags)}   new ids: {len(new_ids)}  "
          f"dups: 0  clashes: 0")

    if check:
        print("  check ok (dry run — nothing written)")
        return

    GUIDE.write_text(out, encoding="utf-8")
    print(f"  ✓ {GUIDE.name} updated")


if __name__ == "__main__":
    main()
