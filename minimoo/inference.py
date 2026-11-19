"""GPU inference adapter: llama-server lifecycle + generation.

Reuses the existing Nisaba runtime binary and model file intact.
No constant idle inference: server starts on demand, stops on pause/idle.
CPU fallback is never silent — caller must pass allow_cpu=True explicitly.
"""
from __future__ import annotations
import json
import os
import subprocess
import time
import urllib.request

class InferenceError(Exception):
    pass

class InferenceAdapter:
    def __init__(self, llama_server: str, model: str, host: str = "127.0.0.1",
                 port: int = 19432, n_ctx: int = 4096, n_gpu_layers: int = 99,
                 pause_file: str = ""):
        self.llama_server = llama_server
        self.model = model
        self.host = host
        self.port = port
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.pause_file = pause_file
        self.proc: subprocess.Popen | None = None

    def base(self) -> str:
        return f"http://{self.host}:{self.port}"

    def paused(self) -> bool:
        return bool(self.pause_file) and os.path.exists(self.pause_file)

    def status(self) -> dict:
        running = self.proc is not None and self.proc.poll() is None
        healthy = False
        if running:
            try:
                with urllib.request.urlopen(self.base() + "/health", timeout=3) as r:
                    healthy = r.status == 200
            except Exception:
                healthy = False
        return {"running": running, "healthy": healthy, "paused": self.paused(),
                "model": self.model, "runtime": self.llama_server,
                "pid": self.proc.pid if running else None}

    def start(self, allow_cpu: bool = False) -> dict:
        if self.paused():
            raise InferenceError("GPU work paused for other applications (pause file present)")
        if not os.path.exists(self.llama_server):
            if not allow_cpu:
                raise InferenceError(f"runtime missing: {self.llama_server}")
            raise InferenceError("no CPU fallback binary configured; refusing silent fallback")
        if not os.path.exists(self.model):
            raise InferenceError(f"model missing: {self.model}")
        if self.proc is not None and self.proc.poll() is None:
            return self.status()
        log = os.path.join(os.path.dirname(self.pause_file or "."), "llama-server.log")
        lf = open(log, "ab")
        self.proc = subprocess.Popen(
            [self.llama_server, "-m", self.model, "--host", self.host, "--port",
             str(self.port), "-c", str(self.n_ctx), "-ngl", str(self.n_gpu_layers)],
            stdout=lf, stderr=subprocess.STDOUT)
        # wait for health
        for _ in range(60):
            time.sleep(1.0)
            st = self.status()
            if st["healthy"]:
                return st
            if self.proc.poll() is not None:
                raise InferenceError("llama-server exited during startup; see llama-server.log")
        raise InferenceError("llama-server did not become healthy in 60s")

    def stop(self) -> dict:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=15)
            except Exception:
                self.proc.kill()
        self.proc = None
        return self.status()

    def pause(self, on: bool) -> dict:
        if on:
            self.stop()
            if self.pause_file:
                open(self.pause_file, "w").write(f"paused {time.time()}\n")
        else:
            if self.pause_file and os.path.exists(self.pause_file):
                os.remove(self.pause_file)
        return self.status()

    def generate(self, prompt: str, max_tokens: int = 220, temperature: float = 0.35,
                 timeout: float = 120) -> dict:
        t0 = time.time()
        body = json.dumps({"prompt": prompt, "n_predict": max_tokens,
                           "temperature": temperature, "stream": False}).encode()
        req = urllib.request.Request(self.base() + "/completion", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode())
        except Exception as e:
            raise InferenceError(f"generation failed: {e}")
        dt = time.time() - t0
        text = data.get("content", "")
        gen = data.get("timings", {}).get("predicted_n", max_tokens)
        tps = (gen / dt) if dt > 0 else 0
        return {"text": text, "seconds": round(dt, 2), "tokens": gen,
                "tps": round(tps, 1), "raw": data}
