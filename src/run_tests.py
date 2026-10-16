import json, time, sqlite3, statistics as st
import numpy as np, pandas as pd
from anomaly import FEATS
from cloud_api import Backend, start
from agent import post
from security import AGENT_KEYS, sign
import uuid

te = pd.read_csv("results/test_predictions.csv")
def payload(r): 
    d = {f: float(r[f]) for f in FEATS}; d["host"] = "laptop-01"; return json.dumps(d).encode()
res = {}

# ---- A. live detection + throughput through the API
be = Backend("data/cloud.db", "data/audit_a.db", rate=5000, burst=5000); srv = start(be, 8765)
lat, pred = [], []
t0 = time.time()
for _, r in te.iterrows():
    t1 = time.perf_counter(); code, out = post(payload(r)); lat.append((time.perf_counter()-t1)*1000)
    assert code == 200, (code, out); pred.append(int(out["anomaly"]))
tot = time.time()-t0
y = te.label.values; p = np.array(pred); tp=int(((p==1)&(y==1)).sum()); fp=int(((p==1)&(y==0)).sum()); fn=int(((p==0)&(y==1)).sum())
res["api"] = dict(requests=len(lat), seconds=round(tot,2), req_per_sec=round(len(lat)/tot,1),
    mean_ms=round(st.mean(lat),2), p50_ms=round(float(np.percentile(lat,50)),2), p95_ms=round(float(np.percentile(lat,95)),2),
    p99_ms=round(float(np.percentile(lat,99)),2), tp=tp, fp=fp, fn=fn, precision=round(tp/(tp+fp),3), recall=round(tp/(tp+fn),3),
    alerts=be.db.execute("SELECT COUNT(*) FROM alerts").fetchone()[0],
    critical=be.db.execute("SELECT COUNT(*) FROM alerts WHERE severity='CRITICAL'").fetchone()[0],
    db_rows=be.db.execute("SELECT COUNT(*) FROM metrics").fetchone()[0])
res["api_latencies"] = lat
res["sample_alerts"] = be.db.execute("SELECT severity,message FROM alerts ORDER BY id DESC LIMIT 4").fetchall()
srv.shutdown(); srv.server_close()

# ---- B. security scenarios
be = Backend("data/cloud_b.db", "data/audit_b.db", rate=10, burst=60); srv = start(be, 8766)
URL = "http://127.0.0.1:8766/ingest"; good = payload(te.iloc[0]); K = AGENT_KEYS["agent-laptop-01"]
def bad(upd): d = json.loads(good); d.update(upd); return json.dumps(d).encode()
d_missing = json.loads(good); d_missing.pop("cpu_mean")
tests = []
def run(name, expect, fn, n=1):
    codes = [fn()[0] for _ in range(n)]
    tests.append(dict(name=name, expected=expect, got=codes[0], ok=all(c == expect for c in codes), n=n))
run("Valid signed request", 200, lambda: post(good, url=URL))
run("Tampered body (signature mismatch)", 401, lambda: post(good, url=URL, sig=sign(K, bad({"cpu_mean": 1}), str(time.time()), "n")), 1)
ts_x = str(time.time()); n_x = uuid.uuid4().hex
run("Wrong signing key", 401, lambda: post(good, url=URL, key=b"wrong-key"), 3)
run("Unknown agent id", 401, lambda: post(good, agent="agent-evil", url=URL), 3)
fixed_ts, fixed_n = str(time.time()), uuid.uuid4().hex
post(good, url=URL, ts=fixed_ts, nonce=fixed_n)
run("Replay of a captured request", 409, lambda: post(good, url=URL, ts=fixed_ts, nonce=fixed_n), 3)
run("Stale timestamp (1 hour old)", 401, lambda: post(good, url=URL, ts=str(time.time()-3600)), 3)
run("Malformed JSON body", 400, lambda: post(b"{not json", url=URL), 3)
run("Out-of-range value (cpu_mean=900)", 422, lambda: post(bad({"cpu_mean": 900}), url=URL), 3)
run("String injected in numeric field", 422, lambda: post(bad({"mem_mean": "1; DROP TABLE metrics"}), url=URL), 3)
run("Unknown extra field", 422, lambda: post(bad({"cmd": "rm -rf /"}), url=URL), 3)
run("Missing required field", 422, lambda: post(json.dumps(d_missing).encode(), url=URL), 3)
run("Oversized body (20 KB)", 413, lambda: post(b"x"*20000, url=URL), 3)
# flood
time.sleep(1.5)
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(32) as ex: codes = list(ex.map(lambda _: post(good, url=URL)[0], range(300)))
res["flood"] = dict(sent=300, ok=codes.count(200), limited=codes.count(429), other=len(codes)-codes.count(200)-codes.count(429))
res["security_tests"] = tests
# ---- C. audit ledger tamper
ok_before, _ = be.audit.verify(); n_entries = be.audit.count()
be.audit.db.execute("UPDATE audit SET detail='nothing happened' WHERE idx=5"); be.audit.db.commit()
ok_after, bad_idx = be.audit.verify()
res["audit"] = dict(entries=n_entries, ok_before=ok_before, ok_after_tamper=ok_after, detected_at=bad_idx)
srv.shutdown(); srv.server_close()
json.dump(res, open("results/system_results.json", "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "api_latencies"}, indent=1))
