# report · jbv_jev2 · 15 items

- JEV 完整版（真 JEV）：System One 決策 + args 確定式填充，除咗最終答案同 escalation 外零 generation

- **工具路由**（3 題）: 3/3 pass  med 471 ms/題
- **RAG 檢索 gating**（4 題）: recall@5=1.000  answer-F1=0.053  trap=0/1  ctx 0.8/6.0  med 5157 ms/題
- **記憶篩選**（3 題）: answer-F1=0.487  sel-R=1.000  med 2605 ms/題
- **情緒分類**（3 題）: pass 1/3  score-err=0.667  med 730 ms/題
- **多步 workflow＋noUL**（2 題）: stop 啱 1/2（over 1 / early 0）  noul 2/3  final-F1=0.200  med 4891 ms/題

- Jev decisions: 54  median: 526 ms  (total run: 41831 ms, usd=$0.0007, μusd=705)

## per-item

| eid | task | metric | ms | n_calls | μusd | note |
|---|---|---|---|---|---|---|
| js5_tool_01 | tool | PASS | 398 | 2 | 6 |  |
| js5_tool_02 | tool | PASS | 458 | 2 | 6 |  |
| js5_tool_03 | tool | PASS | 558 | 2 | 6 |  |
| js5_rag_01 | rag | r5=1.000 f1=0.000 ctx=2/6 | 3844 | 7 | 112 |  |
| js5_rag_02 | rag | r5=1.000 f1=0.000 ctx=1/6 | 4002 | 7 | 83 |  |
| js5_rag_03 | rag | r5=1.000 f1=0.160 ctx=0/6 | 5017 | 7 | 63 |  |
| js5_rag_04 | rag | r5=n/a f1=n/a trap=F ctx=0/6 | 7767 | 7 | 160 |  |
| js5_mem_01 | mem | f1=0.462 selR=1.000 | 2672 | 5 | 38 |  |
| js5_mem_02 | mem | f1=1.000 selR=1.000 | 2458 | 5 | 36 |  |
| js5_mem_03 | mem | f1=0.000 selR=1.000 | 2685 | 5 | 34 |  |
| js5_sent_01 | sent | PASS pred=positive serr=0.000 | 999 | 1 | 4 |  |
| js5_sent_02 | sent | FAIL pred=neutral serr=1.000 | 602 | 1 | 4 |  |
| js5_sent_03 | sent | FAIL pred=positive serr=1.000 | 590 | 1 | 4 |  |
| js5_wf_01 | wf | steps 3/3 OK noul 2/2 | 7081 | 12 | 122 |  |
| js5_wf_02 | wf | steps 2/1 OVER noul 0/1 | 2701 | 6 | 27 |  |
