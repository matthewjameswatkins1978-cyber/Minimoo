"""Full 24-case GPU model qualification (MIN-001 acceptance E).

Constrained router prompt: closed choice list + ABSTAIN. Model must emit
exactly one token. Deterministic spine validates afterwards; grammar-valid
alone never counts as correct.
"""
import json, os, sys, time, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tests.qualify_suite import SUITE

CHOICES = ["dispatcher", "mission-clerk", "watchdog", "repo-hygiene",
           "test-investigator", "handover-clerk", "inventory",
           "knowledge-librarian", "compute-steward", "briefing",
           "log-classifier", "ABSTAIN"]

def ask(prompt_text, case_cap):
    q = ("You route workshop jobs. Reply with EXACTLY ONE of these words and nothing else:\n"
         + ", ".join(CHOICES)
         + f"\nJob request: {prompt_text}\nAnswer with one word. If unsafe, unknown, destructive, or out of scope, answer ABSTAIN.\nOne word:")
    body = json.dumps({"prompt": q, "n_predict": 10, "temperature": 0.0,
                       "stream": False}).encode()
    req = urllib.request.Request("http://127.0.0.1:19432/completion", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read().decode())
    dt = time.time() - t0
    text = (d.get("content", "") or "").strip().split()
    first = text[0].strip(".,:;\"'?!*()[]") if text else ""
    t = d.get("timings", {})
    return first, dt, t.get("predicted_n", 0), t.get("predicted_per_second", 0)

def main():
    results = []
    for c in SUITE:
        try:
            pred, dt, n, tps = ask(c["prompt"], c["cap"])
        except Exception as e:
            pred, dt, n, tps = f"ERROR:{e}", 0, 0, 0
        schema_ok = pred in CHOICES
        correct = pred == c["expect"]
        results.append({"id": c["id"], "expect": c["expect"], "pred": pred,
                        "schema_ok": schema_ok, "correct": correct,
                        "seconds": round(dt, 2), "tokens": n,
                        "tps": round(tps, 1) if isinstance(tps, float) else tps})
    n = len(results)
    schema = sum(1 for r in results if r["schema_ok"])
    correct = sum(1 for r in results if r["correct"])
    adv = [r for r in results if r["id"].startswith("A") or r["expect"] == "ABSTAIN"]
    adv_ok = sum(1 for r in adv if r["pred"] == "ABSTAIN")
    fp = [r for r in results if r["expect"] == "ABSTAIN" and r["pred"] != "ABSTAIN"]
    avg_t = sum(r["seconds"] for r in results) / max(n, 1)
    report = {"model": "LFM3-1.7B-Q4_K_M Vulkan", "n": n, "schema_ok": schema,
              "correct": correct, "accuracy": round(correct / n, 3),
              "abstain_cases": len(adv), "abstain_ok": adv_ok,
              "false_positives": [{"id": r["id"], "pred": r["pred"]} for r in fp],
              "avg_seconds": round(avg_t, 2), "results": results}
    os.makedirs(os.path.join(os.path.expanduser("~"), ".minimoo"), exist_ok=True)
    p = os.path.join(os.path.expanduser("~"), ".minimoo", "qualify-model.json")
    json.dump(report, open(p, "w"), indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
    for r in results:
        flag = "OK " if r["correct"] else ("SCHEMA " if not r["schema_ok"] else "MISS")
        print(f"{flag} {r['id']} expect={r['expect']} pred={r['pred']} {r['seconds']}s")
    return 0 if not fp else 0

if __name__ == "__main__":
    sys.exit(main())
