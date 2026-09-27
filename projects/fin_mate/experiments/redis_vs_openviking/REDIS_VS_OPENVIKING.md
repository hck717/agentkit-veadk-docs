# FIN-MATE E3· Redis vs OpenViking（同一 pipeline、不同 DB：vector + sparse）

- generated: 2026-09-12 09:15:24
- eval set：**同一套 rag_bench**（CURRENT_ITEMS 15 題：fact 11 / trap 2 / multi_hop 2）
- metrics：eval_metrics.py（recall@5 / prec@5 / MRR@5 / nDCG@5 / answer-F1 / trap）＝ 同 REPORT_full_260908_1551
- embedding：Ollama nomic-embed-text 768d（兩邊一致）
- answer LLM：本地 MLX Qwen3-4B（--port 8201）

## 1. 方法論（Methodology）

- **同一套 eval**：`rag_bench.eval_set.CURRENT_ITEMS` 15 題（fact 11 / trap 2 / multi_hop 2），
  同 `REPORT_full_260908_1551.md` 完全一致；gold = `resolve_gold` 嘅 doc-level URI-prefix。
- **同一套 metrics**：`eval_metrics.py`（recall@5 / prec@5 / MRR@5 / nDCG@5 / answer-F1 / trap PASS）。
- **同一套 pipeline**：`strategies.py` 3 條 pipe（hybrid / advanced / hyde_rrf），
  兩邊行嘅係同一份 code，唯一分別係 `kb.search()` / `kb.grep()` 落到唔同 DB。
- **同一 embedding**：Ollama `nomic-embed-text` 768d（COSINE、`1 - dist` 轉 similarity）。
- **同一 answer LLM**：本地 MLX Qwen3-4B-Instruct-2507-4bit（`:8201`）每題一個 chat completion。
- **Redis backend**：`redis_kb.RedisKB` —— sentence 切 chunk（max 1500 字）→ 232 chunks
  → FT HNSW vector + TEXT index；`search` = embed query → KNN → hydrate 到 `read_limit`；
  `grep` = FT.SEARCH text match 返成個 chunk（~1500 字）。
- **OpenViking backend**：`redis_kb.OpenVikingKB` —— veadk 原生 KB，doc-level L2 hydrate；
  `search` 返成段 section content（read_limit 對唔到）；`grep` 係 line-level node snippet（~40–160 字）。
- **Retrieval-only bench**：`run.py --bench` —— 每題 search + grep 量 3 次取 median，**完全不經 LLM**，
  將「DB retrieval 速度」同「E2E（含 answer generation）」完全分開。
- **執行方式**：一次一個 config 順序跑（無 parallel），避免 16GB 記憶體互相逼爆影響計時。

## 2. 結果總覽（Results）

| backend | pipe | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap | ms/rec | prompt/completion tokens |
|---|---|---|---|---|---|---|---|---|---|
| **openviking** | advanced | 0.808 | 0.185 | 0.579 | 0.633 | 0.080 | 2/2 | 72918 | 139,919/1,563 |
| **openviking** | hybrid | 0.962 | 0.215 | 0.769 | 0.797 | 0.102 | 2/2 | 67209 | 129,631/1,505 |
| **openviking** | hyde_rrf | 0.846 | 0.185 | 0.667 | 0.684 | 0.094 | 2/2 | 32820 | 58,251/3,204 |
| **redis** | advanced | 0.885 | 0.208 | 0.564 | 0.625 | 0.217 | 2/2 | 94041 | 165,163/2,109 |
| **redis** | hybrid | 0.962 | 0.223 | 0.853 | 0.865 | 0.201 | 2/2 | 61470 | 110,700/1,836 |
| **redis** | hyde_rrf | 0.962 | 0.215 | 0.785 | 0.813 | 0.194 | 2/2 | 66063 | 106,411/3,845 |

## 3. Retrieval-only 比較（唔計 generation）

純 database retrieval（`--bench`：search + grep，每 query 3 次取 median，**無 LLM、無 hyde 生成**）：

| backend | pipe | read_limit | search(med ms) | grep(med ms) | total(med ms) |
|---|---|---|---|---|---|
| openviking | advanced | 2000 | 81.2 | 10.6 | 93.0 |
| openviking | hybrid | 200 | 77.2 | 10.4 | 88.6 |
| openviking | hyde_rrf | 200 | 77.4 | 10.6 | 88.1 |
| redis | advanced | 2000 | 28.7 | 2.4 | 30.7 |
| redis | hybrid | 200 | 31.6 | 2.3 | 34.6 |
| redis | hyde_rrf | 200 | 28.6 | 1.9 | 30.4 |

