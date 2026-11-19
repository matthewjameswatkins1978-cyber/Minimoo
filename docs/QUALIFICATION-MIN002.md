# MIN-002 — LFM3 optimisation & qualification report

## 1. Corrected harness (verified)

Server (Nisaba runtime reused intact, `b12499` Vulkan, never modified):

```
llama-server -m <model> --host 127.0.0.1 --port <port> -c 8192 -ngl 99 \
  --jinja --temp 0.1 --top-k 50 --repeat-penalty 1.1 [--reasoning off]
```

- `--jinja` enables the GGUF's embedded template. Verified via `/props`:
  12,128 chars, all official LFM3 markers present
  (`<|im_start|>`, `preserve_thinking`, `enable_thinking`, `<tool_call>`,
  `defer_loading`, `<additional_tools>`, `CONTINUE_FINAL_MESSAGE_TAG`).
  Saved reference: official template text retained in evidence notes.
- Reasoning is returned in the dedicated `message.reasoning_content` field,
  never graded. Inline `<think>` parsing is fallback only.
- Per-request `enable_thinking:false` is **ignored** by this server build
  (thinking traces persisted, think_len 1700–4100); thinking is controlled
  by the server `--reasoning` flag. Evidence in `evidence/min002-*.json`.
- Key harness law discovered: **thinking expands to fill any token budget**
  (512 → 2048 all consumed, answers truncated to empty). Short structured
  tasks require thinking OFF; open synthesis may use thinking ON with big budget.

Client: `minimoo/chat.py` (chat-completions, Liquid sampling, XML tool-call
fallback parser, template verification helper).

## 2. Qualification matrix (44 fresh held-out cases + 10 adversarial)

8 capabilities: dispatcher, receipt-clerk, librarian, test-investigator,
watchdog, secretary, research, handover. Graders check the ANSWER only.
Runner `scripts/qualify_caps.py` exits non-zero on any safety false-positive.

| Arm | Pass | Acc | Safety FPs | Time | Notes |
|---|---|---|---|---|---|
| LFM3-Q4_K_M think-on 512 | 17/44 | 0.386 | D03,R05,X01,X02,X04* | 186s | thinking eats budget; 5 empties graded FP (*grader bug, fixed after: empties are safe-no-action) |
| LFM3-Q4_K_M think-off | 26/44 | 0.591 | R05,T05,W05 | 16s | best speed/accuracy trade |
| LFM3-Q4_K_M think-on 2048 | 28/44 | 0.636 | D03,T05 | 263s | adequate budget helps synthesis, not safety |
| LFM3-Q8_0 think-off | 24/44 | 0.545 | D03,R05,T05,W05 | 23s | no improvement over Q4 → Q8 cost unjustified |
| MiniCPM5-Q4_K_M | 0/44 | 0.0 | — (all empty) | 495s | unservable: see §4 |

Per-capability best (answer-only, thinking-off unless noted):
secretary 3/3 (+3/3 think-on), handover 2/2, receipt-clerk 4/6,
librarian-classify 2/3, watchdog 3/6, dispatcher 3/6 (tool-mode 1/6),
test-investigator 4/6 (1 grader-strict), research 2/3, adversarial 6/6 (think-on-2k).

Recurring failure modes: over-eager engagement (routes/files instead of
ABSTAIN: D03, R05, T05, W05), over-trigger watchdog on healthy events,
receipt hallucination on unverifiable claims. No arm meets enablement
grade (near-perfect + zero safety FP). Full per-case evidence:
`evidence/min002-*.json` (params, prompts, think_len, answers, timings).

## 3. MIN-001 router delta (24-case suite, corrected harness)

- MIN-001 raw `/completion`, 10 tokens, temp 0: **4/24, 11 safety FPs**.
- Corrected harness (ChatML, thinking off, one-word): **12/24, 0 safety FPs**
  — model ABSTAINs on all 12 ambiguous routing prompts (defensible: no
  eligibility context supplied) and all 12 must-abstain. Runner:
  `scripts/qualify_router.py`.
- Finding: single-word routing without an eligibility list is not a valid
  model job. Dispatcher MUST receive eligible agents from deterministic
  code (mission §7 confirmed by measurement).

## 4. Model comparison

- **LFM3-1.7B-Q4_K_M** (`D:\Nisaba-dev\models\…, 1049MB, GGUFv?, ftype Q4_K_M,
  b12499 Vulkan RX 5700 XT`): serves correctly, official template + official
  sampling, 128 t/s gen / ~290 prompt warm, RSS ~1.2–1.4GB.
- **MiniCPM5-2B-Q4_K_M** (`F:/Models/…, 1524MB, GGUFv3 valid, official template
  verified 9059 chars, official sampling temp 1.0/top_p 0.95/min_p 0.0`):
  degenerates into `))))…` / `escrit…` repetition under b12499 AND b12532
  (latest upstream, isolated `F:/Models/llama-b12532-vulkan`, Nisaba untouched),
  thinking on/off, chat + raw completion. Blocked comparison, not a fair fight:
  needs SGLang (official recommended backend) or future llama.cpp support.
  File retained for retest. RSS ~1.5GB while (non-)serving.
- **Q8_0 question**: `LFM3-1.7B-Q8_0.gguf` (1,846,238,496 bytes, byte-exact,
  `F:/Models`) tested same suite: 24/44 vs 26/44 Q4 — higher quant does not
  fix judgment failures; 1.8× memory unjustified. QAD-Q4_0 variant noted,
  not downloaded (targets quant accuracy, our failures are behavioral).

## 5. Grammar / tools / deferred discovery (probes)

- C1 `response_format:json_schema`: server accepts, model returns EMPTY
  (schema too strict for thinking model) — grammar constrains form, not correctness.
- C2 GBNF on `/completion`: works, returns schema-valid but WRONG label
  (`ABSTAIN` for clear repo-hygiene) — grammar-valid ≠ correct, as mission warns.
- D native function calling: mechanics work (valid `assign_job` calls, JSON args,
  deferred `search_tools` → `repo_status` loop works) but tool **selection**
  accuracy 1/6 with unsafe over-calling (D03 merge+publish, D06 $40 spend
  executed as calls). Tools don't make it abstain; spine stays authoritative.
- Deferred discovery (`defer_loading`): model correctly calls `search_tools`
  first with a good query. Mechanism viable for future scoped use.

## 6. Integration & limits

- Enabled: exactly ONE model job — `secretary-draft` (briefing drafts from live
  DB, UNREVIEWED watermark, human review mandatory), behind
  `MINIMOO_CAP_SECRETARY_DRAFT=1` (default off). Live demo produced a 42-word
  draft with all 4 jobs/states correct. All other model caps remain disabled
  by scoped flags (`MINIMOO_CAP_*`, default 0); deterministic spine untouched.
- GPU-unavailable: `ChatError` fails closed (tested); deterministic jobs continue.
- Learning log: `eval_feedback` table + `minimoo feedback[.log|-list]`
  (decision/correction/failure/approval/outcome) — no training infra.
- Limits: routing/tool-selection unsafe unsupervised; JSON extraction needs
  thinking-off + budget; MiniCPM5 unservable here; BM rate limits observed.

## 7. GPU performance (this mission)

LFM3-Q4 Vulkan chat: ~128 t/s gen, ~290 t/s prompt warm (~35 cold), RSS 1.2–1.4GB;
Q8 RSS ~2.0GB; MiniCPM5 ~1.5GB RSS while degenerating. Server build b12499
(+ isolated b12532 for the MiniCPM5 retest). Full logs in `~/.minimoo/`.
