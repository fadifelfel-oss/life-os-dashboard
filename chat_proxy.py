#!/usr/bin/env python3
# DEPRECATED / UNUSED (confirmed 2026-07-10): chat.html talks to server.py's
# /api/chat (port 8090), which proxies to Hermes's own gateway on :8642 —
# this standalone proxy on :8091 is not wired to anything in the current
# dashboard. Left as-is (including the stale 'owl-alpha' MODEL_MAP key)
# rather than touched, since fixing dead code risks implying it's live.
# Candidate for deletion in a future cleanup pass.
import json, os, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8091

def get_key():
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if "OPENROUTER" in k and "KEY" in k:
                        return v.strip()
    return os.environ.get("OPENROUTER_API_KEY", "")

MODEL_MAP = {
    "owl-alpha": "google/gemini-2.5-flash-lite",
    "claude-sonnet-4": "google/gemini-2.5-flash",
    "gpt-4o": "google/gemini-2.5-flash",
    "gemini-2.5-pro": "google/gemini-2.5-pro",
    "deepseek-reasoner": "google/gemini-2.5-flash-lite",
}

SYSTEM_PROMPT = """You are OWL, Fadi Felfel's personal AI agent. Fadi is a Senior Construction Project Manager with 25+ years experience. He lives in Milton, Ontario, Canada. He has a wife Sara and three children (Salah 15, Seela 11, Yousef 5). He uses Windows PC and Android phone only — never suggest Apple/iOS/Mac products.

Fadi speaks Arabic (native) and English (fluent). His hard deadline is finding a new Senior PM or Executive role by August 6, 2026 — that's P1 priority.

Your personality: direct, concise, honest. No fluff. Push back when he over-plans. Shipping (application sent, recruiter contacted, proposal sent) beats vault-building every time.

Always be concise. Lead with the verdict. Use plain language for tech — click-by-click steps. One question at a time when you need to ask."""

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/chat":
            return self.send_error(404)
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        msg = data.get("message", "")
        model = data.get("model", "owl-alpha")
        key = get_key()
        if not key:
            return self.send_json(500, {"error": "No key"})
        payload = json.dumps({
            "model": MODEL_MAP.get(model, "google/gemini-2.5-flash-lite"),
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": msg}
            ],
            "max_tokens": 1024,
            "temperature": 0.7
        }).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + key,
                "HTTP-Referer": "http://localhost:8090",
                "X-Title": "Life OS"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read())
            reply = res["choices"][0]["message"]["content"]
            self.send_json(200, {"response": reply, "model": model})
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            self.send_json(502, {"error": "HTTP " + str(e.code), "detail": body[:200]})
        except Exception as e:
            self.send_json(500, {"error": str(e)})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        self.send_json(200, {"status": "running"})

    def send_json(self, c, d):
        r = json.dumps(d).encode()
        self.send_response(c)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(r)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(r)

    def log_message(self, *a):
        pass

print("Chat proxy on port " + str(PORT))
HTTPServer(("0.0.0.0", PORT), H).serve_forever()
