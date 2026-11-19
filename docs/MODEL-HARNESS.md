# Minimoo model harness spec (MIN-002, LFM3-1.7B)

## Server (Nisaba runtime reused intact — never modified)

```
llama-server -m D:\Nisaba-dev\models\LFM3-1.7B-Q4_K_M.gguf \
  --host 127.0.0.1 --port 19432 -c 8192 -ngl 99 \
  --jinja --temp 0.1 --top-k 50 --repeat-penalty 1.1
```

Add `--reasoning off` for short structured tasks (server-level switch;
per-request `enable_thinking:false` is ignored by b12499 — verified).

## Client (`minimoo/chat.py`)

- OpenAI-compatible `/v1/chat/completions` + GGUF template via `--jinja`.
- Sampling: temp 0.1, top_k 50, repeat_penalty 1.1 (Liquid's general/agent preset).
- Reasoning: read `message.reasoning_content`; never grade it.
- Tools: native `tools`/`tool_choice`; XML `<tool_call>` fallback parser.
- Verify deployment with `template_check(/props)`: all official markers required.
- Grammar: GBNF on `/completion` or `response_format` on chat constrain FORM only.
- GPU down → `ChatError`, deterministic jobs continue.

## Model identity

LFM3-1.7B-Q4_K_M, 1049MB, Liquid AI LFM Open License v1.0,
b12499-401563f10 Vulkan, RX 5700 XT. Q8_0 reference file (byte-exact,
1846238496 B) in `F:/Models` — tested, not selected.
MiniCPM5-2B-Q4_K_M (1524MB, `F:/Models`) retained for retest.
Isolated upstream b12532 build in `F:/Models/llama-b12532-vulkan` (MiniCPM5
retest only; Nisaba runtime untouched).

## Scoped capability flags (default all off)

`MINIMOO_CAP_LIBRARIAN, MINIMOO_CAP_STEWARD, MINIMOO_CAP_BRIEFING,`
`MINIMOO_CAP_LOG_CLASSIFIER, MINIMOO_CAP_SECRETARY_DRAFT,`
`MINIMOO_CAP_RECEIPT_DRAFT`. Lab master override: `MINIMOO_MODEL_JOBS=1`
(never used by production paths). Deterministic capabilities need no flags.
