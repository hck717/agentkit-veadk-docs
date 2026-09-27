#!/usr/bin/env python3
"""Group the guide's floating #partnav strip into the same 8 sections.

Before: #partnav is a flat row of 34 chips (one per `main>h1`), in document order.
After : the same chips, but preceded by a small uppercase section-label chip,
        driven by the SAME section table as the #partgrid card grid.

To guarantee the nav and the grid can never drift apart, this script also
hoists the section table into a single declaration (`NAV_SEC`) placed before
both consumers, and rewrites the grid's own `GRID_SEC` to alias it.

Purely additive. Blocks are sliced out of the file by anchor rather than
matched with hand-written regex, so no escaping assumptions are made.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REFS = Path(__file__).resolve().parent.parent
GUIDE = REFS / "veadk-agentkit-comprehensive-guide.html"

# idempotency marker: only present after this script has run
MARKER = "pn-sec"

# ---------------------------------------------------------------- section table
# Single source of truth, imported from guide_parts.py. Order defines nav order
# AND grid order.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guide_parts as G  # noqa: E402

NAV_SEC = [(k, l, [G.part_id(n) for n in ns]) for k, l, ns in G.SECTIONS]


def js_literal() -> str:
    """Render the section table as a JS array literal (same shape as the old GRID_SEC)."""
    return G.sections_js()


# ------------------------------------------------------------------- patch #1
# Declare NAV_SEC once, right after `parts` is computed, so it is initialised
# before BOTH the partnav builder and the partgrid builder run.
DECL_ANCHOR = "const parts=$$('main>h1');"
DECL_NEW = (DECL_ANCHOR
            + "\n  /* section table — single source of truth for nav + grid */\n"
            + "  const NAV_SEC=" + js_literal() + ";")

# ------------------------------------------------------------------- patch #2
# Grid aliases the shared table instead of carrying its own copy.
GRID_START = "const GRID_SEC=["
GRID_END = "];"
GRID_NEW = "const GRID_SEC=NAV_SEC;"

# ------------------------------------------------------------------- patch #3
# Build the nav in section order, with a label chip before each group.
NAV_START = "  parts.forEach((h,i)=>{"
NAV_END = "  });"
NAV_NEW = """  NAV_SEC.forEach(([sk,sl,ids])=>{
    $('#partnav').insertAdjacentHTML('beforeend',`<span class="pn-sec" data-sec="${sk}">${sl}</span>`);
    ids.forEach(id=>{
      const h=document.getElementById(id); if(!h)return;
      const i=parts.indexOf(h); if(i<0)return;
      const kw=(h.textContent||'').split('\u2014')[1]||'';
      const lbl=(kw.split(/[\uff08(]/)[0]||'').trim().slice(0,14)||('Part '+i);
      $('#partnav').insertAdjacentHTML('beforeend',`<a href="#${id}" data-part="${i}">P${i} \u00b7 ${lbl}</a>`);
    });
  });"""

# ------------------------------------------------------------------- patch #4
# Style the label chips.
CSS_ANCHOR = "#partnav a.active{background:var(--accent);color:#03121f;border-color:var(--accent)}"
CSS_NEW = CSS_ANCHOR + (
    "\n#partnav .pn-sec{flex:0 0 auto;align-self:center;font-size:.66rem;font-weight:800;"
    "letter-spacing:.09em;text-transform:uppercase;color:#6fd0ff;padding:0 8px 0 12px;"
    "border-left:1px solid #26496b;margin-left:2px;white-space:nowrap}\n"
    "#partnav .pn-sec:first-child{border-left:0;padding-left:0;margin-left:0}"
)


def slice_between(h: str, start_tok: str, end_tok: str, label: str) -> tuple[int, int, str]:
    """Return (start, end, text) of the first region from start_tok through end_tok."""
    i = h.find(start_tok)
    if i < 0:
        sys.exit(f"ABORT: start token for {label} not found: {start_tok!r}")
    j = h.find(end_tok, i + len(start_tok))
    if j < 0:
        sys.exit(f"ABORT: end token for {label} not found after start")
    j += len(end_tok)
    return i, j, h[i:j]


NODE_CANDIDATES = [
    Path("/Users/brianho/.workbuddy-ai/binaries/node/versions/22.22.2-2/bin/node"),
    Path("/opt/homebrew/bin/node"),
]


def node_bin() -> str:
    for c in NODE_CANDIDATES:
        if c.exists():
            return str(c)
    return "node"


def check_js(h: str) -> None:
    """Run `node --check` over every inline <script> body.

    A syntax error in ANY one of them silently kills ALL guide interactivity
    (search, focus mode, collapse, progress bar), so this is a hard gate.
    """
    import subprocess
    import tempfile

    blocks = re.findall(r"<script([^>]*)>(.*?)</script>", h, re.S)
    checked = 0
    bad = 0
    for n, (attrs, body) in enumerate(blocks):
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
        r = subprocess.run([node_bin(), "--check", tmp],
                           capture_output=True, text=True)
        Path(tmp).unlink(missing_ok=True)
        checked += 1
        if r.returncode != 0:
            bad += 1
            print(f"  ✗ inline script #{n} SYNTAX ERROR:\n{r.stderr.strip()[:600]}")
    if bad:
        sys.exit(f"ABORT: {bad} inline script(s) failed node --check")
    print(f"  ✓ node --check passed on {checked} inline script block(s)")


def main() -> None:
    if not GUIDE.exists():
        sys.exit(f"ABORT: {GUIDE} not found")
    orig = GUIDE.read_text(encoding="utf-8")

    if MARKER in orig:
        print("ALREADY GROUPED — nothing to do")
        return

    print(f"guide: {GUIDE.name}  {len(orig.encode()):,} bytes")
    h = orig
    patches: list[tuple[str, str]] = []

    def replace_span(start_tok: str, end_tok: str, new: str, label: str) -> None:
        nonlocal h
        i, j, old = slice_between(h, start_tok, end_tok, label)
        h = h[:i] + new + h[j:]
        patches.append((old, new))
        print(f"  ✓ patched {label}")

    # 1. NAV_SEC declaration (plain anchor, must be unique)
    n = h.count(DECL_ANCHOR)
    if n != 1:
        sys.exit(f"ABORT: DECL anchor matched {n} times (want 1)")
    h = h.replace(DECL_ANCHOR, DECL_NEW, 1)
    patches.append((DECL_ANCHOR, DECL_NEW))
    print("  ✓ patched NAV_SEC declaration")

    # 2. GRID_SEC -> alias
    replace_span(GRID_START, GRID_END, GRID_NEW, "GRID_SEC -> NAV_SEC alias")

    # 3. grouped nav builder
    replace_span(NAV_START, NAV_END, NAV_NEW, "grouped #partnav builder")

    # 4. styles (plain anchor, must be unique)
    n = h.count(CSS_ANCHOR)
    if n != 1:
        sys.exit(f"ABORT: CSS anchor matched {n} times (want 1)")
    h = h.replace(CSS_ANCHOR, CSS_NEW, 1)
    patches.append((CSS_ANCHOR, CSS_NEW))
    print("  ✓ patched .pn-sec styles")

    # --- additivity proof: reverse every patch, must reproduce the original ---
    rev = h
    for old, rep in patches:
        if rep not in rev:
            sys.exit("ABORT: additivity check — replacement text vanished")
        rev = rev.replace(rep, old, 1)
    if rev != orig:
        sys.exit("ABORT: additivity check FAILED — file is not purely additive")
    print("  ✓ additivity verified (reverse-patch reproduces original byte-for-byte)")

    # --- every section id must resolve to a real part heading ---
    have = set(re.findall(r'<h1[^>]*id="([^"]+)"', h))
    missing = [i for _, _, ids in NAV_SEC for i in ids if i not in have]
    if missing:
        sys.exit(f"ABORT: section table references unknown part ids: {missing}")
    total = sum(len(ids) for _, _, ids in NAV_SEC)
    if total != len(have):
        sys.exit(f"ABORT: table covers {total} parts but document has {len(have)}")
    if len(have) != len(set(have)):
        sys.exit("ABORT: duplicate part ids after patch")
    print(f"  ✓ section table maps all {total} parts, 0 unknown")

    # --- syntax gate: a broken inline script kills the whole page's JS ---
    check_js(h)

    GUIDE.write_text(h, encoding="utf-8")
    print(f"  ✓ wrote {GUIDE.name}  {len(h.encode()):,} bytes")


if __name__ == "__main__":
    main()
