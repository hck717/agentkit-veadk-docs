# report · jbv_jev · 15 items

- JEV 介面層：System One 決策 + escalation；tool args 仍然 chat 生成

- **工具路由**（3 題）: 3/3 pass  med 1008 ms/題
- **RAG 檢索 gating**（4 題）: recall@5=1.000  answer-F1=0.033  trap=0/1  ctx 0.8/6.0  med 4649 ms/題
- **記憶篩選**（3 題）: answer-F1=0.601  sel-R=1.000  med 2816 ms/題
- **情緒分類**（3 題）: pass 1/3  score-err=0.667  med 429 ms/題
- **多步 workflow＋noUL**（2 題）: stop 啱 1/2（over 1 / early 0）  noul 2/3  final-F1=0.200  med 4860 ms/題

- Jev decisions: 57  median: 464 ms  (total run: 41082 ms, usd=$0.0008, μusd=762)

## per-item

| eid | task | metric | ms | n_calls | μusd | note |
|---|---|---|---|---|---|---|
| js5_tool_01 | tool | PASS | 913 | 2 | 11 |  |
| js5_tool_02 | tool | PASS | 1005 | 2 | 10 |  |
| js5_tool_03 | tool | PASS | 1107 | 2 | 12 |  |
| js5_rag_01 | rag | r5=1.000 f1=0.000 ctx=2/6 | 4424 | 7 | 127 |  |
| js5_rag_02 | rag | r5=1.000 f1=0.000 ctx=1/6 | 3378 | 7 | 84 |  |
| js5_rag_03 | rag | r5=1.000 f1=0.098 ctx=0/6 | 3612 | 7 | 68 |  |
| js5_rag_04 | rag | r5=n/a f1=n/a trap=F ctx=0/6 | 7184 | 7 | 161 |  |
| js5_mem_01 | mem | f1=0.462 selR=1.000 | 2492 | 5 | 36 |  |
| js5_mem_02 | mem | f1=0.769 selR=1.000 | 3229 | 5 | 43 |  |
| js5_mem_03 | mem | f1=0.571 selR=1.000 | 2729 | 5 | 35 |  |
| js5_sent_01 | sent | PASS pred=positive serr=0.000 | 389 | 1 | 4 |  |
| js5_sent_02 | sent | FAIL pred=neutral serr=1.000 | 471 | 1 | 4 |  |
| js5_sent_03 | sent | FAIL pred=positive serr=1.000 | 428 | 1 | 4 |  |
| js5_wf_01 | wf | steps 3/3 OK noul 2/2 | 7099 | 12 | 140 |  |
| js5_wf_02 | wf | steps 2/1 OVER noul 0/1 | 2621 | 5 | 24 |  |