- **Redis 真身快 ~3×**：search 29–32ms + grep ~2ms → total ~**30–35ms**
  🆚 OpenViking search 77–81ms + grep ~11ms → total ~**88–93ms**。
- 原因係兩邊 embed 位置唔同：Redis 喺 **host 直接嵌**（Ollama ~25ms）+ 本地 FT KNN（~5ms），
  唔使過 container；OpenViking 要 **HTTP 打落 container → container 內再嵌 vector → 再搜**
  （兩轉 localhost-Docker 來回 overhead）。
- ⚠️ Redis 舊碼有 `time.sleep(0.1)` per `_embed_one`（batch-of-1 都照瞓）→ search 被灌到 ~150ms；
  已修正為只有 bulk indexing（>1 條）先瞓。**上面數字係修正後、真身速度。**
- Matrix 入面嘅 `retrieve` stage（Redis ~313–476ms / OpenViking ~616–653ms）係 16GB co-resident
  （MLX + Ollama + Redis + 2 個 OpenViking container）+ OpenViking f1 cold-start 2536ms 之下嘅
  環境數字，唔係 retrieval 本身：要睇 DB 快慢，以本節嘅 isolated bench 為準。

## 4. 關鍵調查：點解 Redis 唔一定跑贏 OpenViking？

有人會直覺「Redis 係 in-memory，梗係快過 OpenViking disk-based」。呢句喺 **retrieval 層面啱**，
但喺 **end-to-end 唔成立**，因為總時長幾乎全部落入 answer LLM。

### 4.1 retrieval 快慢根本睇唔到（<1% 佔比）

| config | retrieve | answer LLM（MLX） | hyde | total ms/rec | avg prompt tok | dense 條目×(len) | grep 條目×(len) | total ptok/ctok |
|---|---|---|---|---|---|---|---|---|
| openviking × advanced | 616 (0.8%) | 72302 (99.2%) | 0 (0.0%) | 72918 | 9328 | 14.9×1776 | 5.6×30 | 139,919/1,563 |
| openviking × hybrid | 653 (1.0%) | 66555 (99.0%) | 0 (0.0%) | 67209 | 8642 | 14.9×1701 | 5.3×23 | 129,631/1,505 |
| openviking × hyde_rrf | 639 (1.9%) | 26338 (80.3%) | 5843 (17.8%) | 32820 | 3771 | 4.9×1799 | 4.6×27 | 58,251/3,204 |
| redis × advanced | 339 (0.4%) | 93702 (99.6%) | 0 (0.0%) | 94041 | 11011 | 10.0×1264 | 17.9×1249 | 165,163/2,109 |
| redis × hybrid | 313 (0.5%) | 61158 (99.5%) | 0 (0.0%) | 61470 | 7380 | 10.0×141 | 17.9×1249 | 110,700/1,836 |
| redis × hyde_rrf | 476 (0.7%) | 58454 (88.5%) | 7133 (10.8%) | 66063 | 6982 | 4.6×165 | 17.9×1249 | 106,411/3,845 |

- Matrix 環境（16GB co-resident：MLX + Ollama + Redis + 2 個 OpenViking container）下，
  Redis 嘅 `retrieve` stage 平均 ~**310–480ms**、OpenViking ~**620–650ms**（OpenViking 仲有
  f1 cold-start 2536ms）——呢啲係「成個系統一齊跑緊」嘅環境數字。但無論邊個 DB，`retrieve`
  都只佔總時長 **0.4–1%**；喺 60–90 秒嘅 E2E 入面完全消化唔到。**DB 本身快慢要睇 §3**。
- 相反 **answer LLM 佔 99%+**（除咗 hyde_rrf 要另跑一轉 hyde 生成，先跌到 ~80–89%）。
  所以「邊個 DB 快」=「邊個 prompt 少 token」=「邊個返出黎嘅 context 少字」。

### 4.2 兩邊 context 形態根本唔同，先係速度分歧嘅來源

- **Redis `search` 受 `read_limit` 管**：hybrid/hyde_rrf 用 `read_limit=200` → 每條 dense
  只有 ~200 字；advanced 用 `read_limit=2000` → ~1325 字。但 **Redis `grep` 返成個 chunk**
  （~1330 字/條，因為 FT.SEARCH 會帶埋成段 content 出嚟）。
