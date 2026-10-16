"""Module 4 - Security layer: HMAC request signing, replay protection, input validation,
rate limiting and a hash-chained audit ledger."""
import hmac, hashlib, json, time, sqlite3, threading

AGENT_KEYS = {"agent-laptop-01": b"s3cr3t-key-for-laptop-01-demo"}   # demo only; real keys come from a vault
MAX_BODY = 8192
SCHEMA = {  # field -> (min, max)
    "cpu_mean": (0, 100), "cpu_max": (0, 100), "cpu_std": (0, 60), "mem_mean": (0, 100), "mem_max": (0, 100),
    "disk_r": (0, 1e8), "disk_w": (0, 1e8), "net_s": (0, 1e8), "net_r": (0, 1e8),
    "proc_mean": (0, 5000), "proc_max": (0, 5000), "temp_mean": (0, 150),
    "cpu_delta": (-100, 100), "mem_delta": (-100, 100), "proc_delta": (-5000, 5000)}

def sign(key: bytes, body: bytes, ts: str, nonce: str) -> str:
    return hmac.new(key, ts.encode() + b"." + nonce.encode() + b"." + body, hashlib.sha256).hexdigest()

def validate(payload: dict):
    """Return (ok, reason). Rejects unknown fields, wrong types and out-of-range numbers."""
    if not isinstance(payload, dict): return False, "payload must be an object"
    for k in SCHEMA:
        if k not in payload: return False, f"missing field {k}"
    for k, v in payload.items():
        if k not in SCHEMA and k not in ("host", "win"): return False, f"unknown field {k}"
        if k in SCHEMA:
            if isinstance(v, bool) or not isinstance(v, (int, float)): return False, f"{k} not numeric"
            lo, hi = SCHEMA[k]
            if not (lo <= v <= hi): return False, f"{k} out of range"
    if not isinstance(payload.get("host", ""), str) or len(payload.get("host", "")) > 64: return False, "bad host"
    return True, "ok"

class RateLimiter:
    """Token bucket per agent."""
    def __init__(self, rate=50.0, burst=100):
        self.rate, self.burst, self.b, self.lock = rate, burst, {}, threading.Lock()
    def allow(self, who):
        with self.lock:
            tok, last = self.b.get(who, (self.burst, time.monotonic()))
            now = time.monotonic(); tok = min(self.burst, tok + (now-last)*self.rate)
            if tok < 1: self.b[who] = (tok, now); return False
            self.b[who] = (tok-1, now); return True

class NonceCache:
    def __init__(self, ttl=300): self.seen, self.ttl, self.lock = {}, ttl, threading.Lock()
    def check_and_add(self, nonce):
        with self.lock:
            now = time.time()
            for n in [n for n, t in self.seen.items() if now-t > self.ttl]: del self.seen[n]
            if nonce in self.seen: return False
            self.seen[nonce] = now; return True

class AuditLedger:
    """Append-only, SHA-256 hash-chained log kept in SQLite."""
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False); self.lock = threading.Lock()
        self.db.execute("""CREATE TABLE IF NOT EXISTS audit(idx INTEGER PRIMARY KEY, ts REAL, event TEXT,
                           agent TEXT, detail TEXT, prev_hash TEXT, hash TEXT)""")
        self.db.commit()
    @staticmethod
    def _h(idx, ts, event, agent, detail, prev):
        return hashlib.sha256(json.dumps([idx, ts, event, agent, detail, prev]).encode()).hexdigest()
    def record(self, event, agent, detail=""):
        with self.lock:
            row = self.db.execute("SELECT idx, hash FROM audit ORDER BY idx DESC LIMIT 1").fetchone()
            idx, prev = (row[0]+1, row[1]) if row else (0, "0"*64)
            ts = time.time(); h = self._h(idx, ts, event, agent, detail, prev)
            self.db.execute("INSERT INTO audit VALUES(?,?,?,?,?,?,?)", (idx, ts, event, agent, detail, prev, h))
            self.db.commit(); return idx, h
    def verify(self):
        """Return (ok, first_bad_index)."""
        prev = "0"*64
        for idx, ts, ev, ag, det, p, h in self.db.execute("SELECT * FROM audit ORDER BY idx"):
            if p != prev or self._h(idx, ts, ev, ag, det, p) != h: return False, idx
            prev = h
        return True, None
    def count(self): return self.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
