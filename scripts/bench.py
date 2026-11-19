import json, urllib.request, time
for i in range(3):
    t0 = time.time()
    body = json.dumps({"prompt": "Explain in two sentences why backing up files matters.",
                       "n_predict": 100, "temperature": 0.0, "stream": False}).encode()
    req = urllib.request.Request("http://127.0.0.1:19432/completion", data=body,
                                 headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=120)
    d = json.loads(r.read().decode())
    dt = time.time() - t0
    t = d.get("timings", {})
    print(f"run{i} total={dt:.2f}s prompt_tps={t.get('prompt_per_second',0):.1f} gen_tps={t.get('predicted_per_second',0):.1f} n={t.get('predicted_n')}")
    print(d.get("content", "")[:200].replace("\n", " "))
