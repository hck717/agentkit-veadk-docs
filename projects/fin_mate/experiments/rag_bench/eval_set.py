"""RAG 實驗室 eval set：12 fact-QA（8 份研報 + overview）+ 2 trap（KB 無答案）+ 2 multi-hop。

gold 唔 hardcode URI（DB folder 名帶 hash，reseed 會變）——只記 source filename，
`all_doc_uris()` 用 OpenViking fs/tree probe 一次 map 返 doc folder → URI prefix。
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments._lib import load_env  # noqa: E402

TXT = "viking://resources/fin_kb/"
# 舊路由（2026-09-08 15:51 之前）："viking://resources/fin_kb/msft_txt/"；server 已 reseed → 依家 doc folder 直接喺 fin_kb/ 下。
OVERVIEW = "viking://resources/fin_kb/msft_overview/"  # 已不存在（reseed 剷走）——f12 唔再可評（見 CURRENT_ITEMS）

D = "20260205_Deutsche_Bank_MSFT_Microsoft-_F2Q_Leaning_into_the_long_game.txt"
MIZ = "20260205_Mizuho_Securities_MSFT_MSFT-_Good_Overall_Execution-_Albeit_with_More_Modest_Az.txt"
CRR = "20260212_China_Renaissance_Research_MSFT_Microsoft_Corp_F2Q26_Review-_Progresses_in_Azure_and_b.txt"
DEM = "20260227_DeMatteo_Research_MSFT_MSFT_Long_Informal_Idea_Bberg_02.27.26.txt"
BAR = "20260313_Barclays_MSFT_Microsoft_Corp.-_Evolving_AI_Offering_Brings_E7_to_Offic.txt"
WF = "20260316_Wells_Fargo_MSFT_MSFT-_Agentic_Adoption_Hinges_on_Security-_E7_SKU_Presen.txt"
EC1 = "Microsoft_Corp_Earnings_Call_20251029_DN000000003082552535.pdf.txt"
EC2 = "Microsoft_Corp_Earnings_Call_2026128_RT000000003094331726.pdf.txt"

LOCAL_DOCS = (D, MIZ, CRR, DEM, BAR, WF, EC1, EC2)

ITEMS = [
    dict(eid="f1", cat="fact", gold_docs=(D,),
         q="Deutsche 話 Microsoft F2Q 嘅 Azure 增長有幾多？同 guidance 比點？",
         gold="Azure grew 38% year over year on a constant currency basis, 1 point above guidance"),
    dict(eid="f2", cat="fact", gold_docs=(D,),
         q="Deutsche 點樣形容 F2Q 結果 vs 市場預期？主要原因？",
         gold="solid result but fell short of lofty market expectations, mainly Azure growth constrained by GPU and supply constraints"),
    dict(eid="f3", cat="fact", gold_docs=(MIZ,),
         q="Mizuho 話 MSFT F2Q 總收入幾多？同 Street 預期比？",
         gold="total revenue of 81.3 billion up 17% reported and 15% constant currency, above the Street's 80.3 billion estimate"),
    dict(eid="f4", cat="fact", gold_docs=(MIZ,),
         q="Mizuho 對 MSFT 嘅評級係咩？",
         gold="Outperform"),
    dict(eid="f5", cat="fact", gold_docs=(CRR,),
         q="China Renaissance 2026E EPS 預測幾多？vs 市場共識？",
         gold="2026E EPS of 17.11 vs consensus 15.80, 8 percent above"),
    dict(eid="f6", cat="fact", gold_docs=(BAR,),
         q="Barclays 講 Microsoft 新 E7 SKU 定價幾多？包含乜？",
         gold="E7 at 99 dollars per user, above the 60 dollar E5 price, bundling E5 plus Copilot and Agent 365"),
    dict(eid="f7", cat="fact", gold_docs=(WF,),
         q="Wells Fargo 講 E7 新 SKU 每月每位用戶幾多錢？包含咩？",
         gold="E7 at 99 dollars per user per month, including M365 E5 and Entra Suite"),
    dict(eid="f8", cat="fact", gold_docs=(WF,),
         q="Wells Fargo 認為 agentic adoption 取決於咩？",
         gold="agentic adoption hinges on security"),
    dict(eid="f9", cat="fact", gold_docs=(EC2,),
         q="F2Q26 call 話 Microsoft Cloud 季度收入首次突破幾多？同比升幾多？",
         gold="Microsoft Cloud surpassed 50 billion dollars in revenue for the first time, up 26 percent year over year"),
    dict(eid="f10", cat="fact", gold_docs=(EC2,),
         q="F2Q26 call 入面 Microsoft 365 Copilot 付費席位有幾多？",
         gold="15 million paid Microsoft 365 Copilot seats"),
    dict(eid="f11", cat="fact", gold_docs=(DEM,),
         q="DeMatteo idea note 嘅 MSFT 市值大約幾多？（presented 02/25/2026）",
         gold="market cap of approximately 2977 billion dollars"),
    dict(eid="f12", cat="fact", gold_docs=("msft_overview",),
         q="MSFT 三大主要業務係咩？（overview）",
         gold="Azure Intelligent Cloud, Productivity and Business Processes with Microsoft 365, and More Personal Computing with Windows Xbox and Bing"),
    dict(eid="t1", cat="trap", gold_docs=(),
         q="Microsoft 嘅股息殖利率同歷年派息紀錄係點？",
         gold="KB 無資料"),
    dict(eid="t2", cat="trap", gold_docs=(),
         q="Microsoft 喺日本搜尋市場嘅份額同 Yahoo Japan 合作詳情？",
         gold="KB 無資料"),
    dict(eid="m1", cat="multi_hop", gold_docs=(D, BAR),
         q="Azure 供應受限時，Microsoft 點解仲有力推 E7 加價式 upsell？",
         gold="Azure is growing well despite GPU supply constraints at 38 percent constant currency, and E7 bundles more value like Copilot and Agent 365 at a higher 99 dollar price point, supporting an upsell growth strategy"),
    dict(eid="m2", cat="multi_hop", gold_docs=(WF, BAR),
         q="點解 security 對 agentic adoption 同 E7 bundle 咁關鍵？",
         gold="agentic adoption hinges on security, and E7 bundles Entra Suite for security along with M365 E5 Copilot and Agent 365 to drive adoption and upsell"),
]


def all_doc_uris() -> dict[str, str]:
    """fs/tree probe：map source filename → doc-level URI prefix（trailing /）。"""
    load_env()
    key = os.environ["DATABASE_OPENVIKING_API_KEY"]
    base = os.environ.get("DATABASE_OPENVIKING_URL", "http://localhost:1933")
    qs = urllib.parse.urlencode({"uri": TXT, "limit": 1000})
    req = urllib.request.Request(f"{base}/api/v1/fs/tree?{qs}", headers={"X-API-Key": key})
    rows = json.load(urllib.request.urlopen(req, timeout=15))
    rows = rows if isinstance(rows, list) else (rows.get("result") or [])
    out: dict[str, str] = {}
    for e in rows:
        u = e.get("uri") or ""
        if not e.get("isDir") or not u.startswith(TXT):
            continue
        folder = u[len(TXT):].rstrip("/")
        stripped = re.sub(r"_[0-9a-f]{8}$", "", folder)
        for d in LOCAL_DOCS:
            if d not in out and d.startswith(stripped):
                out[d] = u.rstrip("/") + "/"
    missing = [d for d in LOCAL_DOCS if d not in out]
    if missing:
        raise RuntimeError(f"OpenViking fs/tree 揾唔到 doc folder: {missing}")
    return out


def resolve_gold(item: dict, doc_uris: dict[str, str] | None = None) -> set[str]:
    du = doc_uris or all_doc_uris()
    return {du[f] for f in item["gold_docs"]}


def resolve_gold_local(item: dict) -> set[str]:
    """D7 local-backend gold: source filename 就係 doc identifier（同 file_path 對應）。"""
    return set(item["gold_docs"])


def d7_items(vis: bool = False) -> list[dict]:
    """D7 eval set：15 條 CURRENT_ITEMS；vis=True 加埋 5 條 needle（data/kb_vis 語料限定）。"""
    return CURRENT_ITEMS + (D7_VIS_ITEMS if vis else [])


# 依家可 run 嘅 items：server 2026-09-08 reseed 後 msft_overview 已唔存在於 KB，
# f12 嘅 gold 冇得對應實 URI（硬 mapped 落舊 prefix 會令佢永遠 recall 0，誤導比較）。
# D5 新 type（hyde / rerank）只行呢 15 題；舊 run 16 題結果保留（當時 overview 仲喺度）。
CURRENT_ITEMS = [i for i in ITEMS if i["eid"] != "f12"]

# ---- D7 multimodal / needle items ----
# 資料只存在 data/kb_vis/ 嘅新來源（table / chart / scan / HTML）。D7 mm 模式先加呢 5 題；
# 純文字語料（text-only）跑呢啲題會正常 recall=0（語料根本就冇），用嚟驗證 D4 corpus 覆蓋唔到。
VIS_DOCS = {
    "AZT": "msft_azure_revenue.csv",
    "CAPTX": "msft_ai_capex.txt",
    "CAPPNG": "msft_ai_capex.png",
    "SCAN": "msft_scan.pdf",
    "OVW": "msft_kb_overview.html",
}

D7_VIS_ITEMS = [
    dict(eid="mb1", cat="needle", gold_docs=(VIS_DOCS["AZT"],),
         q="Azure revenue table 入面 FY26Q4E 嘅 constant-currency YoY growth 預測係幾多？",
         gold="Azure constant currency revenue growth of 35 percent for FY26Q4E"),
    dict(eid="mb2", cat="needle", gold_docs=(VIS_DOCS["CAPTX"],),
         q="AI compute spend chart 顯示 FY27 Microsoft AI compute spend 預測係幾多？",
         gold="Microsoft AI compute spend forecast 112 billion dollars for FY27"),
    dict(eid="mb3", cat="needle", gold_docs=(VIS_DOCS["CAPTX"],),
         q="AI 效率 chart 顯示 2025 年每百萬 token 嘅 inference cost 幾多？",
         gold="inference cost of 1.2 dollars per million tokens in 2025"),
    dict(eid="mb4", cat="needle", gold_docs=(VIS_DOCS["SCAN"],),
         q="掃描 memo 入面 E7 Copilot Agent Suite FY26 pilot 計劃幾多個席位？",
         gold="250000 M365 E7 pilot seats across 40 enterprise accounts"),
    dict(eid="mb5", cat="needle", gold_docs=(VIS_DOCS["OVW"],),
         q="HTML overview 顯示 FY25 收入嚟自 EMEA 嘅比例係幾多？",
         gold="27 percent of revenue from the EMEA region in FY25"),
]


if __name__ == "__main__":
    du = all_doc_uris()
    assert len(du) == 8, du
    assert len(ITEMS) == 16
    assert len(CURRENT_ITEMS) == 15
    assert sum(i["cat"] == "fact" for i in ITEMS) == 12
    assert sum(i["cat"] == "trap" for i in ITEMS) == 2
    assert sum(i["cat"] == "multi_hop" for i in ITEMS) == 2
    assert "f12" in [i["eid"] for i in ITEMS] and "f12" not in [i["eid"] for i in CURRENT_ITEMS]
    assert len(D7_VIS_ITEMS) == 5 and all(i["cat"] == "needle" for i in D7_VIS_ITEMS)
    assert len(d7_items()) == 15 and len(d7_items(vis=True)) == 20
    print("eval_set OK —", len(du), "docs mapped,", len(CURRENT_ITEMS), "current items (f12 excluded),",
          len(D7_VIS_ITEMS), "D7 needle items")
    for k, v in du.items():
        print(f"  {k[:40]:42s} -> {v}")