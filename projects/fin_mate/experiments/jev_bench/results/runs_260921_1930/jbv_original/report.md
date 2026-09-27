# report · jbv_original · 15 items

- 原裝：所有決定全走 LLM chat

- **工具路由**（3 題）: 3/3 pass  med 595 ms/題
- **RAG 檢索 gating**（4 題）: recall@5=1.000  answer-F1=0.049  trap=1/1  ctx 6.0/6.0  med 1244 ms/題
- **記憶篩選**（3 題）: answer-F1=0.125  sel-R=1.000  leak=1  med 1271 ms/題
- **情緒分類**（3 題）: pass 3/3  med 562 ms/題
- **多步 workflow＋noUL**（2 題）: stop 啱 1/2（over 1 / early 0）  noul 2/3  final-F1=0.200  med 2095 ms/題

- Jev decisions: 0  median: n/a ms  (total run: 16451 ms, usd=$0.0006, μusd=598)

## per-item

| eid | task | metric | ms | n_calls | μusd | note |
|---|---|---|---|---|---|---|
| js5_tool_01 | tool | PASS | 574 | 1 | 10 |  |
| js5_tool_02 | tool | PASS | 681 | 1 | 11 |  |
| js5_tool_03 | tool | PASS | 530 | 1 | 10 |  |
| js5_rag_01 | rag | r5=1.000 f1=0.000 ctx=6/6 | 2072 | 1 | 94 |  |
| js5_rag_02 | rag | r5=1.000 f1=0.000 ctx=6/6 | 663 | 1 | 54 |  |
| js5_rag_03 | rag | r5=1.000 f1=0.146 ctx=6/6 | 1532 | 1 | 108 |  |
| js5_rag_04 | rag | r5=n/a f1=n/a trap=P ctx=6/6 | 710 | 1 | 99 |  |
| js5_mem_01 | mem | f1=0.375 selR=1.000 | 1030 | 1 | 21 |  |
| js5_mem_02 | mem | f1=0.000 selR=1.000 | 1374 | 1 | 30 |  |
| js5_mem_03 | mem | f1=0.000 selR=1.000 | 1409 | 1 | 25 |  |
| js5_sent_01 | sent | PASS pred=positive
Wells Fargo upgrades Microsoft and raises price target to $600 | 640 | 1 | 5 |  |
| js5_sent_02 | sent | PASS pred=negative
解析：标题中提到“Microsoft shares slide 4%”（ | 519 | 1 | 5 |  |
| js5_sent_03 | sent | PASS pred=neutral
The title "Microsoft holds its guidance steady at the quarterly earnings call" | 526 | 1 | 5 |  |
| js5_wf_01 | wf | steps 3/3 OK noul 2/2 | 2657 | 5 | 105 |  |
| js5_wf_02 | wf | steps 2/1 OVER noul 0/1 | 1534 | 3 | 17 |  |
