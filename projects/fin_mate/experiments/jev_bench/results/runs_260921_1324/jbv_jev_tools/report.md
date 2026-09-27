# report · jbv_jev_tools · 39 items

- 原裝，淨係工具調用改用 Jev

- **工具調用**（10 題）: 10/10 pass  med 1570 ms/題
- **RAG 單源事實**（13 題）: recall@5=0.818  answer-F1=0.069  trap: 2/2  med 1141 ms/題
- **RAG 跨源推理**（2 題）: recall@5=0.750  answer-F1=0.179  med 4212 ms/題
- **情緒分類**（6 題）: pass 6/6  med 684 ms/題
- **記憶召回**（8 題）: answer-F1=0.436  med 929 ms/題

- Jev decisions: 30  median: 515 ms  (total run: 50499 ms)
- cost: **$0.0017**   tokens: 58263+2419

## per-item

| eid | task | metric | ms | note |
|---|---|---|---|---|
| js_calc_01 | tool | PASS | 1393 |  |
| js_calc_02 | tool | PASS | 1487 |  |
| js_read_01 | tool | PASS | 1287 |  |
| js_read_02 | tool | PASS | 1572 |  |
| js_fetch_01 | tool | PASS | 1323 |  |
| js_fetch_02 | tool | PASS | 1210 |  |
| js_web_01 | tool | PASS | 1342 |  |
| js_web_02 | tool | PASS | 1392 |  |
| js_link_01 | tool | PASS | 1336 |  |
| js_link_02 | tool | PASS | 3361 |  |
| f1 | rag_fact | r5=1.000 f1=0.000 | 1394 |  |
| f2 | rag_fact | r5=1.000 f1=0.000 | 915 |  |
| f3 | rag_fact | r5=1.000 f1=0.033 | 2665 |  |
| f4 | rag_fact | r5=1.000 f1=0.000 | 788 |  |
| f5 | rag_fact | r5=0.000 f1=0.000 | 539 |  |
| f6 | rag_fact | r5=1.000 f1=0.061 | 1040 |  |
| f7 | rag_fact | r5=1.000 f1=0.211 | 1579 |  |
| f8 | rag_fact | r5=1.000 f1=0.263 | 1236 |  |
| f9 | rag_fact | r5=1.000 f1=0.146 | 1386 |  |
| f10 | rag_fact | r5=1.000 f1=0.049 | 1454 |  |
| f11 | rag_fact | r5=0.000 f1=0.000 | 634 |  |
| t1 | rag_fact | r5=n/a f1=n/a trap=P | 642 |  |
| t2 | rag_fact | r5=n/a f1=n/a trap=P | 565 |  |
| m1 | rag_multi | r5=0.500 f1=0.085 | 4617 |  |
| m2 | rag_multi | r5=1.000 f1=0.273 | 3806 |  |
| sent_3w_01 | sent | PASS pred=positive
解析：标题表明微软云服务收入超过500亿美元， | 453 |  |
| sent_3w_02 | sent | PASS pred=negative
微软股价下跌4%，原因是Azure增长低于预期。这 | 452 |  |
| sent_3w_03 | sent | PASS pred=neutral
 | 362 |  |
| sent_3w_04 | sent | PASS pred=positive
The title indicates that Microsoft has won a significant government cloud deal and its | 1729 |  |
| sent_3w_05 | sent | PASS pred=negative
The title indicates that a bank is warning about an AI capital expenditure ( | 536 |  |
| sent_3w_06 | sent | PASS pred=positive
Wells Fargo upgrades Microsoft and raises the price target to $60 | 569 |  |
| mem_01 | mem | f1=0.667 | 618 |  |
| mem_02 | mem | f1=0.500 | 914 |  |
| mem_03 | mem | f1=0.000 | 1116 |  |
| mem_04 | mem | f1=0.667 | 616 |  |
| mem_05 | mem | f1=0.571 | 843 |  |
| mem_06 | mem | f1=0.800 | 749 |  |
| mem_07 | mem | f1=0.000 | 1156 |  |
| mem_08 | mem | f1=0.286 | 1420 |  |
