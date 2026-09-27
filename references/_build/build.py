#!/usr/bin/env python3
"""Build standalone + combined HTML for VeADK/AgentKit reference docs.

Usage:
    python3 references/_build/build.py             # build all
    python3 references/_build/build.py --combined  # build combined only
    python3 references/_build/build.py --standalone

Reads TABS config, converts .md → .html via pandoc, wraps in dark-theme shell.
Intros: if intros/{key}.html exists, inject that raw HTML as the tab intro
(keeps existing intro content verbatim). Otherwise builds a default intro
from the tab description.

Outputs:
  - references/veadk-agentkit-{...}.html (standalone per unique doc)
  - references/veadk-agentkit-all.html   (combined tabbed view)

Validation: run references/_build/validate.py afterwards.
"""
import subprocess, sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "references"
BUILD = Path(__file__).resolve().parent
INTROS = REFS / "intros"

# ─── TABS CONFIG ───────────────────────────────────────────────────────────
# (key, label, description, [(subdoc_key, md_filename, subdoc_title), ...])
# subdocs may be empty [] for intro-only tabs (arch).

TABS = [
    # ─ D1 定向 Orient ─
    ("overview", "總覽 Overview",
     "README + 使用指南 + 全部參考文檔索引（Tab 導覽）",
     [("ov", "README.md", "README")]),
    ("concepts", "AI 概念百科 AI Concepts",
     "Dictionary / Index · 每個概念用 BytePlus/Volcengine 實例解釋 · 指返專屬 tab",
     [("concepts", "veadk-agentkit-ai-concepts.md", "AI 概念百科")]),
    # ─ D2 起手 Build ─
    ("cli", "CLI / 部署 Deployment",
     "AgentKit CLI 所有指令 · 10 分鐘上手 demo",
     [("cli", "agentkit-cli.md", "AgentKit CLI")]),
    ("api", "開發 API Developer API",
     "VeADK 框架 + AgentKit SDK · 點揀兩者 + 核心架構",
     [("api", "veadk-api.md", "VeADK API"),
      ("sdk", "agentkit-sdk.md", "AgentKit SDK")]),
    # ─ D3 能力 Capabilities ─
    ("tools", "工具 / 能力 Tools & Capabilities",
     "MCP · Tools · Skills · A2A · Guardrail/Filter · 逐樣解構 + BytePlus 實例",
     [("tools", "veadk-agentkit-tools-capabilities.md", "工具 / 能力")]),
    ("vc", "記憶 / 知識庫 Memory & Vector DB",
     "VectorDB 後端 + LTM/KB 矩陣 · 揀後端決策",
     [("vc", "veadk-agentkit-vector-cache.md", "記憶 / 知識庫")]),
    ("rag", "RAG 全攻略 RAG Playbook",
     "Naive → Agentic / Corrective / Hybrid · 檢索 + Ranker + chunking · 速度/準確/平衡/成本 三揀一大表",
     [("rag", "veadk-agentkit-rag-guide.md", "RAG 全攻略")]),
    # ─ D4 數據 + 快 Data & Speed ─
    ("db", "資料庫管理 Database Management",
     "本地 vs 雲端 · SQL / Vector / NoSQL · 記憶三層後端（STM/LTM/KB）+ 檢索",
     [("db", "veadk-agentkit-database-management.md", "資料庫管理")]),
    ("mem", "記憶 + 上下文 Memory & Context",
     "STM / LTM / KB 點流入 context · 上下文管理（window / compaction / cache 協同）· 使用技巧",
     [("mem", "veadk-agentkit-memory-context.md", "記憶 + 上下文管理")]),
    ("cache", "Cache 管理 Cache Management",
     "前綴 / 上下文緩存 + 隱式 cache + output_schema + 128k+ 加倍 · 類型速查",
     [("cache", "veadk-agentkit-cache-management.md", "Cache 管理")]),
    # ─ D5 錢 Money ─
    ("price", "計價 Pricing",
     "Plan / AFP / 額度 / 模型矩陣 / 6 scenarios · 報價 6 步",
     [("price", "veadk-agentkit-pricing.md", "計價 Pricing")]),
    ("cmp", "跨廠商對照 Vendor Comparison",
     "BytePlus vs Azure / AWS / Google / DeepSeek / Qwen / Hunyuan · 五層成本 + 同-model 價差",
     [("cmp", "veadk-vendor-cost-comparison.md", "跨廠商對照")]),
    # ─ D6 變得更強 Make Better ─
    ("ft", "精調 / 優化 + 訓練 Fine-tune & Train",
     "LoRA / SFT / DPO / RLHF / Distillation · 幾時先用嘅決策樹 + TrainingKit（pre/post-training + RL）",
     [("ft", "veadk-agentkit-finetune-optimize.md", "精調 / 優化"),
      ("train", "veadk-agentkit-training-kit.md", "TrainingKit 訓練套件")]),
    ("val", "評估 / 評測 Eval & Testing",
     "CI / Offline / Shadow eval · dataset → evaluator → experiment（AgentKit/VeADK 點做）",
     [("eval", "veadk-agentkit-evaluation.md", "評估 / 評測"),
      ("oe", "veadk-agentkit-optimization-evaluation-guide.md", "優化 + 評估 完全指南")]),
    # ─ D7 底層 Under the Hood ─
    ("hard", "硬體 Hardware",
     "VM / GPU / CPU · GPU 矩陣 + 量化 + Speculative Decoding + 自建 vs 托管",
     [("hard", "veadk-agentkit-hardware.md", "硬體 Hardware")]),
    ("serv", "ServingKit（推理交付 Inference Delivery）",
     "vLLM / SGLang / Dynamo + PD disaggregation + AI 網關 + 重量加速 + xLLM · BytePlus ServingKit",
     [("serv", "veadk-agentkit-serving-kit.md", "ServingKit")]),
    # ─ D8 控制 + 安全 Control & Safety ─
    ("gw", "閘道 / 網關 Gateway",
     "AgentKit Gateway（MCP）+ BytePlus AI Gateway + 方舟 AI 加速網閘 · 統一入口 / fallback / 緩存 / 限流",
     [("gw", "veadk-agentkit-gateway.md", "閘道 / 網關 Gateway")]),
    ("sec", "安全 / 可觀測 Security & Observability",
     "RBAC / PII / Audit / Observability / Guardrail / Input-Output Filter · 四軸 checklist",
     [("sec", "veadk-agentkit-rbac-observability.md", "安全 / 可觀測")]),
    # ─ D9 定位 + 快 Positioning & Speed ─
    ("uniq", "獨特賣點 Unique Value",
     "VeADK / AgentKit / BytePlus + 自家模型四層獨特位 · 真獨特 vs 行貨 · 一包乾 checklist",
     [("uniq", "veadk-agentkit-uniqueness.md", "獨特賣點")]),
    ("perf", "性能 Playbook Performance",
     "Latency / Throughput / Cost / Eval · 5 大偷錢位",
     [("perf", "veadk-agentkit-performance.md", "性能 Playbook")]),
    # ─ 自家模型深潛 Seed Deep-Dives ─
    ("seedream", "Seedream 圖片生 Image Gen",
     "BytePlus 自家生圖家族 · Lite/Pro + 歷代演進 + 定價 + Dreamina/CapCut/ModelArk/VideoOne",
     [("sd", "veadk-agentkit-seedream.md", "Seedream 圖片生成")]),
    ("seedance", "Seedance 視頻生 Video Gen",
     "BytePlus 自家生片家族 · 2.0/2.5/Fast/Mini + LAS 計費 + VideoOne 平台 deep-dive",
     [("se", "veadk-agentkit-seedance.md", "Seedance 視頻生成")]),
    # ─ D10 總結 Capstone ─
    ("arch", "LLM 架構 · 端到端 LLM Architecture",
     "成條鏈 request→GPU · 幾時用咩優化 + Cache 管理 + 預期 Outcome + Improvement Loop",
     []),
    # ─ 實用連結 Quick Links ─
    ("links", "實用連結 Useful Links",
     "官方 Console / 方案頁 / GitHub / Mintlify / 火山文檔 · 全部 master page + 簡介",
     []),
]

