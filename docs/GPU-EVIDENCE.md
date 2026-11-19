# Minimoo 1.0 — GPU evidence (measured 2026-11-19)

## Identity

- Model: `D:\Nisaba-dev\models\LFM3-1.7B-Q4_K_M.gguf` (1,091,380,480 bytes, LFM3 1.7B Q4_K_M, Liquid AI LFM Open License v1.0 — see `D:\Nisaba-dev\licenses\LFM-LICENSE.txt`)
- Runtime: `D:\Nisaba-dev\runtime\b12499-vulkan\llama-server.exe` (build b12499-401563f10), reused intact; `b12499` CPU-only runtime NOT used (no `ggml-vulkan.dll` there)
- GPU: AMD Radeon RX 5700 XT, Vulkan 1.4.315, driver 25.10.30.02, Ryzen 9 3900X 12-core
- Config: `-c 4096 -ngl 99`, endpoint `http://127.0.0.1:19432`

## Measurements

| Run | Prompt t/s | Gen t/s | Notes |
|---|---|---|---|
| CPU runtime (b12499) | 149 | 34 | explicit CPU path; refused as default |
| Vulkan cold (first, cache miss) | 35.6 | 129.9 | prompt eval 67ms/10 tok |
| Vulkan warm 1 | 285.0 | 127.3 | prompt eval 30ms/4 tok (prefix cache) |
| Vulkan warm 2 | 295.1 | 128.0 | stable |

Nisaba lab bench for same model/GPU: 193.5 t/s decode @ n_gen 100 (bench harness, no HTTP/SSE overhead). Our 128 t/s via `/completion` JSON is the honest installed-app number.

## Resources / safety

- `llama-server` RSS: Vulkan 1226–1254 MB vs CPU-only 1872 MB
- Stopped/idle: process exits, 0 MB, GPU freed — no constant idle inference
- Pause: `python -m minimoo gpu --pause on` stops server + writes `%USERPROFILE%\.minimoo\gpu.paused`; `start` refuses while paused (explicit, for gaming/other apps)
- GPU busy/unavailable: `generate()` raises `InferenceError`, never silently falls back to CPU (needs `allow_cpu=True`, and no CPU binary is configured)
