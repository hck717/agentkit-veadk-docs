# report · jbv_jev2 · 15 items

- JEV 完整版（真 JEV）：System One 決策 + args 確定式填充，除咗最終答案同 escalation 外零 generation

- **工具路由**（3 題）: 3/3 pass  med 524 ms/題
- **RAG 檢索 gating**（4 題）: recall@5=1.000  answer-F1=0.037  trap=0/1  ctx 0.8/6.0  med 5045 ms/題
- **記憶篩選**（3 題）: answer-F1=0.667  sel-R=1.000  med 3215 ms/題
- **情緒分類**（3 題）: pass 1/3  score-err=0.667  med 520 ms/題
- **多步 workflow＋noUL**（2 題）: stop 啱 1/2（over 1 / early 0）  noul 2/3  final-F1=0.200  med 5607 ms/題

- System One decisions: 53  median: 529 ms  · tier-0 (確定式): 0  (total run: 44172 ms, usd=$0.0007, μusd=737)

## per-item

| eid | task | metric | ms | n_calls | μusd | note |
|---|---|---|---|---|---|---|
| js5_tool_01 | tool | PASS | 447 | 2 | 6 |  |
| js5_tool_02 | tool | PASS | 533 | 2 | 6 |  |
| js5_tool_03 | tool | PASS | 591 | 2 | 6 |  |
| js5_rag_01 | rag | r5=1.000 f1=0.000 ctx=2/6 | 3880 | 7 | 112 |  |
| js5_rag_02 | rag | r5=1.000 f1=0.000 ctx=1/6 | 4967 | 7 | 84 |  |
| js5_rag_03 | rag | r5=1.000 f1=0.111 ctx=0/6 | 5432 | 7 | 65 |  |
| js5_rag_04 | rag | r5=n/a f1=n/a trap=F ctx=0/6 | 5901 | 7 | 117 |  |
| js5_mem_01 | mem | f1=1.000 selR=1.000 | 2854 | 5 | 30 |  |
| js5_mem_02 | mem | f1=0.556 selR=1.000 | 3187 | 5 | 41 |  |
| js5_mem_03 | mem | f1=0.444 selR=1.000 | 3606 | 5 | 39 |  |
| js5_sent_01 | sent | PASS pred=positive serr=0.000 | 429 | 1 | 4 |  |
| js5_sent_02 | sent | FAIL pred=neutral serr=1.000 | 624 | 1 | 4 |  |
| js5_sent_03 | sent | FAIL pred=positive serr=1.000 | 508 | 1 | 4 |  |
| js5_wf_01 | wf | steps 3/3 OK noul 2/2 | 8648 | 11 | 201 |  |
| js5_wf_02 | wf | steps 2/1 OVER noul 0/1 | 2566 | 5 | 19 |  |