TAB_ORDER = [t[0] for t in TABS]

# ─── CSS / JS ────────────────────────────────────────────────────────────
CSS_COMBINED = """
:root{--bg:#07111f;--text:#edf4ff;--muted:#a8b7cc;--line:#203b59;--accent:#59d4ff}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(900px 450px at 10% -10%,#153f64 0,transparent 62%),radial-gradient(800px 450px at 100% 0,#25205b 0,transparent 65%),var(--bg);color:var(--text);font:16px/1.7 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}.shell{max-width:1600px;margin:auto;padding:28px 22px 70px}.hero{border:1px solid #2c5274;background:linear-gradient(120deg,#0b2035cc,#101d43cc);border-radius:24px;padding:28px;box-shadow:0 25px 80px #0006}.eyebrow{color:var(--accent);font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:.16em}.hero h1{font-size:clamp(2rem,5vw,3.4rem);line-height:1.1;margin:7px 0}.hero p{margin:0;color:var(--muted);max-width:820px}.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}.toolbar button,.copy{cursor:pointer;color:var(--text);background:#173452;border:1px solid #32638e;border-radius:10px;padding:8px 12px;font-weight:700}.navwrap{position:sticky;top:0;z-index:60;margin-top:22px;background:#0a1727f2;border:1px solid var(--line);border-radius:16px;backdrop-filter:blur(6px);padding:10px}.sectionbar{display:flex;gap:8px;flex-wrap:wrap;padding-bottom:10px;margin-bottom:10px;border-bottom:1px solid #1d3a5c}.section-btn{cursor:pointer;color:#cfe6ff;background:#1b3f60;border:1px solid #3b7aa8;border-radius:999px;padding:7px 14px;font-weight:700;font-size:.88rem}.section-btn.active{background:var(--accent);color:#03141f;border-color:var(--accent)}.tab-btn[hidden]{display:none!important}.topbar{display:flex;gap:8px;flex-wrap:wrap}.tab-btn{cursor:pointer;color:var(--muted);background:#173452;border:1px solid #32638e;border-radius:10px;padding:8px 12px;font-weight:700;font-size:.92rem}.tab-btn.active,.subtab-btn.active{background:var(--accent);color:#03141f;border-color:var(--accent)}.tabintro{margin:0 0 22px;padding:18px 22px 8px;border:1px solid #2c6c9a;border-left:4px solid var(--accent);border-radius:16px;background:linear-gradient(160deg,#0d2340cc,#0a1a30cc);box-shadow:inset 0 1px #ffffff0a}.intro-bar{font-weight:800;color:var(--accent);margin:-18px -22px 14px;padding:11px 22px;background:#123a5e;border-bottom:1px solid #2c6c9a;border-radius:15px 15px 0 0;font-size:.86rem;letter-spacing:.02em}.tabintro h2{border-top:none!important;font-size:1.35rem;margin-top:1.6em;padding-top:0}.tabintro h3{color:#caeaff;font-size:1.08rem;margin-top:1.4em}.subtabs{display:flex;gap:6px;margin-bottom:18px;flex-wrap:wrap}.subtab-btn{cursor:pointer;color:var(--muted);background:#173452;border:1px solid #32638e;border-radius:10px;padding:6px 12px;font-weight:700;font-size:.88rem}.layout{display:grid;grid-template-columns:270px minmax(0,1fr);gap:28px;margin-top:28px}.toc{position:sticky;top:18px;height:max-content;max-height:calc(100vh - 36px);overflow:auto;padding:18px;background:#091727d9;border:1px solid var(--line);border-radius:18px}.toc strong{display:block;margin-bottom:10px}.toc a{display:block;color:var(--muted);text-decoration:none;padding:5px 2px;font-size:.91rem}.toc a:hover{color:var(--accent)}main{min-width:0;background:#0a1727d9;border:1px solid var(--line);border-radius:20px;padding:clamp(22px,4vw,48px);box-shadow:0 25px 80px #0004}h1,h2,h3{scroll-margin-top:25px}main h2{margin-top:2.5em;padding-top:.25em;border-top:1px solid var(--line);font-size:1.65rem}main h3{margin-top:1.8em;color:#caeaff;font-size:1.18rem}p,li{color:#d5e1f0}code{background:#0e2a44;padding:1px 5px;border-radius:5px;font-size:.93em}pre{background:#0b1a2e;border:1px solid #1d3a5c;border-radius:12px;padding:18px;overflow:auto;position:relative}pre code{background:none;padding:0;font-size:.88em;line-height:1.6}table{width:100%;border-collapse:collapse;margin:18px 0;font-size:.93rem}th,td{border:1px solid #1d3a5c;padding:10px 14px;text-align:left}th{background:#0e2a44;color:#caeaff;font-weight:700}tr:nth-child(even){background:#09172788}blockquote{border-left:4px solid #32638e;margin:18px 0;padding:12px 18px;background:#0b1a2e88;border-radius:0 12px 12px 0;color:#a8b7cc}a{color:#59d4ff;text-decoration:none}a:hover{text-decoration:underline}hr{border:none;border-top:1px solid #1d3a5c;margin:2em 0}pre .copy{position:absolute;top:8px;right:8px;font-size:.82rem;padding:4px 10px;z-index:2}.copy{position:relative;cursor:pointer;color:var(--text);background:#173452;border:1px solid #32638e;border-radius:10px;padding:8px 12px;font-weight:700}main>.tpage{display:none}main>.tpage.active{display:block}.subdoc{display:none}.subdoc.active{display:block}.subtabs{display:none}.subtabs[data-tab]:not(.hidden){display:flex}"""