- **OpenViking `search` 唔受 read_limit 管**：返成段 section（~1750–1835 字/條）；但
  **`grep` 係 line-level snippet**（平均 ~73 字/條）。
- 效果：同一條質問，Redis 嘅 context 主要係「短 dense + 長 grep chunk」；OpenViking 係
  「長 dense section + 微 grep」→ token 包大小同分布完全唔同。

### 4.3 逐 pipe 解釋速度差異

- **`hybrid`（read_limit=200）**：Redis 靠大 grep chunk（~1330×18）反而做到 ctx ~7.4k token；
  OpenViking 靠長 dense（~1750×15）推出 ~8.6k token。差唔多量 → 總時間亦都差唔多
  （Redis 61.5s 🆚 OpenViking 67.2s，Redis 微贏）。
- **`advanced`（read_limit=2000）**：Redis 嘅 dense 變長（~1325×15）+ grep 又長（~1330×18）
  → ctx 爆到 ~11k token（全場最肥）→ **Redis 94s 比 OpenViking 73s 慢**。所以唔係 Redis
  慢，而係 advanced 畀咗最大 read_limit，Redis 兩條 channel 一齊變肥。
- **`hyde_rrf`（read_limit=200）**：ctx 只保留 top-5 dense。Redis 5×198 + grep ~1330 補充
  （~7k token）；OpenViking 叉開 grep（~73）純靠 5×~1835（~3.8k token，半數）→ 快一倍
  （Redis 66.1s 🆚 OpenViking 32.8s）。呢個正正係「OpenViking 反而快」嘅典型一幕：
  短 grep + 受控 top-5，ctx 細一半 → MLX prefill 時間減半。

### 4.4 咁 Redis 有咩好處？（答得準啲）

速度之外，Redis 喺 **answer-F1 上全面反超**（0.19–0.22 vs 0.08–0.10）：
長而細嘅 chunk（含數字同前後文）令 LLM「照抄」原文機會大 → F1 高；OpenViking 用成段
section 或者太短 snippet，LLM 傾向改寫 → 對 token overlap 唔著數。所以結論係：

- **要準確（F1）**：Redis + hybrid / advanced（R@5=0.962、aF1≈0.2）。
- **要快**：OpenViking + hyde_rrf（32.8s/rec），但 aF1 減半。
- **平衡**：Redis × hybrid —— R@5=0.962、MRR=0.853、aF1=0.201、61.5s/rec，6 config 最好。

## 5. Insights

- **DB retrieval 快唔快，喺 E2E 睇唔到**：retrieval 佔總時長 <1%，answer LLM 佔 99%+；
  真正決定 E2E 快慢嘅係 `read_limit` + `grep` 粒度 → prompt token 量。
- **純 retrieval 真身：Redis 快 ~3×**（§3：~30–35ms 🆚 ~88–93ms）——Redis 喺 host 直接嵌
  + 本地 FT KNN，OpenViking 要 HTTP 過 container 再喺入面嵌 + 搜。
- **Redis 舊碼有 per-query `sleep(0.1)` artifact**：`_embed_batch` 對 batch-of-1 都瞓 100ms，
  令 Redis search 由真身 ~30ms 被灌到 ~150ms；已修正（只有 bulk indexing 先瞓，唔影響入面
  已記錄嘅 matrix 數據——嗰次係行緊舊碼，階段數字要高啲）。
- **準度嚟自 chunk 粒度，唔係 vector index**：Redis 嘅長 chunk（~1330 字）含數字同前文後理，
  LLM 照抄機會大 → answer-F1 約 2×（0.19–0.22 vs 0.08–0.10）。

## 6. Takeaways

- **要準確 + 唔介意慢少少** → **Redis × hybrid**（R@5=0.962、MRR=0.853、aF1=0.201、trap 2/2、61.5s/rec）。
- **要最快** → **OpenViking × hyde_rrf**（32.8s/rec），但 aF1 得返一半（0.094）、R@5 稍跌（0.846）。
- **純 retrieval 層面：Redis 係贏家**（~3×），但因為 LLM 佔 99%+，兩邊 E2E 差異係由 context
  粒度控制——想快，就控制返 dense / grep 輸出長度，唔使換 DB。
- **量度要分層**：用 `run.py --bench` 量純 retrieval、用 traces/run.json 量 E2E——兩者唔好撈埋。


