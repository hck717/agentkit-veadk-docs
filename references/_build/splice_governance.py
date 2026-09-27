#!/usr/bin/env python3
"""Insert §2.21 Agent 治理與安全 into veadk-agentkit-comprehensive-guide.html.

Purely additive: the new block is inserted immediately before the
`<h1 id="part3-veadk">` heading (i.e. at the end of Part 2 — the AgentKit
section). No existing byte of the guide is modified.

- source markdown : _build/section-2-21-governance.md
- images          : referenced relatively from references/assets/ by default
                    (lean, images stay versioned in the repo).
                    Pass --inline to instead embed them as base64 data URIs so
                    the guide becomes one portable self-contained file.

Usage:  python3 references/_build/splice_governance.py [--check] [--inline]
"""
import base64
import html as htmlmod
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "references"
BUILD = Path(__file__).resolve().parent

GUIDE = REFS / "veadk-agentkit-comprehensive-guide.html"
SECTION_MD = BUILD / "section-2-21-governance.md"

ANCHOR = '<h1 id="part3-veadk">'
MARKER = 'id="a21-gov"'

# image assets (kept next to the docs so the repo is self-describing)
ASSETS = REFS / "assets"
IMG_DEPLOY = ASSETS / "agent-platform-deployment-modes.jpg"
IMG_MA = ASSETS / "agentkit-ma-three-tickets-four-gates.jpg"

FIG_STYLE = ("margin:22px 0;padding:12px;border:1px solid #1d3a5c;"
             "border-radius:14px;background:#0b1a2e")
IMG_STYLE = "display:block;width:100%;height:auto;border-radius:10px"
CAP_STYLE = "margin-top:8px;color:#a8b7cc;font-size:.85rem;line-height:1.5"


def figure(path: Path, caption: str, inline: bool) -> str:
    if inline:
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        src = f"data:image/jpeg;base64,{b64}"
    else:
        src = f"assets/{path.name}"          # relative to references/
    return (
        f'<figure style="{FIG_STYLE}">'
        f'<img alt="{htmlmod.escape(caption)}" src="{src}" style="{IMG_STYLE}">'
        f'<figcaption style="{CAP_STYLE}">{caption}</figcaption>'
        f"</figure>"
    )


def to_fragment(inline: bool) -> str:
    r = subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "html5", "--syntax-highlighting=none"],
        input=SECTION_MD.read_text(encoding="utf-8").encode(),
        capture_output=True)
    if r.returncode != 0:
        sys.exit(f"pandoc failed: {r.stderr.decode()[:400]}")
    out = r.stdout.decode()

    # mermaid: <pre class="mermaid"><code>…</code></pre> → <div class="mermaid">…</div>
    out = re.sub(r'<pre class="mermaid"><code>(.*?)</code></pre>',
                 lambda m: '<div class="mermaid">\n'
                           + htmlmod.unescape(m.group(1)).strip() + "\n</div>",
                 out, flags=re.S)

    # inline images
    out = out.replace("<p>{{IMG_DEPLOY}}</p>", figure(
        IMG_DEPLOY, "圖 A — Enterprise Agent Platform 部署模式（表 1：5 種）· "
                    "Execution Placement（表 2：4 種）· Control Surface（表 3：5 種）+ 組合示例",
        inline))
    out = out.replace("<p>{{IMG_MA}}</p>", figure(
        IMG_MA, "圖 B — AgentKit MA「三個人 / 三個範圍 / 三張票 / 四道門」總覽 "
                "＋「三張票 × 四道門」詳解", inline))
    if "{{IMG_" in out:
        sys.exit("unreplaced image placeholder left in fragment")
    return out


def main() -> None:
    inline = "--inline" in sys.argv
    if not SECTION_MD.exists():
        sys.exit(f"missing {SECTION_MD}")
    for p in (IMG_DEPLOY, IMG_MA):
        if not p.exists():
            sys.exit(f"missing asset {p}")

    src = GUIDE.read_text(encoding="utf-8")
    if MARKER in src:
        sys.exit("guide already contains §2.21 governance — aborting.")
    if ANCHOR not in src:
        sys.exit("Part 3 anchor not found — aborting.")

    fragment = to_fragment(inline)
    out = src.replace(ANCHOR, fragment + "\n\n" + ANCHOR, 1)

    if "--check" in sys.argv:
        # additive-only assertion: removing the fragment must reproduce the original
        if out.replace(fragment + "\n\n", "", 1) != src:
            sys.exit("NOT additive — aborting.")
        print(f"  check ok · fragment {len(fragment):,} chars "
              f"({len(fragment)/1024:.0f} KB) · guide {len(src):,} → {len(out):,} chars")
        return

    GUIDE.write_text(out, encoding="utf-8")
    print(f"  ✓ {GUIDE.name}: inserted §2.21 before Part 3 "
          f"({len(src):,} → {len(out):,} chars, +{len(out)-len(src):,})")


if __name__ == "__main__":
    main()