CSS_STANDALONE = ""

# Combined JS
JS_COMBINED = """const SECTIONS=[["orient","定向 Orient",["overview","concepts","uniq","arch","links"]],["build","起手 Build",["cli","api"]],["cap","能力 Capabilities",["tools","vc","rag","db","mem","cache"]],["better","變強 Make Better",["ft","val","perf"]],["cost","錢 Cost",["price","cmp"]],["infra","底層 + 安全 Infra & Safety",["hard","serv","gw","sec"]],["seed","自家模型 Seed Models",["seedream","seedance"]],["guide","攻略完全參考 Guide Parts",["prereq","modelark","akplat","gov","tut","viking","arkclaw","apx"]]];
const secOf=t=>{const s=SECTIONS.find(x=>x[2].indexOf(t)>=0);return s?s[0]:SECTIONS[0][0]};
const syncNav=t=>{const sk=secOf(t),s=SECTIONS.find(x=>x[0]===sk);document.querySelectorAll('.section-btn').forEach(b=>b.classList.toggle('active',b.dataset.section===sk));document.querySelectorAll('.tab-btn').forEach(b=>{b.hidden=s[2].indexOf(b.dataset.tab)<0;b.classList.toggle('active',b.dataset.tab===t)});};
const showSection=sk=>{const s=SECTIONS.find(x=>x[0]===sk);if(!s)return;const cur=document.querySelector('.tpage.active');const t=(cur&&s[2].indexOf(cur.dataset.tab)>=0)?cur.dataset.tab:s[2][0];const d=document.querySelector('.tpage[data-tab="'+t+'"] .subdoc');show(t,d?d.dataset.doc:'');};
const show=(tab,sub)=>{syncNav(tab);document.querySelectorAll('.tpage').forEach(s=>s.classList.toggle('active',s.dataset.tab===tab));const sec=document.querySelector('.tpage[data-tab="'+tab+'"]');if(sec){sec.querySelectorAll('.subdoc').forEach(d=>d.classList.toggle('active',!sub||d.dataset.doc===sub));sec.querySelectorAll('.subtab-btn').forEach(b=>b.classList.toggle('active',!sub||b.dataset.doc===sub));}renderToc();window.scrollTo({top:0,behavior:'smooth'});const h=tab+((sub&&['ov',''].indexOf(sub)<0)?':'+sub:'');history.replaceState(null,'','#'+h);};
const renderToc=()=>{const toc=document.getElementById('toc');const sec=document.querySelector('.tpage.active');let root=sec?sec.querySelector('.subdoc.active'):null;root=root||sec;toc.innerHTML='';if(!root)return;const heads=[...new Set((sec?[...sec.querySelectorAll('.tabintro h2,.tabintro h3')]:[]).concat([...root.querySelectorAll('h2,h3')]))];heads.forEach((h,i)=>{if(!h.id)h.id='sec-'+tab()+'-'+i;let a=document.createElement('a');a.href='#'+h.id;let t=h.textContent.replace(/\\s+/g,' ').trim();a.textContent=t;a.style.paddingLeft=h.tagName==='H3'?'15px':'2px';a.title=t;toc.append(a)});};
const tab=()=>{const a=document.querySelector('.tpage.active');return a?a.dataset.tab:'overview'};
document.querySelectorAll('pre').forEach(pre=>{let b=document.createElement('button');b.className='copy';b.textContent='Copy';b.onclick=async()=>{await navigator.clipboard.writeText(pre.innerText);b.textContent='Copied';setTimeout(()=>b.textContent='Copy',1200)};pre.append(b)});
const collapse=()=>document.querySelectorAll('.tpage.active pre').forEach(p=>p.style.display='none');const expand=()=>document.querySelectorAll('.tpage.active pre').forEach(p=>p.style.display='block');
(()=>{let init=(location.hash||'').replace(/^#/,'');let t='overview',s='';if(init.includes(':')){[t,s]=init.split(':');}else if(init){t=init;}if(!document.querySelector('.tpage[data-tab="'+t+'"]')){t='overview';s=''}const def=document.querySelector('.tpage[data-tab="'+t+'"] .subdoc');show(t,s||(def?def.dataset.doc:''));})();"""