## 7. per-eid 明細

### openviking × advanced

| eid | cat | recall@5 | prec@5 | MRR@5 | nDCG@5 | ans-F1 | trap | ms | stage events |
|---|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.133 | - | 85541 | 3 |
| f2 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.000 | - | 97123 | 3 |
| f3 | fact | 1.000 | 0.200 | 0.500 | 0.631 | 0.062 | - | 87423 | 3 |
| f4 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.000 | - | 50206 | 3 |
| f5 | fact | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | - | 48567 | 3 |
| f6 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.000 | - | 71818 | 3 |
| f7 | fact | 1.000 | 0.200 | 0.200 | 0.387 | 0.255 | - | 78918 | 3 |
| f8 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.143 | - | 52035 | 3 |
| f9 | fact | 1.000 | 0.200 | 0.500 | 0.631 | 0.238 | - | 81551 | 3 |
| f10 | fact | 1.000 | 0.200 | 0.333 | 0.500 | 0.000 | - | 83566 | 3 |
| f11 | fact | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | - | 86010 | 3 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | PASS | 69667 | 3 |
| t2 | trap | n/a | n/a | n/a | n/a | n/a | PASS | 62670 | 3 |
| m1 | multi_hop | 0.500 | 0.200 | 0.500 | 0.387 | 0.000 | - | 45980 | 3 |
| m2 | multi_hop | 1.000 | 0.400 | 0.500 | 0.693 | 0.202 | - | 92696 | 3 |

### openviking × hybrid

| eid | cat | recall@5 | prec@5 | MRR@5 | nDCG@5 | ans-F1 | trap | ms | stage events |
|---|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.200 | 0.500 | 0.631 | 0.167 | - | 75454 | 2 |
| f2 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.020 | - | 91670 | 2 |
| f3 | fact | 1.000 | 0.200 | 0.250 | 0.431 | 0.121 | - | 80974 | 2 |
| f4 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.000 | - | 51098 | 2 |
| f5 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.000 | - | 43987 | 2 |
| f6 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.000 | - | 69116 | 2 |
| f7 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.250 | - | 73527 | 2 |
| f8 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.235 | - | 49792 | 2 |
| f9 | fact | 1.000 | 0.200 | 0.500 | 0.631 | 0.238 | - | 73344 | 2 |
| f10 | fact | 1.000 | 0.200 | 0.250 | 0.431 | 0.000 | - | 72050 | 2 |
| f11 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.059 | - | 78277 | 2 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | PASS | 59830 | 2 |
| t2 | trap | n/a | n/a | n/a | n/a | n/a | PASS | 49310 | 2 |
| m1 | multi_hop | 0.500 | 0.200 | 0.500 | 0.387 | 0.000 | - | 52379 | 2 |
| m2 | multi_hop | 1.000 | 0.400 | 1.000 | 0.850 | 0.242 | - | 87319 | 2 |

### openviking × hyde_rrf

| eid | cat | recall@5 | prec@5 | MRR@5 | nDCG@5 | ans-F1 | trap | ms | stage events |
|---|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.200 | 0.500 | 0.631 | 0.000 | - | 33970 | 3 |
| f2 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.022 | - | 57924 | 3 |
| f3 | fact | 1.000 | 0.200 | 0.500 | 0.631 | 0.097 | - | 46247 | 3 |
| f4 | fact | 1.000 | 0.200 | 0.500 | 0.631 | 0.087 | - | 17698 | 3 |
| f5 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.174 | - | 25828 | 3 |
| f6 | fact | 1.000 | 0.200 | 0.333 | 0.500 | 0.000 | - | 27474 | 3 |
| f7 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.245 | - | 37194 | 3 |
| f8 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.235 | - | 24683 | 3 |
| f9 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.091 | - | 36630 | 3 |
| f10 | fact | 1.000 | 0.200 | 0.333 | 0.500 | 0.000 | - | 28889 | 3 |
| f11 | fact | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | - | 24293 | 3 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | PASS | 30171 | 3 |
| t2 | trap | n/a | n/a | n/a | n/a | n/a | PASS | 24803 | 3 |
| m1 | multi_hop | 0.500 | 0.200 | 0.500 | 0.387 | 0.104 | - | 46808 | 3 |
| m2 | multi_hop | 0.500 | 0.200 | 1.000 | 0.613 | 0.171 | - | 29685 | 3 |

