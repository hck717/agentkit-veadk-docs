"""FIN-MATE D7 安全層：規則式 input/output filter。

純 function、deterministic、零 LLM 依賴，方便 red-team 做精確攔截率測試。
三個偵測器（回傳命中清單）+ 兩個 redactor（輸出清洗）：

  detect_injection(text)  -> prompt injection family 命中
  detect_pii(text)        -> 個人資料（email / 電話 / HKID / 信用咭……）
  detect_sensitive(text)  -> 敏感資料 / secret（api key / token / .env 眼……）

所有規則都係 `(family, name, compiled_regex)`；命中帶 snippet。
redact_pii / redact_sensitive 分別做 masking（■）。
"""
from __future__ import annotations

import re
from typing import Iterator

REDACT = "■"

# ─── Prompt injection 規則（family 對應 red-team 分類 ─────────────────────────
_INJ = [
    # ignore_instructions：要求忽略／拋棄 system prompt
    ("ignore_instructions", "ignore_all_prev", re.compile(r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|messages|rules)", re.I)),
    ("ignore_instructions", "ignore_zh", re.compile(r"忽略[所有之前以上先前過去]{0,4}(的)?(指令|指示|提示|規則|設定)|唔好[之前以上先前再]{0,3}(嘅)?(指令|指示|提示|規則|設定)")),
    ("ignore_instructions", "ignore_zh_prompt", re.compile(r"唔(?:好|使|要|再|使){0,2}(?:理|聽|答|理會)\s*?(?:system prompt|系統提示|內部設定|系統設定)", re.I)),
    ("ignore_instructions", "ignore_zh_setting", re.compile(r"(?:唔(?:好|使|要|再){0,2}|不(?:要|再|用|必))(?:理|聽|管|答)[之前以上先前]{0,3}(?:嘅|的)?(?:system prompt|系統提示|指令|指示|提示|規則|設定)", re.I)),
    ("ignore_instructions", "forget_rules", re.compile(r"forget\s+(all\s+)?(your\s+)?(rules|instructions|guidelines|prompt)|當冇(嘢|指令)發生過", re.I)),
    ("ignore_instructions", "do_anything", re.compile(r"now\s+(you\s+can\s+)?do\s+anything|you\s+have\s+no\s+(rules|limits|restrictions)\s+now|with\s+no\s+(rules|limits|restrictions|boundaries|guardrails)", re.I)),
    # system_override：嘗試改寫 system prompt / 角色
    ("system_override", "system_prompt_leak", re.compile(r"(reveal|show|print|dump|output|display|重複|複製|寫出|列印|冧出|輸出)\s+[^.\n]{0,30}?(system\s+)?(prompt|instructions?|指令|提示詞|system prompt|system 設定|內部(設定|內容))", re.I)),
    ("system_override", "repeat_above", re.compile(r"repeat\s+(everything|all|the)\s+(above|preceding|previous|above,?).{0,40}(instructions?|prompts?|messages|設定|指令|提示)", re.I)),
    ("system_override", "hidden_leak", re.compile(r"(hidden|internal|隱藏|內部)\s+(system\s+)?(instructions?|prompt|設定|指令|提示|內容)", re.I)),
    ("system_override", "exact_content", re.compile(r"(print|show|display|output|dump|reveal|列出|顯示|話俾我)\s+.{0,18}(exact|full|entire|complete|全部|完整|所有)\s+.{0,20}(instructions?|system\s+settings|設定|指令|內容|system prompt)", re.I)),
    ("system_override", "new_system", re.compile(r"(act\s+)?as\s+(the\s+)?system|你(而家|而係|嘅)\s*system|模擬\s*system|override\s+(the\s+)?system", re.I)),
    ("system_override", "role_switch", re.compile(r"你(而家|就)係(一個|個)?(admin|管理員|system|superuser|god)|pretend\s+(you\s+are|to\s+be)\s+(admin|system|god)", re.I)),
    # data_exfil：要 model 輸出內部資料／指示
    ("data_exfil", "dump_memory", re.compile(r"(dump|export|display|print|show)\s+(all|your|the|entire)\s+(memory|context|training|knowledge|logs|transcripts)|(全部|所有|完整).{0,6}(記憶|上下文|記錄|對話|日誌)", re.I)),
    ("data_exfil", "leak_instructions", re.compile(r"第一句話|第一句就|開頭就|sentence\s+(one|once)|first\s+word", re.I)),
    ("data_exfil", "exfil_url", re.compile(r"(?:send|post|upload|export|push|外發|上傳|發送|傳送|POST|導出|匯出|轉發)[\s\S]{0,48}?https?://", re.I)),
    ("data_exfil", "zh_send_data", re.compile(r"(?:把|將)(?:成個|所有|全部|我哋|呢啲|呢)?(?:對話|內容|資料|數據|記錄|訊息|日誌).{0,12}(?:上傳|發送|POST|傳去|傳俾|匯出|導出)", re.I)),
    # dev_mode：聲稱開發／測試以便越權
    ("dev_mode", "dev_assist", re.compile(r"dev\s+mode|測試(模式|用)|開發(模式|環境|版)|debug\s+mode|simulation\s+mode", re.I)),
    ("dev_mode", "dev_mode_assert", re.compile(r"(dev(?:eloper)?|admin|god)\s*-?\s*(mode|模式)|DAN\b|jailbreak|開發(者)?[ -]?模式|調試|除錯(?:模式|用)|debug\s*(?:mode|模式)", re.I)),
    # secrets_extract：誘導輸出密鑰／密碼
    ("secrets_extract", "env_leak", re.compile(r"(read|show|查看|讀取|輸出|打開).{0,8}(\.env|環境變數|env\b|api\s*key|api 密鑰|密碼|password|secret|token)", re.I)),
    ("secrets_extract", "cred_request", re.compile(r"(give|provide|send|tell)\s+(me\s+)?(your\s+)?(api|access|secret|token|password|credentials)|(俾|畀|比)(我)?(你)?(個|嘅)?(api|密匙|密碼|token)", re.I)),
    # role_jailbreak：聲稱有更高權限／話唔使理權限
    ("role_jailbreak", "bypass_auth", re.compile(r"bypass|越權|繞過|skip\s+(auth|authorization|permission|check)|唔使(檢查|權限|認證)|冇(權限|限制)+好過|as\s+(admin|root|owner)", re.I)),
    ("role_jailbreak", "force_comply", re.compile(r"you\s+(must|have\s+to|can{1,2}t\s+refuse)\b[\s\S]{0,40}(do it|answer|comply|照做|答)", re.I)),
    ("role_jailbreak", "threat", re.compile(r"or\s+(else|i\s+will)\b|否則|唔係就|否則我會", re.I)),
    ("role_jailbreak", "no_restrictions", re.compile(r"(?:with|and|have|has|are)\s+no\s+(?:rules|restrictions|limits|boundaries|constraints|guardrails)|no\s+(?:restrictions|limits|boundaries)|冇任何限制|無任何限制|沒有限制|沒有(?:任何|所有)?(?:限制|規則|約束)|冇(?:限制|約束|規矩)", re.I)),
    ("role_jailbreak", "zh_impersonate", re.compile(r"化身(?:為|成|做)|成為.{0,5}?(?:另一個|新|全能|全知)?(?:assistant|助手|agent)|以(?:為|作)(?:另一個|全知|全能)?(?:assistant|助手)|由而家起", re.I)),
]

# ─── PII 規則 ──────────────────────────────────────────────
_PII = [
    ("email", "email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("phone_hk", "hk_mobile", re.compile(r"(?<!\d)(?:\+?852[\s-]?)?[23569]\d{3}[\s-]?\d{4}(?!\d)")),
    ("hkid", "hkid", re.compile(r"[A-Za-z]\d{6}(?:\(\d\)|(?!\d))")),
    ("credit_card", "cc_major", re.compile(r"(?<!\d)(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6(?:011|5\d{2}))[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3,5}(?!\d)")),
    ("passport", "passport", re.compile(r"\b(?:P\d{7}|[EK][A-Z]?\d{8})\b")),
]


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = ord(ch) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0 and len(digits) >= 13


def detect_injection(text: str) -> list[dict]:
    hits = []
    for family, name, rx in _INJ:
        for m in rx.finditer(text or ""):
            s = m.group(0).strip()
            hits.append({"family": family, "rule": name, "snippet": s[:80]})
    return hits


def detect_pii(text: str) -> list[dict]:
    hits = []
    for kind, name, rx in _PII:
        for m in rx.finditer(text or ""):
            raw = m.group(0).strip()
            if kind == "credit_card" and not _luhn_ok(re.sub(r"\D", "", raw)):
                continue
            if kind == "hkid" and not re.match(r"[A-Za-z]\d{6}\(\d\)", raw):
                # 已 capture 但太鬆（例：電話撞樣）——用 cellphone 先排除
                if re.fullmatch(r"[1-9]\d{7}", raw):
                    continue
            hits.append({"family": kind, "rule": name, "snippet": raw[:40]})
    return hits


# ─── 敏感資料 / secret 規則 ──────────────────────────────
_SEC = [
    ("secret", "ark_key", re.compile(r"\b[A-Za-z0-9]{6,10}-[A-Za-z0-9]{20,}\b")),
    ("secret", "sk_prefix", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b", re.I)),
    ("secret", "aws_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("secret", "google_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}\b")),
    ("secret", "gh_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", re.I)),
    ("secret", "bearer", re.compile(r"\bBearer\s+[A-Za-z0-9._~+\-/=]{16,}", re.I)),
    ("secret", "private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("secret", "password_like", re.compile(r"(?i)(password|passwd|pwd|secret|api[_-]?key|access[_-]?token|openviking[_-]?key)\s*[=:]\s*[^\s,;\"']{6,}")),
    ("secret", "jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
]


def detect_sensitive(text: str) -> list[dict]:
    hits = []
    for family, name, rx in _SEC:
        for m in rx.finditer(text or ""):
            hits.append({"family": family, "rule": name, "snippet": (m.group(0)[:40] + "…") if len(m.group(0)) > 40 else m.group(0)})
    return hits


def scan(text: str) -> dict:
    """一次過偵測；回傳分 family 聚合，方便 red-team 對錶。"""
    inj, pii, sec = detect_injection(text), detect_pii(text), detect_sensitive(text)
    by_family: dict[str, list[str]] = {}
    for h in inj + pii + sec:
        by_family.setdefault(h["family"], []).append(h["rule"])
    return {"injection": inj, "pii": pii, "sensitive": sec, "by_family": by_family,
            "blocked": bool(inj or pii or sec)}


def _mask(match: re.Match) -> str:
    return REDACT * len(match.group(0))


def redact_pii(text: str) -> tuple[str, int]:
    out, n = text, 0
    for kind, name, rx in _PII:
        if kind == "credit_card":
            def repl(m):
                digits = re.sub(r"\D", "", m.group(0))
                return m.group(0) if not _luhn_ok(digits) else REDACT * len(m.group(0))
            out2 = rx.sub(repl, out)
        else:
            out2 = rx.sub(_mask, out)
        n += len(rx.findall(out))  # 命中數（mask 前計）
        out = out2
    return out, n


def redact_sensitive(text: str) -> tuple[str, int]:
    out, n = text, 0
    for family, name, rx in _SEC:
        out2 = rx.sub(_mask, out)
        n += len(rx.findall(out))
        out = out2
    return out, n


def redact(text: str) -> tuple[str, dict]:
    """輸出清洗：先 mask secret 再 mask PII。回傳 (clean, stats{removed})。"""
    a, na = redact_sensitive(text)
    b, nb = redact_pii(a)
    return b, {"pii": nb, "sensitive": na, "total": na + nb}


def iter_rules(kind: str) -> Iterator[tuple[str, str, re.Pattern]]:
    tbl = {"injection": _INJ, "pii": _PII, "sensitive": _SEC}[kind]
    yield from tbl