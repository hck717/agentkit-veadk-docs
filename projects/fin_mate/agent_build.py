"""FIN-MATE：共享 Agent 建構（veadk web 同 agentkit deploy 共用）。

組件：
- Builtin tools：web_search / web_fetch / link_reader / run_code / coding（lark 留待下階段）。
- 自建 tools：fetch_news / read_news_file / calc（純 function 自動變 VeADK tool）。
- KnowledgeBase：OpenViking（開源自架，viking:// resource，server 端自動 parse+embed）。
- Memory：STM = sqlite 持久化；LTM = OpenViking（session + 長期記憶一條龍）。
- HITL：before_tool_callback 攔截寫/副作用工具，本地 stdin 人工批准。
- Model fallback：主 seed-1-6-flash-250715 → 備 seed-1-6-flash-250615（同一 api_base）。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from veadk import Agent
from veadk.knowledgebase import KnowledgeBase
from veadk.memory import LongTermMemory, ShortTermMemory
from veadk.tools.builtin_tools.coding import coding
from veadk.tools.builtin_tools.link_reader import link_reader
from veadk.tools.builtin_tools.run_code import run_code
from veadk.tools.builtin_tools.web_fetch import web_fetch
from veadk.tools.builtin_tools.web_search import web_search

from tools.calc import calc
from tools.news_tools import fetch_news, read_news_file

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

AGENT_NAME = "fin_mate"
DESCRIPTION = "FIN-MATE：本地金融研究助理，專攻上市公司基本面、財報、分析師報告同新聞。"

INSTRUCTION = """你係 FIN-MATE，一個金融研究助理，幫用戶研究上市公司（例如 MSFT）。

## 知識來源（按優先次序）
1. **`load_knowledgebase`（本地 fin_kb，最優先）**：內含分析師報告（Deutsche Bank、Mizuho、Barclays、Wells Fargo、China Renaissance、DeMatteo 等）、業績電話會議紀錄、公司概覽（msft_overview）。**任何關於公司／股票代號／財務／業績／估值／風險／前景嘅問題，第一步一定要 call `load_knowledgebase` 攞返原文**，再基於原文回答。
2. `fetch_news`：攞近期新聞標題同情緒（例如 ticker=MSFT）。
3. `web_fetch` / `link_reader`：讀指定 URL 內容。`calc`：計數（市盈率、增長率、CAGR 等）。

## 檢索 query 寫法（好重要）
`load_knowledgebase` 係**語意檢索**，query 要具體、用英文、多關鍵字，唔好用檔名或者單一個 ticker：
- 好：`Microsoft MSFT company overview business segments Azure revenue`
- 好：`MSFT Azure cloud revenue growth margins guidance`
- 好：`Microsoft earnings call commercial bookings AI capex`
- 差：`msft_overview`、`MSFT`、`公司概覽`（會攞到免責聲明或者目錄節錄，唔係正文）
如果第一次檢索結果唔啱，**換一個更具體嘅英文 query 再試**，唔好即刻放棄。