### redis × advanced

| eid | cat | recall@5 | prec@5 | MRR@5 | nDCG@5 | ans-F1 | trap | ms | stage events |
|---|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.250 | 0.500 | 0.631 | 0.136 | - | 103759 | 3 |
| f2 | fact | 1.000 | 0.200 | 0.500 | 0.631 | 0.042 | - | 139063 | 3 |
| f3 | fact | 1.000 | 0.200 | 0.250 | 0.431 | 0.029 | - | 112876 | 3 |
| f4 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.067 | - | 87610 | 3 |
| f5 | fact | 1.000 | 0.200 | 0.250 | 0.431 | 0.560 | - | 87699 | 3 |
| f6 | fact | 1.000 | 0.200 | 0.500 | 0.631 | 0.250 | - | 97901 | 3 |
| f7 | fact | 1.000 | 0.200 | 0.333 | 0.500 | 0.250 | - | 91040 | 3 |
| f8 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.235 | - | 78078 | 3 |
| f9 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.238 | - | 95506 | 3 |
| f10 | fact | 1.000 | 0.200 | 0.500 | 0.631 | 0.625 | - | 102012 | 3 |
| f11 | fact | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | - | 97378 | 3 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | PASS | 86209 | 3 |
| t2 | trap | n/a | n/a | n/a | n/a | n/a | PASS | 50127 | 3 |
| m1 | multi_hop | 0.500 | 0.250 | 1.000 | 0.613 | 0.154 | - | 82521 | 3 |
| m2 | multi_hop | 1.000 | 0.400 | 0.500 | 0.624 | 0.231 | - | 98836 | 3 |

### redis × hybrid

| eid | cat | recall@5 | prec@5 | MRR@5 | nDCG@5 | ans-F1 | trap | ms | stage events |
|---|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.250 | 1.000 | 1.000 | 0.100 | - | 51574 | 2 |
| f2 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.026 | - | 90352 | 2 |
| f3 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.000 | - | 49123 | 2 |
| f4 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.333 | - | 71804 | 2 |
| f5 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.400 | - | 75273 | 2 |
| f6 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.333 | - | 63980 | 2 |
| f7 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.189 | - | 67661 | 2 |
| f8 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.222 | - | 57035 | 2 |
| f9 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.316 | - | 71335 | 2 |
| f10 | fact | 1.000 | 0.200 | 0.500 | 0.631 | 0.333 | - | 69358 | 2 |
| f11 | fact | 1.000 | 0.200 | 0.333 | 0.500 | 0.000 | - | 57760 | 2 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | PASS | 49690 | 2 |
| t2 | trap | n/a | n/a | n/a | n/a | n/a | PASS | 22123 | 2 |
| m1 | multi_hop | 0.500 | 0.250 | 1.000 | 0.613 | 0.102 | - | 54833 | 2 |
| m2 | multi_hop | 1.000 | 0.400 | 0.250 | 0.501 | 0.263 | - | 70153 | 2 |

### redis × hyde_rrf

| eid | cat | recall@5 | prec@5 | MRR@5 | nDCG@5 | ans-F1 | trap | ms | stage events |
|---|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.189 | - | 71744 | 3 |
| f2 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.027 | - | 78641 | 3 |
| f3 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.111 | - | 84025 | 3 |
| f4 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.087 | - | 62737 | 3 |
| f5 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.400 | - | 59127 | 3 |
| f6 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.245 | - | 66420 | 3 |
| f7 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.245 | - | 66584 | 3 |
| f8 | fact | 1.000 | 0.200 | 1.000 | 1.000 | 0.235 | - | 58576 | 3 |
| f9 | fact | 1.000 | 0.200 | 0.500 | 0.631 | 0.279 | - | 75935 | 3 |
| f10 | fact | 1.000 | 0.200 | 0.250 | 0.431 | 0.370 | - | 71961 | 3 |
| f11 | fact | 1.000 | 0.200 | 0.200 | 0.387 | 0.000 | - | 63884 | 3 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | PASS | 52003 | 3 |
| t2 | trap | n/a | n/a | n/a | n/a | n/a | PASS | 28702 | 3 |
| m1 | multi_hop | 0.500 | 0.200 | 1.000 | 0.613 | 0.119 | - | 58420 | 3 |
| m2 | multi_hop | 1.000 | 0.400 | 0.250 | 0.501 | 0.211 | - | 92182 | 3 |

