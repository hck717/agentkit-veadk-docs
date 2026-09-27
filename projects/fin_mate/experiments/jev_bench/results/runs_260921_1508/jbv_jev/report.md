# report · jbv_jev · 15 items

- JEV 介面層：System One 決策 + escalation；tool args 仍然 chat 生成

- **工具路由**（3 題）: 3/3 pass  med 1009 ms/題
- **RAG 檢索 gating**（4 題）: recall@5=1.000  answer-F1=0.027  trap=0/1  ctx 0.8/6.0  med 4911 ms/題
- **記憶篩選**（3 題）: answer-F1=0.500  sel-R=1.000  med 3627 ms/題
- **情緒分類**（3 題）: pass 1/3  score-err=0.667  med 553 ms/題
- **多步 workflow＋noUL**（2 題）: stop 啱 1/2（over 1 / early 0）  noul 2/3  final-F1=0.200  med 5622 ms/題

- System One decisions: 57  median: 546 ms  · tier-0 (確定式): 0  (total run: 46458 ms, usd=$0.0007, μusd=721)

## per-item

| eid | task | metric | ms | n_calls | μusd | note |
|---|---|---|---|---|---|---|
| js5_tool_01 | tool | PASS | 1035 | 2 | 11 |  |
| js5_tool_02 | tool | PASS | 909 | 2 | 10 |  |
| js5_tool_03 | tool | PASS | 1084 | 2 | 11 |  |
| js5_rag_01 | rag | r5=1.000 f1=0.000 ctx=2/6 | 3827 | 7 | 112 |  |
| js5_rag_02 | rag | r5=1.000 f1=0.000 ctx=1/6 | 4261 | 7 | 84 |  |
| js5_rag_03 | rag | r5=1.000 f1=0.080 ctx=0/6 | 4577 | 7 | 72 |  |
| js5_rag_04 | rag | r5=n/a f1=n/a trap=F ctx=0/6 | 6981 | 7 | 117 |  |
| js5_mem_01 | mem | f1=0.600 selR=1.000 | 2931 | 5 | 33 |  |
| js5_mem_02 | mem | f1=0.455 selR=1.000 | 3230 | 5 | 52 |  |
| js5_mem_03 | mem | f1=0.444 selR=1.000 | 4721 | 5 | 40 |  |
| js5_sent_01 | sent | PASS pred=positive serr=0.000 | 526 | 1 | 4 |  |
| js5_sent_02 | sent | FAIL pred=neutral serr=1.000 | 428 | 1 | 4 |  |
| js5_sent_03 | sent | FAIL pred=positive serr=1.000 | 706 | 1 | 4 |  |
| js5_wf_01 | wf | steps 3/3 OK noul 2/2 | 8807 | 12 | 142 |  |
| js5_wf_02 | wf | steps 2/1 OVER noul 0/1 | 2436 | 5 | 24 |  |
