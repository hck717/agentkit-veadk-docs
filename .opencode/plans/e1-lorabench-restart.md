# E1 lora_bench — memory-safe restart plan

## Goal
Run the LoRA/QLoRA vs RAG bench matrix against the 34-record eval, entirely local,
on a 16GB M3 Mac (`projects/fin_mate/`), then write `experiments/lora_bench/report.md`
and sleep the Mac.

## Status recap (verified read-only)
- LoRA + QLoRA fine-tunes finished (val 0.533 / 0.522); fused models exist:
  `finetune/fused/lora` (7.5G bf16), `finetune/fused/qlora` (2.1G 4-bit).
- Crash cause: while bf16 base server (~8GB) was up, `llm_judge` loaded Ollama qwen3
  (~2.5GB) → exceeded 16GB → heavy swap → Ollama 500 → run died.
- Now: mlx server dead, Docker daemon down (OpenViking/KB off), Ollama idle.
- Storage fine (98GB free); all models cached; no new downloads.

## Root-cause fix (the whole point)
Memory is safe only if the MLX server and Ollama are **never** resident together.
The only Ollama dependency is `llm_judge` on 2 `fact_multi` records per row → defer it
to a post-pass that runs with all MLX servers killed.

## Implementation steps (all in `projects/fin_mate/`)

1. **`experiments/lora_bench/run.py`**
   - `_score(...)` gains `no_judge` mode: deterministic evaluators inline;
     `llm_judge` returns pending sentinel (skips Ollama).
   - `run_row()` always runs deterministics inline, stores **full** `pred` (no :200
     truncation), sets `evaluator_pending: true` for llm_judge records.
   - New `judge_pass()`: loads `run.json`, re-resolves golden records by
     `set::id`, calls `EVALUATORS["llm_judge"]` (Ollama-only, shared judge cache),
     writes scores back.
   - CLI: add `--judge` flag; `--report` reads run.json (keeps working).

2. **Run sequence (one server at a time, kill between):**
   - `base`:  `mlx_lm.server --model Qwen/Qwen3-4B-Instruct-2507 --port 8201`
     (add `--prompt-cache-bytes` cap to bound KV) → `run --row base`. Kill.
   - `lora`:  server on `finetune/fused/lora` :8202 → `run --row lora`. Kill.
   - `qlora`: server on `finetune/fused/qlora` :8203 → `run --row qlora`. Kill.
   - `rag`:   restart Docker daemon + OpenViking KB; serve the **4-bit base**
     (`mlx-community/Qwen3-4B-Instruct-2507-4bit`, ~2.5G) on :8201 →
     `run --row rag --model <4bit>` (3 pipes). Kill + `docker compose down` if desired.
   - `judge`: with all servers down → `run --judge` (Ollama alone).
   - `report`: `run --report` → write `experiments/lora_bench/report.md`.

3. **Watch memory** during run: `vm_stat`/swap; abort-and-report if swap grows fast.

4. **Report** covers: methodology (data leakage-safe, 4-bit vs bf16 serving,
   deferred judge, same D6 evaluators), per-set table (pass/score/ms/tokens),
   training stats, honest verdict vs D6 Ark RAG baseline (26/34) —— closed-book 4B
   likely wins on latency but may lose on fact recall; state it plainly.

5. **Sleep Mac**: `pmset sleepnow` after report is written.

## Files touched
- `projects/fin_mate/experiments/lora_bench/run.py`
- `projects/fin_mate/experiments/lora_bench/report.md` (generated)
- `projects/fin_mate/Makefile` (already updated for sequencing; verify flags)

## Not doing
- No retraining, no new model downloads, no cloud (Ark) calls.
- No judge on MLX server (keeps judge identical to D6 for apples-to-apples).