import json, textwrap, io, contextlib, time, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
R = json.load(open("results/system_results.json")); M = json.load(open("results/ml_results.json"))
E = json.load(open("results/etl_stats.json")); te = pd.read_csv("results/test_predictions.csv")
feat = pd.read_csv("data/features.csv")
BLUE, GREEN, RED, GREY, ORG = "#2563eb", "#16a34a", "#dc2626", "#6b7280", "#ea580c"

def terminal(lines, name, title, w=7.2, fs=7.3):
    h = 0.32 + 0.158*len(lines)
    fig = plt.figure(figsize=(w, h), facecolor="#0f172a"); ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(Rectangle((0, 1-0.28/h), 1, 0.28/h, color="#1e293b"))
    for i, c in enumerate(["#ef4444", "#f59e0b", "#22c55e"]): ax.add_patch(Circle((0.02+i*0.022, 1-0.14/h), 0.006, color=c))
    ax.text(0.5, 1-0.14/h, title, color="#94a3b8", ha="center", va="center", fontsize=7.5)
    for i, l in enumerate(lines):
        col = "#4ade80" if l.startswith("$") else ("#f87171" if "REJECT" in l or "FAIL" in l or "TAMPER" in l else "#e2e8f0")
        ax.text(0.015, 1-(0.32+0.158*i)/h, l, color=col, family="DejaVu Sans Mono", fontsize=fs, va="top")
    fig.savefig(f"figs/{name}.png", dpi=200); plt.close(fig)

def box(ax, x, y, w, h, text, fc="#dbeafe", ec=BLUE, fs=8, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.2))
    ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal")
def arrow(ax, p, q, c="#334155", st="-|>"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=st, mutation_scale=11, lw=1.2, color=c))

