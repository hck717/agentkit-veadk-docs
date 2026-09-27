#!/usr/bin/env python3
"""Single source of truth for the comprehensive guide's Part structure.

Both the .md twin (sync_guide_md.py) and the HTML guide
(splice_tabs_into_guide.py, group_guide.py) import this, so the two can never
disagree about which Parts exist, what they are called, or which section they
belong to.

Parts 0–9 are the handcrafted original guide and are never regenerated.
Parts 10+ are assembled here from source documents; a Part may draw on more
than one source (that is how the overlapping topics were merged).
"""
from __future__ import annotations

# Parts 0–9 already exist in the guide and are left untouched.
ORIGINAL_PARTS = 10

# Their ids as they appear in the handcrafted guide (not regenerated here).
ORIGINAL_IDS = {
    0: "part0",
    1: "part1-modelark",
    2: "part2-agentkit",
    3: "part3-veadk",
    4: "part4-sdk",
    5: "part5-cli",
    6: "part6-tutorial",
    7: "part7-viking",
    8: "part8-arkclaw",
    9: "part9-appendix",
}

# (part number, h1 title, part id, [source files relative to references/])
#   - "../README.md" resolves against the repo root
#   - "intros/*.html" are HTML fragments, converted with pandoc
# A Part with several sources concatenates them, each source's own `#` title
# becoming an `##` sub-section inside the Part.
PARTS = [
    (10, "Part 10 — 總覽 Overview", "part10-overview",
     ["../README.md"]),
    (11, "Part 11 — AI 概念百科 AI Concepts", "part11-concepts",
     ["veadk-agentkit-ai-concepts.md"]),
    (12, "Part 12 — 工具 / 能力 Tools & Capabilities", "part12-tools",
     ["veadk-agentkit-tools-capabilities.md"]),

    # ── merged: 記憶 / 知識庫 / 資料庫 / 上下文 ──────────────────────────
    (13, "Part 13 — 記憶 · 知識庫 · 資料庫 · 上下文 Memory, Vector DB & Context",
     "part13-memory",
     ["veadk-agentkit-vector-cache.md",
      "veadk-agentkit-database-management.md",
      "veadk-agentkit-memory-context.md"]),

    (14, "Part 14 — RAG 全攻略 RAG Playbook", "part14-rag",
     ["veadk-agentkit-rag-guide.md"]),
    (15, "Part 15 — Cache 管理 Cache Management", "part15-cache",
     ["veadk-agentkit-cache-management.md"]),

    # ── merged: 計價 + 跨廠商成本對照 ──────────────────────────────────
    (16, "Part 16 — 計價 + 跨廠商成本對照 Pricing & Vendor Cost",
     "part16-cost",
     ["veadk-agentkit-pricing.md",
      "veadk-vendor-cost-comparison.md"]),

    # ── merged: 優化 + 評估（master survey first, then the deep dives）──
    (17, "Part 17 — 優化 + 評估 完全指南 Optimization & Evaluation",
     "part17-optimize-eval",
     ["veadk-agentkit-optimization-evaluation-guide.md",
      "veadk-agentkit-finetune-optimize.md",
      "veadk-agentkit-training-kit.md",
      "veadk-agentkit-evaluation.md",
      "veadk-agentkit-performance.md"]),

    # ── merged: 推理基建（硬體 + ServingKit）───────────────────────────
    (18, "Part 18 — 推理基建：硬體 + ServingKit Hardware & Inference Serving",
     "part18-infra",
     ["veadk-agentkit-hardware.md",
      "veadk-agentkit-serving-kit.md"]),

    (19, "Part 19 — 閘道 / 網關 Gateway", "part19-gateway",
     ["veadk-agentkit-gateway.md"]),
    (20, "Part 20 — 安全 / 可觀測 Security & Observability", "part20-security",
     ["veadk-agentkit-rbac-observability.md"]),
    (21, "Part 21 — 獨特賣點 Unique Value", "part21-uniq",
     ["veadk-agentkit-uniqueness.md"]),

    # ── merged: 生成模型家族（Seedream + Seedance）────────────────────
    (22, "Part 22 — 生成模型家族：Seedream + Seedance Generative Model Families",
     "part22-genmedia",
     ["veadk-agentkit-seedream.md",
      "veadk-agentkit-seedance.md"]),

    (23, "Part 23 — LLM 架構 · 端到端 LLM Architecture", "part23-arch",
     ["intros/arch.html"]),
    (24, "Part 24 — 實用連結 Useful Links", "part24-links",
     ["intros/links.html"]),

    # ── Agent 管控：規則 / 護欄 / 白名單黑名單 / 分層限制 ────────────────
    (25, "Part 25 — Agent 管控：規則 · 護欄 · 白名單 / 黑名單 · 分層限制 "
         "Agent Control & Restrictions",
     "part25-control",
     ["veadk-agentkit-agent-control-rules.md"]),
]