JS_STANDALONE = """const toc=document.getElementById('toc'),heads=[...document.querySelectorAll('main h2,main h3')];heads.forEach((h,i)=>{h.id=h.id||`section-${i}`;let a=document.createElement('a');a.href='#'+h.id;a.textContent=h.textContent;a.style.paddingLeft=h.tagName==='H3'?'15px':'2px';toc.append(a)});document.querySelectorAll('pre').forEach(pre=>{let b=document.createElement('button');b.className='copy';b.textContent='Copy';b.onclick=async()=>{await navigator.clipboard.writeText(pre.innerText);b.textContent='Copied';setTimeout(()=>b.textContent='Copy',1200)};pre.append(b)});const collapse=()=>document.querySelectorAll('pre').forEach(p=>p.style.display='none');const expand=()=>document.querySelectorAll('pre').forEach(p=>p.style.display='block');"""


# ─── COMPREHENSIVE GUIDE INTEGRATION ──────────────────────────────────────
# Merges references/veadk-agentkit-comprehensive-guide.html into the combined
# tabbed view. The guide's own stylesheet is re-emitted scoped under .gx so it
# cannot leak into the 24 existing tabs (which use their own code-block classes).
GUIDE_FILE = REFS / "veadk-agentkit-comprehensive-guide.html"
GX = "gx"

# Existing tabs that receive extra subdocs sourced from the guide.
#   tab_key -> [(subdoc_key, guide_part_id, subdoc_title), ...]
GUIDE_MERGES = {
    "api": [("vfull", "part3-veadk", "VeADK 完全參考（攻略版）"),
            ("sfull", "part4-sdk", "SDK 完全參考（攻略版）")],
    "cli": [("cfull", "part5-cli", "CLI 完全參考（攻略版）")],
}

