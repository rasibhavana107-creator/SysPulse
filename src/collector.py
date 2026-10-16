"""Module 1a - Metric collector.
Samples real laptop metrics with psutil and can also generate a labelled
synthetic stream (normal workload + injected faults) for evaluation."""
import time, csv, math, os
import numpy as np

FIELDS = ["ts","host","cpu_pct","mem_pct","disk_read_kb","disk_write_kb",
          "net_sent_kb","net_recv_kb","proc_count","temp_c","label","fault"]

def sample_real(host="laptop-01"):
    import psutil
    io = psutil.disk_io_counters(); nt = psutil.net_io_counters()
    return {"ts": time.time(), "host": host, "cpu_pct": psutil.cpu_percent(interval=0.2),
            "mem_pct": psutil.virtual_memory().percent,
            "disk_read_kb": io.read_bytes/1024 if io else 0, "disk_write_kb": io.write_bytes/1024 if io else 0,
            "net_sent_kb": nt.bytes_sent/1024, "net_recv_kb": nt.bytes_recv/1024,
            "proc_count": len(psutil.pids()), "temp_c": 45.0, "label": 0, "fault": "normal"}

def generate(hours=48, step=10, seed=7, host="laptop-01"):
    """One row every `step` seconds. Normal load follows a daily curve; faults are injected."""
    rng = np.random.default_rng(seed)
    n = int(hours*3600/step); t0 = 1_760_000_000
    rows = []
    for i in range(n):
        ts = t0 + i*step; hr = (ts/3600) % 24
        work = 0.5 + 0.5*math.sin((hr-9)/24*2*math.pi)
        cpu = 18 + 22*work + rng.normal(0, 3.5)
        mem = 48 + 8*work + rng.normal(0, 1.5)
        rows.append(dict(ts=ts, host=host, cpu_pct=cpu, mem_pct=mem,
            disk_read_kb=max(0, 220+150*work+rng.normal(0,60)), disk_write_kb=max(0, 180+120*work+rng.normal(0,50)),
            net_sent_kb=max(0, 90+60*work+rng.normal(0,25)), net_recv_kb=max(0, 260+120*work+rng.normal(0,70)),
            proc_count=int(210+12*work+rng.normal(0,4)), temp_c=46+0.35*(cpu-30)+rng.normal(0,0.8),
            label=0, fault="normal"))
    def inject(name, dur, count):
        starts = rng.choice(np.arange(60, n-dur-60, 1), size=count, replace=False)
        for s in starts:
            for j in range(dur):
                r = rows[s+j]
                if r["label"]: continue
                r["label"] = 1; r["fault"] = name
                if name == "cpu_spike":    r["cpu_pct"] = min(100, r["cpu_pct"]+45+rng.normal(0,5)); r["temp_c"] += 14
                if name == "memory_leak":  r["mem_pct"] = min(99, r["mem_pct"]+ (j+1)*(30/dur))
                if name == "disk_thrash":  r["disk_write_kb"] *= 9; r["disk_read_kb"] *= 6; r["cpu_pct"] += 10
                if name == "net_exfil":    r["net_sent_kb"] *= 14; r["proc_count"] += 6
                if name == "fork_bomb":    r["proc_count"] += (j+1)*18; r["cpu_pct"] = min(100, r["cpu_pct"]+30)
    inject("cpu_spike", 9, 14); inject("memory_leak", 30, 6); inject("disk_thrash", 8, 10)
    inject("net_exfil", 8, 9);  inject("fork_bomb", 8, 5)
    return rows

def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
        for r in rows: w.writerow({k: (round(v,3) if isinstance(v,float) else v) for k,v in r.items()})

if __name__ == "__main__":
    rows = generate(); write_csv(rows, "data/raw_metrics.csv")
    print(len(rows), "rows;", sum(r["label"] for r in rows), "anomalous samples")
    print("real sample:", sample_real())
