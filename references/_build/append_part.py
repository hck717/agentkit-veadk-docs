#!/usr/bin/env python3
"""Upsert the generated Parts into the comprehensive guide (HTML + .md twin).

Why this exists
---------------
The original pipeline is deliberately one-shot. splice_tabs_into_guide.py,
group_guide_parts.py, group_guide_partnav.py and sync_guide_md.py each abort or
no-op once they have run, because they were written to convert the handcrafted
guide exactly once. Adding a Part later therefore used to require rebuilding the
guide from a pristine original — only possible if you still happen to have one.

This script closes that gap. It is idempotent and general:

  * it rebuilds the whole appended region (Parts ORIGINAL_PARTS..TOTAL_PARTS-1)
    from guide_parts.PARTS, so it also picks up edits to a Part's source file
  * it refreshes the three artefacts baked into the files:
      - the section table, `const NAV_SEC=[…]` in the guide's JS.
        group_guide_partnav.py hoisted it into one declaration and made the Part
        card grid alias it (`GRID_SEC=NAV_SEC`), so there is exactly ONE place
        to patch and the grid and the floating nav can never disagree.
      - the hero note, "另加 N 篇主題參考（Part 10–M）"
      - the .md twin's table of contents and header parity claim
  * it verifies before writing: node --check over every inline script, the
    section table must map every Part heading exactly once, no new duplicate
    ids, no TOC link without a target, no code fence left open, and a second
    pass must be a byte-for-byte no-op

A Part's content still comes from its source document. This script does not
rewrite sources — edit `references/<file>.md`, then run this.

Usage:
  python3 references/_build/append_part.py --check   # dry run, no write
  python3 references/_build/append_part.py           # write in place
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guide_parts as G              # noqa: E402
import splice_tabs_into_guide as SP  # noqa: E402  (HTML fragment helpers)
import sync_guide_md as SM           # noqa: E402  (markdown fragment helpers)

ROOT = HERE.parents[1]
REFS = ROOT / "references"
GUIDE_HTML = REFS / "veadk-agentkit-comprehensive-guide.html"
GUIDE_MD = REFS / "veadk-agentkit-comprehensive-guide.md"

# ─── HTML anchors ──────────────────────────────────────────────────────────
MAIN_CLOSE = "</main>"
H1_RE = re.compile(r'<h1[^>]*id="(part[^"]*)"')
TAG_RE = re.compile(r"<[a-zA-Z][^>]*>")
ID_RE = re.compile(r'(?<![-\w])id="([^"]+)"')
NAV_RE = re.compile(r"const NAV_SEC=\[.*?\];", re.S)
HERO_RE = re.compile(r'<p style="margin:10px 0 0">另加 <b>.*?</p>', re.S)
SCRIPT_RE = re.compile(r"<script([^>]*)>(.*?)</script>", re.S)

# ─── .md anchors ───────────────────────────────────────────────────────────
MD_TOC = "## 目錄"
MD_BODY = "# Part 0 — 前置知識"
MD_PART_RE = re.compile(r"^# Part (\d+) —", re.M)
CLAIM_RE = re.compile(r"^> 同 HTML 互動版.*$", re.M)
SEC_HEAD = "### ▍ "

NODE_CANDIDATES = [
    Path("/Users/brianho/.workbuddy-ai/binaries/node/versions/22.22.2-2/bin/node"),
    Path("/opt/homebrew/bin/node"),
]


def node_bin() -> str:
    for c in NODE_CANDIDATES:
        if c.exists():
            return str(c)
    return "node"


def dup_ids(h: str) -> set[str]:
    """Ids that appear more than once among genuine (unescaped) tags."""
    ids = ID_RE.findall("\n".join(TAG_RE.findall(h)))
    return {x for x in ids if ids.count(x) > 1}


def check_js(h: str) -> None:
    """`node --check` every inline script — one syntax error kills all interactivity."""
    checked = bad = 0
    for n, (attrs, body) in enumerate(SCRIPT_RE.findall(h)):
        if "src=" in attrs:
            continue
        if "type=" in attrs and "javascript" not in attrs:
            continue
        if not body.strip():
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8") as f:
            f.write(body)
            tmp = f.name
        r = subprocess.run([node_bin(), "--check", tmp], capture_output=True, text=True)
        Path(tmp).unlink(missing_ok=True)
        checked += 1
        if r.returncode != 0:
            bad += 1
            print(f"  ✗ inline script #{n} SYNTAX ERROR:\n{r.stderr.strip()[:600]}")
    if bad:
        raise SystemExit(f"ABORT: {bad} inline script(s) failed node --check")
    print(f"  ✓ node --check passed on {checked} inline script block(s)")


def hero_note() -> str:
    n_sources = sum(len(s) for _n, _t, _i, s in G.PARTS)
    n_merged = sum(1 for _n, _t, _i, s in G.PARTS if len(s) > 1)
    return (f'<p style="margin:10px 0 0">另加 <b>{n_sources} 篇主題參考'
            f'（Part {G.ORIGINAL_PARTS}–{G.TOTAL_PARTS - 1}）</b>，其中 '
            f'<b>{n_merged} 個 Part 係同類主題合併</b>'
            f'（內容全部保留，每個來源變成 Part 內嘅子章節）。'
            f'原攻略 Part 0–{G.ORIGINAL_PARTS - 1} 內容保持不變。</p>')


def html_parts() -> dict[str, str]:
    """{part_id: '<h1>…</h1> + converted body'} for every generated Part."""
    out = {}
    for _num, title, pid, sources in G.PARTS:
        frags = [SP.source_fragment(rel, f"{pid}-{i}-")
                 for i, rel in enumerate(sources)]
        out[pid] = SP.block(pid, title, frags)
    return out


# ─── HTML ──────────────────────────────────────────────────────────────────
def upsert_html(h: str, verbose: bool = True) -> str:
    added = "".join(html_parts()[p[2]] for p in G.PARTS)
    tok = f'\n<h1 id="{G.PARTS[0][2]}"'
    i = h.find(tok)
    if i >= 0:
        # re-run: swap the whole generated region in place
        j = h.rfind(MAIN_CLOSE)
        if j < i:
            raise SystemExit(f"ABORT: {MAIN_CLOSE!r} does not follow the generated region")
        h = h[:i] + added + "\n" + h[j:]
        if verbose:
            print(f"  ✓ HTML region rebuilt ({len(G.PARTS)} Parts replaced)")
    else:
        if h.count(MAIN_CLOSE) != 1:
            raise SystemExit(f"ABORT: {MAIN_CLOSE!r} matched {h.count(MAIN_CLOSE)} times")
        h = h.replace(MAIN_CLOSE, added + "\n" + MAIN_CLOSE, 1)
        if verbose:
            print(f"  ✓ HTML region appended ({len(G.PARTS)} Parts inserted)")

    # section table — drives the Part card grid AND the floating #partnav
    h, n = NAV_RE.subn(lambda m: "const NAV_SEC=" + G.sections_js() + ";", h, count=1)
    if n != 1:
        raise SystemExit("ABORT: `const NAV_SEC=[…];` not found exactly once")
    if verbose:
        print("  ✓ NAV_SEC section table refreshed")

    h, n = HERO_RE.subn(lambda m: hero_note(), h, count=1)
    if n != 1:
        raise SystemExit("ABORT: hero note not found exactly once")
    if verbose:
        print("  ✓ hero note refreshed")
    return h


def verify_html(h: str, before_dups: set[str]) -> None:
    have = H1_RE.findall(h)
    expect = [p[2] for p in G.PARTS]
    if len(have) != G.TOTAL_PARTS:
        raise SystemExit(f"ABORT: guide has {len(have)} Part <h1>s, "
                         f"expected {G.TOTAL_PARTS}")
    missing = [i for i in expect if i not in have]
    if missing:
        raise SystemExit(f"ABORT: generated Parts missing from the guide: {missing}")
    if len(set(have)) != len(have):
        raise SystemExit("ABORT: duplicate Part ids in the guide")

    # the baked section table must map every Part heading exactly once
    assigned = [G.part_id(n) for _k, _l, ns in G.SECTIONS for n in ns]
    if sorted(assigned) != sorted(have):
        raise SystemExit(f"ABORT: NAV_SEC maps {len(assigned)} ids but the document "
                         f"has {len(have)} Part headings\n"
                         f"  only in table : {sorted(set(assigned) - set(have))}\n"
                         f"  only in doc   : {sorted(set(have) - set(assigned))}")
    print(f"  ✓ {len(have)} Part headings, section table maps all of them, "
          f"0 unknown")

    new_dups = dup_ids(h) - before_dups
    if new_dups:
        raise SystemExit(f"ABORT: new duplicate ids introduced: {sorted(new_dups)[:10]}")
    print(f"  ✓ no new duplicate ids ({len(dup_ids(h))} pre-existing)")
    check_js(h)


# ─── .md ───────────────────────────────────────────────────────────────────
def upsert_md(m: str, verbose: bool = True) -> str:
    if m.count(MD_TOC) != 1 or m.count(MD_BODY) != 1:
        raise SystemExit(f"ABORT: .md anchors not unique "
                         f"({MD_TOC!r}×{m.count(MD_TOC)}, {MD_BODY!r}×{m.count(MD_BODY)})")
    head_i, body_i = m.index(MD_TOC), m.index(MD_BODY)
    if head_i >= body_i:
        raise SystemExit("ABORT: .md TOC anchor must precede the body")
    pre, old_body = m[:head_i], m[body_i:]

    # ---- 1. drop the previously generated blocks -------------------------
    # render_block() emits "<rule>\n\n# <title>\n\n…", and the first generated
    # block is Part ORIGINAL_PARTS. The rule immediately before that heading is
    # ours (rfind, so an identical rule inside Parts 0–9 cannot be mistaken).
    marker = f"# {G.PARTS[0][1]}"
    k = old_body.find(marker)
    if k >= 0:
        j = old_body.rfind(SM.RULE, 0, k)
        if j < 0:
            raise SystemExit("ABORT: generated Part block found but its rule is missing")
        old_body = old_body[:j].rstrip("\n")
        if verbose:
            print("  ✓ .md generated region dropped for rebuild")

    # ---- 2. rebuild every Part block ------------------------------------
    added = "".join(SM.render_block(t, SM.part_body(s))
                    for _n, t, _i, s in G.PARTS)
    new_body = old_body + "\n\n" + added

    # ---- 3. split the body back into Parts ------------------------------
    marks = [(mm.start(), int(mm.group(1))) for mm in MD_PART_RE.finditer(new_body)]
    if len(marks) != G.TOTAL_PARTS:
        raise SystemExit(f"ABORT: expected {G.TOTAL_PARTS} '# Part N —' headings, "
                         f"found {len(marks)}")
    spans: dict[int, str] = {}
    for idx, (pos, num) in enumerate(marks):
        end = marks[idx + 1][0] if idx + 1 < len(marks) else len(new_body)
        spans[num] = new_body[pos:end]
    mapped = [n for _k, _l, nums in G.SECTIONS for n in nums]
    if sorted(mapped) != sorted(spans):
        raise SystemExit(f"ABORT: section table != document parts\n"
                         f"  table: {sorted(mapped)}\n  doc:   {sorted(spans)}")

    # ---- 4. assign slugs in DOCUMENT order ------------------------------
    seen: dict[str, int] = {}
    slugs: dict[int, list[tuple[int, str, str]]] = {}
    for num in sorted(spans):
        rows = []
        for lvl, text in SM.headings(spans[num], fence_aware=True, max_level=3):
            base = SM.anchor(text)
            n = seen.get(base, 0)
            seen[base] = n + 1
            rows.append((lvl, text, base if n == 0 else f"{base}-{n}"))
        slugs[num] = rows

    # ---- 5. emit the TOC in SECTION order -------------------------------
    toc = [MD_TOC, ""]
    for _key, label, nums in G.SECTIONS:
        toc.append(f"{SEC_HEAD}{label}")
        for num in nums:
            for lvl, text, slug in slugs[num]:
                toc.append("  " * (lvl - 1) + f"- [{text}](#{slug})")
        toc.append("")
    new_toc = "\n".join(toc).rstrip("\n") + "\n\n---\n\n"

    # ---- 6. refresh the parity claim in the header ----------------------
    cm = CLAIM_RE.search(pre)
    if not cm:
        raise SystemExit("ABORT: parity claim not found in the .md header")
    i, j = cm.start(), cm.end()
    while pre.startswith("\n>", j):          # consume the claim's own continuation
        e = pre.find("\n", j + 1)
        j = e if e >= 0 else len(pre)
    new_pre = pre[:i] + SM.NEW_CLAIM + pre[j:]
    if verbose:
        print(f"  ✓ .md header claim refreshed ({G.TOTAL_PARTS} Parts / "
              f"{len(G.SECTIONS)} sections)")

    new = new_pre + new_toc + new_body

    # ---- 7. verify ------------------------------------------------------
    links = re.findall(r"^\s*- \[[^\]]*\]\(#([^)]+)\)", new_toc, re.M)
    dupl = sorted({a for a in links if links.count(a) > 1})
    if dupl:
        raise SystemExit(f"ABORT: duplicate TOC anchors: {dupl[:8]}")
    known = {slug for rows in slugs.values() for _l, _t, slug in rows}
    broken = sorted({a for a in links if a not in known})
    if broken:
        raise SystemExit(f"ABORT: {len(broken)} TOC link(s) have no target: {broken[:8]}")
    _rows, unclosed = SM.fence_state(new)
    if unclosed:
        raise SystemExit("ABORT: a code fence is left open at end of document")
    print(f"  ✓ .md TOC: {len(links)} links, all unique and resolving; fences closed")
    return new


# ─── main ──────────────────────────────────────────────────────────────────
def main() -> None:
    check = "--check" in sys.argv
    h0 = GUIDE_HTML.read_text(encoding="utf-8")
    m0 = GUIDE_MD.read_text(encoding="utf-8")
    before_dups = dup_ids(h0)

    print(f"{GUIDE_HTML.name}: {len(h0.encode()):,} bytes")
    h = upsert_html(h0)
    verify_html(h, before_dups)
    print(f"  {len(h0.encode()):,} -> {len(h.encode()):,} bytes")

    print(f"{GUIDE_MD.name}: {len(m0.encode()):,} bytes")
    m = upsert_md(m0)
    print(f"  {len(m0.encode()):,} -> {len(m.encode()):,} bytes")

    # idempotence: a second pass must be a byte-for-byte no-op
    if upsert_html(h, verbose=False) != h:
        raise SystemExit("ABORT: HTML upsert is not idempotent")
    if upsert_md(m, verbose=False) != m:
        raise SystemExit("ABORT: .md upsert is not idempotent")
    print("  ✓ idempotent — second pass is a byte-for-byte no-op on both documents")

    if check:
        print("  check ok (dry run — nothing written)")
        return

    GUIDE_HTML.write_text(h, encoding="utf-8")
    GUIDE_MD.write_text(m, encoding="utf-8")
    print(f"  ✓ wrote {GUIDE_HTML.name} + {GUIDE_MD.name}")


if __name__ == "__main__":
    main()
