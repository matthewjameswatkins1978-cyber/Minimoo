"""Correct LFM3 inference harness: chat-completions + official ChatML template.

Server must be started with Liquid's recommended agent configuration:
  --jinja --temp 0.1 --top-k 50 --repeat-penalty 1.1
Template is taken from the GGUF (verified: official LFM3 markers present).
Reasoning (<think>) is separated from the final answer; graders never see it.
"""
from __future__ import annotations
import json
import re
import urllib.request

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
REQUIRED_MARKERS = ["<|im_start|>", "preserve_thinking", "enable_thinking",
                    "tool_call", "defer_loading", "additional_tools",
                    "CONTINUE_FINAL_MESSAGE_TAG"]

class ChatError(Exception):
    pass

def template_check(props: dict) -> dict:
    """Verify the server actually applied the official LFM3 template."""
    t = props.get("chat_template", "") or ""
    missing = [m for m in REQUIRED_MARKERS if m not in t]
    return {"template_len": len(t), "missing": missing, "official": not missing}

def split_reasoning(text: str) -> tuple[str, str]:
    """Return (thinking, answer). Thinking defaults on per official template."""
    m = re.search(r"<think>(.*?)</think>", text or "", re.DOTALL)
    thinking = m.group(1).strip() if m else ""
    answer = THINK_RE.sub("", text or "").strip()
    return thinking, answer

class ChatClient:
    def __init__(self, base: str = "http://127.0.0.1:19432",
                 model_id: str = "LFM3-1.7B"):
        self.base = base.rstrip("/")
        self.model_id = model_id

    def _post(self, path: str, payload: dict, timeout: float = 300) -> dict:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(self.base + path, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            raise ChatError(f"{path} failed: {e}")

    def props(self) -> dict:
        try:
            with urllib.request.urlopen(self.base + "/props", timeout=15) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            raise ChatError(f"/props failed: {e}")

    def chat(self, messages: list[dict], max_tokens: int = 512,
             temperature: float = 0.1, top_k: int = 50,
             repeat_penalty: float = 1.1, thinking: bool | None = None,
             tools: list | None = None, tool_choice: str | None = None,
             timeout: float = 300, top_p: float | None = None,
             min_p: float | None = None) -> dict:
        payload: dict = {"model": self.model_id, "messages": messages,
                         "max_tokens": max_tokens, "temperature": temperature,
                         "top_k": top_k, "repeat_penalty": repeat_penalty,
                         "stream": False}
        if top_p is not None:
            payload["top_p"] = top_p
        if min_p is not None:
            payload["min_p"] = min_p
        if thinking is not None:
            payload["enable_thinking"] = thinking
        if tools is not None:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"
        data = self._post("/v1/chat/completions", payload, timeout)
        try:
            msg = data["choices"][0]["message"]
        except (KeyError, IndexError):
            raise ChatError(f"unexpected chat response: {str(data)[:300]}")
        raw_content = msg.get("content") or ""
        # llama.cpp surfaces thinking in a dedicated field; inline <think>
        # parsing is only the fallback (older builds / plain completions).
        thinking_text = (msg.get("reasoning_content") or msg.get("thinking")
                         or msg.get("reasoning") or "")
        if thinking_text:
            thinking_text = thinking_text.strip()
            answer = THINK_RE.sub("", raw_content).strip()
        else:
            thinking_text, answer = split_reasoning(raw_content)
        out = {"thinking": thinking_text, "answer": answer,
               "tool_calls": msg.get("tool_calls") or [],
               "usage": data.get("usage", {}), "timings": data.get("timings", {}),
               "raw": data}
        if tools and not out["tool_calls"]:
            out["tool_calls"] = parse_xml_tool_calls(raw_content)
            if out["tool_calls"]:
                out["answer"] = THINK_RE.sub("", out["answer"]).strip()
        return out

XML_CALL_RE = re.compile(
    r"<tool_call>\s*<function=(?P<fn>[^\s>]+)>\s*"
    r"(?P<params>(?:<parameter=.*?</parameter>\s*)*)"
    r"</function>\s*</tool_call>", re.DOTALL)
XML_PARAM_RE = re.compile(
    r"<parameter=(?P<k>[^\s>]+)>\s*(?P<v>.*?)</parameter>", re.DOTALL)

def parse_xml_tool_calls(text: str) -> list[dict]:
    """Fallback parser for LFM3 native XML tool calls."""
    calls = []
    for m in XML_CALL_RE.finditer(text or ""):
        args: dict = {}
        for p in XML_PARAM_RE.finditer(m.group("params")):
            v = p.group("v").strip()
            try:
                args[p.group("k")] = json.loads(v)
            except Exception:
                args[p.group("k")] = v
        calls.append({"function": {"name": m.group("fn"), "arguments": args}})
    return calls
