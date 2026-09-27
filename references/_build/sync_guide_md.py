#!/usr/bin/env python3
"""Bring veadk-agentkit-comprehensive-guide.md up to the guide's Part structure.

Structure comes from guide_parts.py (shared with the HTML side), so a Part may
draw on several source documents — that is how the overlapping topics were
merged. Each source keeps all of its content; its own `#` title becomes an `##`
sub-section inside the Part.

Headings are demoted by exactly 1 level (source `#` -> `##`), mirroring pandoc's
--shift-heading-level-by=1 on the HTML side, so the injected `# Part N` stays the
only H1. Demotion is FENCE-AWARE: a `# comment` inside a ``` block is left alone
(the source docs are full of shell comments).

The body change is purely additive (append at end); the table of contents is
regenerated.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guide_parts as G  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "references"
GUIDE = REFS / "veadk-agentkit-comprehensive-guide.md"

MARKER = "# Part 10 — 總覽 Overview"
RULE = "-" * 72
HEAD_ANCHOR = "## 目錄"
BODY_ANCHOR = "# Part 0 — 前置知識"
OLD_CLAIM = "> 同 HTML 互動版同源同深度（`veadk-agentkit-comprehensive-guide.html`）。"

N_MERGED = sum(1 for _n, _t, _i, s in G.PARTS if len(s) > 1)
N_SOURCES = sum(len(s) for _n, _t, _i, s in G.PARTS)
NEW_CLAIM = (
    "> 同 HTML 互動版**同源同深度**（`veadk-agentkit-comprehensive-guide.html`）。\n"
    ">\n"
    f"> **{G.TOTAL_PARTS} Parts · {len(G.SECTIONS)} 個分區** —— Part 0–9 = 原攻略；"
    f"Part 10–{G.TOTAL_PARTS - 1} = {N_SOURCES} 個主題參考（其中 {N_MERGED} 個 Part 係"
    "同類主題合併，內容全部保留）。\n"
    "> 分區：" + " · ".join(l for _k, l, _n in G.SECTIONS) + "。"
)


# ------------------------------------------------------------------ helpers
# A fence can be opened inside a list item (`- ```python`), which a naive
# lstrip().startswith("```") check misses — and that silently stops heading
# demotion for the rest of the file. Hence a real (small) state machine.
_FENCE_OPEN = re.compile(r"^(?:[-*+]|\d+\.)?\s*(`{3,}|~{3,})")
_FENCE_CLOSE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")


def fence_state(text: str):
    """[(line_index, line, in_fence_before)] plus whether a fence is left open."""
    rows, infence, ch = [], False, None
    for i, ln in enumerate(text.split("\n")):
        rows.append((i, ln, infence))
        if not infence:
            m = _FENCE_OPEN.match(ln)
            if m:
                infence, ch = True, m.group(1)[0]
        else:
            m = _FENCE_CLOSE.match(ln)
            if m and m.group(1)[0] == ch:
                infence, ch = False, None
    return rows, infence


def headings(text: str, fence_aware: bool = True, max_level: int = 6):
    """[(level, text)] for ATX headings. fence_aware skips fenced blocks."""
    rows, _ = fence_state(text)
    out = []
    for _i, ln, infence in rows:
        if fence_aware and infence:
            continue
        m = re.match(r"^(#{1,6}) +(.*?)\s*$", ln)
        if m and len(m.group(1)) <= max_level:
            out.append((len(m.group(1)), m.group(2)))
    return out


def anchor(text: str) -> str:
    """Reproduce the anchor style already used by this document's TOC:
    lowercase; keep [a-z0-9_]; keep CJK; drop everything else (incl. spaces)."""
    return "".join(c for c in text.lower()
                   if (c.isascii() and (c.isalnum() or c == "_"))
                   or "\u3400" <= c <= "\u9fff")


def demote(text: str) -> str:
    """Shift every ATX heading down one level, skipping fenced code blocks."""
    rows, _ = fence_state(text)
    out = []
    for _i, ln, infence in rows:
        if not infence:
            m = re.match(r"^(#{1,6})( +)(.*)$", ln)
            if m:
                ln = "#" + m.group(1) + m.group(2) + m.group(3)
        out.append(ln)
    return "\n".join(out)


def _require_balanced(text: str, label: str) -> None:
    """Guard: an unclosed fence would silently stop heading demotion."""
    _rows, unclosed = fence_state(text)
    if unclosed:
        sys.exit(f"ABORT: {label} leaves a code fence open — heading demotion "
                 f"would silently stop past that point")


def source_md(rel: str) -> str:
    """One source document -> markdown fragment, demoted by 1 level."""
    if rel.endswith(".html"):
        p = REFS / rel
        if not p.exists():
            sys.exit(f"ABORT: missing source {p}")
        h = p.read_text(encoding="utf-8")
        # drop the tab-shell banner; it makes no sense inside the guide
        h = re.sub(r'<div class="intro-bar">.*?</div>\s*', "", h, count=1, flags=re.S)
        r = subprocess.run(["pandoc", "-f", "html", "-t", "gfm", "--no-highlight"],
                           input=h.encode(), capture_output=True)
        if r.returncode != 0:
            sys.exit(f"ABORT: pandoc failed on {rel}: {r.stderr.decode()[:300]}")
        out = r.stdout.decode()
        _require_balanced(out, rel)
        return out

    p = (ROOT / rel[3:]) if rel.startswith("../") else (REFS / rel)
    if not p.exists():
        sys.exit(f"ABORT: missing source {p}")
    text = p.read_text(encoding="utf-8")
    _require_balanced(text, p.name)
    return demote(text)


def render_block(title: str, body: str) -> str:
    return f"{RULE}\n\n# {title}\n\n{body.strip()}\n"


def part_body(sources) -> str:
    """Concatenate a Part's sources; each keeps its own `##` title."""
    return "\n\n".join(source_md(s).strip() for s in sources)


