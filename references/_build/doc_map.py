#!/usr/bin/env python3
"""Print the navigation map shared by the two superset documents.

Two files describe the same corpus from two angles:

  * references/veadk-agentkit-all.html                 — tabbed view  (build.py)
  * references/veadk-agentkit-comprehensive-guide.html — linear view  (guide_parts.py)

all.html is assembled from three config tables in build.py:

  TABS          topic tabs, each sourced from one or more standalone .md docs
  GUIDE_TABS    tabs whose content is a whole Part of the linear guide
  GUIDE_MERGES  extra subdocs injected into existing tabs from guide Parts

plus a SECTIONS table grouping every tab into one row of section buttons, and a
matching section table for the linear guide's Parts. Both counts are printed
under "## Coverage" rather than restated here, so they cannot go stale.

This script reads every one of those tables, joins them on source filename and
on Part id, and prints the resulting map — so "which tab holds this topic?" and
"which Part of the guide is this?" are answerable without guessing.

Usage:
    python3 references/_build/doc_map.py          # human-readable
    python3 references/_build/doc_map.py --md     # markdown (paste into docs)
    python3 references/_build/doc_map.py --check  # exit 1 if coverage is broken
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent

# ─── load the two configs without running their main() ──────────────────────


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, BUILD / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # both modules are main()-guarded
    return mod


build = _load("build")
G = _load("guide_parts")


def _norm(rel: str) -> str:
    """'../README.md' -> 'readme.md' ; 'intros/arch.html' -> 'arch.html'."""
    return Path(rel).name.lower()


# ─── guide side ─────────────────────────────────────────────────────────────

PART_TITLE = {p[0]: p[1] for p in G.PARTS}
PART_SOURCES: dict[int, list[str]] = {p[0]: [_norm(s) for s in p[3]] for p in G.PARTS}
PID_TO_NUM = {G.part_id(n): n for n in range(G.TOTAL_PARTS)}
PART_ID = {n: G.part_id(n) for n in range(G.TOTAL_PARTS)}
PART_SECTION: dict[int, str] = {}
for _sk, sl, nums in G.SECTIONS:
    for n in nums:
        PART_SECTION[n] = sl

# The governance block is spliced into the end of Part 2 (its own h2, §2.21),
# not promoted to a Part of its own. splice_governance.py inserts it before
# `<h1 id="part3-veadk">`, i.e. inside Part 2.
GOV_ANCHOR = "@a21"
GOV_PART = 2
GOV_LABEL = "P2 §2.21"

# ─── tab side ───────────────────────────────────────────────────────────────

TAB_LABEL = {k: l for k, l, _d, _s in build.TABS}
TAB_LABEL.update({k: l for k, l, _d, _p, _t in build.GUIDE_TABS})

TAB_SOURCES: dict[str, list[str]] = {}
# subdoc keys drive the `all.html#<tab>:<subdoc>` deep link — a tab with more
# than one subdoc cannot be addressed precisely by `#<tab>` alone.
TAB_SUBDOCS: dict[str, list[str]] = {}
for key, _label, _desc, subdocs in build.TABS:
    if subdocs:
        TAB_SOURCES[key] = [_norm(md) for _k, md, _t in subdocs]
        TAB_SUBDOCS[key] = [k for k, _md, _t in subdocs]
    else:  # intro-only tab — content lives in references/intros/<key>.html
        TAB_SOURCES[key] = [f"{key}.html"]
        TAB_SUBDOCS[key] = [key]
for key, _label, _desc, _pid, _title in build.GUIDE_TABS:
    TAB_SOURCES.setdefault(key, [])
    TAB_SUBDOCS.setdefault(key, [key])
# subdocs folded in from the linear guide (tab key -> [(subkey, part_id, title)])
for _tab, merges in build.GUIDE_MERGES.items():
    for subkey, _pid, _title in merges:
        TAB_SUBDOCS.setdefault(_tab, []).append(subkey)

# tab -> part numbers, from three independent sources of truth
TAB_PARTS: dict[str, list[int]] = {k: [] for k in TAB_LABEL}


def _add(tab: str, part) -> None:
    if tab not in TAB_PARTS:
        return
    if part not in TAB_PARTS[tab]:
        TAB_PARTS[tab].append(part)


# (a) whole-Part tabs
for key, _label, _desc, pid, _title in build.GUIDE_TABS:
    if pid == GOV_ANCHOR:
        _add(key, GOV_PART)
    elif pid in PID_TO_NUM:
        _add(key, PID_TO_NUM[pid])

# (b) tabs that absorb guide Parts as extra subdocs
for tab, merges in build.GUIDE_MERGES.items():
    for _subkey, pid, _title in merges:
        if pid in PID_TO_NUM:
            _add(tab, PID_TO_NUM[pid])

# (c) join on source filename
SRC_TO_PARTS: dict[str, list[int]] = {}
for num, srcs in PART_SOURCES.items():
    for s in srcs:
        SRC_TO_PARTS.setdefault(s, []).append(num)
for tab, srcs in TAB_SOURCES.items():
    for s in srcs:
        for num in SRC_TO_PARTS.get(s, []):
            _add(tab, num)

for tab in TAB_PARTS:
    TAB_PARTS[tab].sort()

# reverse: Part -> tabs
PART_TABS: dict[int, list[str]] = {n: [] for n in range(G.TOTAL_PARTS)}
for tab, parts in TAB_PARTS.items():
    for n in parts:
        PART_TABS[n].append(tab)


# ─── rendering ──────────────────────────────────────────────────────────────


def md_preamble() -> list[str]:
    """The .md file's front matter — generated, so `--md > doc_map.md` is a
    complete regeneration and the counts can never drift from the tables."""
    n_tabs = len(TAB_LABEL)
    return [
        "<!-- GENERATED FILE — do not edit by hand.",
        "     Regenerate with:  python3 references/_build/doc_map.py --md "
        "> references/_build/doc_map.md",
        "     Verify with:      python3 references/_build/doc_map.py --check",
        "     Sources of truth: _build/build.py (TABS / GUIDE_TABS / GUIDE_MERGES / SECTIONS)",
        "                       _build/guide_parts.py (PARTS / SECTIONS)",
        "-->",
        "",
        "# Doc map — BytePlus × Volcengine Agent 文檔導覽地圖",
        "",
        "Two superset documents cover the same corpus from two angles:",
        "",
        "| File | Shape | Structure | Generator |",
        "|---|---|---|---|",
        f"| `references/veadk-agentkit-all.html` | Tab view (interactive) | "
        f"**{n_tabs} tabs / {len(build.SECTIONS)} sections** | `_build/build.py` |",
        f"| `references/veadk-agentkit-comprehensive-guide.html` | Part view (linear) | "
        f"**{G.TOTAL_PARTS} Parts / {len(G.SECTIONS)} sections** | `_build/guide_parts.py` |",
        f"| `references/veadk-agentkit-comprehensive-guide.md` | Markdown twin of the Part view | "
        f"same {G.TOTAL_PARTS} Parts | `_build/append_part.py` |",
        "",
        "Deep links: `…all.html#<tab>` or `…all.html#<tab>:<subdoc>` "
        "(the page JS reads `location.hash`);",
        "`…guide.html#<part-id>`.",
        "",
    ]


def render_tabs(md: bool) -> list[str]:
    out = ["## Tab map — `veadk-agentkit-all.html`", ""]
    if md:
        out.append("| Section | Tab | Label | Source doc(s) | Guide Part(s) | Deep link |")
        out.append("|---|---|---|---|---|---|")
    for _sk, sl, keys in build.SECTIONS:
        for k in keys:
            srcs = TAB_SOURCES.get(k) or []
            parts = TAB_PARTS.get(k) or []
            subs = TAB_SUBDOCS.get(k) or []
            plist = ", ".join(f"P{p}" for p in parts) if parts else "—"
            slist = ", ".join(f"`{s}`" for s in srcs) if srcs else "*(guide)*"
            # a tab needs the `#tab:subdoc` form only when it has >1 subdoc.
            # the separator is escaped because a literal `|` would break the
            # markdown table cell it lives in.
            link = f"#{k}" if len(subs) <= 1 else f"#{k}:" + "\\|".join(subs)
            if md:
                out.append(f"| {sl} | `{k}` | {TAB_LABEL.get(k,'')} | {slist} | {plist} | `{link}` |")
            else:
                out.append(f"{sl:28} #{k:10} {TAB_LABEL.get(k,''):34} {plist}")
    out.append("")
    return out


def render_parts(md: bool) -> list[str]:
    out = ["## Part map — `veadk-agentkit-comprehensive-guide.html` / `.md`", ""]
    if md:
        out.append("| Section | Part | Title | Part id | Source doc(s) | Tab(s) |")
        out.append("|---|---|---|---|---|---|")
    for _sk, sl, nums in G.SECTIONS:
        for n in nums:
            title = PART_TITLE.get(n, f"Part {n}")
            srcs = PART_SOURCES.get(n)
            slist = ", ".join(f"`{s}`" for s in srcs) if srcs else "*(handcrafted)*"
            ts = PART_TABS.get(n) or []
            tlist = ", ".join(f"`#{t}`" for t in ts) if ts else "—"
            if md:
                out.append(f"| {sl} | P{n} | {title} | `{PART_ID[n]}` | {slist} | {tlist} |")
            else:
                out.append(f"{sl:28} P{n:<3} {PART_ID[n]:24} {tlist}")
    out.append("")
    return out


def render_coverage() -> tuple[list[str], bool]:
    out = ["## Coverage", ""]
    tab_srcs = {s for srcs in TAB_SOURCES.values() for s in srcs}
    only_tab = sorted(s for s in tab_srcs if s not in SRC_TO_PARTS)
    only_part = sorted(s for s in SRC_TO_PARTS if s not in tab_srcs)
    tabs_no_part = sorted(t for t, p in TAB_PARTS.items() if not p)
    parts_no_tab = sorted(n for n, t in PART_TABS.items() if not t)

    out.append(f"- tabs                        : {len(TAB_LABEL)} in {len(build.SECTIONS)} sections")
    out.append(f"- guide Parts                 : {G.TOTAL_PARTS} in {len(G.SECTIONS)} sections")
    out.append(f"- source docs on the tab side : {len(tab_srcs)}")
    out.append(f"- source docs on the Part side: {len(SRC_TO_PARTS)}")
    out.append(f"- source only in all.html     : {len(only_tab)} {only_tab}")
    out.append(f"- source only in the guide    : {len(only_part)} {only_part}")
    out.append(f"- tabs with no guide Part     : {len(tabs_no_part)} {tabs_no_part}")
    out.append(f"- Parts with no tab           : {len(parts_no_tab)} {parts_no_tab}")
    out.append("")
    ok = not tabs_no_part and not parts_no_tab
    return out, ok


def main() -> None:
    md = "--md" in sys.argv
    check = "--check" in sys.argv

    out: list[str] = []
    if md:
        out += md_preamble()
    out += render_tabs(md)
    out += render_parts(md)
    cov, ok = render_coverage()
    out += cov
    print("\n".join(out))

    if check and not ok:
        raise SystemExit("ABORT: tab/Part coverage mismatch (see above)")


if __name__ == "__main__":
    main()
