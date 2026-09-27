#!/usr/bin/env python3
"""Validation gates for the combined HTML.

Checks:
  1. Unique ids (no duplicates) — scanned on code-stripped text, so markup
     quoted inside <pre>/<code> samples is not counted as a real id
  2. No missing href targets (href="#...", excluding #section-# / #it-# / auto ids)
  3. No `class="math inline"` spans (pandoc math leakage)
  4. Tab order matches TABS + GUIDE_TABS config in build.py
  5. syntax-check extracted JS with node --check

Usage: python3 references/_build/validate.py
"""
import re, subprocess, sys, tempfile, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "references"
OUT = REFS / "veadk-agentkit-all.html"

def real_tags(h):
    """Return only genuine (unescaped) tags.

    Code samples quote markup as escaped text — `<code>&lt;h2 id="a21-gov"&gt;</code>`
    — and pandoc puts real ids *on* <pre> and line <span>s inside code blocks, so
    we cannot simply drop code blocks. Instead we only look inside real tags:
    escaped samples start with `&lt;`, never a literal `<`, so they are excluded,
    while `<pre id="it-cli-cb1">` and `<span id="it-cli-cb1-1">` are kept.
    """
    return re.findall(r"<[a-zA-Z][^>]*>", h)


def load():
    h = OUT.read_text(encoding="utf-8")
    tags = real_tags(h)
    scan = "\n".join(tags)
    # ids — only genuine attributes inside real tags (see real_tags docstring)
    ids = re.findall(r'(?<![-\w])id="([^"]+)"', scan)
    dup = sorted({x for x in ids if ids.count(x) > 1})
    # hrefs
    hrefs = re.findall(r'href="#([^"]+)"', scan)
    id_set = set(ids)
    missing = sorted({x for x in hrefs if x not in id_set})
    # math inline (real DOM leakage, not a code sample quoting the class name)
    math = re.findall(r'class="math inline"', scan)
    return ids, dup, hrefs, missing, math


def check_js():
    # extract JS blocks
    h = OUT.read_text(encoding="utf-8")
    js_blocks = re.findall(r'<script>(.*?)</script>', h, re.S)
    if not js_blocks:
        return "no <script> found"
    js = js_blocks[0]
    fd, path = tempfile.mkstemp(suffix=".js")
    with os.fdopen(fd, "w") as f:
        f.write(js)
    try:
        r = subprocess.run(["node", "--check", path], capture_output=True, cwd=str(ROOT))
        if r.returncode != 0:
            return r.stderr.decode()[:800]
        return "OK"
    finally:
        os.unlink(path)


def tab_sizes(h_text):
    """{tab_key: content chars} — catches a silently empty tab.

    A tab renders as an empty shell when its source went missing (e.g. the guide
    file was rewritten by the preview panel and the <main> regex stopped
    matching). The build still "succeeds", so this check is the safety net.
    """
    out = {}
    for m in re.finditer(r'<section class="tpage" data-tab="(\w+)"', h_text):
        start = m.end()
        nxt = h_text.find('<section class="tpage"', start)
        end = nxt if nxt > 0 else h_text.find("</main>", start)
        if end < 0:
            end = len(h_text)
        out[m.group(1)] = end - start
    return out


def main():
    h_text = OUT.read_text(encoding="utf-8")
    ids, dup, hrefs, missing, math = load()

    # Tab order from the html topbar
    topbar_tabs = re.findall(r'<button class="tab-btn" data-tab="(\w+)"', h_text)
    # Expected order from build.py TABS (+ guide tabs merged in from the guide)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build import TABS, GUIDE_TABS, SECTIONS
    expected = [t[0] for t in TABS] + [t[0] for t in GUIDE_TABS]

    # every tab must live in exactly one section, and no section may name a
    # tab that does not exist
    seen, dup_sec = [], []
    for _, _, tabs in SECTIONS:
        for t in tabs:
            (dup_sec if t in seen else seen).append(t)
    sec_missing = [t for t in expected if t not in seen]
    sec_extra = [t for t in seen if t not in expected]
    bar_sections = re.findall(r'<button class="section-btn[^"]*" data-section="(\w+)"',
                              h_text)
    expected_secs = [s[0] for s in SECTIONS]

    print(f"file: {OUT.name}")
    print(f"ids: {len(ids)}  duplicate: {len(dup)}  missing_hrefs: {len(missing)}  "
          f"math_inline: {len(math)}")
    print(f"sections: {len(bar_sections)}  tabs: {len(topbar_tabs)}  "
          f"tabs-in-sections: {len(seen)}")
    if dup:
        print("  DUPLICATE IDS:", dup[:20])
    if missing:
        print("  MISSING HREFS:", missing[:20])
    if math:
        print("  MATH INLINE:", math[:5])
    if topbar_tabs != expected:
        print("  TAB ORDER:", topbar_tabs)
        print(f"  EXPECTED:  {expected}")
    if bar_sections != expected_secs:
        print("  SECTION BAR:", bar_sections)
        print(f"  EXPECTED:    {expected_secs}")
    if dup_sec:
        print("  TAB IN >1 SECTION:", dup_sec[:20])
    if sec_missing:
        print("  TAB IN NO SECTION:", sec_missing[:20])
    if sec_extra:
        print("  SECTION NAMES UNKNOWN TAB:", sec_extra[:20])
    js = check_js()
    print(f"JS check: {js}")

    sizes = tab_sizes(h_text)
    thin = sorted(k for k, v in sizes.items() if v < 500)
    if thin:
        print(f"  NEARLY-EMPTY TABS ({len(thin)}):", thin[:20])

    ok = (not dup and not missing and not math and topbar_tabs == expected
          and bar_sections == expected_secs and not dup_sec
          and not sec_missing and not sec_extra and not thin and js == "OK")
    print("\n" + ("PASS ✅" if ok else "FAIL ❌"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()