# New top-level tabs sourced from the guide.
#   (key, label, description, guide_part_id, subdoc_title)
GUIDE_TABS = [
    ("prereq", "前置知識 Prerequisites",
     "生態全圖 · BytePlus vs Volcengine 兩個市場 · 帳戶開通 · 憑證體系 · 計費 quota · 術語表",
     "part0", "前置知識"),
    ("modelark", "ModelArk 模型層 ModelArk",
     "Chat API · Function Calling · 模型調用最佳實踐 · Flex · Responses API · 多模態 · 上下文緩存 · 錯誤重試",
     "part1-modelark", "ModelArk 完全參考"),
    ("akplat", "AgentKit 平台 AgentKit Platform",
     "官方定位 · 平台架構 · 功能支柱 · 入門路徑 · Runtime · Sessions/Memory/KB · MCP · A2A · Skills · 模型服務 · 限制 · 遷移 · 最佳實踐",
     "part2-agentkit", "AgentKit 平台完全參考"),
    ("gov", "Agent 治理與安全 Governance ★",
     "部署模式五種光譜 · Execution Placement · Control Surface · AgentKit MA 三個人／三個範圍／三張票／四道門 · Agent Trust Plane · 風險分級 HITL",
     "@a21", "Agent 治理與安全（核心版）"),
    ("ctrl", "Agent 管控 Agent Control ★",
     "六層管控模型 L0–L5 × 五種手段（Allow / Deny / Transform / Gate / Observe）· 分層限制總表 · IAM 三級權限 + Project/Tag 邊界 · Runtime 網絡/認證/WebShell/配額 · Guardrail 四回調 + LLM-FW 五 category · MCP toolset 工具白名單 + 三種 calling mode + 工具參數 allowlist + 出站 scope + Trusted MCP · Viking must / must_not · 白名單 vs 黑名單決策 · 三個實戰場景 · 15 個常見錯誤",
     "part25-control", "Agent 管控完全指南"),
    ("tut", "端到端實戰 Tutorial",
     "由零到部署一隻生產級客服 Agent · 項目結構 · config.yaml · agent.py · 本地測試 · 部署 · 生產配置 · 評測閉環 · 運維優化",
     "part6-tutorial", "端到端實戰"),
    ("viking", "Viking AI Search",
     "BytePlus 自家 AI 搜尋／推薦／問答 · Dataset schema · Search 配置 · Filter 語法 · Recommendation · Conversational Search · 檢索 API 大全 · 計費",
     "part7-viking", "Viking AI Search"),
    ("arkclaw", "ArkClaw 企業級平台 ArkClaw",
     "企業級 Agent 平台 · 計費 · 鑑權 · 管理員能力 · 實例／模型／模板 · Skills · Application Center · 用戶權限 · 網絡 · 安全 · 可觀測",
     "part8-arkclaw", "ArkClaw"),
    ("apx", "附錄 速查總表 Appendix",
     "Endpoint / Region · 環境變數總表 · 安裝速查 · 模型命名對照 · 錯誤處理 · 十大鐵律 · 架構圖索引",
     "part9-appendix", "附錄 速查總表"),
]

# ─── SECTIONS ──────────────────────────────────────────────────────────────
# Groups the top-level tabs into one row of section buttons, so the topbar
# stops being a 32-button wall. (key, label, [tab_keys]) — every tab must
# appear in exactly one section (validate.py enforces this). The JS copy inside
# JS_COMBINED is regenerated from this table by js_with_sections(), so the two
# can never drift apart.
SECTIONS = [
    ("orient", "定向 Orient", ["overview", "concepts", "uniq", "arch", "links"]),
    ("build", "起手 Build", ["cli", "api"]),
    ("cap", "能力 Capabilities", ["tools", "vc", "rag", "db", "mem", "cache"]),
    ("better", "變強 Make Better", ["ft", "val", "perf"]),
    ("cost", "錢 Cost", ["price", "cmp"]),
    ("infra", "底層 + 安全 Infra & Safety", ["hard", "serv", "gw", "sec"]),
    ("seed", "自家模型 Seed Models", ["seedream", "seedance"]),
    ("guide", "攻略完全參考 Guide Parts",
     ["prereq", "modelark", "akplat", "gov", "ctrl", "tut", "viking", "arkclaw", "apx"]),
]


def sections_js() -> str:
    """SECTIONS as the JS array literal the page's own script consumes.

    The literal used to be hand-maintained inside JS_COMBINED, so adding a tab
    to SECTIONS without editing the string silently produced a tab that no
    section button could ever reveal (validate.py checks the Python table, not
    the JS). Generating it here removes that failure mode.
    """
    rows = []
    for key, label, tabs in SECTIONS:
        ids = ",".join(f'"{t}"' for t in tabs)
        rows.append(f'["{key}","{label}",[{ids}]]')
    return "[" + ",".join(rows) + "]"


