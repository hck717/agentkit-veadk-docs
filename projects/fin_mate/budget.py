#!/usr/bin/env python3
"""FIN-MATE budget.py -- 一跑即睇 BytePlus 全項目用量/費用 + 預期定價

執行：
    .venv/bin/python budget.py                 # 本月，實時查 BytePlus 帳單
    .venv/bin/python budget.py --period 2026-08
    .venv/bin/python budget.py --tokens-in 200000 --tokens-out 50000   # 加模型費用估算
    .venv/bin/python budget.py --dry-run        # 唔連網，淨係睇預期定價 + 檢查 .env

所需 API keys（放 .env，見檔內註）：
    BYTEPLUS_ACCESS_KEY / BYTEPLUS_SECRET_KEY   # BytePlus 平台（IAM 攞）
    MODEL_AGENT_API_KEY                          # ModelArk（選填，用黎做估算對比）

用得嘅係 BytePlus Billing OpenAPI：
    Action=ListBillOverviewByProd  Version=2022-01-01  Host=billing.byteplusapi.com
    signature = HMAC-SHA256（BytePlus OpenAPI 簽名）
"""

import argparse
import datetime
import hashlib
import hmac
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(HERE, ".env")

SERVICE = "billing"
HOST_CANDIDATES = ["billing.byteplusapi.com", "billing.bytepluses.com"]
REGION_CANDIDATES = ["ap-singapore-1", "ap-southeast-1"]

# ----------------------------------------------------------------------------
# env loader（鍾意輕量就唔靠 python-dotenv）
# ----------------------------------------------------------------------------
def load_env_file(path=ENV_FILE, log_fn=print):
    if not os.path.isfile(path):
        return {}
    env = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip("'\"")
    return env


def get_secret(name, env_dict):
    val = os.environ.get(name) or env_dict.get(name, "")
    return val.strip()


# ----------------------------------------------------------------------------
# BytePlus OpenAPI 簽名（HMAC-SHA256，跟官方 docs「Calculating a signature」）
# ----------------------------------------------------------------------------
URLENCODE_SAFE = "-_.~"


def enc(s):
    return urllib.parse.quote(str(s), safe=URLENCODE_SAFE)


def hmac_sha256(key, msg):
    return hmac.new(key, msg, hashlib.sha256).digest()


def build_canonical_query(params):
    return "&".join(f"{enc(k)}={enc(v)}" for k, v in sorted(params.items()))


