"""Module 3 - Isolation Forest anomaly detector vs a static-threshold baseline."""
import time, json, joblib
import numpy as np, pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score

FEATS = ["cpu_mean","cpu_max","cpu_std","mem_mean","mem_max","disk_r","disk_w","net_s","net_r",
         "proc_mean","proc_max","temp_mean","cpu_delta","mem_delta","proc_delta"]

def static_rules(df):
    """What a basic monitoring tool does: fixed limits."""
    return ((df.cpu_mean > 80) | (df.mem_mean > 85) | (df.proc_mean > 400) | (df.temp_mean > 85)).astype(int)

def metrics(y, p, score=None):
    tn, fp, fn, tp = confusion_matrix(y, p, labels=[0,1]).ravel()
    return dict(precision=precision_score(y,p,zero_division=0), recall=recall_score(y,p), f1=f1_score(y,p),
                fpr=fp/(fp+tn), tp=int(tp), fp=int(fp), fn=int(fn), tn=int(tn))

def main():
    df = pd.read_csv("data/features.csv")
    cut = len(df)//2                       # first day = training, second day = testing
    tr, te = df.iloc[:cut], df.iloc[cut:]
    sc = StandardScaler().fit(tr[FEATS])
    model = IsolationForest(n_estimators=200, contamination=0.04, random_state=42).fit(sc.transform(tr[FEATS]))
    t0 = time.perf_counter()
    pred = (model.predict(sc.transform(te[FEATS])) == -1).astype(int)
    lat_ms = (time.perf_counter()-t0)/len(te)*1000
    score = -model.score_samples(sc.transform(te[FEATS]))
    y = te.label.values
    out = {"isolation_forest": metrics(y, pred), "static_rules": metrics(y, static_rules(te).values)}
    out["isolation_forest"]["auc"] = float(roc_auc_score(y, score))
    out["isolation_forest"]["latency_ms_per_window"] = lat_ms
    out["train_windows"], out["test_windows"] = len(tr), len(te)
    out["test_anomalous_windows"] = int(y.sum())
    # per fault-type recall
    te = te.assign(pred=pred, rule=static_rules(te).values, score=score)
    per = {}
    for f, g in te[te.label==1].groupby("fault_name"):
        per[f] = dict(windows=len(g), iforest=float(g.pred.mean()), rules=float(g.rule.mean()))
    out["per_fault"] = per
    te.to_csv("results/test_predictions.csv", index=False)
    joblib.dump((sc, model), "data/model.joblib")
    json.dump(out, open("results/ml_results.json","w"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))

if __name__ == "__main__":
    main()