def js_with_sections(js: str) -> str:
    """Rewrite the `const SECTIONS=[…];` literal in JS_COMBINED from SECTIONS."""
    out, n = re.subn(r"const SECTIONS=\[.*?\];",
                     lambda m: "const SECTIONS=" + sections_js() + ";",
                     js, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("ABORT: could not locate `const SECTIONS=[…];` in JS_COMBINED")
    return out

# Guide selectors that belong to the guide's own page shell — dropped on merge.
_SHELL_SEL = (":root", "*", "html", "body", ".shell", ".hero", ".eyebrow",
              ".toolbar", ".layout", ".toc", ".main", ".copy")


_MAIN_RE = re.compile(r"<main[^>]*>", re.I)
_STYLE_RE = re.compile(r"<style[^>]*>", re.I)
# The desktop preview panel rewrites a file in place while it is open: it adds
# data-page-node-id to every element and turns `<main>` into `<main data-…>`.
# Strip those markers so they can never leak into the combined view.
_INSTR_RE = re.compile(r'\s+data-page-node-id="[^"]*"')


def _guide_body():
    if not GUIDE_FILE.exists():
        return ""
    h = GUIDE_FILE.read_text(encoding="utf-8")
    m = _MAIN_RE.search(h)
    if not m:
        return ""
    j = h.find("</main>", m.end())
    if j < 0:
        return ""
    return _INSTR_RE.sub("", h[m.end():j])


def guide_parts():
    """{part_id: html}. Also splits Part 2 so the 2.21 governance section is
    returned separately under '@a21' — it becomes its own core tab, and Part 2
    is cut there so nothing is duplicated."""
    body = _guide_body()
    if not body:
        return {}
    marks = [(m.start(), m.group(1))
             for m in re.finditer(r'<h1[^>]*id="([^"]*)"', body)]
    parts = {}
    for i, (pos, pid) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        parts[pid] = body[pos:end]
    p2 = parts.get("part2-agentkit", "")
    m = re.search(r'<h2[^>]*id="a21-gov"', p2)
    if m:
        parts["part2-agentkit"] = p2[:m.start()]
        parts["@a21"] = p2[m.start():]
    return parts


def guide_css():
    """Guide stylesheet re-emitted scoped under .gx (plus its CSS vars)."""
    if not GUIDE_FILE.exists():
        return ""
    h = GUIDE_FILE.read_text(encoding="utf-8")
    sm = _STYLE_RE.search(h)
    if not sm:
        return ""
    e = h.find("</style>", sm.end())
    if e < 0:
        return ""
    css = h[sm.end():e]
    css = re.sub(r"@media[^{]*\{(?:[^{}]*\{[^}]*\})*[^}]*\}", "", css)
    css = re.sub(r"\bmain (?=[a-zA-Z])", "", css)          # "main h1" -> "h1"
    out = []
    for sel, body in re.findall(r"([^{}]+)\{([^}]*)\}", css):
        sel = sel.strip()
        if not sel or sel.startswith("@"):
            continue
        if any(sel == s or sel.startswith(s + c)
               for s in _SHELL_SEL for c in (",", " ", ".", ":", "")):
            continue
        scoped = ",".join(f".{GX} {p.strip()}"
                          for p in sel.split(",") if p.strip())
        out.append(f"{scoped}{{{body}}}")
    return ("".join(out)
            # guide-only custom properties, added (not overriding) at :root
            + ":root{--accent2:#c9a6ff;--warn:#ffcf5e;--good:#7ee7a2;"
              "--bad:#ff7d7d;--code:#ffe6a7}"
            + f".{GX} ul{{margin:10px 0}}.{GX} li{{margin:3px 0}}"
            + f".{GX} h1:first-child{{margin-top:.4em}}"
            + f"@media(max-width:1000px){{.{GX} .grid2"
              "{grid-template-columns:minmax(0,1fr)}}")


def guide_block(tab_key, subdoc_key, part_id, title, parts):
    """One <div class="subdoc"> holding a guide Part, wrapped for CSS scoping."""
    html = parts.get(part_id, "")
    if not html:
        print(f"  WARN guide part missing: {part_id}", file=sys.stderr)
        return ""
    return (f'<div class="subdoc" data-tab="{tab_key}" data-doc="{subdoc_key}">\n'
            f'<div class="{GX}">\n{html}\n</div>\n</div>')


# ─── PANDOC ────────────────────────────────────────────────────────────────
def md_to_html(md_text, id_prefix=""):
    args = ["pandoc", "-f", "gfm-tex_math_dollars", "-t", "html5",
            "--no-highlight"]
    if id_prefix:
        args += ["--id-prefix", id_prefix]
    r = subprocess.run(args, input=md_text.encode(), capture_output=True)
    if r.returncode != 0:
        print(f"  pandoc err: {r.stderr.decode()[:300]}", file=sys.stderr)
        return ""
    return r.stdout.decode()


# ─── INTRO ─────────────────────────────────────────────────────────────────
def tab_intro(key, label, desc):
    """Return <div class="tabintro">…</div> or '' if none."""
    f = INTROS / f"{key}.html"
    if f.exists():
        content = f.read_text(encoding="utf-8").strip()
        bar = "📘 呢頁詳細解說（先睇呢度，再落下面文件）"
        return (f'<div class="tabintro" data-tab="{key}">'
                f'<div class="intro-bar">{bar}</div>\n{content}\n</div>')
    # New tabs: default minimal intro
    return (f'<div class="tabintro" data-tab="{key}">'
            f'<div class="intro-bar">📘 呢頁詳細解說（先睇呢度，再落下面文件）</div>\n'
            f'<p>{desc}</p>\n</div>')


# ─── WRAPPERS ──────────────────────────────────────────────────────────────
def standalone_html(title, body):
    shell_max = "1440px"
    css = CSS_COMBINED.replace("1600px", shell_max, 1) \
                      .replace("main>.tpage{display:none}main>.tpage.active{display:block}.subdoc{display:none}.subdoc.active{display:block}.subtabs{display:none}.subtabs[data-tab]:not(.hidden){display:flex}", "main h2:first-of-type{margin-top:.2em}")
    return (f'<!doctype html><html lang="zh-HK"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title><style>\n{css}\n</style></head>'
            f'<body><div class="shell"><header class="hero">'
            f'<div class="eyebrow">BytePlus · Volcengine Agent 開發文檔</div>'
            f'<h1>{title}</h1><p>參考文檔（獨立頁面）</p>'
            f'<div class="toolbar"><button onclick="collapse()">Hide code</button>'
            f'<button onclick="expand()">Show code</button>'
            f'<button onclick="window.scrollTo({{top:0,behavior:\'smooth\'}})">Back to top</button>'
            f'</div></header><div class="layout"><aside class="toc">'
            f'<strong>On this page</strong><nav id="toc"></nav></aside><main>\n'
            f'{body}\n</main></div></div><script>{JS_STANDALONE}</script></body></html>')


def combined_html():
    parts = guide_parts()
    guide_extra_css = guide_css()

    def eff_subdocs(key, subdocs):
        """TABS subdocs + any guide subdocs merged into this tab."""
        return list(subdocs) + list(GUIDE_MERGES.get(key, []))

    labels = {k: l for k, l, _, _ in TABS}
    labels.update({k: l for k, l, _, _, _ in GUIDE_TABS})
    order = [k for k, _, _, _ in TABS] + [k for k, _, _, _, _ in GUIDE_TABS]
    first_section = set(SECTIONS[0][2])
    # Tabs outside the first section start hidden so the topbar never flashes
    # all 32 buttons before JS filters them.
    topbar = "".join(
        f'<button class="tab-btn" data-tab="{k}"'
        f'{" hidden" if k not in first_section else ""}'
        f' onclick="show(\'{k}\',\'\')">{labels[k]}</button>'
        for k in order)
    sectionbar = "".join(
        f'<button class="section-btn{" active" if i == 0 else ""}" data-section="{sk}"'
        f' onclick="showSection(\'{sk}\')">{sl}</button>'
        for i, (sk, sl, _) in enumerate(SECTIONS))

    sections = []
    for key, label, desc, subdocs in TABS:
        intro = tab_intro(key, label, desc)
        eff = eff_subdocs(key, subdocs)
        subdoc_blocks = []
        for sd_key, sd_file, sd_title in subdocs:
            p = (ROOT if sd_file == "README.md" else REFS) / sd_file
            if not p.exists():
                print(f"  WARN missing {sd_file}", file=sys.stderr)
                continue
            md = p.read_text(encoding="utf-8")
            prefix = ("ov-" if sd_key == "ov" else f"{sd_key}-")
            body = md_to_html(md, prefix)
            subdoc_blocks.append(
                f'<div class="subdoc" data-tab="{key}" data-doc="{sd_key}">\n{body}\n</div>')
        for g_key, g_part, g_title in GUIDE_MERGES.get(key, []):
            blk = guide_block(key, g_key, g_part, g_title, parts)
            if blk:
                subdoc_blocks.append(blk)
        subtabs = ""
        if len(eff) > 1:
            subtabs = ('<div class="subtabs" data-tab="%s">%s</div>' % (
                key, "".join(f'<button class="subtab-btn" data-tab="{key}" '
                             f'data-doc="{sdk}" onclick="show(\'{key}\',\'{sdk}\')">{sdt}</button>'
                             for sdk, _, sdt in eff)))
        section = (f'<section class="tpage" data-tab="{key}">'
                   f'<div class="tabhead"><div class="eyebrow">{label}</div>'
                   f'<p>{desc}</p></div>\n{intro}\n{subtabs}\n'
                   f'{chr(10).join(subdoc_blocks)}</section>')
        sections.append(section)

    # Guide-only tabs appended after the existing 24
    for key, label, desc, part_id, sd_title in GUIDE_TABS:
        intro = tab_intro(key, label, desc)
        blk = guide_block(key, key, part_id, sd_title, parts)
        section = (f'<section class="tpage" data-tab="{key}">'
                   f'<div class="tabhead"><div class="eyebrow">{label}</div>'
                   f'<p>{desc}</p></div>\n{intro}\n'
                   f'<div class="subtabs hidden" data-tab="{key}"></div>\n'
                   f'{blk}</section>')
        sections.append(section)

    all_sections = "\n".join(sections)
    n_tabs = len(TABS) + len(GUIDE_TABS)
    return (f'<!doctype html><html lang="zh-HK"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>AgentKit + VeADK 全部參考文檔（Tab 導覽）</title><style>\n'
            f'{CSS_COMBINED}\n{guide_extra_css}\n</style></head>'
            f'<body><div class="shell"><header class="hero">'
            f'<div class="eyebrow">BytePlus · Volcengine Agent 開發文檔</div>'
            f'<h1>AgentKit + VeADK 全部參考文檔</h1>'
            f'<p>一個 HTML 睇晒全部 reference docs：最上一行 <b>分區</b>（{len(SECTIONS)} 個）'
            f'→ 第二行 <b>主題 Tab</b>（{n_tabs} 個）→ 有需要再切<b>子頁</b>；'
            f'左側 TOC 跟住而家睇緊嘅頁。已併入《完全攻略》全部內容。</p>'
            f'<div class="toolbar"><button onclick="collapse()">Hide code</button>'
            f'<button onclick="expand()">Show code</button>'
            f'<button onclick="window.scrollTo({{top:0,behavior:\'smooth\'}})">Back to top</button>'
            f'</div></header><nav class="navwrap" id="navwrap">'
            f'<nav class="sectionbar" id="sectionbar">{sectionbar}</nav>'
            f'<nav class="topbar" id="topbar">{topbar}</nav></nav>'
            f'<div class="layout"><aside class="toc"><strong>On this page</strong>'
            f'<nav id="toc"></nav></aside><main>\n{all_sections}\n</main></div></div>'
            f'<script>{js_with_sections(JS_COMBINED)}</script></body></html>')


# ─── BUILD ─────────────────────────────────────────────────────────────────
def _guide_parts_cfg():
    """guide_parts.PARTS, imported lazily so importing build.py stays cheap.

    (validate.py and doc_map.py both import build.py just to read its config.)
    """
    sys.path.insert(0, str(BUILD))
    import guide_parts as G
    return G.PARTS


def _doc_title(p: Path) -> str:
    """First ATX H1 of a markdown file, else its stem."""
    for ln in p.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^#\s+(.*\S)\s*$", ln)
        if m:
            return m.group(1)
    return p.stem


def build_standalone():
    """One standalone page per reference document.

    Sources come from two places: the TABS subdocs, and the guide Parts. A Part
    whose source is not also a tab subdoc — Part 25's agent-control guide, for
    instance — would otherwise be the only .md without a browser-viewable .html
    sibling.
    """
    seen, count = set(), 0

    def emit(rel, title):
        if rel in seen or rel == "README.md" or rel.startswith("../"):
            return 0
        if rel.endswith(".html"):
            return 0
        seen.add(rel)
        p = REFS / rel
        if not p.exists():
            print(f"  SKIP missing {rel}", file=sys.stderr)
            return 0
        body = md_to_html(p.read_text(encoding="utf-8"))
        (p.with_suffix(".html")).write_text(
            standalone_html(title or _doc_title(p), body), encoding="utf-8")
        print(f"  ✓ {p.with_suffix('.html').name}")
        return 1

    for _, _, _, subdocs in TABS:
        for _sd_key, sd_file, sd_title in subdocs:
            count += emit(sd_file, sd_title)
    for _num, _title, _pid, sources in _guide_parts_cfg():
        for rel in sources:
            count += emit(rel, None)
    return count


def build_combined():
    out = REFS / "veadk-agentkit-all.html"
    html = combined_html()
    # Guard against a silent partial merge: if the guide exists but yielded no
    # parts, the combined view is missing every guide tab and would still look
    # "successful". Make that impossible to miss.
    if GUIDE_FILE.exists() and not guide_parts():
        print("  !! WARNING: guide file exists but no <h1> parts could be read —\n"
              "     the guide content was NOT merged into the combined view.",
              file=sys.stderr)
    out.write_text(html, encoding="utf-8")
    print(f"  ✓ {out.name}")


def main():
    args = set(sys.argv[1:])
    a = "--combined" in args
    s = "--standalone" in args
    if not a and not s:
        a = s = True
    print("Building docs...")
    if s:
        print(f"Standalone: {build_standalone()} files.")
    if a:
        build_combined()
    print("Done.")
    if a:
        print("Run python3 references/_build/validate.py to check ids/hrefs/math.")


if __name__ == "__main__":
    main()
