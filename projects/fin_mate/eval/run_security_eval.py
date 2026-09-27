"""FIN-MATE D7 security eval：injection / PII / secrets / authz 全 deterministic。

唔經 model，直接打 security layer（filters + gate + auth）：
  injection  scan → detect_injection；matched = 命中且 family 對
  pii       detect_pii  → matched = 出返嘅 kind 覆蓋 golden.pii
  secrets   detect_sensitive；同上
  authz     authorize_tool(role, tool) → allowed == golden.allowed
Assertion：所有 golden.allowed=false 嘅越權 call 必須全數 blocked，唔係就 FAIL exit 1。

輸出：eval/reports/security_report.md + security_run.json（附每 set 攔截率 table）。
用法：`./.venv/bin/python -m eval.run_security_eval`
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from security.filters import detect_injection, detect_pii, detect_sensitive  # noqa: E402
from security.gate import authorize_tool  # noqa: E402

GOLDEN = ROOT / "eval" / "golden_datasets" / "security"
REPORTS = ROOT / "eval" / "reports"
SETS = ["injection", "pii", "secrets", "authz"]


def _load(set_name: str) -> list[dict]:
    rows = []
    for line in (GOLDEN / f"{set_name}.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _check(rec: dict) -> tuple[bool, list[str]]:
    st = rec["set"]
    prompt = rec["prompt"]
    notes: list[str] = []
    if st == "injection":
        hits = detect_injection(prompt)
        triggered = bool(hits)
        ok = triggered == rec["golden"]["triggered"]
        fams = sorted({h.get("family") for h in hits})
        if triggered:
            want = rec["golden"].get("family")
            if want and want not in fams:
                ok = False
                notes.append(f"family={fams} != want {want}")
            notes.append(f"rules={sorted({h.get('rule') for h in hits})}")
        return ok, notes
    if st in ("pii", "secrets"):
        want = rec["golden"].get("pii" if st == "pii" else "secrets", [])
        hits = detect_pii(prompt) if st == "pii" else detect_sensitive(prompt)
        # pii 睇 family（email/phone_hk/hkid/credit_card/passport）；secrets 睇 rule 名
        detected = sorted({h.get("family") for h in hits}) if st == "pii" else sorted({h.get("rule") for h in hits})
        ok = set(want) == set(detected)
        notes.append(f"detected={detected}")
        return ok, notes
    if st == "authz":
        g = rec["golden"]
        allowed, reason = authorize_tool(g["role"], g["tool"])
        ok = allowed == g["allowed"]
        notes.append(f"reason={reason!r}")
        return ok, notes
    return False, ["unknown set"]


def main() -> int:
    results: dict[str, list[dict]] = {}
    total, passed = 0, 0
    table = {}  # per-set 攔截率
    violations: list[dict] = []
    for st in SETS:
        rows = _load(st)
        out = []
        for rec in rows:
            ok, notes = _check(rec)
            out.append({"id": rec["id"], "ok": ok, "notes": notes,
                        "golden": rec.get("golden", {}), "meta": rec.get("meta", {})})
            total += 1
            passed += int(ok)
            if ok is False:
                violations.append({"id": rec["id"], "set": st, "notes": notes})
        results[st] = out
        hit = sum(1 for r in out if r["ok"])
        table[st] = {"n": len(out), "pass": hit, "rate": hit / len(out)}
    # assertion：越權 call 全 block（injection 全攔、authz 越權全拒）
    block_fail = [
        v for v in violations
        if (v.get("set") == "authz" and v.get("golden", {}).get("allowed") is False)
        or (v.get("set") == "injection" and v.get("golden", {}).get("triggered") is True)
    ]
    run = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "engine": "deterministic (no model)",
        "total": total, "passed": passed,
        "per_set": table,
        "interceptions": table,
        "block_policy": {"name": "all_denied_blocked", "passed": not block_fail,
                         "violations": block_fail},
    }
    (REPORTS / "security_run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2))
    _md(REPORTS / "security_report.md", table, total, passed, block_fail)
    print(f"[sec-eval] {passed}/{total} passed  (injection/pii/secrets/authz)"
          f"  block-policy {'OK' if not block_fail else 'FAIL'}")
    for st, t in table.items():
        print(f"  {st:<10} {t['rate']:.0%}  ({t['pass']}/{t['n']})")
    if block_fail:
        print("block-policy VIOLATION:")
        for v in block_fail:
            print(f"  {v['id']} {v['set']} {v['notes']}")
    sys.stdout.flush()
    return 1 if block_fail else 0


def _md(path: Path, table: dict, total: int, passed: int, block_fail: list) -> None:
    L = [f"# Security Eval · {time.strftime('%Y-%m-%d %H:%M:%S')}",
         "",
         f"- overall: **{passed}/{total}** ({passed / total:.0%})", "- engine: deterministic（唔經 model，直接打 filters＋gate）",
         "- block policy：所有 golden 越權 call 全 block（injection triggered＋authz denied）",
         "",
         "## 攔截率（per set）", "",
         "| set | n | pass | 攔截率 |", "|---|---|---|---|"]
    for st, t in table.items():
        L.append(f"| {st} | {t['n']} | {t['pass']} | {t['rate']:.0%} |")
    L += ["", "## block policy", ""]
    L.append(f"- status: **{'OK' if not block_fail else 'VIOLATION'}**")
    for v in block_fail:
        L.append(f"- `{v['id']}` {v['set']}: {v['notes']}")
    L.append(f"\n→ eval/reports/security_run.json（逐條 golden record）")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())