## 規則
- **嚴禁捏造數字**（股價、EPS、營收、市盈率、目標價）。知識庫同工具冇提供嘅，直接講「本地資料未有提供」，唔好靠估或者假設。
- 回答要**引用來源**（例如「Mizuho 報告」「FY26 Q2 業績會議」「msft_overview」）。
- 開放式問題（例如「介紹 MSFT」）：先 `load_knowledgebase` 攞公司概覽＋最新業績，再 `fetch_news` 補近期動態，最後綜合。
- 某個工具失敗（例如 web_search 未配置）就跳過，改用知識庫繼續，唔好停低或者改用估算。
- 默認用繁體中文回答（用戶用其他語言就跟返）。
"""

# ---- Model fallback（同一 api_base 降級；可用 env 覆寫）----
MODEL_PRIMARY = os.getenv("MODEL_PRIMARY", "seed-1-6-flash-250715")
MODEL_BACKUP = os.getenv("MODEL_BACKUP", "seed-1-6-flash-250615")

# ---- 本地模型 override（E4 vllm-mlx／任何 OpenAI-compatible endpoint）----
# 預設 Ark；設 MODEL_LOCAL_BASE（例如 http://127.0.0.1:8203/v1）就整個轉去本地，唔使 API key。
MODEL_LOCAL_BASE = os.getenv("MODEL_LOCAL_BASE")
MODEL_LOCAL_NAME = os.getenv("MODEL_LOCAL_NAME", "fin-mate-local")
MODEL_LOCAL_API_KEY = os.getenv("MODEL_LOCAL_API_KEY", "not-needed")


def _model_kwargs() -> dict:
    """回傳 Agent 嘅 model 參數：有 MODEL_LOCAL_BASE 行本地，否則 Ark primary→backup。"""
    if MODEL_LOCAL_BASE:
        logger.info(
            "Model: local endpoint %s (model=%s)", MODEL_LOCAL_BASE, MODEL_LOCAL_NAME
        )
        return {
            "model_name": MODEL_LOCAL_NAME,
            "model_provider": "openai",
            "model_api_base": MODEL_LOCAL_BASE,
            "model_api_key": MODEL_LOCAL_API_KEY,
        }
    return {"model_name": [MODEL_PRIMARY, MODEL_BACKUP]}


_DATA_DIR = Path(__file__).resolve().parent / "data"


def _patch_openviking_hydrate() -> None:
    """Compat shim：veadk openviking backend 淨係靠 `is_leaf` 決定用 read() 定 overview()。

    OpenViking `find` 回傳嘅 resource 全部 `is_leaf=None`（就算 level=2 leaf chunk），
    搞到 veadk 永遠行 overview() → '[Directory overview is not ready]'，攞唔到正文。
    呢度 monkey-patch `_hydrate`，header 之後直接 read() 拉葉節內容。
    """
    try:
        from veadk.knowledgebase.backends.openviking_backend import (
            OpenVikingKnowledgeBackend,
        )
    except Exception:  # noqa: BLE001 - backend 未裝就 skip
        return

    original = OpenVikingKnowledgeBackend._hydrate

    def _hydrate_patched(self, uri: str, item: dict):
        if not uri:
            return str(item.get("abstract") or "")
        try:
            client = self._ensure_client()
            if item.get("is_leaf"):
                return client.read(uri, offset=0, limit=self.read_limit)
            # 即使 find 唔標 is_leaf，讀到正文就用正文；read() 失敗先 fallback overview
            try:
                return client.read(uri, offset=0, limit=self.read_limit)
            except Exception:  # noqa: BLE001
                return client.overview(uri)
        except Exception as e:  # noqa: BLE001 - hydration 失敗 fallback 去 abstract
            logger.debug(f"Failed to hydrate OpenViking resource {uri}: {e}")
            return str(item.get("abstract") or "")

    if getattr(OpenVikingKnowledgeBackend, "_finite_hydrate_patched", False):
        return
    OpenVikingKnowledgeBackend._hydrate = _hydrate_patched
    OpenVikingKnowledgeBackend._finite_hydrate_patched = True
    logger.info("Patched OpenViking KB hydration to prefer read() over overview().")


_patch_openviking_hydrate()

# ---- HITL：只攔寫/副作用工具 ----
_WRITE_TOOLS = {"run_code", "coding", "read_news_file"}
_AUTOAPPROVE = os.getenv("FIN_MATE_AUTOAPPROVE", "").strip().lower() in {
    "1",
    "true",
    "yes",
}

# ---- D7 安全層 hooks（role gate 先行，blocked 唔會入 HITL）----
from security.hooks import (  # noqa: E402
    _last_user_text,
    input_injection_filter,
    output_pii_filter,
    role_tool_gate,
)


def human_gate(tool, args, tool_context) -> dict | None:
    """before_tool_callback：對寫/副作用工具做人工審批。

    返回 None 代表放行（真正執行 tool）；返回 dict 代表取代 tool 結果
    （tool 唔執行）。所有只讀工具自動放行。
    """
    if tool.name not in _WRITE_TOOLS:
        return None
    if _AUTOAPPROVE:
        return None
    print(f"\n⚠️  HITL 審批：{tool.name}({args})")
    ans = input("批准執行 (y/N)? ").strip().lower()
    if ans == "y":
        return None
    return {"result": "USER_REJECTED", "reason": "人工拒絕執行", "tool": tool.name}


def tool_security_gate(tool, args, tool_context) -> dict | None:
    """before_tool_callback（chain 1）：D7 role allowlist 執法。"""
    return role_tool_gate(tool, args, tool_context)


class JevToolDecider:
    """真 JEV System One step decider（opt-in by env `FIN_MATE_JEV=1`）。

    `before_model_callback`：當最新 content 係用戶提出新 request（冇 pending
    tool result）時，用 System One 決定「下一步要揀邊個 tool」，並由
    `jev/actions` 確定式填 args —— 短回路直接出 tool call，System Two 唔使
    generation。每次決策 1–3 token + logprobs（零 prose generation）。

    唔會短回路嘅情況（全部 escalates 返去正常 LLM 流程）：
      - 唔係新 user turn（例如緊跟 tool result 嘅 chain / 總結）→ System Two 睇齊
      - System One 低 confidence（< TOOL_CONF_MIN）或 failed
      - 揀到「N：唔使工具，直接答」
      - 揀到嘅 tool 用確定式 args 填唔到（例如要自由格式查詢）
    """

    def __init__(self, conf_min: float | None = None) -> None:
        self._conf_min = conf_min
        self._n = 0

    async def __call__(self, callback_context, llm_request) -> Optional[LlmResponse]:
        from google.adk.models.llm_response import LlmResponse
        from google.genai import types

        contents = getattr(llm_request, "contents", None) or []
        if not contents or getattr(contents[-1], "role", "") != "user":
            return None
        text = _last_user_text(llm_request)
        if not text:
            return None
        from jev import actions
        from jev import decisions as D
        from jev import policy
        from jev.gate import decide_choice

        d = await decide_choice(
            D.tool_state(text),
            "用戶要求下一步係咩？",
            actions.LIVE_TOOLS,
            gate="live_decide",
            conf_min=self._conf_min if self._conf_min is not None else policy.TOOL_CONF_MIN,
        )
        if d.escalated or d.choice is None:
            return None
        tool = actions.LIVE_TOOL_BY_ID.get(d.choice)
        if tool is None or tool == "none":
            return None
        args = actions.fill_args(tool, text)
        if args is None:
            return None
        self._n += 1
        logger.info("JEV decider 短回路 → %s(%s) conf=%.3f", tool, args, d.confidence)
        part = types.Part(function_call=types.FunctionCall(name=tool, args=args))
        return LlmResponse(content=types.Content(role="model", parts=[part]), turn_complete=True)


def _jev_enabled() -> bool:
    return os.getenv("FIN_MATE_JEV", "").strip().lower() in {"1", "true", "yes"}


def attach_decision_gate(agent) -> None:
    """live agent 掛一粒真 JEV System One step decider（opt-in by env FIN_MATE_JEV=1）。"""
    if not _jev_enabled():
        return agent
    existing = agent.before_model_callback or []
    if callable(existing):
        existing = [existing]
    agent.before_model_callback = [*existing, JevToolDecider()]
    logger.info("JEV System One step decider 已掛（before_model_callback；FIN_MATE_JEV=1）")
    return agent


def _openviking_has_data(index: str = "fin_kb") -> bool:
    """OpenViking resources 目錄已有資源就唔再 add（避免重複塞 data）。

    用 SDK list_tasks 檢查該 index 冇 running add_resource 而且有 completed，
    就當已 seed。
    """
    try:
        from openviking_sdk import SyncHTTPClient

        client = SyncHTTPClient(
            url=os.getenv("DATABASE_OPENVIKING_URL") or "http://localhost:1933",
            api_key=os.getenv("DATABASE_OPENVIKING_API_KEY"),
            timeout=15,
        )
        client.initialize()
        try:
            tasks = client.list_tasks(limit=100)
        finally:
            client.close()
        return any(
            t.get("task_type") == "add_resource"
            and index in (t.get("resource_id") or "")
            and t.get("status") == "completed"
            for t in tasks
        )
    except Exception:  # noqa: BLE001 - check 失敗時唔好 blocking，照 add
        return False


def _build_local_otlp_tracer():
    """本地 OTel trace（Jaeger/collector）。

    只喺 OTLP endpoint 可達先掛 tracer，否則照舊行（graceful degrade）。
    Env: OBSERVABILITY_OTLP_ENDPOINT（例如 http://localhost:4318/v1/traces）。
    """
    endpoint = os.getenv(
        "OBSERVABILITY_OTLP_ENDPOINT", "http://localhost:4318/v1/traces"
    ).strip()
    if not endpoint:
        return None
    try:
        from veadk.tracing.telemetry.exporters.base_exporter import BaseExporter
        from veadk.tracing.telemetry.opentelemetry_tracer import OpentelemetryTracer
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        class LocalOtlpExporter(BaseExporter):
            """把 veadk span 用標準 OTLP (HTTP) 送出到本地 collector（Jaeger）。"""

            resource_attributes: dict = {"service.name": AGENT_NAME}

            def model_post_init(self, context) -> None:
                self._exporter = OTLPSpanExporter(endpoint=endpoint, timeout=10)
                self.processor = BatchSpanProcessor(self._exporter)
                logger.info(f"LocalOtlpExporter -> {endpoint}")

            def export(self) -> None:
                if self._exporter:
                    self._exporter.force_flush()

        return OpentelemetryTracer(exporters=[LocalOtlpExporter()])
    except Exception as exc:  # noqa: BLE001 - 觀察後端未就緒時唔好阻 agent 起
        logger.warning("OTLP tracer 唔可用 (%s); agent 照常 (冇 tracing)。", exc)
        return None


def build_knowledgebase() -> KnowledgeBase:
    """KnowledgeBase：OpenViking（開源自架，viking:// resource，server 端 parse+embed）。

    KB 資料喺 data/kb（含 msft_txt/ 子目錄）。已 seed 過（有 completed add_resource）
    就 skip，避免每次重啟重複 insert。
    """
    kb_root = _DATA_DIR / "kb"
    source_paths = sorted({kb_root, *(p for p in kb_root.rglob("*") if p.is_dir())})

    try:
        kb = KnowledgeBase(backend="openviking", index="fin_kb", top_k=5)
        if not _openviking_has_data(index="fin_kb"):
            for p in source_paths:
                kb.add_from_directory(str(p))
            logger.info("KnowledgeBase backend: openviking (self-hosted) — seeded")
        else:
            logger.info("KnowledgeBase backend: openviking (self-hosted) — already seeded, skip add")
        return kb
    except Exception as exc:  # noqa: BLE001 - config 未齊/服務未通時降級
        logger.warning("No working KB backend (%s); agent will run without knowledgebase.", exc)
        return None


def build_agent() -> Agent:
    """建構 FIN-MATE agent（`veadk web` 同 agentkit deploy 共用）。"""
    kb = build_knowledgebase()

    stm = ShortTermMemory(
        backend="sqlite",
        local_database_path=str(_DATA_DIR / "stores" / "fin_mate.db"),
    )
    ltm = LongTermMemory(backend="openviking")

    tools = [
        web_search,
        web_fetch,
        link_reader,
        run_code,
        coding,
        fetch_news,
        read_news_file,
        calc,
        # lark: 留待下階段（需 Lark MCP server config），依家唔掛
    ]

    tracers = []
    _otlp = _build_local_otlp_tracer()
    if _otlp is not None:
        tracers.append(_otlp)

    return Agent(
        name=AGENT_NAME,
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        tools=tools,
        knowledgebase=kb,
        short_term_memory=stm,
        long_term_memory=ltm,
        auto_save_session=True,
        **_model_kwargs(),
        before_model_callback=input_injection_filter,
        after_model_callback=output_pii_filter,
        before_tool_callback=[tool_security_gate, human_gate],
        tracers=tracers or None,
    )
    return attach_decision_gate(agent)