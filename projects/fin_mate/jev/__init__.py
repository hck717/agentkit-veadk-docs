"""fin-mate JEV「System One」決策層。

將 agent 入面所有「要一個 label／揀一樣嘢／畀個分」嘅決定，統一經
1–3 token + logprobs 決策（backed by `experiments.jev_bench.lib.jev_client`），
同「一定要生文字」嘅 System Two 生成層分開：

  System One（決策）：揀工具、RAG doc 相關度分、記憶篩選、情緒 label、noUL 續步
  System Two（生成）：  最終答案、free-form args、總結

Package：
  gate.py      DecisionGate 基礎類 + 組裝 agent 用嘅 helper
  decisions.py 每個決策點嘅 gate 規格（state packing + 選項/rubric）
  policy.py    門檻 + escalation 規則
  ledger.py    per-decision 成本/延時 ledger
"""