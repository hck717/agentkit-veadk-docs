PY := .venv/bin/python
SHELL := /bin/bash

.PHONY: eval eval-lock eval-qa bench obs sec-eval schema-bench demo ft-data ft-lora ft-qlora ft-fuse lora-bench jev-bench

# 完整 eval：run + regression gate（exit 0 pass / 1 fail）
eval:
	$(PY) -m eval.run_eval --tag $$(date +%y%m%d_%H%M) && $(PY) -m eval.gate

# 第一次 / prompt 大改之後：run + 錄 baseline
eval-lock:
	$(PY) -m eval.run_eval --tag $$(date +%y%m%d_%H%M) && $(PY) -m eval.gate --lock-baseline

# 快速 lane：只 QA、唔行 LLM-judge（rule-based 快檢）
eval-qa:
	$(PY) -m eval.run_eval --suite qa --no-judge --tag $$(date +%y%m%d_%H%M) && $(PY) -m eval.gate

# 引擎對比（Ollama vs Ark；冇 key → ark(mock) 照出 report）
bench:
	$(PY) -m experiments.engine_bench.run

# D7 安全層 eval：injection/PII/secrets/authz 全 deterministic，越權全 block 先叫 pass
sec-eval:
	$(PY) -m security.self_test && $(PY) -m eval.run_security_eval

# D7 structured output 對比：plain vs output_schema（Ark json_schema）
schema-bench:
	$(PY) -m experiments.schema_bench.run

# D7 SequentialAgent 委派 demo（research → risk；安全層全開）
demo:
	$(PY) -m demo.multiagent_demo --ticker MSFT --role admin

# observability bundle
obs:
	$(PY) scripts/trace_all.py

# JEV bench：System One 決策層 vs 原裝 pipeline（6 variants，全 family）
jev-bench:
	$(PY) -m experiments.jev_bench.run --out experiments/jev_bench/results/runs_$$(date +%y%m%d_%H%M)

# ---------- E1 fine-tune（MLX-LM） ----------
PYBIN := .venv/bin
MLX_LORA := $(PYBIN)/mlx_lm.lora
MLX_FUSE := $(PYBIN)/mlx_lm.fuse
MLX_SRV  := $(PYBIN)/mlx_lm.server
BASE := Qwen/Qwen3-4B-Instruct-2507
Q4   := mlx-community/Qwen3-4B-Instruct-2507-4bit

.PHONY: ft-data ft-lora ft-qlora ft-fuse lora-bench lora-bench-report

# ---------- veadk web / studio（本機 UI） ----------
HOST       := 127.0.0.1
WEB_PORT   := 8000
STUDIO_PORT:= 8001
VEADK      := $(PYBIN)/veadk
AGENTS_DIR := ..

.PHONY: stack web studio web-stop studio-stop

# 起 db + observability（唔起 web container，避免霸 8000）
stack:
	docker compose up -d openviking otel-collector jaeger

# chat-first UI（http://127.0.0.1:8000）：ADK web，agents-dir 用 positional
web: stack
	$(VEADK) web $(AGENTS_DIR) --host $(HOST) --port $(WEB_PORT)

# AgentKit Studio（add-agent landing，管理 local agent/KB/memory）
studio: stack
	$(VEADK) studio --agents-dir $(AGENTS_DIR) --dev --host $(HOST) --port $(STUDIO_PORT)

web-stop:
	-pkill -f "veadk web"

studio-stop:
	-pkill -f "veadk studio"

# 由 KB 產生 training data（leakage-safe，唔會用 eval/golden）
ft-data:
	$(PY) -m finetune.build_dataset

# LoRA（bf16 base，順便首次下戴模型）
ft-lora:
	$(MLX_LORA) --model $(BASE) --train --data finetune/datasets \
	  --fine-tune-type lora --num-layers 16 --batch-size 4 --iters 500 \
	  --learning-rate 1e-5 --steps-per-report 25 --steps-per-eval 100 --val-batches 10 \
	  --save-every 100 --adapter-path finetune/adapters/lora --mask-prompt --grad-checkpoint \
	  --max-seq-length 2048 --seed 7 --optimizer adamw

# QLoRA（4bit base 自動變 QLoRA）
ft-qlora:
	$(MLX_LORA) --model $(Q4) --train --data finetune/datasets \
	  --fine-tune-type lora --num-layers 16 --batch-size 4 --iters 500 \
	  --learning-rate 1e-5 --steps-per-report 25 --steps-per-eval 100 --val-batches 10 \
	  --save-every 100 --adapter-path finetune/adapters/qlora --mask-prompt --grad-checkpoint \
	  --max-seq-length 2048 --seed 7 --optimizer adamw

# fuse adapters → 獨立 serve 用 model
ft-fuse:
	$(MLX_FUSE) --model $(BASE) --adapter-path finetune/adapters/lora  --save-path finetune/fused/lora
	$(MLX_FUSE) --model $(Q4)   --adapter-path finetune/adapters/qlora --save-path finetune/fused/qlora

# lora_bench 完整流程：3 個 server 都行，再合成 report（thinking 由 harness per-request 關）
lora-bench:
	$(MLX_SRV) --model $(BASE) --port 8201 &
	sleep 30; $(PY) -m experiments.lora_bench.run --row rag   --port 8201 --model $(BASE)
	$(PY) -m experiments.lora_bench.run --row base  --port 8201 --model $(BASE)
	kill %1
	$(MLX_SRV) --model finetune/fused/lora --port 8202 &
	sleep 20; $(PY) -m experiments.lora_bench.run --row lora  --port 8202 --model finetune/fused/lora
	kill %1
	$(MLX_SRV) --model finetune/fused/qlora --port 8203 &
	sleep 20; $(PY) -m experiments.lora_bench.run --row qlora --port 8203 --model finetune/fused/qlora
	kill %1
	$(PY) -m experiments.lora_bench.run --report