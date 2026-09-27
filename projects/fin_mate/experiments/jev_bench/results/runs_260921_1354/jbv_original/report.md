# report · jbv_original · 15 items

- 原裝：所有決定全走 LLM chat

- **工具路由**（3 題）: 3/3 pass  med 579 ms/題
- **RAG 檢索 gating**（4 題）: recall@5=1.000  answer-F1=0.150  trap=1/1  ctx 6.0/6.0  med 1049 ms/題
- **記憶篩選**（3 題）: answer-F1=0.481  sel-R=1.000  med 1293 ms/題
- **情緒分類**（3 題）: pass 3/3  med 534 ms/題
- **多步 workflow＋noUL**（2 題）: stop 啱 1/2（over 1 / early 0）  noul 2/3  final-F1=0.143  med 3052 ms/題

- Jev decisions: 0  median: n/a ms  (total run: 17518 ms, usd=$0.0006, μusd=611)

## per-item

| eid | task | metric | ms | n_calls | μusd | note |
|---|---|---|---|---|---|---|
| js5_tool_01 | tool | PASS | 480 | 1 | 10 |  |
| js5_tool_02 | tool | PASS | 618 | 1 | 9 |  |
| js5_tool_03 | tool | PASS | 639 | 1 | 10 |  |
| js5_rag_01 | rag | r5=1.000 f1=0.000 ctx=6/6 | 1468 | 1 | 108 |  |
| js5_rag_02 | rag | r5=1.000 f1=0.000 ctx=6/6 | 701 | 1 | 54 |  |
| js5_rag_03 | rag | r5=1.000 f1=0.449 ctx=6/6 | 1385 | 1 | 107 |  |
| js5_rag_04 | rag | r5=n/a f1=n/a trap=P ctx=6/6 | 641 | 1 | 99 |  |
| js5_mem_01 | mem | f1=0.231 selR=1.000 | 1463 | 1 | 32 |  |
| js5_mem_02 | mem | f1=0.769 selR=1.000 | 1357 | 1 | 18 |  |
| js5_mem_03 | mem | f1=0.444 selR=1.000 | 1059 | 1 | 19 |  |
| js5_sent_01 | sent | PASS pred=positive
Wells Fargo upgrades Microsoft and raises price target to $600 | 501 | 1 | 5 |  |
| js5_sent_02 | sent | PASS pred=negative
解析：标题中提到“Microsoft shares slide 4%”（ | 526 | 1 | 5 |  |
| js5_sent_03 | sent | PASS pred=neutral
微软在季度 earnings 电话会议上维持指引不变，这一 | 575 | 1 | 5 |  |
| js5_wf_01 | wf | steps 3/3 OK noul 2/2 | 3427 | 5 | 113 |  |
| js5_wf_02 | wf | steps 2/1 OVER noul 0/1 | 2678 | 3 | 16 |  |