# (section key, label, [part numbers]) — drives the HTML section row, the Part
# card grid, the floating nav and the .md table of contents.
SECTIONS = [
    ("orient", "定向 Orient", [0, 10, 11, 21, 23, 24]),
    ("build", "起手 Build", [1, 2, 3, 4, 5, 6]),
    ("cap", "能力 Capabilities", [7, 12, 13, 14, 15]),
    ("better", "變強 Make Better", [17]),
    ("cost", "錢 Cost", [16]),
    ("infra", "底層 + 安全 Infra & Safety", [8, 18, 19, 20, 25]),
    ("seed", "自家模型 Seed Models", [22]),
    ("appx", "附錄 Appendix", [9]),
]

TOTAL_PARTS = ORIGINAL_PARTS + len(PARTS)


def part_by_num(num: int):
    for p in PARTS:
        if p[0] == num:
            return p
    return None


def part_id(num: int) -> str:
    """id for any part number, original (0–9) or generated (10+)."""
    if num in ORIGINAL_IDS:
        return ORIGINAL_IDS[num]
    p = part_by_num(num)
    if p is None:
        raise SystemExit(f"ABORT: unknown part number {num}")
    return p[2]


def sections_js() -> str:
    """SECTIONS as a JS array literal (for the guide's own script)."""
    rows = []
    for key, label, nums in SECTIONS:
        ids = ",".join(f'"{part_id(n)}"' for n in nums)
        rows.append(f'["{key}","{label}",[{ids}]]')
    return "[" + ",".join(rows) + "]"


def sanity_check() -> None:
    """Fail loudly if the tables are inconsistent."""
    nums = [p[0] for p in PARTS]
    if nums != sorted(nums):
        raise SystemExit("ABORT: PARTS must be in ascending part-number order")
    if len(set(nums)) != len(nums):
        raise SystemExit("ABORT: duplicate part numbers in PARTS")
    ids = [p[2] for p in PARTS]
    if len(set(ids)) != len(ids):
        raise SystemExit("ABORT: duplicate part ids in PARTS")
    if nums and nums[0] != ORIGINAL_PARTS:
        raise SystemExit(f"ABORT: PARTS must start at {ORIGINAL_PARTS}, got {nums[0]}")
    if nums and nums[-1] != TOTAL_PARTS - 1:
        raise SystemExit(f"ABORT: PARTS must end at {TOTAL_PARTS - 1}, got {nums[-1]}")

    mapped = [n for _k, _l, ns in SECTIONS for n in ns]
    if sorted(mapped) != sorted(range(TOTAL_PARTS)):
        missing = sorted(set(range(TOTAL_PARTS)) - set(mapped))
        extra = sorted(set(mapped) - set(range(TOTAL_PARTS)))
        dupes = sorted({n for n in mapped if mapped.count(n) > 1})
        raise SystemExit(f"ABORT: SECTIONS must cover every part exactly once\n"
                         f"  missing={missing} extra={extra} dupes={dupes}")
    for p in PARTS:
        if not p[3]:
            raise SystemExit(f"ABORT: part {p[0]} has no source")


sanity_check()
