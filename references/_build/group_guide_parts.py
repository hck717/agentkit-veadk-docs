#!/usr/bin/env python3
"""Group the guide's Part cards into the same sections used by all.html.

The guide's `#partgrid` renders one card per `main > h1` — a flat wall of cards
once the tab content is spliced in. This patches the grid loop so a section
heading row is emitted per section, and adds the `.psec` style.

The section table comes from guide_parts.py, the single source of truth shared
with the .md twin and with splice_tabs_into_guide.py, so the three can never
disagree.

Idempotent: aborts if the marker is already present.

Usage:
  python3 references/_build/group_guide_parts.py --check   # dry run
  python3 references/_build/group_guide_parts.py           # write
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guide_parts as G  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "references"
GUIDE = REFS / "veadk-agentkit-comprehensive-guide.html"

MARKER = 'class="psec"'

# (key, label, [part ids]) — from the shared config
GRID_SEC = [(k, l, [G.part_id(n) for n in ns]) for k, l, ns in G.SECTIONS]

PGRID_CSS = (
    ".psec{grid-column:1/-1;margin:14px 0 -2px;padding:7px 12px;"
    "border-left:3px solid var(--accent);background:#0e2740;border-radius:8px;"
    "color:var(--accent);font-weight:800;font-size:.8rem;letter-spacing:.1em;"
    "text-transform:uppercase}"
    ".psec:first-child{margin-top:0}"
)

# the original grid loop, matched by shape so incidental whitespace does not matter
PG_RE = re.compile(r"\$\$\('#partgrid'\)\.forEach\(pg=>\{.*?\n  \}\);", re.S)


def new_loop() -> str:
    """Emit one heading per section, then that section's cards.

    Iterating `parts` in document order and inserting a heading on section
    change does NOT work here: the guide's Part 0–9 interleave with the spliced
    Part 10+, so sections would repeat (14 headings instead of 8). Driving the
    grid from the section table instead keeps each section contiguous and emits
    exactly one heading each; the card still shows its real document Part number.
    """
    return (
        "const GRID_SEC=" + G.sections_js() + ";\n"
        "  $$('#partgrid').forEach(pg=>{\n"
        "    GRID_SEC.forEach(([sk,label,ids])=>{\n"
        "      pg.insertAdjacentHTML('beforeend',"
        "`<div class=\"psec\" data-sec=\"${sk}\">${label}</div>`);\n"
        "      ids.forEach(id=>{\n"
        "        const h=parts.find(x=>x.id===id); if(!h)return;\n"
        "        const i=parts.indexOf(h);\n"
        "        let d=''; const sb=partSiblings(h);\n"
        "        const fp=sb.find(el=>el.tagName==='P'); if(fp)d=fp.innerText.slice(0,72)+'…';\n"
        "        pg.insertAdjacentHTML('beforeend',\n"
        "          `<a class=\"pcard\" href=\"#${h.id}\" data-part=\"${i}\" data-sec=\"${sk}\">"
        "<span class=\"pn\">PART ${i}</span>"
        "<b>${partTitle(h).replace('Part '+i+' — ','')}</b>"
        "<span class=\"pd\">${d}</span></a>`);\n"
        "      });\n"
        "    });\n"
        "  });")


def main() -> None:
    check = "--check" in sys.argv
    h = GUIDE.read_text(encoding="utf-8")

    if MARKER in h:
        sys.exit("guide part grid already grouped — aborting (idempotent guard).")

    # every part in the guide must have a section, or it would silently land in
    # the fallback bucket and the grouping would be wrong
    mm = re.search(r"<main[^>]*>", h, re.I)
    if not mm:
        sys.exit("no <main> found — aborting.")
    me = h.find("</main>", mm.end())
    if me < 0:
        sys.exit("no </main> found — aborting.")
    part_ids = re.findall(r'<h1[^>]*id="(part[^"]*)"', h[mm.end():me])
    if len(part_ids) != G.TOTAL_PARTS:
        sys.exit(f"expected {G.TOTAL_PARTS} parts in <main>, found {len(part_ids)}")
    assigned = [p for _, _, ps in GRID_SEC for p in ps]
    missing = [p for p in part_ids if p not in assigned]
    unknown = [p for p in assigned if p not in part_ids]
    if missing or unknown:
        sys.exit(f"section map mismatch — unassigned: {missing}  unknown: {unknown}")

    m = PG_RE.search(h)
    if not m:
        sys.exit("partgrid loop not found — aborting.")

    out = h[:m.start()] + new_loop() + h[m.end():]

    sm = re.search(r"<style[^>]*>", out)
    se = out.find("</style>", sm.end())
    if se < 0:
        sys.exit("no </style> found — aborting.")
    out = out[:se] + PGRID_CSS + out[se:]

    # additive assertion: reverting both edits must reproduce the original
    if out.replace(new_loop(), m.group(0), 1).replace(PGRID_CSS, "", 1) != h:
        sys.exit("NOT additive — aborting.")

    print(f"  guide {len(h):,} -> {len(out):,} chars (+{len(out)-len(h):,})")
    print(f"  parts mapped : {len(part_ids)}  sections: {len(GRID_SEC)}")
    for k, l, ps in GRID_SEC:
        print(f"    {k:<8} {l:<32} {len(ps)} parts")

    if check:
        print("  check ok (dry run — nothing written)")
        return

    GUIDE.write_text(out, encoding="utf-8")
    print(f"  ✓ {GUIDE.name} updated")


if __name__ == "__main__":
    main()
