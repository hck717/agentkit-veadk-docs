# report · jbv_original · 39 items

- 原裝：全部 LLM chat（tool-call 都係）

- **工具調用**（10 題）: 10/10 pass  med 555 ms/題
- **RAG 單源事實**（13 題）: recall@5=0.818  answer-F1=0.085  trap: 2/2  med 1333 ms/題
- **RAG 跨源推理**（2 題）: recall@5=0.750  answer-F1=0.121  med 2770 ms/題
- **情緒分類**（6 題）: pass 6/6  med 552 ms/題
- **記憶召回**（8 題）: answer-F1=0.360  med 1160 ms/題

- Jev decisions: 0  median: n/a ms  (total run: 41005 ms)
- cost: **$0.0017**   tokens: 55707+2485

## per-item

| eid | task | metric | ms | note |
|---|---|---|---|---|
| js_calc_01 | tool | PASS | 803 |  |
| js_calc_02 | tool | PASS | 537 |  |
| js_read_01 | tool | PASS | 530 |  |
| js_read_02 | tool | PASS | 506 |  |
| js_fetch_01 | tool | PASS | 534 |  |
| js_fetch_02 | tool | PASS | 518 |  |
| js_web_01 | tool | PASS | 555 |  |
| js_web_02 | tool | PASS | 537 |  |
| js_link_01 | tool | PASS | 534 |  |
| js_link_02 | tool | PASS | 491 |  |
| f1 | rag_fact | r5=1.000 f1=0.182 | 1386 |  |
| f2 | rag_fact | r5=1.000 f1=0.000 | 2979 |  |
| f3 | rag_fact | r5=1.000 f1=0.032 | 2086 |  |
| f4 | rag_fact | r5=1.000 f1=0.000 | 749 |  |
| f5 | rag_fact | r5=0.000 f1=0.000 | 723 |  |
| f6 | rag_fact | r5=1.000 f1=0.061 | 1108 |  |
| f7 | rag_fact | r5=1.000 f1=0.211 | 1585 |  |
| f8 | rag_fact | r5=1.000 f1=0.263 | 1320 |  |
| f9 | rag_fact | r5=1.000 f1=0.143 | 1358 |  |
| f10 | rag_fact | r5=1.000 f1=0.049 | 1713 |  |
| f11 | rag_fact | r5=0.000 f1=0.000 | 851 |  |
| t1 | rag_fact | r5=n/a f1=n/a trap=P | 810 |  |
| t2 | rag_fact | r5=n/a f1=n/a trap=P | 658 |  |
| m1 | rag_multi | r5=0.500 f1=0.000 | 612 |  |
| m2 | rag_multi | r5=1.000 f1=0.242 | 4929 |  |
| sent_3w_01 | sent | PASS pred=positive
The title states that Microsoft Cloud revenue has exceeded $50 billion and | 540 |  |
| sent_3w_02 | sent | PASS pred=negative
 | 395 |  |
| sent_3w_03 | sent | PASS pred=neutral
The title "Taiwan Semiconductor holds its guidance steady this quarter" | 659 |  |
| sent_3w_04 | sent | PASS pred=positive
解析：标题中提到“Microsoft wins big government cloud deal（微软 | 679 |  |
| sent_3w_05 | sent | PASS pred=negative
The title mentions a bank warning of an AI capex bubble and cutting | 519 |  |
| sent_3w_06 | sent | PASS pred=positive
Wells Fargo upgrades Microsoft and raises the price target to $60 | 523 |  |
| mem_01 | mem | f1=0.667 | 527 |  |
| mem_02 | mem | f1=0.462 | 2096 |  |
| mem_03 | mem | f1=0.000 | 1396 |  |
| mem_04 | mem | f1=0.667 | 619 |  |
| mem_05 | mem | f1=0.308 | 1331 |  |
| mem_06 | mem | f1=0.444 | 1301 |  |
| mem_07 | mem | f1=0.000 | 939 |  |
| mem_08 | mem | f1=0.333 | 1071 |  |