# --------------------------------------------------------------------- main
def main() -> None:
    check = "--check" in sys.argv
    src = GUIDE.read_text(encoding="utf-8")

    if MARKER in src:
        print("ALREADY SYNCED — nothing to do")
        return

    for tok, label in ((HEAD_ANCHOR, "TOC"), (BODY_ANCHOR, "body start"),
                       (OLD_CLAIM, "parity claim")):
        if src.count(tok) != 1:
            sys.exit(f"ABORT: {label} anchor matched {src.count(tok)} times (want 1)")

    head_i = src.index(HEAD_ANCHOR)
    body_i = src.index(BODY_ANCHOR)
    if not head_i < body_i:
        sys.exit("ABORT: TOC anchor must precede the body")

    pre, _old_toc, old_body = src[:head_i], src[head_i:body_i], src[body_i:]

    # ---- 0. refresh the parity claim in the header ---------------------
    orig_pre = pre
    pre = pre.replace(OLD_CLAIM, NEW_CLAIM, 1)
    if pre.replace(NEW_CLAIM, OLD_CLAIM, 1) != orig_pre:
        sys.exit("ABORT: header claim edit is not reversible")
    print(f"  ✓ header parity claim refreshed "
          f"({G.TOTAL_PARTS} Parts / {len(G.SECTIONS)} sections)")

    # ---- 1. build the appended body ------------------------------------
    blocks = [(n, t, part_body(s)) for n, t, _i, s in G.PARTS]
    added = "".join(render_block(t, b) for _n, t, b in blocks)
    new_body = old_body.rstrip("\n") + "\n\n" + added

    if new_body.replace("\n\n" + added, "", 1) != old_body.rstrip("\n"):
        sys.exit("ABORT: body change is not purely additive")

    # ---- 2. group parts by section -------------------------------------
    marks = [(m.start(), int(m.group(1)))
             for m in re.finditer(r"^# Part (\d+) —", new_body, re.M)]
    if len(marks) != G.TOTAL_PARTS:
        sys.exit(f"ABORT: expected {G.TOTAL_PARTS} '# Part N —' headings, "
                 f"found {len(marks)}")
    spans = {}
    for i, (pos, num) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(new_body)
        spans[num] = new_body[pos:end]

    mapped = [n for _k, _l, nums in G.SECTIONS for n in nums]
    if sorted(mapped) != sorted(spans):
        sys.exit(f"ABORT: section table != document parts\n"
                 f"  table: {sorted(mapped)}\n  doc:   {sorted(spans)}")

    # ---- 3. assign slugs in DOCUMENT order -----------------------------
    # A renderer disambiguates duplicate headings in document order, so the
    # counters must be built that way even though the TOC is emitted grouped.
    seen: dict[str, int] = {}
    slugs_by_part: dict[int, list[tuple[int, str, str]]] = {}
    for num in sorted(spans):
        rows = []
        for lvl, text in headings(spans[num], fence_aware=True, max_level=3):
            base = anchor(text)
            n = seen.get(base, 0)
            seen[base] = n + 1
            rows.append((lvl, text, base if n == 0 else f"{base}-{n}"))
        slugs_by_part[num] = rows
    collisions = sum(1 for n in seen.values() if n > 1)

    # ---- 4. emit the TOC in SECTION order ------------------------------
    toc = [HEAD_ANCHOR, ""]
    for _key, label, nums in G.SECTIONS:
        toc.append(f"### ▍ {label}")
        for num in nums:
            for lvl, text, slug in slugs_by_part[num]:
                toc.append("  " * (lvl - 1) + f"- [{text}](#{slug})")
        toc.append("")
    new_toc = "\n".join(toc).rstrip("\n") + "\n\n---\n\n"

    new = pre + new_toc + new_body

    # ---- 5. verify every TOC link resolves, and none collide -----------
    links = re.findall(r"^\s*- \[[^\]]*\]\(#([^)]+)\)", new_toc, re.M)
    dupl = sorted({a for a in links if links.count(a) > 1})
    if dupl:
        sys.exit(f"ABORT: duplicate TOC anchors: {dupl[:8]}")
    known = {slug for rows in slugs_by_part.values() for _, _, slug in rows}
    broken = sorted({a for a in links if a not in known})
    if broken:
        sys.exit(f"ABORT: {len(broken)} TOC link(s) have no target: {broken[:8]}")
    print(f"  ✓ TOC: {len(links)} links, all unique and resolving "
          f"({collisions} duplicate headings disambiguated)")

    # ---- 6. verify no fence is left open, and census the headings ------
    rows, unclosed = fence_state(new)
    if unclosed:
        sys.exit("ABORT: a code fence is left open at end of document")
    blocks_n = sum(1 for _i, ln, inf in rows if not inf and _FENCE_OPEN.match(ln))
    census = {}
    for lvl, _ in headings(new_body, fence_aware=True):
        census[lvl] = census.get(lvl, 0) + 1
    print(f"  ✓ code fences all closed ({blocks_n} blocks)")
    print(f"  ✓ body headings H1..H5: {dict(sorted(census.items()))}")

    if check:
        print("  check ok (dry run — nothing written)")
        return

    GUIDE.write_text(new, encoding="utf-8")
    print(f"  ✓ {GUIDE.name}: {len(src.encode()):,} -> {len(new.encode()):,} bytes "
          f"(+{len(new.encode()) - len(src.encode()):,})")


if __name__ == "__main__":
    main()
