# report · jbv_original · 15 items

- 原裝：所有決定全走 LLM chat

- **工具路由**（3 題）: 3/3 pass  med 608 ms/題
- **RAG 檢索 gating**（4 題）: recall@5=1.000  answer-F1=0.062  trap=1/1  ctx 6.0/6.0  med 1173 ms/題
- **記憶篩選**（3 題）: answer-F1=0.477  sel-R=1.000  med 1250 ms/題
- **情緒分類**（3 題）: pass 3/3  med 613 ms/題
- **多步 workflow＋noUL**（2 題）: stop 啱 1/2（over 1 / early 0）  noul 2/3  final-F1=0.200  med 3225 ms/題

- System One decisions: 0  median: n/a ms  · tier-0 (確定式): 0  (total run: 18555 ms, usd=$0.0006, μusd=593)

## per-item

| eid | task | metric | ms | n_calls | μusd | note |
|---|---|---|---|---|---|---|
| js5_tool_01 | tool | PASS | 604 | 1 | 10 |  |
| js5_tool_02 | tool | PASS | 625 | 1 | 11 |  |
| js5_tool_03 | tool | PASS | 596 | 1 | 10 |  |
| js5_rag_01 | rag | r5=1.000 f1=0.000 ctx=6/6 | 1194 | 1 | 94 |  |
| js5_rag_02 | rag | r5=1.000 f1=0.000 ctx=6/6 | 837 | 1 | 54 |  |
| js5_rag_03 | rag | r5=1.000 f1=0.186 ctx=6/6 | 1591 | 1 | 109 |  |
| js5_rag_04 | rag | r5=n/a f1=n/a trap=P ctx=6/6 | 1069 | 1 | 99 |  |
| js5_mem_01 | mem | f1=0.375 selR=1.000 | 1008 | 1 | 23 |  |
| js5_mem_02 | mem | f1=0.556 selR=1.000 | 1592 | 1 | 26 |  |
| js5_mem_03 | mem | f1=0.500 selR=1.000 | 1151 | 1 | 21 |  |
| js5_sent_01 | sent | PASS pred=positive
Wells Fargo 上調了對微軟的評級並 | 737 | 1 | 5 |  |
| js5_sent_02 | sent | PASS pred=negative
The title states that Microsoft shares "slide 4%" and Azure growth | 571 | 1 | 5 |  |
| js5_sent_03 | sent | PASS pred=neutral
解析：标题“Microsoft holds its guidance steady at the quarterly earnings call | 531 | 1 | 5 |  |
| js5_wf_01 | wf | steps 3/3 OK noul 2/2 | 3653 | 5 | 104 |  |
| js5_wf_02 | wf | steps 2/1 OVER noul 0/1 | 2797 | 3 | 17 |  |
