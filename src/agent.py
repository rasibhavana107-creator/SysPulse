"""Edge agent: signs each window and POSTs it to the backend."""
import json, time, uuid, urllib.request, urllib.error
from security import AGENT_KEYS, sign

def post(payload_bytes, agent="agent-laptop-01", key=None, ts=None, nonce=None, url="http://127.0.0.1:8765/ingest", sig=None):
    key = key or AGENT_KEYS.get(agent, b"x"); ts = ts or str(time.time()); nonce = nonce or uuid.uuid4().hex
    sig = sig or sign(key, payload_bytes, ts, nonce)
    req = urllib.request.Request(url, data=payload_bytes, method="POST", headers={
        "Content-Type": "application/json", "X-Agent-Id": agent, "X-Timestamp": ts, "X-Nonce": nonce, "X-Signature": sig})
    try:
        with urllib.request.urlopen(req, timeout=5) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
