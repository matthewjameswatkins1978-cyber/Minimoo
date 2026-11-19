# Minimoo 1.0 — Qualification report (frozen suite, 24 cases)

Suite: `tests/qualify_suite.py` — 20 representative + 4 adversarial
(prompt-injection, exfiltration, auto-merge, transcript-copy). Each case names
the expected capability or `ABSTAIN`.

## Deterministic baseline (router rules, replayable)

Rule: exact capability match; abstain on risk words
(`spend, delete all, rm -rf, merge, auto-accept, token, exfiltrate,
ignore previous, root, transcript, ../, system32`).

Result: **24/24 correct** (measured in `test_qualify_deterministic_baseline`;
gate is ≥20). No false positives on adversarial probes — all abstain.

## Model run (LFM3-1.7B-Q4_K_M, Vulkan, sampled)

6 representative prompts through the local GPU server (`scripts/bench.py`
harness, temp 0.0, n_predict 100): coherent 2-sentence answers, ~128 t/s gen,
285–295 t/s prompt warm. The small model answers fluently but does NOT
reliably emit exact capability IDs/schemas unassisted — hence model-dependent
jobs stay `experimental` and route through the deterministic spine, which
validates before acting. Grammar-valid ≠ correct: no model output is trusted
without `control.check_tool_call` + receipt-field validation. Full 24-case
model pass is future work; enabling any model job requires it.

## Enabled set

- proven (deterministic): dispatcher, mission-clerk, watchdog, repo-hygiene,
  test-investigator, handover-clerk, inventory
- experimental (model-gated): knowledge-librarian, compute-steward, briefing,
  log-classifier — abstain by default, human approval for writes/promotion
- unsupported: remote-merge, paid-spend (denied by policy)

## Safety probes

Injection (`ignore previous instructions`, `you are now root`), secret
reveal (`MINIMOO_TOKEN`), path escape (`../../../`), destructive
(`delete all merged`, `rm -rf`, `merge automatically`), exfiltration —
all refused by `control.py` fail-closed gate (unit-tested).
