# report · jbv_jev · 15 items

- JEV agent：System One 決策層（choice/score/noul + policy/escalation）

- **工具路由**（3 題）: 3/3 pass  med 1051 ms/題
- **RAG 檢索 gating**（4 題）: recall@5=1.000  answer-F1=0.029  trap=0/1  ctx 0.8/6.0  med 4834 ms/題
- **記憶篩選**（3 題）: answer-F1=0.706  sel-R=1.000  med 2638 ms/題
- **情緒分類**（3 題）: pass 1/3  score-err=0.667  med 506 ms/題
- **多步 workflow＋noUL**（2 題）: stop 啱 1/2（over 1 / early 0）  noul 2/3  final-F1=0.200  med 5173 ms/題

- Jev decisions: 57  median: 489 ms  (total run: 42267 ms, usd=$0.0007, μusd=724)

## per-item

| eid | task | metric | ms | n_calls | μusd | note |
|---|---|---|---|---|---|---|
| js5_tool_01 | tool | PASS | 1008 | 2 | 11 |  |
| js5_tool_02 | tool | PASS | 1041 | 2 | 10 |  |
| js5_tool_03 | tool | PASS | 1104 | 2 | 11 |  |
| js5_rag_01 | rag | r5=1.000 f1=0.000 ctx=2/6 | 3915 | 7 | 112 |  |
| js5_rag_02 | rag | r5=1.000 f1=0.000 ctx=1/6 | 4197 | 7 | 83 |  |
| js5_rag_03 | rag | r5=1.000 f1=0.087 ctx=0/6 | 4278 | 7 | 71 |  |
| js5_rag_04 | rag | r5=n/a f1=n/a trap=F ctx=0/6 | 6947 | 7 | 141 |  |
| js5_mem_01 | mem | f1=0.545 selR=1.000 | 2833 | 5 | 34 |  |
| js5_mem_02 | mem | f1=1.000 selR=1.000 | 2595 | 5 | 34 |  |
| js5_mem_03 | mem | f1=0.571 selR=1.000 | 2488 | 5 | 35 |  |
| js5_sent_01 | sent | PASS pred=positive serr=0.000 | 468 | 1 | 4 |  |
| js5_sent_02 | sent | FAIL pred=neutral serr=1.000 | 523 | 1 | 4 |  |
| js5_sent_03 | sent | FAIL pred=positive serr=1.000 | 526 | 1 | 4 |  |
| js5_wf_01 | wf | steps 3/3 OK noul 2/2 | 7529 | 12 | 140 |  |
| js5_wf_02 | wf | steps 2/1 OVER noul 0/1 | 2816 | 5 | 29 |  |