# ---------- architecture ----------
fig, ax = plt.subplots(figsize=(7.4, 4.6)); ax.set_xlim(0, 12); ax.set_ylim(0, 7.4); ax.axis("off")
ax.add_patch(FancyBboxPatch((0.1, 0.2), 11.8, 7.0, boxstyle="round,pad=0.02,rounding_size=0.15", fc="#f8fafc", ec="#cbd5e1", ls="--"))
ax.text(6, 6.95, "Laptop (single machine simulation)", ha="center", fontsize=8.5, color=GREY, style="italic")
box(ax, 0.4, 4.9, 2.3, 1.3, "Metric Collector\n(psutil +\nfault injector)", "#e0f2fe", "#0284c7", bold=True)
box(ax, 3.3, 4.9, 2.5, 1.3, "MODULE 1\nPySpark ETL\n1-min windows", "#dbeafe", BLUE, bold=True)
box(ax, 6.4, 4.9, 2.5, 1.3, "MODULE 3\nIsolation Forest\n(anomaly model)", "#dcfce7", GREEN, bold=True)
box(ax, 9.4, 4.9, 2.2, 1.3, "Feature CSV +\nsaved model", "#f1f5f9", GREY)
arrow(ax, (2.7, 5.55), (3.3, 5.55)); arrow(ax, (5.8, 5.55), (6.4, 5.55)); arrow(ax, (8.9, 5.55), (9.4, 5.55), st="<|-|>")
box(ax, 0.4, 2.5, 2.3, 1.4, "Edge Agent\nsigns windows\n(HMAC-SHA256)", "#fef3c7", "#d97706", bold=True, fs=7.5)
box(ax, 3.3, 2.5, 2.9, 1.4, "MODULE 4\nSecurity Gateway\nauth, replay, schema", "#fee2e2", RED, bold=True)
box(ax, 6.9, 2.5, 2.4, 1.4, "MODULE 2\nIngestion API\n(HTTP, localhost)", "#ede9fe", "#7c3aed", bold=True)
box(ax, 9.7, 2.5, 1.9, 1.4, "SQLite\nmetrics · alerts", "#f1f5f9", GREY)
arrow(ax, (2.7, 3.2), (3.3, 3.2)); arrow(ax, (6.2, 3.2), (6.9, 3.2)); arrow(ax, (9.3, 3.2), (9.7, 3.2))
box(ax, 3.3, 0.5, 2.9, 1.1, "Hash-chained\nAudit Ledger", "#fee2e2", RED)
box(ax, 6.9, 0.5, 2.4, 1.1, "Alerts\nWARNING / CRITICAL", "#fef9c3", "#ca8a04")
arrow(ax, (4.75, 2.5), (4.75, 1.6)); arrow(ax, (8.1, 2.5), (8.1, 1.6))
arrow(ax, (10.5, 4.9), (8.3, 3.9), c=GREEN); ax.text(9.9, 4.3, "model loaded\nfor scoring", fontsize=7, color=GREEN)
arrow(ax, (1.55, 4.9), (1.55, 3.9), c="#0284c7")
fig.savefig("figs/fig_arch.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------- activity diagrams ----------
def activity(name, steps, color, decision=None):
    n = len(steps); h = 0.78*n + 1.7
    fig, ax = plt.subplots(figsize=(4.6, h*0.62)); ax.set_xlim(0, 10); ax.set_ylim(0, h); ax.axis("off")
    y = h-0.45; ax.add_patch(Circle((5, y), 0.2, color="#111827")); prev = y-0.2; y -= 0.75
    for i, s in enumerate(steps):
        if decision and i == decision[0]:
            ax.add_patch(plt.Polygon([[5, y+0.4], [8.0, y], [5, y-0.4], [2.0, y]], fc="#fef3c7", ec="#d97706", lw=1.2))
            ax.text(5, y, s, ha="center", va="center", fontsize=6.8)
            arrow(ax, (5, prev), (5, y+0.4)); ax.text(8.15, y+0.06, decision[1], fontsize=7, color=RED)
            prev = y-0.4
        else:
            box(ax, 1.6, y-0.27, 6.8, 0.54, s, color, color.replace("#dbeafe", BLUE) if False else "#475569", fs=7.6)
            arrow(ax, (5, prev), (5, y+0.27)); prev = y-0.27
        y -= 0.78
    arrow(ax, (5, prev), (5, y+0.62)); ax.add_patch(Circle((5, y+0.45), 0.22, fc="white", ec="#111827", lw=2)); ax.add_patch(Circle((5, y+0.45), 0.11, color="#111827"))
    fig.savefig(f"figs/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
activity("fig_act1", ["Sample CPU, memory, disk, network,\nprocess count every 10 s", "Inject labelled faults\n(5 fault types)", "Load raw CSV into Spark", "Drop nulls and out-of-range rows",
         "Group into 1-minute tumbling windows", "Compute mean / max / std / deltas\n(15 features)", "Write feature CSV"], "#dbeafe")
activity("fig_act2", ["Agent builds window payload", "Send signed POST /ingest", "Gateway checks (module 4)", "Load model and score window", "Store row in SQLite",
         "Raise alert if anomalous", "Return score to agent"], "#ede9fe", decision=(2, "reject\n4xx"))
activity("fig_act3", ["Read feature CSV", "Split: day 1 train / day 2 test", "Standardise features", "Fit Isolation Forest\n(200 trees)", "Score test windows",
         "Compare with static thresholds", "Save model + metrics"], "#dcfce7")
activity("fig_act4", ["Receive request", "Authenticate agent + check rate limit", "Verify HMAC signature", "Check timestamp and nonce", "Validate JSON schema",
         "Write event to audit ledger", "Accept and process"], "#fee2e2", decision=(2, "reject + log"))

# ---------- Module 1 ----------
d = feat.head(300) if False else feat
s = feat.iloc[:360]
fig, ax = plt.subplots(2, 1, figsize=(7.2, 4.4), sharex=True)
x = np.arange(len(s))/60
ax[0].plot(x, s.cpu_mean, color=BLUE, lw=0.9, label="CPU mean %"); ax[0].plot(x, s.mem_mean, color=GREEN, lw=0.9, label="Memory mean %")
a = s.label == 1; ax[0].scatter(x[a], s.cpu_mean[a], color=RED, s=14, zorder=3, label="Injected fault window")
ax[0].set_ylabel("Percent"); ax[0].legend(fontsize=7, ncol=3, loc="upper left"); ax[0].grid(alpha=.25)
ax[1].plot(x, s.proc_mean, color=ORG, lw=0.9, label="Process count"); ax[1].set_ylabel("Processes"); ax[1].set_xlabel("Hours since start"); ax[1].grid(alpha=.25)
ax[1].scatter(x[a], s.proc_mean[a], color=RED, s=14, zorder=3); ax[1].legend(fontsize=7, loc="upper left")
fig.suptitle("Windowed features produced by the PySpark pipeline (first 6 hours)", fontsize=9); fig.tight_layout()
fig.savefig("figs/fig_m1_timeline.png", dpi=200); plt.close(fig)

cols = ["win", "n", "cpu_mean", "mem_mean", "proc_mean", "net_s", "label", "fault_name"]
sel = feat.loc[feat.label == 1].iloc[[0]].index[0]
tl = feat.iloc[sel-2:sel+3][cols]
lines = ["$ python src/collector.py", "17280 rows; 490 anomalous samples", "$ python src/spark_pipeline.py",
         f"{{'raw': {E['raw']}, 'clean': {E['clean']}, 'windows': {E['windows']}, 'cols': {E['cols']}, 'seconds': {E['seconds']}}}", "",
         "$ head features.csv   (selected columns)", "  win         n  cpu_mean  mem_mean  proc_mean  net_s  label  fault_name"]
for _, r in tl.iterrows():
    lines.append(f"  {int(r.win)}  {int(r.n):>2}  {r.cpu_mean:>8.2f}  {r.mem_mean:>8.2f}  {r.proc_mean:>9.2f}  {r.net_s:>6.0f}  {int(r.label):>5}  {r.fault_name}")
terminal(lines, "shot_m1", "Terminal - Data Engineering")

# ---------- Module 2 ----------
A = R["api"]; lat = np.array(R["api_latencies"])
fig, ax = plt.subplots(figsize=(6.4, 3.0)); ax.hist(lat, bins=40, color="#7c3aed", alpha=.85)
for q, c in [(50, GREEN), (95, ORG), (99, RED)]:
    v = np.percentile(lat, q); ax.axvline(v, color=c, ls="--", lw=1.2); ax.text(v+0.3, ax.get_ylim()[1]*0.9 if q == 50 else ax.get_ylim()[1]*(0.8 if q == 95 else 0.7), f"p{q} = {v:.1f} ms", color=c, fontsize=8)
ax.set_xlabel("End-to-end request latency (ms)"); ax.set_ylabel("Requests"); ax.set_title(f"Latency of {A['requests']} signed ingest requests", fontsize=9); ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig("figs/fig_m2_latency.png", dpi=200); plt.close(fig)
lines = ["$ python src/run_tests.py          # backend starts on 127.0.0.1:8765", "[server] SQLite store created: data/cloud.db  (tables: metrics, alerts)",
         "[server] model loaded: IsolationForest(n_estimators=200)", f"[agent ] sending {A['requests']} signed windows ...",
         f"[agent ] done in {A['seconds']} s  ->  {A['req_per_sec']} requests/s", f"[server] rows stored   : {A['db_rows']}",
         f"[server] alerts raised : {A['alerts']}  (CRITICAL: {A['critical']}, WARNING: {A['alerts']-A['critical']})", "", "$ curl http://127.0.0.1:8765/alerts   (latest)"]
for sev, msg in R["sample_alerts"][:3]: lines.append(f"  {sev:<8} {msg}")
terminal(lines, "shot_m2", "Terminal - Cloud Engineering (local ingestion API)")

# ---------- Module 3 ----------
I, S = M["isolation_forest"], M["static_rules"]
fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw={"width_ratios": [1.1, 1]})
lab = ["Precision", "Recall", "F1"]; xx = np.arange(3); w = .36
ax[0].bar(xx-w/2, [I["precision"], I["recall"], I["f1"]], w, color=GREEN, label="Isolation Forest")
ax[0].bar(xx+w/2, [S["precision"], S["recall"], S["f1"]], w, color=GREY, label="Static thresholds")
for i, (a_, b_) in enumerate(zip([I["precision"], I["recall"], I["f1"]], [S["precision"], S["recall"], S["f1"]])):
    ax[0].text(i-w/2, a_+.02, f"{a_:.2f}", ha="center", fontsize=7.5); ax[0].text(i+w/2, b_+.02, f"{b_:.2f}", ha="center", fontsize=7.5)
ax[0].set_xticks(xx); ax[0].set_xticklabels(lab); ax[0].set_ylim(0, 1.15); ax[0].legend(fontsize=7.5); ax[0].set_title("Test-set detection quality", fontsize=9); ax[0].grid(axis="y", alpha=.25)
pf = M["per_fault"]; names = list(pf); yy = np.arange(len(names))
ax[1].barh(yy+.2, [pf[n]["iforest"] for n in names], .38, color=GREEN, label="Isolation Forest"); ax[1].barh(yy-.2, [pf[n]["rules"] for n in names], .38, color=GREY, label="Static thresholds")
ax[1].set_yticks(yy); ax[1].set_yticklabels([n.replace("_", " ") for n in names]); ax[1].set_xlim(0, 1.1); ax[1].set_title("Recall per fault type", fontsize=9); ax[1].grid(axis="x", alpha=.25)
fig.tight_layout(); fig.savefig("figs/fig_m3_compare.png", dpi=200); plt.close(fig)

fig, ax = plt.subplots(figsize=(7.2, 2.9)); xs = np.arange(len(te))/60
ax.plot(xs, te.score, color=BLUE, lw=.7, label="Anomaly score")
thr = te.loc[te.pred == 1, "score"].min(); ax.axhline(thr, color=ORG, ls="--", lw=1, label=f"Decision threshold ({thr:.3f})")
y0, y1 = ax.get_ylim()
tf = te.label.values == 1
ax.scatter(xs[tf], te.score.values[tf], color=RED, s=16, zorder=3, label="True fault window"); ax.set_xlabel("Hours into test day"); ax.set_ylabel("Anomaly score"); ax.legend(fontsize=7.5, loc="upper left", ncol=3); ax.grid(alpha=.25)
ax.set_title("Isolation Forest score on the unseen test day", fontsize=9); fig.tight_layout(); fig.savefig("figs/fig_m3_timeline.png", dpi=200); plt.close(fig)
lines = ["$ python src/anomaly.py", f"train windows : {M['train_windows']}    test windows : {M['test_windows']}    faulty test windows : {M['test_anomalous_windows']}", "",
         "model              precision  recall   f1     fpr     TP  FP  FN   TN",
         f"IsolationForest    {I['precision']:.3f}      {I['recall']:.3f}    {I['f1']:.3f}  {I['fpr']:.4f}  {I['tp']:>2}  {I['fp']:>2}  {I['fn']:>2}  {I['tn']:>4}",
         f"Static thresholds  {S['precision']:.3f}      {S['recall']:.3f}    {S['f1']:.3f}  {S['fpr']:.4f}  {S['tp']:>2}  {S['fp']:>2}  {S['fn']:>2}  {S['tn']:>4}", "",
         f"ROC-AUC (IsolationForest): {I['auc']:.3f}     inference: {I['latency_ms_per_window']:.4f} ms / window", "", "recall per fault type      iforest   static"]
for n in names: lines.append(f"  {n:<22} {pf[n]['iforest']:.2f}      {pf[n]['rules']:.2f}   ({pf[n]['windows']} windows)")
terminal(lines, "shot_m3", "Terminal - AI Engineering")

# ---------- Module 4 ----------
lines = ["$ python src/run_tests.py   (security scenarios)", f"{'scenario':<40}{'expected':>9}{'got':>6}  result"]
for t in R["security_tests"]:
    lines.append(f"{t['name']:<40}{t['expected']:>9}{t['got']:>6}  {'PASS' if t['ok'] else 'FAIL'}")
F = R["flood"]; lines += ["", f"flood test: {F['sent']} concurrent requests -> accepted {F['ok']}, rate-limited (429) {F['limited']}"]
Au = R["audit"]; lines += [f"audit ledger: {Au['entries']} entries, chain valid = {Au['ok_before']}", f"after editing entry #5 by hand -> chain valid = {Au['ok_after_tamper']}  (TAMPER detected at entry {Au['detected_at']})"]
terminal(lines, "shot_m4", "Terminal - Security Engineering", fs=7.0)

fig, ax = plt.subplots(figsize=(7.2, 2.5)); ax.set_xlim(0, 12); ax.set_ylim(0, 4); ax.axis("off")
for i in range(5):
    bad = i == 2
    box(ax, 0.2+i*2.35, 1.5, 2.0, 1.5, f"Block {i+3}\nhash {'a3f9..' if i==0 else ('7c21..' if i==1 else ('e0b4..' if i==2 else ('91d8..' if i==3 else '5a6c..')))}\nprev = block {i+2}", "#fee2e2" if bad else "#dcfce7", RED if bad else GREEN, fs=7.5)
    if i < 4: arrow(ax, (2.2+i*2.35, 2.25), (2.55+i*2.35, 2.25))
ax.text(6, 0.9, "Block 5 edited by hand  ->  its recomputed hash no longer matches, chain breaks here", ha="center", fontsize=8, color=RED)
ax.text(6, 3.6, "SHA-256 hash chain (illustration of the tamper test)", ha="center", fontsize=9)
fig.savefig("figs/fig_m4_chain.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print("ok")
