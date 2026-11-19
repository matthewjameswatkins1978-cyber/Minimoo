"""Minimoo configuration — Windows-friendly, stdlib only."""
from __future__ import annotations
import os
from dataclasses import dataclass, field

DEFAULT_PORT = 3737
DEFAULT_HOST = "127.0.0.1"

# Reuse existing Nisaba runtime/model intact. Never copy or move them.
DEFAULT_LLAMA_SERVER = r"D:\Nisaba-dev\runtime\b12499-vulkan\llama-server.exe"
DEFAULT_MODEL = r"D:\Nisaba-dev\models\LFM3-1.7B-Q4_K_M.gguf"

def data_dir() -> str:
    return os.environ.get("MINIMOO_DATA", os.path.join(os.path.expanduser("~"), ".minimoo"))

@dataclass
class MinimooConfig:
    data_dir: str = field(default_factory=data_dir)
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    llama_server: str = DEFAULT_LLAMA_SERVER
    model: str = DEFAULT_MODEL
    n_ctx: int = 4096
    n_gpu_layers: int = 99
    api_token: str = ""  # set via MINIMOO_TOKEN env; dashboard binds 127.0.0.1 only
    gpu_pause_file: str = ""

    @classmethod
    def load(cls) -> "MinimooConfig":
        d = data_dir()
        return cls(
            data_dir=d,
            host=os.environ.get("MINIMOO_HOST", DEFAULT_HOST),
            port=int(os.environ.get("MINIMOO_PORT", str(DEFAULT_PORT))),
            llama_server=os.environ.get("MINIMOO_LLAMA_SERVER", DEFAULT_LLAMA_SERVER),
            model=os.environ.get("MINIMOO_MODEL", DEFAULT_MODEL),
            n_ctx=int(os.environ.get("MINIMOO_CTX", "4096")),
            n_gpu_layers=int(os.environ.get("MINIMOO_GPU_LAYERS", "99")),
            api_token=os.environ.get("MINIMOO_TOKEN", ""),
            gpu_pause_file=os.path.join(d, "gpu.paused"),
        )

    @property
    def db_path(self) -> str:
        return os.path.join(self.data_dir, "minimoo.db")

    @property
    def outbox_path(self) -> str:
        return os.path.join(self.data_dir, "outbox-pi.md")

    @property
    def log_path(self) -> str:
        return os.path.join(self.data_dir, "minimoo.log")