def sign_request(ak, sk, method, host, path, query_params, region):
    now = datetime.datetime.now(datetime.timezone.utc)
    x_date = now.strftime("%Y%m%dT%H%M%SZ")
    short_date = x_date[:8]
    payload = ""
    x_content_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    canonical_uri = path or "/"
    canonical_query = build_canonical_query(query_params)
    canonical_headers = (
        "content-type:application/x-www-form-urlencoded; charset=utf-8\n"
        f"host:{host}\n"
        f"x-content-sha256:{x_content_sha256}\n"
        f"x-date:{x_date}\n"
    )
    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_request = "\n".join(
        [method.upper(), canonical_uri, canonical_query, canonical_headers,
         signed_headers, x_content_sha256]
    )
    hashed = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    credential_scope = f"{short_date}/{region}/{SERVICE}/request"
    string_to_sign = "\n".join(["HMAC-SHA256", x_date, credential_scope, hashed])
    k_date = hmac_sha256(sk.encode("utf-8"), short_date.encode("utf-8"))
    k_region = hmac_sha256(k_date, region.encode("utf-8"))
    k_service = hmac_sha256(k_region, SERVICE.encode("utf-8"))
    signing_key = hmac_sha256(k_service, b"request")
    signature = hmac_sha256(signing_key, string_to_sign.encode("utf-8")).hex()
    authorization = (
        f"HMAC-SHA256 Credential={ak}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return x_date, x_content_sha256, authorization


def fetch_bill_overview(ak, sk, period, limit, offset, host, region):
    params = {
        "Action": "ListBillOverviewByProd",
        "Version": "2022-01-01",
        "BillPeriod": period,
        "Limit": str(limit),
        "Offset": str(offset),
        "NeedRecordNum": "1",
        "IgnoreZero": "1",
    }
    x_date, x_sha, auth = sign_request(
        ak, sk, "GET", host, "/", params, region
    )
    url = f"https://{host}/?{build_canonical_query(params)}"
    req = urllib.request.Request(url, method="GET", headers={
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "Host": host,
        "X-Date": x_date,
        "X-Content-Sha256": x_sha,
        "Authorization": auth,
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_bills(payload):
    result = (payload or {}).get("Response", {}).get("Result", {})
    return result.get("List", []) or []


def bill_error(payload):
    meta = (payload or {}).get("ResponseMetadata", {}) or {}
    err = meta.get("Error") or {}
    return err.get("Code", ""), err.get("Message", "")


# ----------------------------------------------------------------------------
# 預期定價（本地 research 價，最後以 BytePlus console 實價為準）
# ----------------------------------------------------------------------------
RMBCNY_PER_USD = 7.1


def print_expected_pricing(tokens_in, tokens_out):
    print("\n━━━ 預期定價（rate card）━━━")
    print(f"（匯率估算 ¥{RMBCNY_PER_USD}/USD；實際以 BytePlus console 為準）")
    rows = [
        ("ModelArk seed-1-6-flash-250715 input (≤32K)", "¥0.15 / 1M", "≈ $0.021"),
        ("ModelArk seed-1-6-flash output", "¥1.5 / 1M", "≈ $0.211"),
        ("ModelArk seed-1-6-flash cache-hit input", "¥0.03 / 1M", "≈ $0.004"),
        ("Embedding (網上去 doubao-embedding)", "—", "以 console 為準"),
        ("Embedding (本地 Ollama nomic-embed-text)", "免費", "本地，唔入帳"),
        ("CR 容器鏡像儲存 (hybrid)", "極少量", "以 console 為準"),
        ("Runtime / 混合運算 (hybrid)", "按使用", "以 console 為準"),
        ("VikingDB (日後上 cloud)", "~$0.25/CU·hr + $0.002/GB·hr", "上線前核實"),
        ("LLM Shield 內容安全", "按量", "以 console 為準"),
    ]
    print(f"{'服務項目':<44}{'定價':<28}{'備註'}")
    print("-" * 78)
    for a, b, c in rows:
        print(f"{a:<44}{b:<28}{c}")

    if tokens_in or tokens_out:
        fin = float(tokens_in or 0) / 1e6
        fout = float(tokens_out or 0) / 1e6
        cny = 0.15 * fin + 1.5 * fout
        cache_cny = 0.03 * fin
        print("\n── Seed-1-6-flash 費用估算 ──")
        print(f"  input  {fin:>10.2f}M  → ¥{0.15*fin:.4f}")
        print(f"  output {fout:>10.2f}M  → ¥{1.5*fout:.4f}")
        print(f"  cache-hit input（假設全部命中）→ ¥{cache_cny:.4f}（慳 ¥{0.12*fin:.4f}）")
        print(f"  合計 ≈ ¥{cny:.4f}（≈ ${cny/RMBCNY_PER_USD:.4f}）")


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="FIN-MATE: BytePlus 用量/費用")
    ap.add_argument("--period", default=None, help="帳期 YYYY-MM（預設本月）")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--tokens-in", type=int, default=0, help="估算用 input tokens")
    ap.add_argument("--tokens-out", type=int, default=0, help="估算用 output tokens")
    ap.add_argument("--dry-run", action="store_true", help="唔連網，淨印 rate card")
    ap.add_argument("--host", default=None)
    ap.add_argument("--region", default=None)
    args = ap.parse_args()

    env = load_env_file()
    ak = get_secret("BYTEPLUS_ACCESS_KEY", env)
    sk = get_secret("BYTEPLUS_SECRET_KEY", env)

    period = args.period or datetime.date.today().strftime("%Y-%m")
    print(f"FIN-MATE 費用報告 — 帳期 {period}（BytePlus）")

    if args.dry_run:
        print("（dry-run：冇連網）")
        print_expected_pricing(args.tokens_in, args.tokens_out)
        return

    if not ak or not sk:
        print("\n⚠️  未偵測到 BYTEPLUS_ACCESS_KEY / BYTEPLUS_SECRET_KEY。")
        print("    1) BytePlus console → User Profile → IAM → Access Keys 建立一對")
        print("    2) 填入 .env（已被 .gitignore 忽略）")
        print("    攰到之後再默默嘗試...\n")
        print_expected_pricing(args.tokens_in, args.tokens_out)
        sys.exit(0)

    hosts = [args.host] if args.host else HOST_CANDIDATES
    regions = [args.region] if args.region else REGION_CANDIDATES

    last_err = ""
    for host in hosts:
        for region in regions:
            try:
                payload = fetch_bill_overview(ak, sk, period, args.limit,
                                              args.offset, host, region)
            except Exception as exc:  # network / TLS / timeout
                last_err = f"[{host}/{region}] {exc}"
                continue
            code, msg = bill_error(payload)
            if code:
                last_err = f"[{host}/{region}] {code}: {msg}"
                if any(w in (code + msg).upper()
                       for w in ("SIGNATURE", "REGION", "CREDENTIAL", "AUTHENTICATION")):
                    continue
                break
            bills = extract_bills(payload)
            total_success = True

            col = ["Product", "PayableAmount", "OriginalBillAmount",
                   "DiscountBillAmount", "PaidAmount", "UnpaidAmount"]
            print("\n━━━ 各服務用量/費用（ListBillOverviewByProd）━━━")
            print(f"{'服務':<40}{'應付':>12}{'原價':>12}{'折扣':>12}"
                  f"{'已付':>12}{'未付':>12}")
            print("-" * 100)
            grand = 0.0
            if not bills:
                print("  無資料（本月未產生費用，或無權限查此幣種）")
            for b in sorted(bills, key=lambda x: float(
                    x.get("PayableAmount") or 0), reverse=True):
                pay = float(b.get("PayableAmount") or 0)
                grand += pay
                name = b.get("Product") or b.get("ProductZh") or "?"
                print(f"{name:<40}{pay:>12.4f}"
                      f"{float(b.get('OriginalBillAmount') or 0):>12.4f}"
                      f"{float(b.get('DiscountBillAmount') or 0):>12.4f}"
                      f"{float(b.get('PaidAmount') or 0):>12.4f}"
                      f"{float(b.get('UnpaidAmount') or 0):>12.4f}")
            print("-" * 100)
            print(f"{'合計':<40}{grand:>12.4f}")
            print("（金額單位以 BytePlus 帳單幣種為準，通常 USD）")
            print_expected_pricing(args.tokens_in, args.tokens_out)
            return total_success, host, region

    print("\n⚠️  全部候選 host/region 都失敗。")
    print(f"    最後錯誤：{last_err}")
    print("    檢查 .env 嘅 AK/SK 正確、帳戶有 billing 權限；")
    print("    或者試 `--host ... --region ...`（見 budget.py --help）。")
    print_expected_pricing(args.tokens_in, args.tokens_out)
    sys.exit(1)


if __name__ == "__main__":
    main()