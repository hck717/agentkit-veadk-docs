# report · jbv_jev3 · 15 items

- JEV tier-0（確定式）：RAG gate 用 RRF、tool 用規則路由、mem 用 marker rule + 並行 score、noUL asymmetric（STOP 一律 honor）、sentiment 退出 System One

- **工具路由**（3 題）: 3/3 pass  med 0 ms/題
- **RAG 檢索 gating**（4 題）: recall@5=1.000  answer-F1=0.049  trap=1/1  ctx 5.0/6.0  med 1178 ms/題
- **記憶篩選**（3 題）: answer-F1=0.857  sel-R=1.000  med 1509 ms/題
- **情緒分類**（3 題）: pass 3/3  med 589 ms/題
- **多步 workflow＋noUL**（2 題）: stop 啱 2/2  noul 3/3  final-F1=0.400  med 1741 ms/題

- System One decisions: 14  median: 546 ms  · tier-0 (確定式): 35  (total run: 14486 ms, usd=$0.0006, μusd=564)

## per-item

| eid | task | metric | ms | n_calls | μusd | note |
|---|---|---|---|---|---|---|
| js5_tool_01 | tool | PASS | 0 | 1 | 0 |  |
| js5_tool_02 | tool | PASS | 1 | 1 | 0 |  |
| js5_tool_03 | tool | PASS | 0 | 1 | 0 |  |
| js5_rag_01 | rag | r5=1.000 f1=0.000 ctx=5/6 | 1081 | 7 | 93 |  |
| js5_rag_02 | rag | r5=1.000 f1=0.000 ctx=5/6 | 871 | 7 | 53 |  |
| js5_rag_03 | rag | r5=1.000 f1=0.146 ctx=5/6 | 1881 | 7 | 110 |  |
| js5_rag_04 | rag | r5=n/a f1=n/a trap=P ctx=5/6 | 878 | 7 | 98 |  |
| js5_mem_01 | mem | f1=1.000 selR=1.000 | 1062 | 5 | 30 |  |
| js5_mem_02 | mem | f1=1.000 selR=1.000 | 1216 | 5 | 34 |  |
| js5_mem_03 | mem | f1=0.571 selR=1.000 | 2248 | 5 | 31 |  |
| js5_sent_01 | sent | PASS pred=positive
Wells Fargo upgrades Microsoft and raises its price target, which are both | 716 | 1 | 5 |  |
| js5_sent_02 | sent | PASS pred=negative
解析：标题提到“Microsoft shares slide 4%”（微软 | 525 | 1 | 5 |  |
| js5_sent_03 | sent | PASS pred=neutral
 | 524 | 1 | 2 |  |
| js5_wf_01 | wf | steps 3/3 OK noul 2/2 | 2969 | 11 | 99 |  |
| js5_wf_02 | wf | steps 1/1 OK noul 1/1 | 513 | 2 | 5 |  |
