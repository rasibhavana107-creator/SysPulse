"""Module 2 - Local 'cloud' backend: HTTP ingestion API + SQLite store + live scoring.
Runs entirely on the laptop (127.0.0.1) and mimics a small cloud service."""
import json, sqlite3, time, threading, joblib, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
from security import AGENT_KEYS, MAX_BODY, sign, validate, RateLimiter, NonceCache, AuditLedger
from anomaly import FEATS
import hmac

class Backend:
    def __init__(self, db_path, audit_path, model_path="data/model.joblib", rate=50.0, burst=100):
        for p in (db_path, audit_path):
            if os.path.exists(p): os.remove(p)
        self.db = sqlite3.connect(db_path, check_same_thread=False); self.lock = threading.Lock()
        self.db.execute("CREATE TABLE metrics(id INTEGER PRIMARY KEY, ts REAL, agent TEXT, payload TEXT, score REAL, is_anomaly INT)")
        self.db.execute("CREATE TABLE alerts(id INTEGER PRIMARY KEY, ts REAL, agent TEXT, severity TEXT, message TEXT)")
        self.scaler, self.model = joblib.load(model_path)
        self.audit = AuditLedger(audit_path); self.rl = RateLimiter(rate, burst); self.nonces = NonceCache()
        self.counters = dict(accepted=0, rejected=0)
    def score(self, p):
        x = self.scaler.transform([[p[f] for f in FEATS]])
        return float(-self.model.score_samples(x)[0]), int(self.model.predict(x)[0] == -1)
    def store(self, agent, p):
        s, a = self.score(p)
        with self.lock:
            self.db.execute("INSERT INTO metrics(ts,agent,payload,score,is_anomaly) VALUES(?,?,?,?,?)",
                            (time.time(), agent, json.dumps(p), s, a))
            if a:
                sev = "CRITICAL" if s > 0.62 else "WARNING"
                self.db.execute("INSERT INTO alerts(ts,agent,severity,message) VALUES(?,?,?,?)",
                    (time.time(), agent, sev, f"anomaly score {s:.3f} cpu={p['cpu_mean']} mem={p['mem_mean']} proc={p['proc_mean']}"))
            self.db.commit()
        return s, a

def make_handler(be: Backend):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, obj):
            b = json.dumps(obj).encode(); self.send_response(code)
            self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b)))
            self.end_headers(); self.wfile.write(b)
        def _reject(self, code, reason, agent="-"):
            be.counters["rejected"] += 1; be.audit.record("REJECTED", agent, f"{code} {reason}")
            self._send(code, {"error": reason})
        def do_GET(self):
            if self.path == "/health": return self._send(200, {"status": "ok", **be.counters})
            if self.path == "/alerts":
                rows = be.db.execute("SELECT ts,severity,message FROM alerts ORDER BY id DESC LIMIT 10").fetchall()
                return self._send(200, {"alerts": rows})
            self._send(404, {"error": "not found"})
        def do_POST(self):
            if self.path != "/ingest": return self._send(404, {"error": "not found"})
            agent = self.headers.get("X-Agent-Id", ""); ts = self.headers.get("X-Timestamp", "")
            nonce = self.headers.get("X-Nonce", ""); sig = self.headers.get("X-Signature", "")
            try: n = int(self.headers.get("Content-Length", "0"))
            except ValueError: return self._reject(400, "bad content-length", agent)
            if n > MAX_BODY or n <= 0: return self._reject(413, "body size not allowed", agent)
            body = self.rfile.read(n)
            key = AGENT_KEYS.get(agent)
            if not key: return self._reject(401, "unknown agent", agent)
            if not be.rl.allow(agent): return self._reject(429, "rate limit exceeded", agent)
            try: fresh = abs(time.time() - float(ts)) <= 300
            except ValueError: fresh = False
            if not fresh: return self._reject(401, "stale or invalid timestamp", agent)
            if not hmac.compare_digest(sig, sign(key, body, ts, nonce)): return self._reject(401, "bad signature", agent)
            if not be.nonces.check_and_add(nonce): return self._reject(409, "replayed request", agent)
            try: p = json.loads(body)
            except Exception: return self._reject(400, "malformed json", agent)
            ok, why = validate(p)
            if not ok: return self._reject(422, why, agent)
            s, a = be.store(agent, p); be.counters["accepted"] += 1
            if a: be.audit.record("ANOMALY_ALERT", agent, f"score={s:.3f}")
            self._send(200, {"score": round(s, 4), "anomaly": bool(a)})
    return H

def start(be, port=8765):
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(be))
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv
