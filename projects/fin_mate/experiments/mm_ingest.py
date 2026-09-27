"""D7 multimodal corpus builder: derives table/chart/scan/HTML artifacts under data/kb_vis/.

Run once before D7 mm runs:
    python -m experiments.mm_ingest

Artifacts (facts NOT present in the 8 analyst .txt docs — needle targets):
  msft_azure_revenue.csv   — Azure cc-growth outlook table (FY26Q4E = 35%)
  msft_ai_capex.txt        — chart caption + data (FY27 spend 112B; 2025 inf/cost 1.2$/1M tok)
  msft_ai_capex.png        — the chart image itself (auth artifact, not ingested as text)
  msft_scan.pdf            — scanned-style internal memo (FY26 E7 pilot 250K seats) w/ text layer
  msft_kb_overview.html    — HTML overview (EMEA 27% of FY25 revenue)
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "kb_vis"

AZT = "msft_azure_revenue.csv"
CAPTX = "msft_ai_capex.txt"
CAPPNG = "msft_ai_capex.png"
SCAN = "msft_scan.pdf"
OVW = "msft_kb_overview.html"

AZURE_ROWS = [
    ("FY25Q3", "42.6", "33"),
    ("FY25Q4", "44.2", "32"),
    ("FY26Q1", "46.8", "36"),
    ("FY26Q2", "49.1", "38"),
    ("FY26Q3E", "51.2", "37"),
    ("FY26Q4E", "52.9", "35"),
]
CAPEX = {"FY25": 62.0, "FY26": 82.0, "FY27": 112.0, "FY28": 150.0}
_INF = [("2024", 3.5), ("2025", 1.2), ("2026E", 0.4)]


def write_csv(p: Path) -> None:
    lines = ["Quarter,AzureRevenueB,AzureGrowthCC_pct"]
    lines += [",".join(r) for r in AZURE_ROWS]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_caption(p: Path) -> None:
    spend = " | ".join(f"{k}: {v:.1f}" for k, v in CAPEX.items())
    inf = ", ".join(f"{k} {v:g}" for k, v in _INF)
    text = f"""Microsoft AI Compute Spend by Fiscal Year ($B) — chart 01 (D7 KB, table source).
Spend per fiscal year: {spend}.
Inference cost per 1M tokens ($): {inf}.
Method: company-provided FY25-FY26; FY27-FY28 are management forecasts.
Source: fin_mate KB multimodal corpus, chart_src=msft_ai_capex.png
"""
    p.write_text(text, encoding="utf-8")


def write_chart(p: Path) -> None:
    """PIL bar chart of AI compute spend 62/82/112/150 with a 1M-token cost mini panel."""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1240, 600
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    try:
        f_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
        f_lab = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        f_val = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except Exception:
        f_title = f_lab = f_val = ImageFont.load_default()

    def _bars(x0, y0, x1, y1, title, entries):
        d.text((x0, y0 - 46), title, fill="black", font=f_title)
        n = len(entries)
        slot = (x1 - x0) / (n + 1)
        bw = slot * 0.55
        ymax = max(v for _, v in entries)
        for i, (lab, v) in enumerate(entries):
            cx = x0 + slot * (i + 1)
            bh = (v / ymax) * (y1 - y0 - 20)
            d.rectangle([cx - bw / 2, y1 - bh, cx + bw / 2, y1], fill="#1f6feb", outline="black")
            d.text((cx - 18, y1 - bh - 26), f"{v:g}", fill="black", font=f_val)
            d.text((cx - 24, y1 + 6), lab, fill="black", font=f_lab)
        d.line([(x0, y1), (x1, y1)], fill="black", width=2)

    _bars(70, 340, 620, 520, "Microsoft AI Compute Spend ($B) by fiscal year",
          [(k, v) for k, v in CAPEX.items()])
    d.ellipse([635, 320, 645, 330], fill="red")
    d.text((650, 314), "FY27 = $112B (needle)", fill="red", font=f_lab)
    _bars(660, 100, 1200, 280, "Inference cost per 1M tokens ($)",
          [(k, v) for k, v in _INF])
    d.ellipse([884, 82, 894, 92], fill="red")
    d.text((900, 76), "2025 = $1.2 (needle)", fill="red", font=f_lab)
    img.save(p)


def write_scan(p: Path) -> None:
    """Scanned-style memo PDF with a real text layer (PyMuPDF)."""
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    page.draw_rect(fitz.Rect(50, 50, 545, 792), color=(0.0, 0.0, 0.0), fill=(0.96, 0.96, 0.93), width=1.5)
    y = 90
    left = 78
    for txt, size, bold in [
        ("MICROSOFT INTERNAL MEMO — CONFIDENTIAL", 16, True),
        ("Subject: E7 Copilot + Agent Suite — FY26 pilot program", 13, True),
        ("Date: 2026-03-18 | Origin: Enterprise Commercial Sales Ops", 10, False),
        ("", 10, False),
        ("1. Pilot scope: 250,000 M365 E7 seats across 40 enterprise accounts.", 11, False),
        ("2. List price $99/user/month; pilot discount 20% net 30 days.", 11, False),
        ("3. Datacenter: North Netherlands +1.2 GW capacity add in H1 FY27.", 11, False),
        ("4. Security review pending via Entra Suite rollout (see E7 SKU brief).", 11, False),
    ]:
        page.insert_text((left, y), txt, fontsize=size, fontname="helv" if not bold else "hebo")
        y += 26
    page.insert_text((left, y + 10), "Page scanned 2026-03-19 by CorpScan #0417", fontsize=9)
    doc.save(p)
    doc.close()


def write_html(p: Path) -> None:
    rows = [
        ("Productivity & Business Processes", "78.1", "24%"),
        ("Intelligent Cloud", "145.2", "45%"),
        ("More Personal Computing", "99.2", "31%"),
    ]
    trs = "\n".join(
        f"<tr><td>{seg}</td><td>{rev}</td><td>{share}</td></tr>" for seg, rev, share in rows)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Microsoft Corporation (MSFT) — Corporate Overview</title></head>
<body>
<section id="company">
<h1>Microsoft Corporation (MSFT)</h1>
<p>Incorporated 1975, HQ Redmond WA. FY2025 revenue $322.5B, operating income $139.4B.</p>
</section>
<section id="segments">
<h2>FY25 segment revenue ($B)</h2>
<table border="1">
<tr><th>Segment</th><th>Revenue ($B)</th><th>Share</th></tr>
{trs}
</table>
</section>
<section id="geography">
<p>Geographic mix FY25: US 53%, EMEA 27%, APAC 20%.</p>
</section>
<section id="products">
<p>Microsoft 365 Consumer subscribers: 95 million; Teams MAU: 320 million.</p>
</section>
</body>
</html>
"""
    p.write_text(html, encoding="utf-8")


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / AZT)
    write_caption(OUT / CAPTX)
    write_chart(OUT / CAPPNG)
    write_scan(OUT / SCAN)
    write_html(OUT / OVW)
    for f in sorted(OUT.iterdir()):
        print(f"{f.name:28s} {f.stat().st_size:>8} bytes")


if __name__ == "__main__":
    build()