#!/usr/bin/env python3
"""
Life OS Dashboard Server
Serves the Life OS dashboard and provides API endpoints for integration with Hermes
"""

import http.server
import json
import os
import re
import datetime
import time
import mimetypes
import asyncio
import urllib.parse
from pathlib import Path
import threading
import brain  # BUILD SPEC v1 Part A -- deterministic retrieval ladder

# Configuration
STATIC_DIR = Path(__file__).parent
VAULT_DIR = Path("/root/second-brain")   # READ-ONLY git mirror of the Second Brain vault (Decision Gate 1)
DATA_DIR = Path("/root/life-os-data")    # ALL server-side writes go here — never into VAULT_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "clippings").mkdir(exist_ok=True)
PORT = 8090
HERMES_CHAT_PROXY_URL = "http://127.0.0.1:8642"  # Hermes API Server

# Live OpenRouter model catalog cache — avoids hitting OpenRouter on every
# page load. 6h TTL; falls back to the small curated list below on any
# fetch failure (no key, network, rate limit, etc.) so the page never breaks.
_MODELS_CACHE = {"data": None, "ts": 0}
_MODELS_CACHE_TTL = 6 * 3600

# OKF wiki schema — ships alongside server.py in the repo, deployed into the
# vault itself (00_Kernel/OKF-WIKI-SCHEMA.md) on first /api/wiki/migrate run.
try:
    _OKF_SCHEMA_CONTENT = (STATIC_DIR / "OKF-WIKI-SCHEMA.md").read_text(encoding='utf-8')
except Exception:
    _OKF_SCHEMA_CONTENT = None

# Load whisper model at server startup (avoids blocking first request)
print("Loading Whisper model (base)...")
_whisper_model = None
_whisper_loading = True

def _load_whisper_model():
    global _whisper_model, _whisper_loading
    try:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel('base', device='cpu', compute_type='int8')
        print("✓ Whisper model loaded")
    except Exception as e:
        print(f"⚠ Whisper model failed to load: {e}")
    finally:
        _whisper_loading = False

# Start model loading in background thread so server can start immediately
threading.Thread(target=_load_whisper_model, daemon=True).start()


# ============================================================
# /api/today aggregation helpers (Task 3.1)
# Pure, read-only parsers over vault markdown. Unit-tested against the real
# vault files. These NEVER write to VAULT_DIR (Decision Gate 1).
# ============================================================

def _today_parse_radar(text):
    """Opportunity Radar.md -> {"high":[...], "medium":[...]}.
    HIGH table cols:   | Signal | Source Clip | Pipeline Match | Action |
    MEDIUM table cols: | Topic  | # Clips      | Potential Angle | Explore? |
    """
    high, medium = [], []
    section = None  # 'high' | 'medium' | None
    for raw in text.split('\n'):
        line = raw.strip()
        low = line.lower()
        if line.startswith('#'):
            if 'high confidence' in low:
                section = 'high'
            elif 'medium signal' in low:
                section = 'medium'
            elif line.startswith('## '):
                section = None
            continue
        if section and line.startswith('|'):
            cells = [c.strip() for c in line.strip('|').split('|')]
            if len(cells) < 2:
                continue
            first = cells[0].lower()
            # skip header + separator rows
            if first in ('signal', 'topic') or (cells[0] and set(cells[0]) <= set('-: ')):
                continue
            if not cells[0]:
                continue
            if section == 'high':
                high.append({
                    "title": cells[0],
                    "match": cells[2] if len(cells) > 2 else "",
                    "action": cells[3] if len(cells) > 3 else "",
                    "confidence": "HIGH",
                })
            else:
                medium.append({
                    "title": cells[0],
                    "angle": cells[2] if len(cells) > 2 else "",
                    "action": cells[3] if len(cells) > 3 else "",
                    "confidence": "MEDIUM",
                })
    return {"high": high, "medium": medium}


def _today_parse_log(text):
    """log.md -> latest NIGHTLY digest + open WAGER lines.
    Line format: - YYYY-MM-DD | OPERATION | Detail | Outcome
    A WAGER is 'open' unless resolved (no checkmark/cross) or explicitly 'TBD'.
    """
    nightly, nightly_date, wagers = None, "", []
    for raw in text.split('\n'):
        line = raw.strip()
        if not line.startswith('- '):
            continue
        body = line[2:].strip()
        parts = [p.strip() for p in body.split('|')]
        if len(parts) < 2:
            continue
        date, op = parts[0], parts[1].upper()
        detail = parts[2] if len(parts) > 2 else ""
        outcome = parts[3] if len(parts) > 3 else ""
        if op in ('NIGHTLY', 'DIGEST'):
            nightly, nightly_date = (detail or outcome), date  # log is chronological; last wins
        elif op == 'WAGER':
            full = ' | '.join(parts[2:]) if len(parts) > 2 else body
            is_open = ('✅' not in body and '❌' not in body) or ('tbd' in body.lower())
            wagers.append({"date": date, "text": full, "open": is_open})
    return {
        "nightly_digest": nightly,
        "nightly_date": nightly_date,
        "wagers_open": [w for w in wagers if w["open"]],
    }


def _today_parse_power3(text):
    """Daily journal note -> Power 3 items (numbered list under the 'Power 3' heading)."""
    items, in_section = [], False
    for raw in text.split('\n'):
        line = raw.strip()
        if line.startswith('#'):
            if 'power 3' in line.lower():
                in_section = True
                continue
            elif in_section:
                break  # next heading ends the section
        if in_section:
            m = re.match(r'^\d+[.)]\s*(.+)$', line)
            if m and m.group(1).strip():
                items.append(m.group(1).strip())
    return items


def _today_select_kanban(cards):
    """Kanban store cards -> {"in_progress":[...], "due":[...]}.
    No due-date field exists in the current schema; 'due' is supported defensively."""
    today = datetime.date.today().isoformat()
    in_progress, due = [], []
    for c in cards:
        col = (c.get('column') or '').lower()
        card = {
            "id": c.get('id', ''),
            "title": c.get('title', 'Untitled'),
            "priority": c.get('priority', 'medium'),
            "tag": c.get('tag', ''),
            "column": col,
        }
        if col in ('progress', 'in progress', 'doing', 'active'):
            in_progress.append(card)
        d = c.get('due') or c.get('dueDate')
        if d and str(d)[:10] <= today and col != 'done':
            c2 = dict(card)
            c2["due"] = str(d)[:10]
            due.append(c2)
    return {"in_progress": in_progress, "due": due}


class LifeOSHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # Serve static files
        if path == "/" or path == "":
            self._serve_file(STATIC_DIR / "index.html")
            return
        elif path.startswith("/api/"):
            self._handle_api_get(parsed_path)
            return
        elif path.startswith("/knowledge/"):
            # Serve vault files directly under /knowledge/
            file_path = VAULT_DIR / path[10:].lstrip('/')
            self._serve_file(file_path)
            return
        else:
            # Try to serve static file
            file_path = STATIC_DIR / path.lstrip("/")
            if file_path.exists() and file_path.is_file():
                self._serve_file(file_path)
            else:
                self._json_error(404, "File not found")
                return
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        if path == "/api/chat":
            self._handle_chat_proxy()
        elif path == "/api/upload":
            self._handle_file_upload()
        elif path == "/api/browser/run":
            self._handle_browser_run()
        elif path == "/api/clip":
            self._handle_clip_endpoint()
        elif path == "/api/auth":
            self._handle_auth_endpoint()
        elif path == "/api/clippings/process":
            self._handle_process_clip()
        elif path == "/api/task":
            self._handle_task_save()
        elif path == "/api/meetings":
            self._handle_meetings_post()
        elif path == "/api/meetings/process":
            self._handle_meeting_process()
        elif path == "/api/transcribe":
            self._handle_transcribe()
        elif path == "/api/chat/session":
            self._handle_chat_session_save()
        elif path == "/api/chat/session/delete":
            self._handle_chat_session_delete()
        elif path == "/api/wiki/query":
            self._handle_wiki_query()
        elif path == "/api/wiki/migrate":
            self._handle_wiki_migrate()
        elif path == "/api/wiki/lint/analyze":
            self._handle_wiki_lint_analyze()
        elif path == "/api/wiki/ingest-fireflies":
            self._handle_fireflies_ingest()
        elif path == "/api/wiki/ingest-youtube":
            self._handle_youtube_ingest()
        elif path == "/api/wiki/ingest-gmail":
            self._handle_gmail_ingest()
        elif path == "/api/wiki/ingest-crm":
            self._handle_crm_ingest()
        elif path == "/api/wiki/extract-prompts":
            self._handle_extract_prompts()
        else:
            self._json_error(404, "Endpoint not found")
            return
    
    def _serve_file(self, file_path):
        """Serve a static file"""
        try:
            if not file_path.exists():
                self._json_error(404, "File not found")
                return
                
            # Guess the MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type is None:
                mime_type = "application/octet-stream"
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._json_error(500, f"Failed to serve file: {str(e)}")
    
    def _json_response(self, data, status=200):
        """Send a JSON response"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _json_error(self, status, message):
        """Send a JSON error response"""
        self._json_response({"error": message}, status)
    
    def _handle_api_get(self, parsed_path):
        """Handle GET requests to API endpoints"""
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)
        
        if path == "/api/models":
            self._serve_models()
        elif path == "/api/today":
            self._serve_today()
        elif path == "/api/tasks":
            self._serve_tasks()
        elif path == "/api/wiki":
            self._serve_wiki_index()
        elif path == "/api/tree":
            self._serve_vault_tree()
        elif path == "/api/file":
            self._serve_vault_file(query)
        elif path == "/api/use-cases":
            self._serve_use_cases()
        elif path == "/api/state":
            self._serve_state()
        elif path == "/api/skills":
            self._serve_skills()
        elif path == "/api/skills/stats":
            self._serve_skill_stats()
        elif path == "/api/providers":
            self._serve_providers()
        elif path == "/api/auth":
            self._serve_auth_pool()
        elif path == "/api/clippings":
            self._serve_clippings(query)
        elif path == "/api/cron":
            self._serve_cron(query)
        elif path == "/api/meetings":
            self._serve_meetings_get(query)
        elif path == "/api/chat/sessions":
            self._serve_chat_sessions()
        elif path == "/api/chat/session":
            self._serve_chat_session(query)
        elif path == "/api/kb/search":
            self._serve_kb_search(query)
        elif path == "/api/wiki/page":
            self._serve_wiki_page(query)
        elif path == "/api/wiki/lint":
            self._serve_wiki_lint()
        elif path == "/api/hermes-pilot":
            self._serve_hermes_pilot()
        elif path == "/api/wiki/prompts":
            self._serve_prompts_library()
        elif path == "/api/arms":
            self._serve_arms()
        elif path == "/api/projects":
            self._serve_projects()
        elif path == "/api/logs":
            self._serve_logs(query)
        elif path == "/api/wiki/crm":
            self._serve_crm_snapshot()
        elif path == "/api/upload":
            self._json_error(405, "Method not allowed. Use POST.")
        elif path == "/api/chat":
            self._json_error(405, "Method not allowed. Use POST.")
        elif path == "/api/browser/run":
            self._json_error(405, "Method not allowed. Use POST.")
        elif path == "/api/clip":
            self._json_error(405, "Method not allowed. Use POST.")
        else:
            self._json_error(404, "API endpoint not found")

    def _serve_arms(self):
        """GET /api/arms — the ARMS registry (Applications / Routines / Skills)
        parsed from _system/registry/*.md in the vault mirror. Feeds the 3D
        Brain's systems panel + the Loops/Skills hubs. Defensive by design: a
        missing or malformed file yields an empty arm, never a 500."""
        base = VAULT_DIR / "_system" / "registry"

        def parse_tables(text):
            rows, headers, section = [], None, None
            for line in text.splitlines():
                s = line.strip()
                if s.startswith("## "):
                    section, headers = s[3:].strip(), None
                    continue
                if not s.startswith("|"):
                    if s == "":
                        headers = None  # blank line ends the current table
                    continue
                cells = [c.strip() for c in s.strip("|").split("|")]
                joined = "".join(cells)
                if joined and set(joined) <= set("-: "):
                    continue  # separator row (|---|:--:|)
                if headers is None:
                    headers = cells
                    continue
                rec = {}
                for i, h in enumerate(headers):
                    rec[h] = cells[i] if i < len(cells) else ""
                if section:
                    rec["_section"] = section
                rows.append(rec)
            return rows

        out = {}
        for arm in ("applications", "routines", "skills"):
            f = base / (arm + ".md")
            try:
                out[arm] = parse_tables(f.read_text(encoding="utf-8")) if f.exists() else []
            except Exception:
                out[arm] = []
        counts = {k: len(v) for k, v in out.items()}
        self._json_response({"data": out, "counts": counts})

    def _serve_projects(self):
        """GET /api/projects — read `010 Projects/` hub notes (OPERATION 7) as
        JSON for the read-only Projects registry view. Cowork owns/writes these
        (one hub note per Cowork project); the dashboard only reads. Defensive:
        missing folder or malformed note yields an empty/partial row, never 500."""
        try:
            out_dir = VAULT_DIR / "010 Projects"
            rows = []
            if out_dir.exists():
                for f in sorted(out_dir.rglob("*.md")):
                    try:
                        meta, _ = self._parse_frontmatter(f.read_text(encoding='utf-8'))
                    except Exception:
                        continue
                    # Hub notes only: journal entries / strategies / programs also live
                    # under 010 Projects (typed trade/workout/strategy/program as of
                    # 2026-07-09) and must not render as projects. Typed hubs pass;
                    # untyped files pass only if named like their folder (hub convention).
                    ftype = str(meta.get('type') or '').strip().lower()
                    if ftype not in ('project', 'cowork-project-hub') and not (ftype == '' and f.stem == f.parent.name):
                        continue
                    tags = meta.get('tags', []) or []
                    if isinstance(tags, str):
                        tags = [t.strip() for t in tags.strip('[]').split(',')]

                    def tag_after(prefix):
                        for t in tags:
                            s = str(t).strip()
                            if s.startswith(prefix):
                                return s[len(prefix):]
                        return ''

                    rows.append({
                        "name": meta.get('project') or meta.get('title') or f.stem,
                        "status": meta.get('status') or tag_after('status/'),
                        "priority": tag_after('priority/'),
                        "area": tag_after('area/'),
                        "folder": meta.get('folder', ''),
                        "last_synced": meta.get('last_synced') or '',
                        "path": str(f.relative_to(VAULT_DIR)),
                    })
            self._json_response({"data": rows})
        except Exception as e:
            self._json_error(500, f"Failed to serve projects: {str(e)}")

    def _serve_logs(self, query):
        """GET /api/logs?kind=trading|fitness — journal-entry frontmatter from
        the vault mirror's 010 Projects log folders (Cowork/Fadi write entries
        from _Templates; this dashboard only reads). Feeds trading.html and
        fitness.html. Defensive: missing folder or malformed entry yields
        empty/partial rows, never a 500."""
        KINDS = {
            "trading": ("010 Projects/Prop Trading/Trade Journal", "trade"),
            "fitness": ("010 Projects/Fitness Rebuild/Workout Log", "workout"),
        }
        kind = (query.get("kind") or ["trading"])[0].strip().lower()
        if kind not in KINDS:
            self._json_error(400, "kind must be one of: " + ", ".join(sorted(KINDS)))
            return
        folder, expected_type = KINDS[kind]
        rows = []
        try:
            log_dir = VAULT_DIR / folder
            if log_dir.exists():
                for f in sorted(log_dir.glob("*.md")):
                    try:
                        meta, _ = self._parse_frontmatter(f.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    clean = {}
                    for k, v in meta.items():
                        if isinstance(v, str):
                            # strip the templates' inline "# comment" hints from values
                            v = v.split(" #")[0].split("\t#")[0].strip()
                        clean[k] = v
                    ftype = str(clean.get("type") or "").strip().lower()
                    if ftype and ftype != expected_type:
                        continue
                    clean["path"] = str(f.relative_to(VAULT_DIR))
                    clean["file"] = f.stem
                    rows.append(clean)
            rows.sort(key=lambda r: str(r.get("date") or r.get("file") or ""), reverse=True)
            self._json_response({"data": rows, "kind": kind, "count": len(rows)})
        except Exception as e:
            self._json_error(500, f"Failed to serve logs: {str(e)}")

    def _get_env_var(self, var_name):
        """Generic reader for any NAME=value line in ~/.hermes/.env — shared
        by all the provider-specific _get_*_key() helpers below and by
        providers (gmail, notion) that need a plain config value rather than
        the provider_id + '_API_KEY' convention Settings > API Keys uses."""
        env_path = Path.home() / ".hermes" / ".env"
        if not env_path.exists():
            return ""
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith(f"{var_name}="):
                return line.split('=', 1)[1].strip().strip('\'"')
        return ""

    def _get_openrouter_key(self):
        """Read OPENROUTER_API_KEY from ~/.hermes/.env — same file/format the
        Settings > API Keys page writes to (see the 'test' action above)."""
        env_path = Path.home() / ".hermes" / ".env"
        if not env_path.exists():
            return ""
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith("OPENROUTER_API_KEY="):
                return line.split('=', 1)[1].strip().strip('\'"')
        return ""

    def _fetch_live_openrouter_models(self):
        """Fetch the full live OpenRouter catalog (hundreds of models) and
        normalize to the shape models.html / model-catalog.js expect.
        Category/score/speed/rank are intentionally omitted — models.html
        already derives all of those client-side (generateTags/detectProvider/
        scoreOf) when a model doesn't carry them, so we don't need to
        hand-curate every entry just to keep the catalog live and complete."""
        import urllib.request
        key = self._get_openrouter_key()
        if not key:
            raise RuntimeError("No OpenRouter API key configured")
        req = urllib.request.Request(
            'https://openrouter.ai/api/v1/models',
            headers={'Authorization': f'Bearer {key}'}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = json.loads(r.read()).get('data', [])

        out = []
        for m in raw:
            pricing = m.get('pricing') or {}
            try:
                prompt_price = float(pricing.get('prompt', 0) or 0)
            except (TypeError, ValueError):
                prompt_price = 0.0
            try:
                completion_price = float(pricing.get('completion', 0) or 0)
            except (TypeError, ValueError):
                completion_price = 0.0
            top_provider = m.get('top_provider') or {}
            out.append({
                "id": m.get('id', ''),
                "name": m.get('name') or m.get('id', ''),
                "provider": (m.get('id', '') or '').split('/')[0] if '/' in (m.get('id') or '') else '',
                "context_length": m.get('context_length', 0) or 0,
                "max_tokens": top_provider.get('max_completion_tokens') or m.get('context_length', 0) or 0,
                "pricing": {"prompt": prompt_price, "completion": completion_price},
            })
        return out

    def _serve_models(self):
        """Serve model catalog. Tries the live OpenRouter API first (cached
        6h); falls back to a small curated list if no key is configured or
        the fetch fails, so the page always renders something."""
        now = time.time()
        if _MODELS_CACHE["data"] and (now - _MODELS_CACHE["ts"]) < _MODELS_CACHE_TTL:
            self._json_response({"data": _MODELS_CACHE["data"], "source": "openrouter_live", "cached": True})
            return
        try:
            live = self._fetch_live_openrouter_models()
            if live:
                _MODELS_CACHE["data"] = live
                _MODELS_CACHE["ts"] = now
                self._json_response({"data": live, "source": "openrouter_live", "cached": False})
                return
        except Exception as e:
            print(f"[models] Live OpenRouter fetch failed, using fallback: {e}")

        self._json_response({"data": self._FALLBACK_MODELS, "source": "fallback_curated"})

    _FALLBACK_MODELS = [
            # ═══════════════════════════════════════════════════════════
            # 🏆 FREE CHAMPIONS — Best free models (no cost)
            # ═══════════════════════════════════════════════════════════
            {"id": "openrouter/owl-alpha", "name": "Owl Alpha", "provider": "OWL", "context_length": 1048756, "max_tokens": 262144,
             "pricing": {"prompt": 0, "completion": 0},
             "category": "free", "best_for": "Agent workflows, autonomous tasks",
             "score": 88, "speed": "fast", "rank": 1},
            {"id": "google/lyria-3-pro-preview", "name": "Lyria 3 Pro Preview", "provider": "Google", "context_length": 1048576, "max_tokens": 65536,
             "pricing": {"prompt": 0, "completion": 0},
             "category": "free", "best_for": "Reasoning, long context, analysis",
             "score": 87, "speed": "fast", "rank": 2},
            {"id": "qwen/qwen3-coder:free", "name": "Qwen3 Coder 480B", "provider": "Alibaba", "context_length": 1048576, "max_tokens": 262000,
             "pricing": {"prompt": 0, "completion": 0},
             "category": "free", "best_for": "Coding, long context, open source",
             "score": 85, "speed": "fast", "rank": 3},
            {"id": "nvidia/nemotron-3-ultra-550b-a55b:free", "name": "NVIDIA Nemotron 3 Ultra", "provider": "NVIDIA", "context_length": 1000000, "max_tokens": 65536,
             "pricing": {"prompt": 0, "completion": 0},
             "category": "free", "best_for": "Reasoning, math, open source",
             "score": 84, "speed": "fast", "rank": 4},
            {"id": "google/lyria-3-clip-preview", "name": "Lyria 3 Clip Preview", "provider": "Google", "context_length": 1048576, "max_tokens": 65536,
             "pricing": {"prompt": 0, "completion": 0},
             "category": "free", "best_for": "Vision + text, multimodal",
             "score": 82, "speed": "fast", "rank": 5},
            {"id": "nvidia/nemotron-3-super-120b-a12b:free", "name": "NVIDIA Nemotron 3 Super", "provider": "NVIDIA", "context_length": 1000000, "max_tokens": 65536,
             "pricing": {"prompt": 0, "completion": 0},
             "category": "free", "best_for": "General purpose, reasoning, open source",
             "score": 81, "speed": "fast", "rank": 6},

            # ═══════════════════════════════════════════════════════════
            # 🧠 REASONING — Deep thinking, analysis, multi-step reasoning
            # ═══════════════════════════════════════════════════════════
            {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "Google", "context_length": 1048576, "max_tokens": 16384,
             "pricing": {"prompt": 0.00000125, "completion": 0.00001},
             "category": "reasoning", "best_for": "Complex reasoning, multi-step analysis",
             "score": 92, "speed": "fast", "rank": 1},
            {"id": "anthropic/claude-opus-4-20250514", "name": "Claude Opus 4", "provider": "Anthropic", "context_length": 200000, "max_tokens": 16384,
             "pricing": {"prompt": 0.000015, "completion": 0.000075},
             "category": "reasoning", "best_for": "Deep analysis, research-grade thinking",
             "score": 99, "speed": "medium", "rank": 2},
            {"id": "anthropic/claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "provider": "Anthropic", "context_length": 1048576, "max_tokens": 16384,
             "pricing": {"prompt": 0.000003, "completion": 0.000015},
             "category": "reasoning", "best_for": "Balanced reasoning + speed",
             "score": 95, "speed": "fast", "rank": 3},
            {"id": "deepseek/deepseek-r1-0528", "name": "DeepSeek R1", "provider": "DeepSeek", "context_length": 163840, "max_tokens": 8192,
             "pricing": {"prompt": 0.0000005, "completion": 0.00000215},
             "category": "reasoning", "best_for": "Open-source reasoning, math",
             "score": 90, "speed": "medium", "rank": 4},
            {"id": "moonshotai/kimi-k2", "name": "Kimi K2", "provider": "Moonshot", "context_length": 131072, "max_tokens": 8192,
             "pricing": {"prompt": 0.00000057, "completion": 0.0000023},
             "category": "reasoning", "best_for": "Long context, Chinese/English",
             "score": 87, "speed": "fast", "rank": 5},
            {"id": "z-ai/glm-5", "name": "GLM 5", "provider": "Z.ai", "context_length": 202752, "max_tokens": 8192,
             "pricing": {"prompt": 0.0000006, "completion": 0.00000192},
             "category": "reasoning", "best_for": "Bilingual CN/EN, long context reasoning",
             "score": 85, "speed": "medium", "rank": 6},
            {"id": "z-ai/glm-5.2", "name": "GLM 5.2", "provider": "Z.ai", "context_length": 1048576, "max_tokens": 16384,
             "pricing": {"prompt": 0.00000095, "completion": 0.000003},
             "category": "reasoning", "best_for": "Long context, complex analysis, CN/EN",
             "score": 86, "speed": "medium", "rank": 7},

            # ═══════════════════════════════════════════════════════════
            # 💻 CODING — Code generation, debugging, architecture
            # ═══════════════════════════════════════════════════════════
            {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "Google", "context_length": 1048576, "max_tokens": 16384,
             "pricing": {"prompt": 0.0000003, "completion": 0.0000025},
             "category": "coding", "best_for": "Code generation, debugging",
             "score": 91, "speed": "fastest", "rank": 1},
            {"id": "openai/gpt-4.1", "name": "GPT-4.1", "provider": "OpenAI", "context_length": 1047576, "max_tokens": 16384,
             "pricing": {"prompt": 0.000002, "completion": 0.000008},
             "category": "coding", "best_for": "Complex coding, agent workflows",
             "score": 93, "speed": "fast", "rank": 2},
            {"id": "mistralai/codestral-2508", "name": "Codestral", "provider": "Mistral", "context_length": 256000, "max_tokens": 8192,
             "pricing": {"prompt": 0.0000003, "completion": 0.0000009},
             "category": "coding", "best_for": "Fast coding, fill-in-the-middle",
             "score": 86, "speed": "fast", "rank": 3},
            {"id": "openai/o4-mini", "name": "GPT-o4-mini", "provider": "OpenAI", "context_length": 200000, "max_tokens": 16384,
             "pricing": {"prompt": 0.0000011, "completion": 0.0000044},
             "category": "coding", "best_for": "Efficient coding, cost-effective",
             "score": 89, "speed": "fast", "rank": 4},
            {"id": "anthropic/claude-haiku-3-5-20241022", "name": "Claude Haiku 3.5", "provider": "Anthropic", "context_length": 200000, "max_tokens": 8192,
             "pricing": {"prompt": 0.000001, "completion": 0.000005},
             "category": "coding", "best_for": "Quick coding, simple fixes",
             "score": 83, "speed": "fast", "rank": 5},
            {"id": "minimax/minimax-m1", "name": "MiniMax M1", "provider": "MiniMax", "context_length": 131072, "max_tokens": 8192,
             "pricing": {"prompt": 0.0000004, "completion": 0.0000022},
             "category": "coding", "best_for": "Chinese/English coding, long context",
             "score": 82, "speed": "medium", "rank": 6},

            # ═══════════════════════════════════════════════════════════
            # 💬 CHAT — Conversation, general use, writing
            # ═══════════════════════════════════════════════════════════
            {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "OpenAI", "context_length": 128000, "max_tokens": 16384,
             "pricing": {"prompt": 0.0000025, "completion": 0.00001},
             "category": "chat", "best_for": "General conversation, analysis",
             "score": 90, "speed": "fast", "rank": 1},
            {"id": "deepseek/deepseek-chat-v3-1", "name": "DeepSeek V3", "provider": "DeepSeek", "context_length": 163840, "max_tokens": 8192,
             "pricing": {"prompt": 0.00000021, "completion": 0.00000079},
             "category": "chat", "best_for": "Chat, analysis, multilingual",
             "score": 88, "speed": "fast", "rank": 2},
            {"id": "x-ai/grok-4.20", "name": "Grok 4", "provider": "xAI", "context_length": 2000000, "max_tokens": 16384,
             "pricing": {"prompt": 0.00000125, "completion": 0.0000025},
             "category": "chat", "best_for": "Long context, real-time info",
             "score": 86, "speed": "fast", "rank": 3},
            {"id": "meta-llama/llama-4-maverick", "name": "Llama 4 Maverick", "provider": "Meta", "context_length": 1048576, "max_tokens": 16384,
             "pricing": {"prompt": 0.00000015, "completion": 0.0000006},
             "category": "chat", "best_for": "Open model, custom fine-tuning",
             "score": 84, "speed": "fast", "rank": 4},
            {"id": "qwen/qwen-plus-2025-07-28", "name": "Qwen Plus", "provider": "Alibaba", "context_length": 1000000, "max_tokens": 16384,
             "pricing": {"prompt": 0.00000026, "completion": 0.00000078},
             "category": "chat", "best_for": "Chinese/English, multilingual",
             "score": 85, "speed": "fast", "rank": 5},

            # ═══════════════════════════════════════════════════════════
            # 👁️ VISION — Image understanding, screenshots, diagrams
            # ═══════════════════════════════════════════════════════════
            {"id": "google/gemma-3-27b-it", "name": "Gemma 3 27B", "provider": "Google", "context_length": 131072, "max_tokens": 8192,
             "pricing": {"prompt": 0.00000008, "completion": 0.00000016},
             "category": "vision", "best_for": "Open vision model, diagrams",
             "score": 78, "speed": "fast", "rank": 1},
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "OpenAI", "context_length": 128000, "max_tokens": 16384,
             "pricing": {"prompt": 0.00000015, "completion": 0.0000006},
             "category": "vision", "best_for": "Image analysis, OCR, cheap",
             "score": 82, "speed": "fast", "rank": 2},
            {"id": "google/gemini-2-5-flash-lite", "name": "Gemini Flash Lite", "provider": "Google", "context_length": 1048576, "max_tokens": 8192,
             "pricing": {"prompt": 0.0000001, "completion": 0.0000004},
             "category": "vision", "best_for": "Cheap image processing",
             "score": 76, "speed": "fastest", "rank": 3},
            {"id": "meta-llama/llama-4-scout", "name": "Llama 4 Scout", "provider": "Meta", "context_length": 10000000, "max_tokens": 8192,
             "pricing": {"prompt": 0.0000001, "completion": 0.0000003},
             "category": "vision", "best_for": "Ultra-long context, open",
             "score": 75, "speed": "fast", "rank": 4},
            {"id": "mistralai/mistral-small-3.2-24b-instruct", "name": "Mistral Small 3", "provider": "Mistral", "context_length": 128000, "max_tokens": 8192,
             "pricing": {"prompt": 0.00000007, "completion": 0.0000002},
             "category": "vision", "best_for": "Cheap, fast processing",
             "score": 72, "speed": "fast", "rank": 5},

            # ═══════════════════════════════════════════════════════════
            # 💰 BUDGET — Best value for everyday use
            # ═══════════════════════════════════════════════════════════
            {"id": "openai/o3", "name": "GPT-o3", "provider": "OpenAI", "context_length": 200000, "max_tokens": 16384,
             "pricing": {"prompt": 0.000002, "completion": 0.000008},
             "category": "budget", "best_for": "Reasoning + value",
             "score": 88, "speed": "medium", "rank": 1},
            {"id": "qwen/qwen-max", "name": "Qwen Max", "provider": "Alibaba", "context_length": 1000000, "max_tokens": 16384,
             "pricing": {"prompt": 0.00000026, "completion": 0.00000078},
             "category": "budget", "best_for": "Best value, long context",
             "score": 85, "speed": "fast", "rank": 2},
            {"id": "mistralai/mistral-large-3", "name": "Mistral Large 3", "provider": "Mistral", "context_length": 128000, "max_tokens": 16384,
             "pricing": {"prompt": 0.0000002, "completion": 0.0000006},
             "category": "budget", "best_for": "European compliance, GDPR",
             "score": 80, "speed": "fast", "rank": 3},
            {"id": "x-ai/grok-3", "name": "Grok 3", "provider": "xAI", "context_length": 2000000, "max_tokens": 16384,
             "pricing": {"prompt": 0.00000125, "completion": 0.0000025},
             "category": "budget", "best_for": "Long context, real-time",
             "score": 83, "speed": "fast", "rank": 4},
            {"id": "google/gemini-2-5-flash-lite", "name": "Gemini Flash Lite", "provider": "Google", "context_length": 1048576, "max_tokens": 8192,
             "pricing": {"prompt": 0.0000001, "completion": 0.0000004},
             "category": "budget", "best_for": "Best overall value",
             "score": 76, "speed": "fastest", "rank": 5},
        ]

    def _serve_tasks(self):
        """Serve tasks: combine vault markdown checkboxes + kanban store"""
        return self._serve_tasks_impl()

    def _serve_today(self):
        """GET /api/today (Task 3.1) — aggregate the day for the Today/Hub page:
        (a) Opportunity Radar HIGH/MEDIUM signals, (b) kanban due/in-progress,
        (c) latest NIGHTLY digest line, (d) open WAGER lines, (e) today's Power 3.
        Read-only from VAULT_DIR; kanban from DATA_DIR. Never writes."""
        result = {
            "date": datetime.date.today().isoformat(),
            "radar": {"high": [], "medium": []},
            "kanban": {"due": [], "in_progress": []},
            "nightly_digest": None,
            "nightly_date": "",
            "wagers_open": [],
            "power3": [],
            "sources": {},
        }
        # (a) Opportunity Radar
        radar_path = VAULT_DIR / "Opportunity Radar.md"
        try:
            if radar_path.exists():
                result["radar"] = _today_parse_radar(radar_path.read_text(encoding='utf-8'))
                result["sources"]["radar"] = True
            else:
                result["sources"]["radar"] = False
        except Exception as e:
            result["sources"]["radar_error"] = str(e)
        # (c) + (d) log.md — nightly digest + open wagers
        log_path = VAULT_DIR / "log.md"
        try:
            if log_path.exists():
                parsed = _today_parse_log(log_path.read_text(encoding='utf-8'))
                result["nightly_digest"] = parsed["nightly_digest"]
                result["nightly_date"] = parsed["nightly_date"]
                result["wagers_open"] = parsed["wagers_open"]
                result["sources"]["log"] = True
            else:
                result["sources"]["log"] = False
        except Exception as e:
            result["sources"]["log_error"] = str(e)
        # (e) Power 3 from today's journal note
        journal_path = VAULT_DIR / "journal" / (result["date"] + ".md")
        try:
            if journal_path.exists():
                result["power3"] = _today_parse_power3(journal_path.read_text(encoding='utf-8'))
                result["sources"]["journal"] = True
            else:
                result["sources"]["journal"] = False
        except Exception as e:
            result["sources"]["journal_error"] = str(e)
        # (b) Kanban due / in-progress from DATA_DIR
        store_path = DATA_DIR / ".kanban_store.json"
        try:
            if store_path.exists():
                with open(store_path, 'r', encoding='utf-8') as f:
                    cards = json.load(f)
                if isinstance(cards, list):
                    result["kanban"] = _today_select_kanban(cards)
                result["sources"]["kanban"] = True
            else:
                result["sources"]["kanban"] = False
        except Exception as e:
            result["sources"]["kanban_error"] = str(e)
        self._json_response(result)

    def _serve_tasks_impl(self):
        """Serve tasks: combine vault markdown checkboxes + kanban store"""
        tasks = []
        
        # Load kanban store (manual tasks)
        store_path = DATA_DIR / ".kanban_store.json"
        kanban_tasks = []
        if store_path.exists():
            try:
                with open(store_path, 'r', encoding='utf-8') as f:
                    kanban_tasks = json.load(f)
            except Exception:
                pass
        
        # Format kanban tasks
        for t in kanban_tasks:
            tasks.append({
                "id": t.get('id', ''),
                "title": t.get('title', 'Untitled'),
                "description": t.get('description', ''),
                "priority": t.get('priority', 'medium'),
                "tag": t.get('tag', 'project'),
                "column": t.get('column', 'backlog'),
                "source": t.get('source', 'Kanban'),
                "file": "",
                "line": 0,
                "completed": t.get('column') == 'done'
            })
        
        # Also scan vault markdown for tasks with column metadata in tags
        try:
            for md_file in VAULT_DIR.rglob("*.md"):
                if '.kanban' in str(md_file):
                    continue
                if md_file.is_file():
                    try:
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            lines = content.split('\n')
                            in_kanban_section = False
                            current_column = 'backlog'
                            for i, line in enumerate(lines, 1):
                                # Detect kanban section headers: ## Backlog, ## In Progress, etc.
                                line_lower = line.lower().strip()
                                if '## backlog' in line_lower or '## todo' in line_lower:
                                    in_kanban_section = True
                                    current_column = 'backlog'
                                    continue
                                elif '## in progress' in line_lower or '## doing' in line_lower or '## active' in line_lower:
                                    current_column = 'progress'
                                    continue
                                elif '## review' in line_lower or '## in review' in line_lower:
                                    current_column = 'review'
                                    continue
                                elif '## done' in line_lower or '## complete' in line_lower or '## completed' in line_lower:
                                    current_column = 'done'
                                    continue
                                elif line.startswith('## ') and in_kanban_section:
                                    # New section, exit kanban mode
                                    in_kanban_section = False
                                    continue
                                
                                if in_kanban_section and ('- [ ]' in line or '- [x]' in line):
                                    task_title = line[line.index('- [ ]') + 5:].strip() if '- [ ]' in line else line[line.index('- [x]') + 5:].strip()
                                    # Check for inline kanban metadata: {priority: high, tag: career}
                                    priority = 'medium'
                                    tag = 'project'
                                    for p in ['high', 'medium', 'low']:
                                        if f'priority: {p}' in task_title or f'|{p}|' in task_title:
                                            priority = p
                                    for t_kw in ['career', 'fieldbridge', 'trading', 'personal', 'urgent']:
                                        if t_kw in task_title.lower():
                                            tag = t_kw
                                    # Extract inline ID if present
                                    task_id = ''
                                    if '{id:' in task_title:
                                        id_start = task_title.index('{id:') + 5
                                        id_end = task_title.index('}', id_start)
                                        task_id = task_title[id_start:id_end]
                                        task_title = task_title[:task_title.index('{id:')].strip()
                                    
                                    tasks.append({
                                        "id": task_id,
                                        "title": task_title,
                                        "description": "",
                                        "priority": priority,
                                        "tag": tag,
                                        "column": current_column,
                                        "source": str(md_file.relative_to(VAULT_DIR)),
                                        "file": str(md_file.relative_to(VAULT_DIR)),
                                        "line": i,
                                        "completed": '- [x]' in line
                                    })
                    except Exception as e:
                        print(f"Error reading {md_file}: {e}")
                        continue
        except Exception as e:
            print(f"Error scanning for tasks: {e}")
        
        self._json_response({"tasks": tasks, "data": tasks})
    
    # ═══════════════════════════════════════════════════════════
    # OKF / LLM-WIKI HELPERS
    # ═══════════════════════════════════════════════════════════

    # Top-level vault folders considered part of the "wiki" surface for the
    # 3D Brain graph — SECOND BRAIN vault structure (agents.md governs; the
    # old 20_Wiki/OKF structure is retired). Excludes system/dotfiles and
    # raw, unprocessed sources.
    _WIKI_DOMAIN_FOLDERS = {
        "030 Resources": "ai-tools",   # overridden per-subfolder in _infer_domain
        "010 Projects": "general",     # overridden per-subfolder in _infer_domain
        "020 Areas": "general",        # overridden per-subfolder in _infer_domain
        "30_Context": "construction",  # overridden per-subfolder in _infer_domain
        "CRM": "fieldbridgehq",
        "journal": "general",
    }
    # Pretty frontmatter domain names (as written by agents.md) → graph domain keys.
    # NOTE Phase 2 (Blueprint Dark) renames these keys to the life-area palette;
    # until then "Personal & Mindset" maps to general.
    _PRETTY_DOMAINS = {
        "ai & aios": "ai-tools",
        "pkm & second brain": "ai-tools",
        "business & strategy": "fieldbridgehq",
        "construction pm": "construction",
        "construction law": "construction",
        "personal & mindset": "general",
        "trading": "trading",
        "trading & finance": "trading",
        "fieldbridge": "fieldbridgehq",
    }
    _KNOWN_DOMAINS = {"career", "fieldbridgehq", "trading", "construction", "ai-tools", "health", "family", "inbox", "general"}

    @staticmethod
    def _parse_frontmatter(content):
        """Minimal YAML-frontmatter parser (no external deps). Handles
        key: value, key: "quoted", and key: [a, b, c] list syntax — the
        subset actually used across this vault. Returns (meta_dict, body_str)."""
        meta = {}
        body = content
        if content.startswith('---'):
            end = content.find('\n---', 3)
            if end != -1:
                fm_block = content[3:end].strip('\n')
                body = content[end + 4:].lstrip('\n')
                for line in fm_block.splitlines():
                    if ':' not in line:
                        continue
                    key, _, val = line.partition(':')
                    key = key.strip()
                    val = val.strip()
                    if not key:
                        continue
                    if val.startswith('[') and val.endswith(']'):
                        items = [v.strip().strip('"\'') for v in val[1:-1].split(',') if v.strip()]
                        meta[key] = items
                    else:
                        meta[key] = val.strip('"\'')
        return meta, body

    def _call_hermes(self, messages, model='owl-alpha', max_tokens=1200, temperature=0.4):
        """Internal helper — call the Hermes chat completion endpoint directly
        (server-side, not proxied through a browser request) and return the
        assistant's text, or None on failure."""
        try:
            import urllib.request
            openai_request = {
                'model': model,
                'messages': messages,
                'stream': False,
                'temperature': temperature,
                'max_tokens': max_tokens,
            }
            req = urllib.request.Request(
                f"{HERMES_CHAT_PROXY_URL}/v1/chat/completions",
                data=json.dumps(openai_request).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer life-os-dashboard-2026',
                },
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data['choices'][0]['message']['content']
        except Exception as e:
            print(f"⚠ _call_hermes failed: {e}")
            return None

    def _infer_domain(self, rel_path, meta):
        """Resolve a page's domain — explicit frontmatter wins (raw key or
        pretty agents.md name), else inferred from vault folder/subfolder,
        else 'general'."""
        fm = str(meta.get('domain', '')).strip()
        if fm in self._KNOWN_DOMAINS:
            return fm
        if fm.lower() in self._PRETTY_DOMAINS:
            return self._PRETTY_DOMAINS[fm.lower()]
        parts = rel_path.split('/')
        top = parts[0] if parts else ''
        sub = parts[1].lower() if len(parts) > 1 else ''
        if top in ("030 Resources", "30_Context") and sub:
            if sub in self._PRETTY_DOMAINS:
                return self._PRETTY_DOMAINS[sub]
            # keyword fallback so any NEW domain folder agents.md creates
            # still lands somewhere sensible without a code change
            for kw, dom in (('construction', 'construction'), ('trading', 'trading'),
                            ('health', 'health'), ('family', 'family'),
                            ('business', 'fieldbridgehq'), ('ai', 'ai-tools'),
                            ('pkm', 'ai-tools'), ('knowledge', 'ai-tools')):
                if kw in sub:
                    return dom
            return 'general'
        if top in ("010 Projects", "020 Areas") and sub:
            if 'fieldbridge' in sub:
                return 'fieldbridgehq'
            if 'career' in sub or 'job' in sub:
                return 'career'
            if 'trading' in sub or 'crypto' in sub or 'finance' in sub:
                return 'trading'
            if 'health' in sub:
                return 'health'
            if 'family' in sub:
                return 'family'
            if 'knowledge' in sub or 'learning' in sub:
                return 'ai-tools'
            if 'work' in sub:
                return 'construction'
            return 'general'
        return self._WIKI_DOMAIN_FOLDERS.get(top, 'general')

    def _iter_wiki_files(self):
        """Yield every markdown file considered part of the wiki surface —
        the whole vault minus dotfiles, raw Clippings, and processed-source
        archives (those are 'raw sources', not wiki pages, per the schema)."""
        exclude_top = {"Clippings", "10_Sources", ".chat_sessions",
                       "000 Inbox", "_Templates", "040 Archive"}
        for md_file in VAULT_DIR.rglob("*.md"):
            if not md_file.is_file():
                continue
            try:
                rel = md_file.relative_to(VAULT_DIR)
            except ValueError:
                continue
            parts = rel.parts
            if any(p.startswith('.') for p in parts):
                continue
            if parts and parts[0] in exclude_top:
                continue
            yield md_file, str(rel).replace('\\', '/')

    def _load_wiki_pages(self):
        """Scan the whole wiki surface, parse OKF frontmatter, and return a
        list of page dicts. Shared by the graph, page-detail, query, and lint
        endpoints so they all see the same view of the vault."""
        pages = []
        for md_file, rel_path in self._iter_wiki_files():
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    raw_content = f.read(80000)
            except Exception:
                continue
            meta, body = self._parse_frontmatter(raw_content)
            title = meta.get('title', '')
            if not title:
                for line in body.splitlines()[:5]:
                    if line.strip().startswith('#'):
                        title = line.lstrip('#').strip()
                        break
            if not title:
                title = md_file.stem.replace('-', ' ').replace('_', ' ').title()
            domain = self._infer_domain(rel_path, meta)
            wikilinks = [m.strip() for m in re.findall(r'\[\[([^\]|#]+)', raw_content)]
            pages.append({
                "title": title,
                "name": md_file.name,
                "file": rel_path,
                "path": rel_path,
                "id": md_file.stem,
                "folder": rel_path.split('/')[0] if '/' in rel_path else 'root',
                "domain": domain,
                "type": meta.get('type', ''),
                "description": meta.get('description', ''),
                "tags": meta.get('tags', []),
                "timestamp": meta.get('timestamp') or meta.get('last_reviewed') or meta.get('date_processed') or meta.get('created') or '',
                "resource": meta.get('resource') or meta.get('source_url') or meta.get('source') or '',
                # agents.md pages carry domain/tags rather than the old OKF 'type' —
                # count either convention as conformant so lint doesn't false-flag the new vault
                "okf_conformant": bool(meta.get('type') or meta.get('domain') or meta.get('tags')),
                "words": len(body.split()),
                "links": len(wikilinks),
                "wikilinks": wikilinks,
                "rawContent": raw_content,
            })
        return pages

    def _serve_wiki_index(self):
        """GET /api/wiki — full-vault OKF-aware page index for the 3D Brain graph.
        Scans every wiki-surface markdown file (not just 20_Wiki/), so
        FieldBridge/Career/Trading content — the domains most likely to hold
        cross-domain monetization links — actually show up in the graph."""
        try:
            pages = self._load_wiki_pages()
            # Inbound link counts, used by the graph + lint for orphan detection
            title_index = {}
            for p in pages:
                title_index.setdefault(p['title'], []).append(p['id'])
                title_index.setdefault(p['id'], []).append(p['id'])
            inbound = {p['id']: 0 for p in pages}
            for p in pages:
                for wl in p['wikilinks']:
                    target_name = wl.split('/')[-1]
                    for target_id in title_index.get(wl, []) or title_index.get(target_name, []):
                        if target_id != p['id']:
                            inbound[target_id] = inbound.get(target_id, 0) + 1
            for p in pages:
                p['inbound_links'] = inbound.get(p['id'], 0)
            self._json_response({"data": pages})
        except Exception as e:
            self._json_error(500, f"Failed to serve wiki index: {str(e)}")

    def _serve_wiki_page(self, query):
        """GET /api/wiki/page?path=... — full content of one wiki page, for
        the 3D Brain's node-detail panel."""
        try:
            path_str = (query.get('path') or [''])[0].lstrip('/')
            if not path_str:
                self._json_error(400, "Missing 'path' parameter")
                return
            file_path = VAULT_DIR / path_str
            try:
                file_path.resolve().relative_to(VAULT_DIR.resolve())
            except ValueError:
                self._json_error(403, "Path outside vault")
                return
            if not file_path.exists():
                self._json_error(404, "Page not found")
                return
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            meta, body = self._parse_frontmatter(content)
            self._json_response({"data": {
                "path": path_str,
                "meta": meta,
                "body": body,
            }})
        except Exception as e:
            self._json_error(500, f"Failed to serve wiki page: {str(e)}")

    def _serve_wiki_lint(self):
        """GET /api/wiki/lint — health-check pass over the wiki (Karpathy's
        'Lint' operation): orphan pages, dangling links, stale pages, and
        pages missing the OKF-required 'type' field. Read-only; the narrative
        opportunity/gap analysis on top of this is /api/wiki/lint/analyze."""
        try:
            pages = self._load_wiki_pages()
            title_index = {}
            for p in pages:
                title_index.setdefault(p['title'], []).append(p['id'])
                title_index.setdefault(p['id'], []).append(p['id'])
            inbound = {p['id']: 0 for p in pages}
            dangling = []
            for p in pages:
                for wl in p['wikilinks']:
                    target_name = wl.split('/')[-1]
                    hits = title_index.get(wl) or title_index.get(target_name)
                    if not hits:
                        dangling.append({"from": p['title'], "from_path": p['path'], "target": wl})
                        continue
                    for target_id in hits:
                        if target_id != p['id']:
                            inbound[target_id] = inbound.get(target_id, 0) + 1

            now = datetime.datetime.now()
            stale = []
            missing_type = []
            orphans = []
            for p in pages:
                if not p['okf_conformant']:
                    missing_type.append({"title": p['title'], "path": p['path']})
                if inbound.get(p['id'], 0) == 0 and p['folder'] not in ('00_Kernel',):
                    orphans.append({"title": p['title'], "path": p['path'], "domain": p['domain']})
                ts = p.get('timestamp')
                if ts:
                    try:
                        ts_clean = ts.replace('Z', '').split('T')[0]
                        ts_date = datetime.datetime.strptime(ts_clean, '%Y-%m-%d')
                        age_days = (now - ts_date).days
                        if age_days > 60 and p['domain'] in ('career', 'fieldbridgehq', 'trading'):
                            stale.append({"title": p['title'], "path": p['path'], "domain": p['domain'], "age_days": age_days})
                    except Exception:
                        pass

            # Cross-domain opportunity heuristic — same signal the 3D Brain
            # graph already glows for, surfaced here as a structured list.
            cross_domain_pairs = []
            id_to_page = {p['id']: p for p in pages}
            for p in pages:
                for wl in p['wikilinks']:
                    target_name = wl.split('/')[-1]
                    hits = title_index.get(wl) or title_index.get(target_name)
                    if not hits:
                        continue
                    for target_id in hits:
                        target = id_to_page.get(target_id)
                        if target and target['domain'] != p['domain']:
                            cross_domain_pairs.append({
                                "from": p['title'], "from_domain": p['domain'],
                                "to": target['title'], "to_domain": target['domain'],
                            })

            self._json_response({"data": {
                "total_pages": len(pages),
                "orphans": orphans[:30],
                "orphan_count": len(orphans),
                "dangling_links": dangling[:30],
                "dangling_count": len(dangling),
                "stale_pages": stale[:30],
                "stale_count": len(stale),
                "missing_type": missing_type[:30],
                "missing_type_count": len(missing_type),
                "cross_domain_links": cross_domain_pairs[:30],
                "cross_domain_count": len(cross_domain_pairs),
                "generated_at": now.isoformat(),
            }})
        except Exception as e:
            self._json_error(500, f"Failed to lint wiki: {str(e)}")

    def _handle_wiki_lint_analyze(self):
        """POST /api/wiki/lint/analyze — takes a lint report (or regenerates
        one) and asks Hermes for the narrative: best next use case, best
        monetization angle, single highest-value gap to fill. Per the schema,
        this should give ONE best answer per category, not an exhaustive list."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length else b'{}'
            data = json.loads(body.decode('utf-8')) if body else {}
        except Exception:
            data = {}

        try:
            pages = self._load_wiki_pages()
            domain_counts = {}
            for p in pages:
                domain_counts[p['domain']] = domain_counts.get(p['domain'], 0) + 1

            # Caller (the 3D Brain page) normally passes the lint report it
            # already fetched; if absent, fall back to domain counts only.
            lint_summary = data.get('lint')

            prompt = (
                "You are analyzing Fadi's personal knowledge vault (LLM wiki) as the periodic "
                "'Lint' pass. Context: Fadi is a Senior Construction PM running three parallel "
                "priorities through August 6 2026 — (1) job search: Senior PM/Executive roles in "
                "Ontario, Egypt, UAE, Saudi, (2) FieldBridge HQ: an AI field-intelligence product "
                "for specialty trade contractors, (3) steady side income / prop trading exploration. "
                f"Vault contents by domain: {json.dumps(domain_counts)}. "
                f"Lint findings: {json.dumps(lint_summary) if lint_summary else 'not provided — use domain counts only'}. "
                "Give exactly three things, each 1-2 sentences, no filler: "
                "1) NEW USE CASE — the single best new way Hermes could help Fadi based on what's "
                "actually in the vault right now. "
                "2) MONETIZATION ANGLE — the single best intersection between vault knowledge and "
                "his FieldBridge/CRM pipeline that could turn into revenue. "
                "3) BIGGEST GAP — the one most valuable missing piece of knowledge worth adding next. "
                "Be specific and reference real vault content, not generic advice."
            )
            answer = self._call_hermes(
                [{"role": "user", "content": prompt}],
                max_tokens=700,
            )
            if answer is None:
                self._json_error(502, "Hermes did not respond — check the Hermes gateway is running")
                return
            self._json_response({"data": {"analysis": answer, "generated_at": datetime.datetime.now().isoformat()}})
        except Exception as e:
            self._json_error(500, f"Lint analysis failed: {str(e)}")

    def _handle_wiki_query(self):
        """POST /api/wiki/query — brain.py's deterministic retrieval ladder
        (BUILD SPEC v1, Part A / GAP A): score the index without opening any
        wiki page body, open exactly the one top-scoring page, pull the one
        best section (capped 1500 chars), optionally follow one [[wikilink]]
        pointer, then make exactly one Hermes call citing that page. Replaces
        the old 'open every page, score raw content, send top-6' pattern."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._json_error(400, "No data provided")
                return
            data = json.loads(self.rfile.read(content_length).decode('utf-8'))
            question = (data.get('question') or '').strip()
            if not question:
                self._json_error(400, "Missing 'question'")
                return

            evidence = brain.retrieve(question, VAULT_DIR, data_dir=DATA_DIR)

            if not evidence.get("found"):
                self._json_response({"data": {
                    "answer": "Nothing in the vault matches that yet — this might be a genuine knowledge gap worth filling.",
                    "sources": [],
                    "evidence": evidence,
                }})
                return

            prompt = (
                f"Answer this question using ONLY the vault excerpt below. Cite the page title "
                f"for every claim (e.g. 'per [Page Title]'). If the excerpt doesn't actually answer "
                f"the question, say so plainly rather than guessing.\n\n"
                f"QUESTION: {question}\n\n"
                f"PAGE: {evidence['page_title']} (path: {evidence['page_path']}, domain: {evidence['domain']})\n"
                f"SECTION: {evidence['section_heading']}\n{evidence['text']}"
            )
            answer = self._call_hermes([{"role": "user", "content": prompt}], max_tokens=900)
            if answer is None:
                self._json_error(502, "Hermes did not respond — check the Hermes gateway is running")
                return

            self._json_response({"data": {
                "answer": answer,
                "sources": [{
                    "title": evidence['page_title'],
                    "path": evidence['page_path'],
                    "domain": evidence['domain'],
                }],
                "evidence": evidence,
            }})
        except Exception as e:
            self._json_error(500, f"Wiki query failed: {str(e)}")

    def _handle_wiki_migrate(self):
        """POST /api/wiki/migrate — one-time (repeatable, non-destructive)
        pass that backfills missing OKF-required frontmatter on every wiki
        page. Never overwrites an existing field, only adds what's missing.
        Also writes OKF-WIKI-SCHEMA.md into 00_Kernel/ if not already present."""
        # ── RETIRED 2026-07-05 (Decision Gate 1): the vault is a read-only git
        # mirror; ALL ingestion runs in Claude Cowork via agents.md operations
        # (OPERATION 1/5/6/7 + the nightly-second-brain-sync task). Server-side
        # writes into the vault would break the 15-min git pull. This endpoint
        # is kept for API compatibility but performs no writes.
        self._json_response({
            "retired": True,
            "message": "Ingestion moved to Cowork (agents.md operations). Drop sources into the vault's 10_Sources/raw/ or 000 Inbox/ — the nightly sync ingests them and this mirror receives the result within 15 minutes of the 9:30 PM vault push."
        }, status=410)
        return
        try:
            updated = 0
            scanned = 0
            skipped = 0
            for md_file, rel_path in self._iter_wiki_files():
                scanned += 1
                try:
                    content = md_file.read_text(encoding='utf-8', errors='ignore')
                except Exception:
                    skipped += 1
                    continue
                meta, body = self._parse_frontmatter(content)
                if meta.get('type'):
                    continue  # already OKF-conformant on the one required field

                # Infer sensible defaults rather than requiring a human pass
                title = meta.get('title', '')
                if not title:
                    for line in body.splitlines()[:5]:
                        if line.strip().startswith('#'):
                            title = line.lstrip('#').strip()
                            break
                if not title:
                    title = md_file.stem.replace('-', ' ').replace('_', ' ').title()

                folder = rel_path.split('/')[0] if '/' in rel_path else 'root'
                inferred_type = {
                    'Clippings': 'Clipping', '10_Sources': 'Source', '90_Skills': 'Skill',
                    '40_Tasks': 'Task', '95_Outputs': 'Output', '00_Kernel': 'System',
                }.get(folder, 'Note')
                domain = self._infer_domain(rel_path, meta)

                new_fields = []
                if 'type' not in meta:
                    new_fields.append(f'type: {inferred_type}')
                if 'title' not in meta:
                    new_fields.append(f'title: "{title}"')
                if 'domain' not in meta:
                    new_fields.append(f'domain: {domain}')
                if 'timestamp' not in meta and 'last_reviewed' not in meta:
                    mtime = datetime.datetime.fromtimestamp(md_file.stat().st_mtime).strftime('%Y-%m-%dT%H:%M:%S')
                    new_fields.append(f'timestamp: "{mtime}"')

                if content.startswith('---'):
                    end = content.find('\n---', 3)
                    if end != -1:
                        insert_at = end
                        new_content = content[:insert_at] + '\n' + '\n'.join(new_fields) + content[insert_at:]
                    else:
                        new_content = content
                else:
                    fm = '---\n' + '\n'.join(new_fields) + '\n---\n\n'
                    new_content = fm + content

                try:
                    md_file.write_text(new_content, encoding='utf-8')
                    updated += 1
                except Exception:
                    skipped += 1

            # Deploy the schema file into the vault if it isn't there yet
            schema_dst = VAULT_DIR / "00_Kernel" / "OKF-WIKI-SCHEMA.md"
            schema_deployed = False
            if not schema_dst.exists() and _OKF_SCHEMA_CONTENT:
                try:
                    schema_dst.parent.mkdir(parents=True, exist_ok=True)
                    schema_dst.write_text(_OKF_SCHEMA_CONTENT, encoding='utf-8')
                    schema_deployed = True
                except Exception:
                    pass

            self._json_response({"data": {
                "scanned": scanned, "updated": updated, "skipped": skipped,
                "schema_deployed": schema_deployed,
            }})
        except Exception as e:
            self._json_error(500, f"OKF migration failed: {str(e)}")

    # ═══════════════════════════════════════════════════════════
    # FIREFLIES INGESTION — first of the queued source integrations
    # (see life-os-ui-backlog memory). Pulls recent meeting
    # transcripts into the wiki as OKF-conformant pages.
    # ═══════════════════════════════════════════════════════════

    # HARD EXCLUSION — never ingest anything referencing Jackman/KOC,
    # regardless of context. Standing rule, not a one-time filter.
    # See life-os-ui-backlog memory entry "Jackman/KOC exclusion note".
    _JACKMAN_EXCLUDE_TERMS = ("jackman", "koc")

    def _get_fireflies_key(self):
        """Read FIREFLIES_API_KEY from ~/.hermes/.env — same file/format as
        _get_openrouter_key(). Set via Settings > API Keys > Fireflies.ai."""
        env_path = Path.home() / ".hermes" / ".env"
        if not env_path.exists():
            return ""
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith("FIREFLIES_API_KEY="):
                return line.split('=', 1)[1].strip().strip('\'"')
        return ""

    def _fetch_fireflies_transcripts(self, limit=25):
        """Fetch recent meeting transcripts via the Fireflies GraphQL API."""
        import urllib.request
        key = self._get_fireflies_key()
        if not key:
            raise RuntimeError("No Fireflies API key configured — add one in Settings > API Keys")
        query = """
        query Transcripts($limit: Int) {
          transcripts(limit: $limit) {
            id
            title
            dateString
            duration
            summary {
              short_summary
              overview
              keywords
              action_items
            }
          }
        }
        """
        payload = json.dumps({"query": query, "variables": {"limit": limit}}).encode('utf-8')
        req = urllib.request.Request(
            'https://api.fireflies.ai/graphql',
            data=payload,
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
        if resp.get('errors'):
            raise RuntimeError(resp['errors'][0].get('message', 'Fireflies GraphQL error'))
        return (resp.get('data') or {}).get('transcripts') or []

    def _fireflies_contains_excluded_terms(self, transcript):
        """True if title/summary/keywords/action_items mention Jackman/KOC
        in any form — checked as substrings, deliberately broad/paranoid."""
        summary = transcript.get('summary') or {}
        haystack_parts = [
            transcript.get('title') or '',
            summary.get('short_summary') or '',
            summary.get('overview') or '',
            summary.get('action_items') or '',
            ' '.join(summary.get('keywords') or []),
        ]
        haystack = ' '.join(haystack_parts).lower()
        return any(term in haystack for term in self._JACKMAN_EXCLUDE_TERMS)

    def _infer_meeting_domain(self, transcript):
        """Lightweight content-based domain guess for a meeting — meetings
        don't live in a domain-specific folder the way wiki pages do, so we
        can't use _infer_domain()'s folder heuristic here."""
        summary = transcript.get('summary') or {}
        text = ' '.join([
            transcript.get('title') or '',
            summary.get('short_summary') or '',
            summary.get('overview') or '',
            ' '.join(summary.get('keywords') or []),
        ]).lower()
        if any(w in text for w in ('fieldbridge', 'contractor', 'claim', 'prospect', 'estimating', 'proposal')):
            return 'fieldbridgehq'
        if any(w in text for w in ('recruiter', 'interview', 'job offer', 'resume', 'cv ', 'hiring')):
            return 'career'
        if any(w in text for w in ('trading', 'crypto', 'stock', 'position size', 'tp/sl')):
            return 'trading'
        return 'general'

    def _handle_fireflies_ingest(self):
        """POST /api/wiki/ingest-fireflies — pull recent Fireflies meetings
        into the wiki as OKF-conformant pages under 10_Sources/Fireflies/.
        Idempotent (tracks ingested IDs in .fireflies_ingested.json) and
        hard-excludes anything matching _JACKMAN_EXCLUDE_TERMS."""
        # ── RETIRED 2026-07-05 (Decision Gate 1): the vault is a read-only git
        # mirror; ALL ingestion runs in Claude Cowork via agents.md operations
        # (OPERATION 1/5/6/7 + the nightly-second-brain-sync task). Server-side
        # writes into the vault would break the 15-min git pull. This endpoint
        # is kept for API compatibility but performs no writes.
        self._json_response({
            "retired": True,
            "message": "Ingestion moved to Cowork (agents.md operations). Drop sources into the vault's 10_Sources/raw/ or 000 Inbox/ — the nightly sync ingests them and this mirror receives the result within 15 minutes of the 9:30 PM vault push."
        }, status=410)
        return
        try:
            state_path = VAULT_DIR / ".fireflies_ingested.json"
            ingested_ids = set()
            if state_path.exists():
                try:
                    ingested_ids = set(json.loads(state_path.read_text(encoding='utf-8')))
                except Exception:
                    ingested_ids = set()

            transcripts = self._fetch_fireflies_transcripts(limit=25)

            out_dir = VAULT_DIR / "10_Sources" / "Fireflies"
            out_dir.mkdir(parents=True, exist_ok=True)

            created = 0
            skipped_duplicate = 0
            skipped_excluded = 0
            excluded_titles = []

            for t in transcripts:
                tid = t.get('id')
                if not tid or tid in ingested_ids:
                    skipped_duplicate += 1
                    continue
                if self._fireflies_contains_excluded_terms(t):
                    skipped_excluded += 1
                    excluded_titles.append(t.get('title', 'Untitled'))
                    ingested_ids.add(tid)  # never re-check this one again
                    continue

                title = t.get('title') or 'Untitled Meeting'
                date_str = (t.get('dateString') or '')[:10] or datetime.datetime.now().strftime('%Y-%m-%d')
                summary = t.get('summary') or {}
                domain = self._infer_meeting_domain(t)
                keywords = summary.get('keywords') or []
                action_items = (summary.get('action_items') or '').strip()
                overview = (summary.get('short_summary') or summary.get('overview') or '').strip()

                safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')[:60] or 'meeting'
                filename = f"{date_str}-{safe_title}-{tid[:8]}.md"
                filepath = out_dir / filename

                frontmatter_lines = [
                    "---",
                    "type: Meeting",
                    f'title: "{title.replace(chr(34), chr(39))}"',
                    f"domain: {domain}",
                    f'timestamp: "{date_str}"',
                    f'resource: "https://app.fireflies.ai/view/{tid}"',
                    f"tags: [type/meeting, area/{domain}, source/fireflies]",
                    "---",
                    "",
                    f"# {title}",
                    "",
                    "## Summary",
                    overview or "_No summary available._",
                    "",
                    "## Keywords",
                    ', '.join(keywords) if keywords else "_None extracted._",
                    "",
                    "## Action Items",
                    action_items if action_items else "_None extracted._",
                    "",
                    "## Opportunity Signal",
                    "_Not yet analyzed — run Wiki Health → 🔮 Ask Hermes to Analyze for cross-vault opportunity signals._",
                    "",
                    f"*Source: Fireflies transcript {tid} | Ingested: {datetime.datetime.now().strftime('%Y-%m-%d')}*",
                ]

                try:
                    filepath.write_text('\n'.join(frontmatter_lines), encoding='utf-8')
                    created += 1
                    ingested_ids.add(tid)
                except Exception as e:
                    print(f"[fireflies-ingest] Failed to write {filename}: {e}")

            state_path.write_text(json.dumps(sorted(ingested_ids)), encoding='utf-8')

            self._json_response({"data": {
                "fetched": len(transcripts),
                "created": created,
                "skipped_duplicate": skipped_duplicate,
                "skipped_excluded": skipped_excluded,
                "excluded_titles": excluded_titles,
            }})
        except Exception as e:
            self._json_error(500, f"Fireflies ingestion failed: {str(e)}")

    # ═══════════════════════════════════════════════════════════
    # YOUTUBE / VIDEO TRANSCRIPT INGESTION — second source integration
    # (see life-os-ui-backlog memory, "biggest dormant-data unlock").
    # Solves "I clip videos but never have time to watch them": finds
    # video clips already saved via the web clipper, pulls their
    # transcripts, and enriches the existing clip page in place rather
    # than creating a duplicate page.
    # ═══════════════════════════════════════════════════════════

    _VIDEO_URL_RE = re.compile(
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|vimeo\.com/)([\w-]{6,20})'
    )

    def _extract_video_id(self, url):
        m = self._VIDEO_URL_RE.search(url or '')
        return m.group(1) if m else None

    def _fetch_youtube_transcript_text(self, video_id):
        """Fetch auto-captions via youtube-transcript-api — no API key needed.
        Raises RuntimeError with an actionable message if the library isn't
        installed on the VPS yet, or if no captions exist for the video."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            raise RuntimeError(
                "youtube-transcript-api not installed on the server. "
                "Run: pip install youtube-transcript-api"
            )
        try:
            segments = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e:
            raise RuntimeError(f"No transcript available ({e.__class__.__name__})")
        return ' '.join(s.get('text', '').strip() for s in segments if s.get('text'))

    def _handle_youtube_ingest(self):
        """POST /api/wiki/ingest-youtube — scan Clippings/ for video-clip
        pages not yet transcribed, fetch their transcripts, and enrich the
        existing page in place (frontmatter flag `transcribed: true` plus an
        appended Transcript section) so nothing gets duplicated. Idempotent
        via that frontmatter flag; also tracked in .youtube_ingested.json as
        a fallback for pages whose frontmatter got hand-edited."""
        # ── RETIRED 2026-07-05 (Decision Gate 1): the vault is a read-only git
        # mirror; ALL ingestion runs in Claude Cowork via agents.md operations
        # (OPERATION 1/5/6/7 + the nightly-second-brain-sync task). Server-side
        # writes into the vault would break the 15-min git pull. This endpoint
        # is kept for API compatibility but performs no writes.
        self._json_response({
            "retired": True,
            "message": "Ingestion moved to Cowork (agents.md operations). Drop sources into the vault's 10_Sources/raw/ or 000 Inbox/ — the nightly sync ingests them and this mirror receives the result within 15 minutes of the 9:30 PM vault push."
        }, status=410)
        return
        try:
            state_path = VAULT_DIR / ".youtube_ingested.json"
            ingested_ids = set()
            if state_path.exists():
                try:
                    ingested_ids = set(json.loads(state_path.read_text(encoding='utf-8')))
                except Exception:
                    ingested_ids = set()

            clips_dir = DATA_DIR / "clippings"
            if not clips_dir.exists():
                self._json_response({"data": {"scanned": 0, "transcribed": 0, "skipped": 0, "message": "No Clippings folder yet."}})
                return

            scanned = 0
            transcribed = 0
            skipped_duplicate = 0
            skipped_no_video = 0
            skipped_excluded = 0
            failed = []
            lib_missing = False

            for item in sorted(clips_dir.iterdir()):
                if not item.is_file() or item.name.startswith('.') or not item.name.endswith('.md'):
                    continue
                try:
                    raw = item.read_text(encoding='utf-8')
                except Exception:
                    continue
                meta, body = self._parse_frontmatter(raw)
                source_url = meta.get('source_url') or meta.get('resource') or ''
                video_id = self._extract_video_id(source_url)
                if not video_id:
                    continue
                scanned += 1
                if meta.get('transcribed') or video_id in ingested_ids:
                    skipped_duplicate += 1
                    continue
                title = meta.get('title', item.stem)
                haystack = f"{title} {body}".lower()
                if any(term in haystack for term in self._JACKMAN_EXCLUDE_TERMS):
                    skipped_excluded += 1
                    ingested_ids.add(video_id)
                    continue
                try:
                    transcript = self._fetch_youtube_transcript_text(video_id)
                except RuntimeError as e:
                    msg = str(e)
                    if 'not installed' in msg:
                        lib_missing = True
                    failed.append({"title": title, "reason": msg})
                    continue

                if any(term in transcript.lower() for term in self._JACKMAN_EXCLUDE_TERMS):
                    skipped_excluded += 1
                    ingested_ids.add(video_id)
                    continue

                # Enrich in place: flip transcribed flag in frontmatter, append transcript.
                new_raw = raw
                if 'transcribed:' in new_raw:
                    new_raw = re.sub(r'transcribed:\s*\w+', 'transcribed: true', new_raw)
                else:
                    new_raw = new_raw.replace('---\n\n', 'transcribed: true\n---\n\n', 1)
                new_raw += (
                    f"\n\n## Transcript (auto-captions)\n\n{transcript}\n\n"
                    "## Opportunity Signal\n"
                    "_Not yet analyzed — run Wiki Health → 🔮 Ask Hermes to Analyze._\n"
                )
                try:
                    item.write_text(new_raw, encoding='utf-8')
                    transcribed += 1
                    ingested_ids.add(video_id)
                except Exception as e:
                    failed.append({"title": title, "reason": f"Write failed: {e}"})

            state_path.write_text(json.dumps(sorted(ingested_ids)), encoding='utf-8')
            result = {
                "scanned": scanned, "transcribed": transcribed,
                "skipped_duplicate": skipped_duplicate, "skipped_excluded": skipped_excluded,
                "failed": failed,
            }
            if lib_missing:
                result["setup_needed"] = "pip install youtube-transcript-api on the VPS, then re-run."
            self._json_response({"data": result})
        except Exception as e:
            self._json_error(500, f"YouTube ingestion failed: {str(e)}")

    # ═══════════════════════════════════════════════════════════
    # GMAIL INGESTION — third source integration. Uses an IMAP App
    # Password (self-service Google Account setting, no OAuth consent
    # screen needed) rather than full OAuth, same "paste a key in
    # Settings" pattern as Fireflies. HARD-SCOPED: only pulls threads
    # matching a Gmail label query (default: FieldBridge label tree) —
    # never the whole inbox. If the scoped query returns nothing, this
    # does NOT silently widen scope; it reports 0 and tells you why.
    # ═══════════════════════════════════════════════════════════

    def _handle_gmail_ingest(self):
        """POST /api/wiki/ingest-gmail — pull recent FieldBridge-labeled
        Gmail threads into 10_Sources/Gmail/ as OKF-conformant pages.
        Body (optional JSON): {"query": "label:fieldbridge", "limit": 30}"""
        # ── RETIRED 2026-07-05 (Decision Gate 1): the vault is a read-only git
        # mirror; ALL ingestion runs in Claude Cowork via agents.md operations
        # (OPERATION 1/5/6/7 + the nightly-second-brain-sync task). Server-side
        # writes into the vault would break the 15-min git pull. This endpoint
        # is kept for API compatibility but performs no writes.
        self._json_response({
            "retired": True,
            "message": "Ingestion moved to Cowork (agents.md operations). Drop sources into the vault's 10_Sources/raw/ or 000 Inbox/ — the nightly sync ingests them and this mirror receives the result within 15 minutes of the 9:30 PM vault push."
        }, status=410)
        return
        import imaplib
        import email as email_lib
        from email.header import decode_header

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body_data = {}
            if content_length:
                try:
                    body_data = json.loads(self.rfile.read(content_length).decode('utf-8'))
                except Exception:
                    body_data = {}

            gmail_addr = self._get_env_var('GMAIL_ADDRESS') or 'fadi@fieldbridgehq.com'
            app_password = self._get_env_var('GMAIL_API_KEY')
            if not app_password:
                self._json_error(400, "No Gmail App Password configured — add one in Settings > API Keys > Gmail. Generate at https://myaccount.google.com/apppasswords")
                return

            gm_query = body_data.get('query') or 'label:fieldbridge'
            limit = min(int(body_data.get('limit', 30)), 50)

            imap = imaplib.IMAP4_SSL('imap.gmail.com', timeout=20)
            imap.login(gmail_addr, app_password)
            imap.select('"[Gmail]/All Mail"', readonly=True)
            typ, data = imap.search(None, 'X-GM-RAW', f'"{gm_query}"')
            if typ != 'OK':
                imap.logout()
                self._json_error(500, f"IMAP search failed: {typ}")
                return
            ids = data[0].split()
            if not ids:
                imap.logout()
                self._json_response({"data": {
                    "fetched": 0, "created": 0,
                    "message": f"0 threads matched \"{gm_query}\". Scope stays narrow by design — "
                               "apply the FieldBridge Gmail label taxonomy to threads first, or pass "
                               "a broader \"query\" in the request body.",
                }})
                return
            ids = ids[-limit:]  # most recent

            state_path = VAULT_DIR / ".gmail_ingested.json"
            ingested_ids = set()
            if state_path.exists():
                try:
                    ingested_ids = set(json.loads(state_path.read_text(encoding='utf-8')))
                except Exception:
                    ingested_ids = set()

            out_dir = VAULT_DIR / "10_Sources" / "Gmail"
            out_dir.mkdir(parents=True, exist_ok=True)

            created = 0
            skipped_duplicate = 0
            skipped_excluded = 0
            excluded_subjects = []

            for msg_id in ids:
                typ, msg_data = imap.fetch(msg_id, '(RFC822)')
                if typ != 'OK' or not msg_data or not msg_data[0]:
                    continue
                msg = email_lib.message_from_bytes(msg_data[0][1])
                message_id = (msg.get('Message-ID') or msg_id.decode()).strip()
                if message_id in ingested_ids:
                    skipped_duplicate += 1
                    continue

                def _decode(val):
                    if not val:
                        return ''
                    parts = decode_header(val)
                    return ''.join(
                        p.decode(enc or 'utf-8', errors='ignore') if isinstance(p, bytes) else p
                        for p, enc in parts
                    )

                subject = _decode(msg.get('Subject', 'No Subject'))
                sender = _decode(msg.get('From', ''))
                date_hdr = msg.get('Date', '')

                text_body = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain' and not part.get('Content-Disposition'):
                            try:
                                text_body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                            except Exception:
                                pass
                            break
                else:
                    try:
                        text_body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
                    except Exception:
                        text_body = str(msg.get_payload())
                text_body = text_body.strip()[:6000]

                haystack = f"{subject} {sender} {text_body}".lower()
                if any(term in haystack for term in self._JACKMAN_EXCLUDE_TERMS):
                    skipped_excluded += 1
                    excluded_subjects.append(subject)
                    ingested_ids.add(message_id)
                    continue

                try:
                    date_str = email_lib.utils.parsedate_to_datetime(date_hdr).strftime('%Y-%m-%d')
                except Exception:
                    date_str = datetime.datetime.now().strftime('%Y-%m-%d')

                domain_text = haystack
                if any(w in domain_text for w in ('contractor', 'claim', 'proposal', 'discovery', 'retainer', 'fieldbridge')):
                    domain = 'fieldbridgehq'
                elif any(w in domain_text for w in ('recruiter', 'interview', 'job offer')):
                    domain = 'career'
                else:
                    domain = 'general'

                safe_subject = re.sub(r'[^\w\s-]', '', subject).strip().replace(' ', '-')[:60] or 'email'
                filename = f"{date_str}-{safe_subject}-{abs(hash(message_id)) % 100000}.md"
                filepath = out_dir / filename
                frontmatter_lines = [
                    "---",
                    "type: Email",
                    f'title: "{subject.replace(chr(34), chr(39))}"',
                    f"domain: {domain}",
                    f'timestamp: "{date_str}"',
                    f'from: "{sender.replace(chr(34), chr(39))}"',
                    f"tags: [type/email, area/{domain}, source/gmail]",
                    "---",
                    "",
                    f"# {subject}",
                    "",
                    f"**From:** {sender}  ",
                    f"**Date:** {date_str}",
                    "",
                    "## Body",
                    text_body or "_No plain-text body extracted._",
                    "",
                    "## Opportunity Signal",
                    "_Not yet analyzed — run Wiki Health → 🔮 Ask Hermes to Analyze._",
                    "",
                    f"*Source: Gmail | Ingested: {datetime.datetime.now().strftime('%Y-%m-%d')}*",
                ]
                try:
                    filepath.write_text('\n'.join(frontmatter_lines), encoding='utf-8')
                    created += 1
                    ingested_ids.add(message_id)
                except Exception as e:
                    print(f"[gmail-ingest] Failed to write {filename}: {e}")

            imap.logout()
            state_path.write_text(json.dumps(sorted(ingested_ids)), encoding='utf-8')
            self._json_response({"data": {
                "query": gm_query, "fetched": len(ids), "created": created,
                "skipped_duplicate": skipped_duplicate, "skipped_excluded": skipped_excluded,
                "excluded_subjects": excluded_subjects,
            }})
        except imaplib.IMAP4.error as e:
            self._json_error(401, f"Gmail login failed: {str(e)}")
        except Exception as e:
            self._json_error(500, f"Gmail ingestion failed: {str(e)}")

    # ═══════════════════════════════════════════════════════════
    # NOTION CRM INGESTION — fourth source integration, the one the
    # whole "CRM feedback → opportunities" loop depends on. Canonical
    # database confirmed 2026-07-03: "Client Pipeline" (under the
    # 🤝 CRM — Client Pipeline page, FieldBridge HQ hub) — matches the
    # live consultancy pipeline stages (Lead→Discovery→Proposal→Active
    # Client→Retainer). The OTHER Notion database that looked similar,
    # "Client CRM — FieldBridge" (SaaS Shield/Bid/Command tiers), is
    # the stale pre-pivot one — not used here.
    # ═══════════════════════════════════════════════════════════

    _CRM_DATABASE_ID = "8d843040-ffa5-4dff-891e-8178d3fc8ab9"

    def _notion_plain_text(self, rich_text_or_value):
        """Best-effort flatten of a Notion property value to plain text
        across the handful of property types the Client Pipeline schema
        uses (title, rich_text, select, email, phone_number, number, date,
        url)."""
        if rich_text_or_value is None:
            return ''
        t = rich_text_or_value.get('type')
        if t in ('title', 'rich_text'):
            return ''.join(seg.get('plain_text', '') for seg in rich_text_or_value.get(t, []))
        if t == 'select':
            sel = rich_text_or_value.get('select')
            return sel.get('name', '') if sel else ''
        if t in ('email', 'phone_number', 'url'):
            return rich_text_or_value.get(t) or ''
        if t == 'number':
            n = rich_text_or_value.get('number')
            return '' if n is None else str(n)
        if t == 'date':
            d = rich_text_or_value.get('date')
            return (d or {}).get('start', '') or ''
        return ''

    def _fetch_notion_crm_rows(self):
        import urllib.request
        key = self._get_env_var('NOTION_API_KEY')
        if not key:
            raise RuntimeError("No Notion integration token configured — add one in Settings > API Keys > Notion (CRM)")
        req = urllib.request.Request(
            f'https://api.notion.com/v1/databases/{self._CRM_DATABASE_ID}/query',
            data=json.dumps({"page_size": 100}).encode('utf-8'),
            headers={'Authorization': f'Bearer {key}', 'Notion-Version': '2022-06-28', 'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = json.loads(r.read())
        return resp.get('results', [])

    def _handle_crm_ingest(self):
        """POST /api/wiki/ingest-crm — pull every row from the live Notion
        Client Pipeline database into CRM/*.md pages, matching this vault's
        existing hand-authored CRM/ convention so they show up in the graph
        alongside everything else (CRM/ is NOT in the wiki-exclude list).
        Full upsert every run (Notion is the source of truth, no diffing
        needed) — one page per company, filename = company name."""
        # ── RETIRED 2026-07-05 (Decision Gate 1): the vault is a read-only git
        # mirror; ALL ingestion runs in Claude Cowork via agents.md operations
        # (OPERATION 1/5/6/7 + the nightly-second-brain-sync task). Server-side
        # writes into the vault would break the 15-min git pull. This endpoint
        # is kept for API compatibility but performs no writes.
        self._json_response({
            "retired": True,
            "message": "Ingestion moved to Cowork (agents.md operations). Drop sources into the vault's 10_Sources/raw/ or 000 Inbox/ — the nightly sync ingests them and this mirror receives the result within 15 minutes of the 9:30 PM vault push."
        }, status=410)
        return
        try:
            rows = self._fetch_notion_crm_rows()
        except RuntimeError as e:
            self._json_error(400, str(e))
            return
        except Exception as e:
            self._json_error(500, f"Notion fetch failed: {str(e)}")
            return

        out_dir = VAULT_DIR / "CRM"
        out_dir.mkdir(parents=True, exist_ok=True)

        created = 0
        skipped_excluded = 0
        companies = []

        for row in rows:
            props = row.get('properties', {})
            company = self._notion_plain_text(props.get('Company')) or 'Unnamed'
            contact = self._notion_plain_text(props.get('Contact Name'))
            stage = self._notion_plain_text(props.get('Stage'))
            trade = self._notion_plain_text(props.get('Trade'))
            region = self._notion_plain_text(props.get('Region'))
            email_addr = self._notion_plain_text(props.get('Email'))
            phone = self._notion_plain_text(props.get('Phone'))
            revenue = self._notion_plain_text(props.get('Revenue Potential (CAD)'))
            next_action = self._notion_plain_text(props.get('Next Action'))
            next_action_date = self._notion_plain_text(props.get('Next Action Date'))
            notes = self._notion_plain_text(props.get('Notes'))
            last_updated = self._notion_plain_text(props.get('Last Updated'))

            haystack = f"{company} {contact} {notes}".lower()
            if any(term in haystack for term in self._JACKMAN_EXCLUDE_TERMS):
                skipped_excluded += 1
                continue

            safe_name = re.sub(r'[^\w\s-]', '', company).strip().replace(' ', '-') or 'unnamed'
            filepath = out_dir / f"{safe_name}.md"
            frontmatter_lines = [
                "---",
                "type: Client",
                f'title: "{company}"',
                "domain: fieldbridgehq",
                f'timestamp: "{last_updated[:10] if last_updated else datetime.datetime.now().strftime("%Y-%m-%d")}"',
                "tags: [type/crm, area/fieldbridgehq, source/notion]",
                f'stage: "{stage}"',
                f'trade: "{trade}"',
                f'region: "{region}"',
                "---",
                "",
                f"# {company}",
                "",
                f"- **Contact:** {contact or '_unknown_'}",
                f"- **Email:** {email_addr or '_unknown_'}",
                f"- **Phone:** {phone or '_unknown_'}",
                f"- **Stage:** {stage or '_unknown_'}",
                f"- **Trade:** {trade or '_unknown_'}",
                f"- **Region:** {region or '_unknown_'}",
                f"- **Revenue Potential (CAD):** {revenue or '_unknown_'}",
                f"- **Next Action:** {next_action or '_none logged_'} ({next_action_date or 'no date'})",
                "",
                "## Notes",
                notes or "_No notes._",
                "",
                "## Opportunity Signal",
                "_Not yet analyzed — run Wiki Health → 🔮 Ask Hermes to Analyze for cross-vault matches "
                "(e.g. clipped articles or meeting transcripts that speak to this client's stated pain)._",
                "",
                f"*Source: Notion Client Pipeline | Synced: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            ]
            try:
                filepath.write_text('\n'.join(frontmatter_lines), encoding='utf-8')
                created += 1
                companies.append(company)
            except Exception as e:
                print(f"[crm-ingest] Failed to write {filepath.name}: {e}")

        self._json_response({"data": {
            "fetched": len(rows), "created": created,
            "skipped_excluded": skipped_excluded, "companies": companies,
        }})

    def _serve_crm_snapshot(self):
        """GET /api/wiki/crm — quick read of the CRM/ folder as JSON, for a
        dashboard card without re-hitting Notion on every page load."""
        try:
            out_dir = VAULT_DIR / "CRM"
            rows = []
            if out_dir.exists():
                for f in sorted(out_dir.glob("*.md")):
                    try:
                        meta, _ = self._parse_frontmatter(f.read_text(encoding='utf-8'))
                    except Exception:
                        continue
                    rows.append({
                        "company": meta.get('title', f.stem),
                        "stage": meta.get('stage', ''),
                        "trade": meta.get('trade', ''),
                        "region": meta.get('region', ''),
                        "path": str(f.relative_to(VAULT_DIR)),
                    })
            self._json_response({"data": rows})
        except Exception as e:
            self._json_error(500, f"Failed to serve CRM snapshot: {str(e)}")

    # ═══════════════════════════════════════════════════════════
    # PROMPTS LIBRARY — replaces the honest placeholder on the Hermes
    # Playbook (use-cases.html) "Saved Prompts" tab. Heuristic extraction
    # only (same honesty standard as skill-usage tracking): flags
    # candidate reusable prompts from chat history, doesn't claim to
    # understand intent. Fadi reviews before reuse.
    # ═══════════════════════════════════════════════════════════

    def _looks_like_reusable_prompt(self, text):
        t = text.strip()
        if not (40 <= len(t) <= 800):
            return False
        # Heuristic signals: imperative opener, or explicit instruction phrasing.
        imperative_openers = (
            'write ', 'build ', 'create ', 'draft ', 'analyze ', 'summarize ',
            'generate ', 'review ', 'compare ', 'design ', 'plan ', 'find ',
            'scan ', 'extract ', 'check ', 'act as', 'you are ', 'help me ',
        )
        low = t.lower()
        if low.startswith(imperative_openers):
            return True
        if '?' not in t and any(w in low for w in ('always', 'every time', 'from now on', 'template', 'format:')):
            return True
        return False

    def _handle_extract_prompts(self):
        """POST /api/wiki/extract-prompts — scan .chat_sessions/*.json for
        candidate reusable prompts (heuristic, not semantic) and cache the
        result in .prompts_library.json. Served back via GET /api/wiki/prompts."""
        try:
            sessions_dir = DATA_DIR / ".chat_sessions"
            candidates = []
            seen_text = set()
            if sessions_dir.exists():
                for sf in sessions_dir.glob("*.json"):
                    try:
                        session = json.loads(sf.read_text(encoding='utf-8'))
                    except Exception:
                        continue
                    title = session.get('title', sf.stem)
                    for msg in session.get('messages', []):
                        if msg.get('role') != 'user':
                            continue
                        content = (msg.get('content') or '').strip()
                        if not self._looks_like_reusable_prompt(content):
                            continue
                        key = content.lower()[:200]
                        if key in seen_text:
                            continue
                        seen_text.add(key)
                        candidates.append({
                            "text": content,
                            "source_session": sf.stem,
                            "source_title": title,
                        })
            lib_path = VAULT_DIR / ".prompts_library.json"
            lib_path.write_text(json.dumps(candidates, indent=2), encoding='utf-8')
            self._json_response({"data": {"extracted": len(candidates)}})
        except Exception as e:
            self._json_error(500, f"Prompt extraction failed: {str(e)}")

    def _serve_prompts_library(self):
        """GET /api/wiki/prompts — serve the cached candidate-prompt list.
        Honest empty state if extraction hasn't been run yet."""
        try:
            lib_path = VAULT_DIR / ".prompts_library.json"
            if not lib_path.exists():
                self._json_response({"data": [], "extracted": False})
                return
            candidates = json.loads(lib_path.read_text(encoding='utf-8'))
            self._json_response({"data": candidates, "extracted": True})
        except Exception as e:
            self._json_error(500, f"Failed to serve prompts library: {str(e)}")

    def _serve_vault_tree(self, query=None):
        """Serve vault directory structure"""
        try:
            base_dir = VAULT_DIR
            if query and 'path' in query:
                requested = query['path'][0].lstrip('/')
                if requested:
                    candidate = VAULT_DIR / requested
                    # Security: must be inside VAULT_DIR
                    try:
                        candidate.resolve().relative_to(VAULT_DIR.resolve())
                        if candidate.exists() and candidate.is_dir():
                            base_dir = candidate
                    except ValueError:
                        pass

            def build_tree(dir_path, rel_path=""):
                items = []
                try:
                    for item in sorted(dir_path.iterdir()):
                        if item.name.startswith('.'):
                            continue
                        item_rel_path = f"{rel_path}/{item.name}" if rel_path else item.name
                        if item.is_dir():
                            items.append({
                                "type": "directory",
                                "name": item.name,
                                "path": item_rel_path,
                                "children": build_tree(item, item_rel_path)
                            })
                        else:
                            items.append({
                                "type": "file",
                                "name": item.name,
                                "path": item_rel_path,
                                "size": item.stat().st_size
                            })
                except Exception as e:
                    print(f"Error reading directory {dir_path}: {e}")
                return items
            
            tree = build_tree(base_dir)
            self._json_response({"data": tree})
        except Exception as e:
            self._json_error(500, f"Failed to serve vault tree: {str(e)}")
    
    def _serve_vault_file(self, query):
        """Serve a specific file from the vault"""
        try:
            file_path_str = query.get('path', [None])[0]
            if not file_path_str:
                self._json_error(400, "Missing 'path' parameter")
                return
            
            file_path = VAULT_DIR / file_path_str.lstrip('/')
            if not file_path.exists():
                self._json_error(404, "File not found")
                return
            
            # Check if file is within vault directory (security)
            try:
                file_path.resolve().relative_to(VAULT_DIR.resolve())
            except ValueError:
                self._json_error(403, "Access denied")
                return
            
            # Determine if we should render as markdown or serve raw
            if file_path.suffix == '.md':
                # Render markdown to HTML and return as JSON
                try:
                    import markdown
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    html = markdown.markdown(content, extensions=['tables', 'fenced_code', 'codehilite'])
                    self._json_response({"html": html})
                except ImportError:
                    # Fallback to plain text
                    with open(file_path, 'r', encoding='utf-8') as f:
                        raw = f.read()
                    self._json_response({"content": raw})
            else:
                # Non-markdown: return as text
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw = f.read()
                self._json_response({"content": raw})
        except Exception as e:
            self._json_error(500, f"Failed to serve vault file: {str(e)}")
    
    def _serve_use_cases(self):
        """Serve live use cases and prompt library"""
        try:
            use_cases = []
            prompts = []
            
            # Scan vault for use cases (files with actionable content)
            for md_file in VAULT_DIR.rglob("*.md"):
                if md_file.is_file():
                    try:
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Simple heuristic: look for action-oriented content
                            lines = content.split('\n')
                            action_lines = [line.strip() for line in lines if 
                                          any(keyword in line.lower() for keyword in 
                                              ['todo', 'action', 'task', 'should', 'must', 'need to', 'will', 'going to'])]
                            if action_lines:
                                rel = str(md_file.relative_to(VAULT_DIR))
                                domain = rel.split('/')[0] if '/' in rel else 'general'
                                use_cases.append({
                                    "file": rel,
                                    "title": md_file.stem.replace('-', ' ').title(),
                                    "domain": domain,
                                    "tags": [domain],
                                    "snippet": ' '.join(action_lines[:3])[:200] + ('...' if len(' '.join(action_lines)) > 200 else ''),
                                    "action_count": len(action_lines)
                                })
                    except Exception:
                        continue
            
            # Extract prompt templates from wiki
            wiki_dir = VAULT_DIR / "20_Wiki"
            if wiki_dir.exists():
                for md_file in wiki_dir.rglob("*.md"):
                    if md_file.is_file():
                        try:
                            with open(md_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                # Look for prompt-like content
                                if '```' in content or 'prompt' in md_file.name.lower():
                                    prompts.append({
                                        "name": md_file.stem,
                                        "file": str(md_file.relative_to(VAULT_DIR)),
                                        "content": content[:500] + ('...' if len(content) > 500 else '')
                                    })
                        except Exception:
                            continue
            
            # Build domain stats
            domain_counts = {}
            for uc in use_cases:
                d = uc.get('domain', 'general')
                domain_counts[d] = domain_counts.get(d, 0) + 1
            
            self._json_response({
                "use_cases": use_cases,
                "prompts": prompts,
                "stats": {"domains": domain_counts, "total_use_cases": len(use_cases), "total_prompts": len(prompts)},
                "updated": datetime.datetime.now().isoformat()
            })
        except Exception as e:
            self._json_error(500, f"Failed to serve use cases: {str(e)}")
    
    def _serve_hermes_pilot(self):
        """READ-ONLY view into the FB-PILOT workspace (~/hermes-pilot).
        Reporting layer only — the dashboard never writes there and the pilot
        never reads the dashboard (separation wall, see FieldBridge HQ
        tools/hermes-pilot/HERMES-BOOTSTRAP.md). Graceful empty state until
        the pilot is installed (planned weekend of 2026-07-04)."""
        try:
            pilot_dir = Path.home() / "hermes-pilot"
            if not pilot_dir.exists():
                self._json_response({"data": {
                    "installed": False,
                    "message": "Pilot not installed yet — see Fieldbridge HQ/tools/hermes-pilot/SETUP-GUIDE.md",
                    "entries": [], "skills": [], "counts": {}
                }})
                return

            def _names(sub):
                d = pilot_dir / sub
                if not d.is_dir():
                    return []
                return sorted(f.name for f in d.iterdir() if f.is_file())

            inbox, outbox, skills = _names("inbox"), _names("outbox"), _names("skills")

            # pilot-log.md format (per HERMES-BOOTSTRAP.md):
            # date | task | self-score | measured score | skill created/updated | lesson
            entries = []
            log_file = pilot_dir / "log" / "pilot-log.md"
            if log_file.exists():
                for line in log_file.read_text(encoding='utf-8', errors='replace').splitlines():
                    line = line.strip().lstrip('-').strip()
                    if not line or line.startswith('#') or '|' not in line:
                        continue
                    parts = [p.strip() for p in line.strip('|').split('|')]
                    if len(parts) < 2 or parts[0].lower() in ('date', '---'):
                        continue
                    if set(parts[0]) <= set('-: '):
                        continue  # markdown table separator row
                    parts += [''] * (6 - len(parts))
                    entries.append({
                        "date": parts[0], "task": parts[1],
                        "self_score": parts[2], "measured": parts[3],
                        "skill": parts[4], "lesson": parts[5],
                    })

            self._json_response({"data": {
                "installed": True,
                "entries": entries[-20:],
                "skills": skills,
                "counts": {"inbox": len(inbox), "outbox": len(outbox),
                           "skills": len(skills), "log_entries": len(entries)},
            }})
        except Exception as e:
            self._json_error(500, f"Failed to serve hermes-pilot: {str(e)}")

    def _serve_state(self):
        """Serve CURRENT-STATE.md as structured JSON"""
        try:
            state_file = VAULT_DIR / "00_Kernel" / "CURRENT-STATE.md"
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                # For now, return as text - could parse frontmatter later
                self._json_response({"data": content})
            else:
                self._json_error(404, "CURRENT-STATE.md not found")
        except Exception as e:
            self._json_error(500, f"Failed to serve state: {str(e)}")
    
    def _serve_skills(self):
        """Serve skills from vault and installed skills"""
        try:
            skills = self._get_all_skills()
            self._json_response({"data": skills})
        except Exception as e:
            self._json_error(500, f"Failed to serve skills: {str(e)}")

    def _get_all_skills(self):
        """Shared helper: collect skill name/description list from vault + installed Hermes
        skills. Used by both /api/skills and the usage-mention logger below."""
        try:
            skills = []

            # Scan vault for skills
            skills_dir = VAULT_DIR / "90_Skills"
            if skills_dir.exists():
                for skill_dir in skills_dir.iterdir():
                    if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                        try:
                            with open(skill_dir / "SKILL.md", 'r', encoding='utf-8') as f:
                                content = f.read()
                                # Extract description from YAML frontmatter
                                name = skill_dir.name
                                description = ""
                                if content.startswith('---'):
                                    # Parse frontmatter
                                    parts = content.split('---', 2)
                                    if len(parts) >= 3:
                                        for fm_line in parts[1].split('\n'):
                                            fm_line = fm_line.strip()
                                            if fm_line.lower().startswith('description'):
                                                # Handle description: "value" or description: > or description: | 
                                                val = fm_line.split(':', 1)[1].strip().strip('"').strip("'")
                                                if val in ('>', '|', ''):
                                                    # Multi-line value — skip, get next non-empty line
                                                    continue
                                                description = val
                                                break
                                if not description:
                                    # Fallback: first meaningful line after frontmatter
                                    after_fm = content.split('---', 2)[2] if content.count('---') >= 2 else content
                                    for line in after_fm.split('\n'):
                                        line = line.strip()
                                        if line and not line.startswith('#') and not line.startswith('-') and not line.startswith('>'):
                                            description = line[:120]
                                            break
                            
                            skills.append({
                                "name": name,
                                "description": description,
                                "path": str(skill_dir.relative_to(VAULT_DIR)),
                                "type": "vault"
                            })
                        except Exception as e:
                            print(f"Error reading skill {skill_dir.name}: {e}")
                            continue
            
            # Add installed Hermes skills
            hermes_skills_dir = Path("/root/.hermes/skills")
            if hermes_skills_dir.exists():
                for skill_dir in hermes_skills_dir.iterdir():
                    if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                        try:
                            with open(skill_dir / "SKILL.md", 'r', encoding='utf-8') as f:
                                content = f.read()
                                name = skill_dir.name
                                description = ""
                                lines = content.split('\n')
                                for line in lines:
                                    if line.startswith('description:'):
                                        description = line.split(':', 1)[1].strip()
                                        break
                                if not description:
                                    for line in lines:
                                        if line.strip() and not line.startswith('#') and not line.startswith('-'):
                                            description = line.strip()
                                            break
                            
                            skills.append({
                                "name": name,
                                "description": description,
                                "path": str(skill_dir.relative_to(Path("/root/.hermes/skills"))),
                                "type": "installed"
                            })
                        except Exception as e:
                            print(f"Error reading installed skill {skill_dir.name}: {e}")
                            continue

            return skills
        except Exception as e:
            print(f"Failed to collect skills: {e}")
            return []

    def _serve_skill_stats(self):
        """GET /api/skills/stats — usage health-check: counts + most-used ranking.

        IMPORTANT LIMITATION: Hermes executes skills internally and does not report which
        skill it used back to this dashboard, so this cannot be a precise invocation counter.
        Instead it counts how often each known skill NAME is mentioned in Hermes's chat
        replies (logged in _log_skill_mentions, hooked into chat session saves). Real signal,
        honestly labelled as "mentioned in chat" in the UI — not claimed as exact call counts.
        """
        log_path = VAULT_DIR / ".skill_usage.json"
        log = []
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    log = json.load(f)
            except Exception:
                log = []
        counts = {}
        last_used = {}
        for entry in log:
            name = entry.get('skill')
            if not name:
                continue
            counts[name] = counts.get(name, 0) + 1
            if name not in last_used or entry.get('time', '') > last_used[name]:
                last_used[name] = entry.get('time')
        ranking = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        self._json_response({
            "data": {
                "counts": counts,
                "ranking": [{"skill": k, "count": v, "last_used": last_used.get(k)} for k, v in ranking],
                "total_events": len(log),
                "tracking_started": log[0]['time'] if log else None
            }
        })

    def _log_skill_mentions(self, new_messages):
        """Scan newly-added assistant messages for mentions of known skill names and log them
        to .skill_usage.json. See _serve_skill_stats docstring for the honesty caveat."""
        try:
            skill_names = [s['name'] for s in self._get_all_skills() if s.get('name')]
            if not skill_names:
                return
            log_path = VAULT_DIR / ".skill_usage.json"
            log = []
            if log_path.exists():
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        log = json.load(f)
                except Exception:
                    log = []
            now = datetime.datetime.now().isoformat()
            changed = False
            for m in new_messages:
                if m.get('role') != 'assistant':
                    continue
                content_lower = (m.get('content') or '').lower()
                for name in skill_names:
                    if name.lower() in content_lower:
                        log.append({"skill": name, "time": now})
                        changed = True
            if changed:
                with open(log_path, 'w', encoding='utf-8') as f:
                    json.dump(log[-2000:], f, indent=2)
        except Exception as e:
            print(f"Skill usage logging failed: {e}")

    def _handle_chat_proxy(self):
        """Proxy chat requests to Hermes API Server (OpenAI-compatible)"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._json_error(400, "No data provided")
            return
        
        try:
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            # Transform to OpenAI format if needed
            messages = data.get('messages', [])
            model = data.get('model', 'owl-alpha')
            
            # Build OpenAI-compatible request
            openai_request = {
                'model': model,
                'messages': messages,
                'stream': False,
                'temperature': data.get('temperature', 0.7),
                'max_tokens': data.get('max_tokens', 4000)
            }
            
            # Forward to Hermes API Server
            import urllib.request
            req = urllib.request.Request(
                f"{HERMES_CHAT_PROXY_URL}/v1/chat/completions",
                data=json.dumps(openai_request).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer life-os-dashboard-2026',
                },
                method='POST'
            )
            
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    response_data = response.read()
                    self.send_response(response.status)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(response_data)
            except urllib.error.URLError as e:
                self._json_error(502, f"Failed to connect to Hermes API Server: {str(e)}")
            except Exception as e:
                self._json_error(500, f"Error proxying to Hermes: {str(e)}")
                
        except json.JSONDecodeError:
            self._json_error(400, "Invalid JSON")
        except Exception as e:
            self._json_error(500, f"Failed to handle chat request: {str(e)}")
    
    def _handle_file_upload(self):
        """Handle file uploads to 10_Sources/uploads/"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._json_error(400, "No data provided")
            return
        
        try:
            # Parse multipart/form-data (simplified)
            # In a real implementation, you'd use a proper multipart parser
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self._json_error(400, "Expected multipart/form-data")
                return
            
            # For simplicity, we'll assume the body is JSON with base64 encoded file
            # A proper implementation would parse the multipart data
            try:
                data = json.loads(self.rfile.read(content_length).decode('utf-8'))
                file_name = data.get('name', 'uploaded_file')
                file_data = data.get('data', '')  # base64 encoded
                file_type = data.get('type', 'unknown')
                
                if not file_data:
                    self._json_error(400, "No file data provided")
                    return
                
                # Decode base64
                import base64
                try:
                    file_bytes = base64.b64decode(file_data)
                except Exception:
                    self._json_error(400, "Invalid base64 data")
                    return
                
                # Determine upload directory based on file type
                upload_dir = VAULT_DIR / "10_Sources" / "uploads" / file_type
                upload_dir.mkdir(parents=True, exist_ok=True)
                
                # Create filename with timestamp to avoid conflicts
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_filename = "".join(c for c in file_name if c.isalnum() or c in '._- ').rstrip()
                if not safe_filename:
                    safe_filename = "upload"
                filepath = upload_dir / f"{timestamp}_{safe_filename}"
                
                # Write file
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)
                
                self._json_response({
                    "success": True,
                    "filename": filepath.name,
                    "path": str(filepath.relative_to(VAULT_DIR)),
                    "size": len(file_bytes)
                })
            except json.JSONDecodeError:
                self._json_error(400, "Invalid JSON in request body")
                
        except Exception as e:
            self._json_error(500, f"Failed to handle file upload: {str(e)}")
    
    def _handle_browser_run(self):
        """Handle browser automation requests via Playwright"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._json_error(400, "No data provided")
            return
        
        try:
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            self._json_error(400, "Invalid JSON")
            return
        except Exception as e:
            self._json_error(400, f"Failed to read request: {str(e)}")
            return

        # Validate request
        if not isinstance(data, dict):
            self._json_error(400, "Request must be a JSON object")
            return

        action = data.get('action')
        workflow = data.get('workflow')

        if not action and not workflow:
            self._json_error(400, "Missing 'action' or 'workflow' field")
            return

        # Import and run the browser automation
        try:
            # Import the FB-BROWSER skill module
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '90_Skills', 'fb-browser'))

            if workflow:
                from fb_browser import run_browser_workflow
                # Run the workflow
                result = asyncio.run(run_browser_workflow(workflow))
                self._json_response({"workflow": True, "results": result})
            else:
                from fb_browser import run_browser_action
                # Run the action
                result = asyncio.run(run_browser_action(data))
                self._json_response(result)

        except ImportError as e:
            # Fallback to simulation if Playwright not available
            self._json_response({
                "success": False,
                "error": "Playwright not installed. Install with: pip install playwright && playwright install chromium",
                "action": data.get('action'),
                "simulation": True
            })
        except Exception as e:
            self._json_error(500, f"Browser automation failed: {str(e)}")
    
    def _handle_clip_endpoint(self):
        """Handle web clipper endpoint"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._json_error(400, "No data provided")
            return
        
        try:
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            self._json_error(400, "Invalid JSON")
            return
        except Exception as e:
            self._json_error(400, f"Failed to read request: {str(e)}")
            return
        
        # Validate required fields
        required_fields = ['title', 'content']
        for field in required_fields:
            if field not in data:
                self._json_error(400, f"Missing required field: {field}")
                return
        
        try:
            # Create clip file in Clippings directory
            clips_dir = DATA_DIR / "clippings"
            clips_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename from title
            import re
            from datetime import datetime
            
            # Clean title for filename
            safe_title = re.sub(r'[^\w\s-]', '', data['title']).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            if not safe_title:
                safe_title = "clip"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{safe_title}.md"
            filepath = clips_dir / filename
            
            # Create frontmatter — OKF-conformant (type is the one required
            # field) while keeping the existing source_url/clipped_at names
            # so nothing that already reads clips breaks.
            frontmatter = f"""---
type: Clipping
title: "{data['title']}"
description: "{data.get('description', '') or 'Web clip — not yet ingested into the wiki.'}"
domain: general
resource: "{data.get('source_url', '')}"
source_url: "{data.get('source_url', '')}"
timestamp: "{datetime.now().isoformat()}"
clipped_at: "{datetime.now().isoformat()}"
tags: {data.get('tags', [])}
---

"""
            
            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(frontmatter + data['content'])
            
            # Auto-commit to git if possible
            try:
                import subprocess
                result = subprocess.run(['git', 'add', str(filepath.relative_to(VAULT_DIR))], 
                                      cwd=VAULT_DIR, capture_output=True, text=True)
                if result.returncode == 0:
                    subprocess.run(['git', 'commit', '-m', f'Add clip: {data["title"]}'], 
                                 cwd=VAULT_DIR, capture_output=True, text=True)
            except Exception as e:
                print(f"Warning: Failed to auto-commit clip to git: {e}")
            
            self._json_response({
                "success": True,
                "filename": filename,
                "path": str(filepath.relative_to(VAULT_DIR)),
                "size": len(data['content'])
            })
        except Exception as e:
            self._json_error(500, f"Failed to create clip: {str(e)}")

    def _serve_auth_pool(self):
        """Serve credential pool summary from auth.json"""
        try:
            auth_path = Path.home() / ".hermes" / "auth.json"
            providers = []
            total = 0
            if auth_path.exists():
                try:
                    auth_data = json.loads(auth_path.read_text(encoding='utf-8'))
                    for pid, pdata in auth_data.get("providers", {}).items():
                        keys = pdata if isinstance(pdata, list) else [pdata] if pdata else []
                        active = 0
                        for k in keys:
                            if isinstance(k, dict):
                                total += 1
                                if k.get("active", True):
                                    active += 1
                            elif isinstance(k, str) and k:
                                total += 1
                                active += 1
                        providers.append({"name": pid, "active": active, "total": total if total else len(keys)})
                except Exception:
                    pass
            self._json_response({"providers": providers, "total_keys": total})
        except Exception as e:
            self._json_error(500, f"Failed to serve auth pool: {str(e)}")

    def _serve_providers(self):
        """Serve API provider list from .env/auth.json"""
        try:
            env_path = Path.home() / ".hermes" / ".env"
            env_vars = {}
            if env_path.exists():
                for line in env_path.read_text(encoding='utf-8').splitlines():
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, _, val = line.partition('=')
                        env_vars[key.strip()] = val.strip().strip('\'"')

            auth_path = Path.home() / ".hermes" / "auth.json"
            auth_data = {"providers": {}}
            if auth_path.exists():
                try:
                    auth_data = json.loads(auth_path.read_text(encoding='utf-8'))
                except Exception:
                    pass

            known = [
                {"id": "openrouter", "name": "OpenRouter", "envVar": "OPENROUTER_API_KEY", "url": "https://openrouter.ai", "icon": "🌐"},
                {"id": "openai", "name": "OpenAI", "envVar": "OPENAI_API_KEY", "url": "https://platform.openai.com", "icon": "🤖"},
                {"id": "anthropic", "name": "Anthropic", "envVar": "ANTHROPIC_API_KEY", "url": "https://console.anthropic.com", "icon": "🧩"},
                {"id": "deepseek", "name": "DeepSeek", "envVar": "DEEPSEEK_API_KEY", "url": "https://platform.deepseek.com", "icon": "🐋"},
                {"id": "google", "name": "Google AI", "envVar": "GOOGLE_API_KEY", "url": "https://ai.google.dev", "icon": "🔍"},
                {"id": "github", "name": "GitHub", "envVar": "GITHUB_TOKEN", "url": "https://github.com/settings/tokens", "icon": "🐙"},
                {"id": "together", "name": "Together AI", "envVar": "TOGETHER_API_KEY", "url": "https://api.together.xyz", "icon": "⚡"},
                {"id": "groq", "name": "Groq", "envVar": "GROQ_API_KEY", "url": "https://console.groq.com", "icon": "🚀"},
                {"id": "mistral", "name": "Mistral", "envVar": "MISTRAL_API_KEY", "url": "https://console.mistral.ai", "icon": "🌬️"},
                {"id": "perplexity", "name": "Perplexity", "envVar": "PERPLEXITY_API_KEY", "url": "https://perplexity.ai", "icon": "❓"},
                {"id": "cohere", "name": "Cohere", "envVar": "COHERE_API_KEY", "url": "https://cohere.com", "icon": "🔗"},
                {"id": "fireflies", "name": "Fireflies.ai", "envVar": "FIREFLIES_API_KEY", "url": "https://app.fireflies.ai/settings", "icon": "🎙️"},
                {"id": "notion", "name": "Notion (CRM)", "envVar": "NOTION_API_KEY", "url": "https://www.notion.so/my-integrations", "icon": "🗂️"},
                {"id": "gmail", "name": "Gmail (App Password)", "envVar": "GMAIL_API_KEY", "url": "https://myaccount.google.com/apppasswords", "icon": "📧"},
            ]

            providers = []
            for p in known:
                val = env_vars.get(p["envVar"], "")
                has = bool(val)
                preview = ""
                if has:
                    preview = val[-4:] if len(val) >= 4 else val
                providers.append({
                    **p,
                    "hasKey": has,
                    "source": "env",
                    "keyPreview": preview
                })

            # Add any providers in auth.json not already listed
            for pid, pdata in auth_data.get("providers", {}).items():
                if not any(p["id"] == pid for p in providers):
                    keys = pdata if isinstance(pdata, list) else [pdata] if pdata else []
                    active_keys = [k for k in keys if isinstance(k, dict) and k.get("active", True)]
                    preview = ""
                    if active_keys:
                        first = active_keys[0].get("key", "")
                        preview = first[-4:] if len(first) >= 4 else first
                    providers.append({
                        "id": pid,
                        "name": pid.replace('_', ' ').title(),
                        "envVar": f"{pid.upper()}_API_KEY",
                        "url": "",
                        "icon": "🔌",
                        "hasKey": bool(active_keys),
                        "source": "pool",
                        "keyPreview": preview
                    })

            self._json_response({"data": providers})
        except Exception as e:
            self._json_error(500, f"Failed to serve providers: {str(e)}")

    def _handle_auth_endpoint(self):
        """Add/test/remove API keys"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._json_error(400, "No data provided")
                return
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            action = data.get('action')
            provider = data.get('provider', '').lower().replace(' ', '')

            if action == 'add':
                key = data.get('key', '').strip()
                if not provider or not key:
                    self._json_response({"ok": False, "message": "Provider and key required"})
                    return
                env_path = Path.home() / ".hermes" / ".env"
                env_path.parent.mkdir(parents=True, exist_ok=True)
                lines = []
                if env_path.exists():
                    lines = env_path.read_text(encoding='utf-8').splitlines()
                var_name = f"{provider.upper().replace('.', '_')}_API_KEY"
                updated = False
                for i, line in enumerate(lines):
                    if line.strip().startswith(var_name + '='):
                        lines[i] = f'{var_name}={key}'
                        updated = True
                        break
                if not updated:
                    lines.append(f'{var_name}={key}')
                env_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                self._json_response({"ok": True, "message": f"Key saved for {provider}. Restart Hermes gateway to activate."})
                return

            if action == 'remove':
                env_path = Path.home() / ".hermes" / ".env"
                if env_path.exists():
                    lines = env_path.read_text(encoding='utf-8').splitlines()
                    var_name = f"{provider.upper().replace('.', '_')}_API_KEY"
                    lines = [line for line in lines if not line.strip().startswith(var_name + '=')]
                    env_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                self._json_response({"ok": True, "message": f"Key removed for {provider}"})
                return

            if action == 'test':
                # Read current key
                env_path = Path.home() / ".hermes" / ".env"
                key = ""
                var_name = f"{provider.upper().replace('.', '_')}_API_KEY"
                if env_path.exists():
                    for line in env_path.read_text(encoding='utf-8').splitlines():
                        if line.strip().startswith(var_name + '='):
                            key = line.split('=', 1)[1].strip().strip('\'"')
                            break
                if not key:
                    self._json_response({"ok": False, "message": "No key found"})
                    return
                try:
                    import urllib.request
                    if provider == 'openrouter':
                        req = urllib.request.Request(
                            'https://openrouter.ai/api/v1/models',
                            headers={'Authorization': f'Bearer {key}'}
                        )
                        with urllib.request.urlopen(req, timeout=10) as r:
                            self._json_response({"ok": True, "message": f"Connected ({len(json.loads(r.read()))} models)"})
                    elif provider == 'deepseek':
                        req = urllib.request.Request(
                            'https://api.deepseek.com/models',
                            headers={'Authorization': f'Bearer {key}'}
                        )
                        with urllib.request.urlopen(req, timeout=10) as r:
                            self._json_response({"ok": True, "message": "Connected"})
                    elif provider == 'github':
                        req = urllib.request.Request(
                            'https://api.github.com/user',
                            headers={'Authorization': f'token {key}', 'User-Agent': 'LifeOS'}
                        )
                        with urllib.request.urlopen(req, timeout=10) as r:
                            self._json_response({"ok": True, "message": "Connected"})
                    elif provider == 'fireflies':
                        gql = json.dumps({"query": "query { user { name } }"}).encode('utf-8')
                        req = urllib.request.Request(
                            'https://api.fireflies.ai/graphql',
                            data=gql,
                            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                            method='POST'
                        )
                        with urllib.request.urlopen(req, timeout=10) as r:
                            resp = json.loads(r.read())
                            if resp.get('errors'):
                                self._json_response({"ok": False, "message": resp['errors'][0].get('message', 'GraphQL error')})
                            else:
                                name = (resp.get('data') or {}).get('user', {}).get('name', 'account')
                                self._json_response({"ok": True, "message": f"Connected ({name})"})
                    elif provider == 'notion':
                        req = urllib.request.Request(
                            'https://api.notion.com/v1/users/me',
                            headers={'Authorization': f'Bearer {key}', 'Notion-Version': '2022-06-28'}
                        )
                        with urllib.request.urlopen(req, timeout=10) as r:
                            info = json.loads(r.read())
                            self._json_response({"ok": True, "message": f"Connected ({info.get('name', 'integration')})"})
                    elif provider == 'gmail':
                        import imaplib
                        gmail_addr = os.environ.get('GMAIL_ADDRESS') or self._get_env_var('GMAIL_ADDRESS') or 'fadi@fieldbridgehq.com'
                        try:
                            imap = imaplib.IMAP4_SSL('imap.gmail.com', timeout=10)
                            imap.login(gmail_addr, key)
                            imap.logout()
                            self._json_response({"ok": True, "message": f"Connected ({gmail_addr})"})
                        except imaplib.IMAP4.error as e:
                            self._json_response({"ok": False, "message": f"IMAP login failed: {str(e)}"})
                    else:
                        self._json_response({"ok": True, "message": "Key present (test not implemented for this provider)"})
                except Exception as e:
                    self._json_response({"ok": False, "message": f"Connection failed: {str(e)}"})
                return

            self._json_error(400, "Unknown action")
        except Exception as e:
            self._json_error(500, f"Auth endpoint error: {str(e)}")

    def _serve_clippings(self, query=None):
        """Serve unprocessed clips from Clippings/ folder"""
        try:
            clips_dir = DATA_DIR / "clippings"
            clips = []
            if clips_dir.exists() and clips_dir.is_dir():
                for item in sorted(clips_dir.iterdir()):
                    if not item.is_file() or item.name.startswith('.'):
                        continue
                    if item.name.lower() == 'processed':
                        continue
                    stat = item.stat()
                    title = item.stem
                    source = ""
                    try:
                        content = item.read_text(encoding='utf-8', errors='ignore')
                        # Extract title from first markdown heading
                        for line in content.splitlines()[:10]:
                            if line.startswith('# '):
                                title = line[2:].strip()
                                break
                        # Extract source_url from frontmatter
                        for line in content.splitlines()[:20]:
                            if line.lower().startswith('source_url:') or line.lower().startswith('source:'):
                                source = line.split(':', 1)[1].strip()
                                break
                    except Exception:
                        pass
                    clips.append({
                        "name": item.name,
                        "path": str(item.relative_to(VAULT_DIR)),
                        "title": title,
                        "source": source,
                        "size": stat.st_size,
                        "created": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "modified": stat.st_mtime
                    })
            self._json_response(clips)
        except Exception as e:
            self._json_error(500, f"Failed to serve clippings: {str(e)}")

    def _serve_cron(self, query=None):
        """Serve cron jobs from the Hermes scheduler"""
        try:
            # Read from the Hermes cron storage
            cron_jobs = []
            # Check if hermes cron output directory exists
            cron_dir = Path.home() / ".hermes" / "cron" / "output"
            if cron_dir.exists():
                for job_dir in sorted(cron_dir.iterdir()):
                    if not job_dir.is_dir():
                        continue
                    # Read job config if available
                    config_file = job_dir / "config.json"
                    job_info = {
                        "id": job_dir.name,
                        "name": job_dir.name,
                        "status": "active",
                        "last_run": None,
                        "output_count": 0
                    }
                    if config_file.exists():
                        try:
                            with open(config_file) as f:
                                cfg = json.load(f)
                            job_info["name"] = cfg.get("name", job_dir.name)
                            job_info["schedule"] = cfg.get("schedule", "unknown")
                            job_info["status"] = cfg.get("status", "active")
                        except Exception:
                            pass
                    # Count output files
                    output_files = list(job_dir.glob("*.json"))
                    job_info["output_count"] = len(output_files)
                    if output_files:
                        latest = max(output_files, key=lambda f: f.stat().st_mtime)
                        job_info["last_run"] = datetime.datetime.fromtimestamp(latest.stat().st_mtime).isoformat()
                    cron_jobs.append(job_info)
            
            # Also check the in-memory cron list from the cronjob tool
            self._json_response({"data": cron_jobs})
        except Exception as e:
            self._json_error(500, f"Failed to serve cron jobs: {str(e)}")

    def _handle_process_clip(self):
        """Move a clip to 10_Sources/processed/clippings/"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._json_error(400, "No data provided")
                return
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            filename = data.get('filename', '')
            if not filename:
                self._json_response({"ok": False, "error": "filename required"})
                return
            src = DATA_DIR / "clippings" / filename
            processed_dir = DATA_DIR / "clippings" / "processed"
            processed_dir.mkdir(parents=True, exist_ok=True)
            dst = processed_dir / filename
            # Avoid overwrite by appending timestamp if exists
            if dst.exists():
                dst = processed_dir / f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-{filename}"
            src.rename(dst)
            self._json_response({"ok": True, "path": str(dst.relative_to(VAULT_DIR))})
        except Exception as e:
            self._json_error(500, f"Failed to process clip: {str(e)}")

    def _handle_task_save(self):
        """Save a kanban card (create or update)"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._json_error(400, "No data provided")
                return
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            task_id = data.get('id', '')
            if not task_id:
                self._json_error(400, "Task ID required")
                return
            
            # Delete flag
            if data.get('_delete'):
                # Remove from kanban store
                store_path = DATA_DIR / ".kanban_store.json"
                if store_path.exists():
                    with open(store_path, 'r') as f:
                        store = json.load(f)
                    store = [t for t in store if t.get('id') != task_id]
                    with open(store_path, 'w') as f:
                        json.dump(store, f, indent=2)
                self._json_response({"ok": True, "deleted": True})
                return
            
            # Upsert task to store
            store_path = DATA_DIR / ".kanban_store.json"
            store = []
            if store_path.exists():
                with open(store_path, 'r') as f:
                    store = json.load(f)
            
            # Remove existing task with same id
            store = [t for t in store if t.get('id') != task_id]
            # Add updated task
            store.append(data)
            
            with open(store_path, 'w') as f:
                json.dump(store, f, indent=2)
            
            self._json_response({"ok": True, "id": task_id})
        except Exception as e:
            self._json_error(500, f"Failed to save task: {str(e)}")

    # ═══════════════════════════════════════════════════════════
    # CHAT SESSION PERSISTENCE (added 2026-07-01 — real multi-session
    # chat memory, replaces the hardcoded fake sidebar in chat.html)
    # ═══════════════════════════════════════════════════════════

    def _serve_chat_sessions(self):
        """GET /api/chat/sessions — list all chat sessions (index only, no full message bodies)"""
        index_path = VAULT_DIR / ".chat_sessions_index.json"
        sessions = []
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    sessions = json.load(f)
            except Exception:
                sessions = []
        sessions.sort(key=lambda s: s.get('updated', ''), reverse=True)
        self._json_response({"data": sessions})

    def _serve_chat_session(self, query):
        """GET /api/chat/session?id=X — full session including messages"""
        session_id = (query.get('id') or [''])[0]
        if not session_id:
            self._json_error(400, "Session id required")
            return
        session_path = DATA_DIR / ".chat_sessions" / f"{session_id}.json"
        if not session_path.exists():
            self._json_error(404, "Session not found")
            return
        try:
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            self._json_response({"data": session})
        except Exception as e:
            self._json_error(500, f"Failed to load session: {str(e)}")

    def _handle_chat_session_save(self):
        """POST /api/chat/session — create or upsert a full session {id, title, coach, messages}"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._json_error(400, "No data provided")
            return
        try:
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            session_id = data.get('id') or ('sess_' + datetime.datetime.now().strftime('%Y%m%d%H%M%S%f'))
            data['id'] = session_id
            data['updated'] = datetime.datetime.now().isoformat()
            if 'created' not in data:
                data['created'] = data['updated']

            sessions_dir = DATA_DIR / ".chat_sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            session_path = sessions_dir / f"{session_id}.json"

            # Only scan messages added since the last save, so re-saving the same
            # conversation repeatedly doesn't re-count old messages as new skill mentions.
            previous_count = 0
            if session_path.exists():
                try:
                    with open(session_path, 'r', encoding='utf-8') as f:
                        previous_count = len(json.load(f).get('messages', []))
                except Exception:
                    previous_count = 0
            new_messages = data.get('messages', [])[previous_count:]

            with open(session_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            if new_messages:
                self._log_skill_mentions(new_messages)

            # Update lightweight index used by the sidebar
            index_path = VAULT_DIR / ".chat_sessions_index.json"
            index = []
            if index_path.exists():
                try:
                    with open(index_path, 'r', encoding='utf-8') as f:
                        index = json.load(f)
                except Exception:
                    index = []
            index = [s for s in index if s.get('id') != session_id]
            messages = data.get('messages', [])
            last_user_msg = next((m.get('content', '') for m in reversed(messages) if m.get('role') == 'user'), '')
            preview = (last_user_msg or '')[:80]
            title = data.get('title') or (messages[0].get('content', 'New Chat')[:40] if messages else 'New Chat')
            index.append({
                "id": session_id,
                "title": title,
                "coach": data.get('coach', 'lifeos'),
                "updated": data['updated'],
                "preview": preview,
                "message_count": len(messages)
            })
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)

            self._json_response({"ok": True, "id": session_id, "title": title})
        except Exception as e:
            self._json_error(500, f"Failed to save session: {str(e)}")

    def _handle_chat_session_delete(self):
        """POST /api/chat/session/delete — delete a session by id"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._json_error(400, "No data provided")
            return
        try:
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            session_id = data.get('id', '')
            if not session_id:
                self._json_error(400, "Session id required")
                return

            session_path = DATA_DIR / ".chat_sessions" / f"{session_id}.json"
            if session_path.exists():
                session_path.unlink()

            index_path = VAULT_DIR / ".chat_sessions_index.json"
            if index_path.exists():
                with open(index_path, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                index = [s for s in index if s.get('id') != session_id]
                with open(index_path, 'w', encoding='utf-8') as f:
                    json.dump(index, f, indent=2)

            self._json_response({"ok": True, "deleted": session_id})
        except Exception as e:
            self._json_error(500, f"Failed to delete session: {str(e)}")

    # ═══════════════════════════════════════════════════════════
    # KNOWLEDGE-BASE-AWARE CHAT (added 2026-07-01 — powers the
    # previously-nonfunctional "KB" toggle in chat.html with a real
    # keyword search across the vault)
    # ═══════════════════════════════════════════════════════════

    def _serve_kb_search(self, query):
        """GET /api/kb/search?q=... — brain.py ladder steps 1-2 only (BUILD
        SPEC v1 Part A): score the index/CRM/30_Context candidate lines and
        return the top paths + their index-line snippets. Never opens a
        wiki page body — chat context injection stops reading file bodies
        here; replaces the old full-vault rglob."""
        q = (query.get('q') or [''])[0].strip()
        if not q:
            self._json_response({"data": []})
            return
        try:
            result = brain.score_index(q, VAULT_DIR, data_dir=DATA_DIR, top_n=5)
            results = [{
                "file": r["path"],
                "score": r["score"],
                "snippet": r["insight"],
            } for r in result["results"] if r["score"] > 0]
            self._json_response({"data": results})
        except Exception as e:
            self._json_error(500, f"KB search failed: {str(e)}")

    # ═══════════════════════════════════════════════════════════
    # MEETING ASSISTANT API
    # ═══════════════════════════════════════════════════════════

    def _serve_meetings_get(self, query):
        """GET /api/meetings — return current meeting state"""
        meeting_store = VAULT_DIR / ".meeting_store.json"
        if meeting_store.exists():
            with open(meeting_store, 'r') as f:
                data = json.load(f)
            self._json_response(data)
        else:
            self._json_response({"meeting": None, "agenda": [], "transcript": None, "summary": None, "actionItems": [], "coverage": []})

    def _handle_meetings_post(self):
        """POST /api/meetings — handle meeting actions"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            # Check if it's multipart (file upload)
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' in content_type:
                self._handle_meeting_file_upload()
                return
            self._json_error(400, "Invalid JSON")
            return
        
        action = data.get('action', '')
        
        if action == 'upload':
            self._handle_meeting_upload(data)
        elif action == 'confirm':
            self._handle_meeting_confirm(data)
        elif action == 'start_recording':
            self._handle_start_recording(data)
        elif action == 'stop_recording':
            self._handle_stop_recording(data)
        elif action == 'regenerate':
            self._handle_regenerate_brief(data)
        else:
            self._json_error(400, f"Unknown action: {action}")

    def _handle_meeting_upload(self, data):
        """Process uploaded document and extract agenda"""
        # Support file upload (base64), doc_link, or description
        meeting = {
            "id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "title": data.get('title', 'Untitled Meeting'),
            "date": data.get('date', datetime.datetime.now().strftime("%Y-%m-%d")),
            "attendees": data.get('attendees', []),
            "created_at": datetime.datetime.now().isoformat()
        }
        
        agenda = []
        questions = []
        
        # If description provided, extract agenda from it
        description = data.get('description', '')
        if description:
            lines = description.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 3:
                    agenda.append({
                        "title": line,
                        "question": "",
                        "status": "pending"
                    })
        
        # If agenda items provided directly
        if data.get('agenda'):
            agenda = data['agenda']
        
        # If questions provided
        if data.get('questions'):
            questions = data['questions']
        
        # If doc_link provided, try to fetch content
        doc_link = data.get('doc_link', '')
        if doc_link:
            meeting['doc_link'] = doc_link
            try:
                import urllib.request
                req = urllib.request.Request(doc_link, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    content = resp.read().decode('utf-8', errors='ignore')
                    # Basic extraction — strip HTML tags
                    import re
                    text = re.sub(r'<[^>]+>', ' ', content)
                    text = re.sub(r'\s+', ' ', text).strip()
                    # Try to extract agenda lines
                    for line in text.split('\n'):
                        line = line.strip()
                        if line and len(line) > 10 and len(line) < 200:
                            agenda.append({
                                "title": line,
                                "question": "",
                                "status": "pending"
                            })
            except Exception:
                pass
        
        # Save to store
        meeting_store = VAULT_DIR / ".meeting_store.json"
        meeting_data = {
            "meeting": meeting,
            "agenda": agenda,
            "questions": questions,
            "transcript": None,
            "summary": None,
            "actionItems": [],
            "coverage": [],
            "phase": "uploaded"
        }
        with open(meeting_store, 'w') as f:
            json.dump(meeting_data, f, indent=2, ensure_ascii=False)
        
        self._json_response({
            "success": True,
            "meeting": meeting,
            "agenda": agenda,
            "questions": questions
        })

    def _handle_meeting_confirm(self, data):
        """Confirm agenda and prepare for meeting"""
        meeting_store = VAULT_DIR / ".meeting_store.json"
        if meeting_store.exists():
            with open(meeting_store, 'r') as f:
                meeting_data = json.load(f)
            
            meeting_data['phase'] = 'confirmed'
            if data.get('agenda'):
                meeting_data['agenda'] = data['agenda']
            if data.get('meeting'):
                meeting_data['meeting'] = data['meeting']
            
            with open(meeting_store, 'w') as f:
                json.dump(meeting_data, f, indent=2, ensure_ascii=False)
            
            self._json_response({"success": True, "phase": "confirmed"})
        else:
            self._json_error(404, "No meeting to confirm")

    def _handle_start_recording(self, data):
        """Mark recording as started"""
        meeting_store = VAULT_DIR / ".meeting_store.json"
        if meeting_store.exists():
            with open(meeting_store, 'r') as f:
                meeting_data = json.load(f)
            
            meeting_data['phase'] = 'recording'
            meeting_data['recording_started'] = datetime.datetime.now().isoformat()
            
            with open(meeting_store, 'w') as f:
                json.dump(meeting_data, f, indent=2, ensure_ascii=False)
            
            self._json_response({"success": True, "phase": "recording"})
        else:
            self._json_error(404, "No meeting loaded")

    def _handle_stop_recording(self, data):
        """Process stop recording — transcribe and generate outputs"""
        meeting_store = VAULT_DIR / ".meeting_store.json"
        if meeting_store.exists():
            with open(meeting_store, 'r') as f:
                meeting_data = json.load(f)
            
            meeting_data['phase'] = 'complete'
            meeting_data['recording_ended'] = datetime.datetime.now().isoformat()
            
            # Generate sample outputs (in production, these come from Whisper API + Hermes)
            # For now, mark as ready for frontend display
            meeting_data['transcript'] = []
            meeting_data['summary'] = {}
            meeting_data['actionItems'] = []
            meeting_data['coverage'] = []
            
            with open(meeting_store, 'w') as f:
                json.dump(meeting_data, f, indent=2, ensure_ascii=False)
            
            self._json_response({"success": True, "phase": "complete"})
        else:
            self._json_error(404, "No meeting loaded")

    def _handle_regenerate_brief(self, data):
        """Regenerate the meeting brief from the document"""
        meeting_store = VAULT_DIR / ".meeting_store.json"
        if meeting_store.exists():
            with open(meeting_store, 'r') as f:
                meeting_data = json.load(f)
            
            # Keep same meeting but regenerate agenda
            self._json_response({
                "success": True,
                "meeting": meeting_data.get('meeting'),
                "agenda": meeting_data.get('agenda', []),
                "questions": meeting_data.get('questions', [])
            })
        else:
            self._json_error(404, "No meeting loaded")

    def _handle_meeting_process(self):
        """Process uploaded audio file: transcribe → summarize → coverage check"""
        import urllib.request
        
        content_type = self.headers.get('Content-Type', '')
        
        if 'multipart/form-data' not in content_type:
            self._json_error(400, "Expected multipart/form-data")
            return
        
        # Parse multipart manually
        boundary = content_type.split('boundary=')[-1].strip()
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        # Extract audio file from multipart
        audio_data = None
        audio_filename = "audio.wav"
        
        parts = body.split(b'--' + boundary.encode())
        for part in parts:
            if b'Content-Disposition' in part:
                # Extract filename
                if b'filename="' in part:
                    start = part.index(b'filename="') + 10
                    end = part.index(b'"', start)
                    audio_filename = part[start:end].decode()
                
                # Extract file data (after double CRLF)
                header_end = part.find(b'\r\n\r\n')
                if header_end >= 0:
                    file_data = part[header_end + 4:]
                    # Remove trailing CRLF
                    if file_data.endswith(b'\r\n'):
                        file_data = file_data[:-2]
                    if len(file_data) > 0:
                        audio_data = file_data
        
        if not audio_data:
            self._json_error(400, "No audio file found in upload")
            return
        
        # Save audio to temp file
        tmp_path = VAULT_DIR / "temp_uploads" / audio_filename
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, 'wb') as f:
            f.write(audio_data)
        
        # Step 1: Transcribe with faster-whisper (local, free, multi-language)
        transcript = self._transcribe_audio(tmp_path)
        
        if not transcript:
            # If whisper returned empty (model not loaded or empty audio), create a placeholder
            transcript = [{"time": "00:00", "speaker": "", "text": "(No speech detected in audio)"}]
        
        # Step 2: Load meeting context
        meeting_store = VAULT_DIR / ".meeting_store.json"
        if meeting_store.exists():
            with open(meeting_store, 'r') as f:
                meeting_data = json.load(f)
            agenda = meeting_data.get('agenda', [])
        else:
            agenda = []
        
        # Step 3: Generate summary via Hermes/OpenRouter
        summary = self._generate_summary(transcript, agenda)
        
        # Step 4: Extract action items
        action_items = self._extract_action_items(transcript, agenda)
        
        # Step 5: Coverage check
        coverage = self._check_coverage(transcript, agenda)
        
        # Step 6: Save everything to vault
        meeting_id = meeting_data.get('meeting', {}).get('id', datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        meeting_dir = VAULT_DIR / "30_Meetings" / meeting_id
        meeting_dir.mkdir(parents=True, exist_ok=True)
        
        # Save transcript
        with open(meeting_dir / "transcript.md", 'w', encoding='utf-8') as f:
            f.write(f"# Legal Transcript\n\n")
            f.write(f"**Meeting:** {meeting_data.get('meeting', {}).get('title', 'Untitled')}\n")
            f.write(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write("---\n\n")
            for seg in transcript:
                time_str = seg.get('time', '')
                speaker = seg.get('speaker', '')
                text = seg.get('text', '')
                f.write(f"**{time_str}** {speaker}: {text}\n\n" if speaker else f"**{time_str}** {text}\n\n")
        
        # Save summary
        with open(meeting_dir / "summary.md", 'w', encoding='utf-8') as f:
            f.write(f"# Meeting Summary\n\n")
            if summary.get('decisions'):
                f.write("## Key Decisions\n\n")
                for d in summary['decisions']:
                    f.write(f"- {d}\n")
                f.write("\n")
            if summary.get('discussion'):
                f.write("## Discussion Points\n\n")
                for d in summary['discussion']:
                    f.write(f"- {d}\n")
                f.write("\n")
            if summary.get('conclusion'):
                f.write(f"## Conclusion\n\n{summary['conclusion']}\n\n")
            if summary.get('next_steps'):
                f.write("## Next Steps\n\n")
                for s in summary['next_steps']:
                    f.write(f"- {s}\n")
        
        # Save action items
        with open(meeting_dir / "action-items.md", 'w', encoding='utf-8') as f:
            f.write(f"# Action Items\n\n")
            f.write("| Task | Assignee | Due | Source |\n")
            f.write("|------|----------|-----|--------|\n")
            for item in action_items:
                f.write(f"| {item.get('task', '')} | {item.get('assignee', '—')} | {item.get('due', '—')} | {item.get('source', '—')} |\n")
        
        # Save coverage report
        with open(meeting_dir / "coverage.md", 'w', encoding='utf-8') as f:
            f.write(f"# Coverage Report\n\n")
            for item in coverage:
                icon = "✅" if item['status'] == 'covered' else "⚠️" if item['status'] == 'partial' else "❌"
                f.write(f"{icon} **{item['title']}** — {item['status'].upper()}\n")
                if item.get('snippet'):
                    f.write(f"   > {item['snippet']}\n")
                f.write("\n")
        
        # Update meeting store
        meeting_data['transcript'] = transcript
        meeting_data['summary'] = summary
        meeting_data['actionItems'] = action_items
        meeting_data['coverage'] = coverage
        meeting_data['phase'] = 'complete'
        meeting_data['vault_path'] = str(meeting_dir)
        with open(meeting_store, 'w') as f:
            json.dump(meeting_data, f, indent=2, ensure_ascii=False)
        
        # Clean up temp file
        try:
            tmp_path.unlink()
        except:
            pass
        
        self._json_response({
            "success": True,
            "transcript_segments": len(transcript),
            "action_items_count": len(action_items),
            "coverage_total": len(coverage),
            "coverage_covered": len([c for c in coverage if c['status'] == 'covered']),
            "vault_path": str(meeting_dir)
        })
    
    def _transcribe_audio(self, audio_path):
        """Transcribe audio using faster-whisper (local, multi-language)"""
        global _whisper_model, _whisper_loading
        try:
            # Wait for model to finish loading (max 120s)
            import time
            wait_start = time.time()
            while _whisper_loading and _whisper_model is None:
                if time.time() - wait_start > 120:
                    return []
                time.sleep(0.5)
            
            if _whisper_model is None:
                return []
            
            segments, info = _whisper_model.transcribe(
                str(audio_path),
                language=None,  # Auto-detect language
                task='transcribe',
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            result = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    # Detect if segment is Arabic for speaker labeling
                    import re
                    is_arabic = bool(re.search(r'[\u0600-\u06FF]', text))
                    result.append({
                        "time": f"{int(segment.start//60):02d}:{int(segment.start%60):02d}",
                        "speaker": "Speaker A" if not is_arabic else "Speaker A (AR)",
                        "text": text,
                        "lang": "ar" if is_arabic else "en"
                    })
            
            return result
        
        except Exception as e:
            print(f"Transcription error: {e}")
            return []

    def _handle_transcribe(self):
        """Handle voice transcription for quick capture - accepts audio file, returns transcript"""
        content_type = self.headers.get('Content-Type', '')
        
        if 'multipart/form-data' not in content_type:
            self._json_error(400, "Expected multipart/form-data")
            return
        
        # Parse multipart manually (same as meeting_process)
        boundary = content_type.split('boundary=')[-1].strip()
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        # Extract audio file from multipart
        audio_data = None
        audio_filename = "audio.wav"
        
        parts = body.split(b'--' + boundary.encode())
        for part in parts:
            if b'Content-Disposition' in part:
                if b'filename="' in part:
                    start = part.index(b'filename="') + 10
                    end = part.index(b'"', start)
                    audio_filename = part[start:end].decode()
                
                header_end = part.find(b'\r\n\r\n')
                if header_end >= 0:
                    file_data = part[header_end + 4:]
                    if file_data.endswith(b'\r\n'):
                        file_data = file_data[:-2]
                    if len(file_data) > 0:
                        audio_data = file_data
        
        if not audio_data:
            self._json_error(400, "No audio file found in upload")
            return
        
        # Save audio to temp file
        tmp_path = VAULT_DIR / "temp_uploads" / audio_filename
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, 'wb') as f:
            f.write(audio_data)
        
        # Transcribe
        transcript = self._transcribe_audio(tmp_path)
        
        if not transcript:
            transcript = [{"time": "00:00", "speaker": "", "text": "(No speech detected)", "lang": "en"}]
        
        # Return just the text for quick capture
        text = " ".join([seg.get("text", "") for seg in transcript])
        
        self._json_response({
            "success": True,
            "transcript": transcript,
            "text": text.strip(),
            "language": transcript[0].get("lang", "en") if transcript else "en"
        })
    
    def _generate_summary(self, transcript, agenda):
        """Generate summary by proxying to Hermes agent (which has all credentials)"""
        transcript_text = "\n".join([f"[{s.get('time', '')}] {s.get('text', '')}" for s in transcript])
        
        agenda_text = ""
        if agenda:
            agenda_text = "\n".join([f"- {item.get('title', '')}" for item in agenda])
        
        prompt = f"""You are a senior construction PM meeting assistant. Summarize this meeting transcript.

AGENDA:
{agenda_text}

TRANSCRIPT:
{transcript_text}

Provide a JSON response with:
1. "decisions" — list of key decisions made
2. "discussion" — list of main discussion points per agenda item
3. "conclusion" — one paragraph summary of where things stand
4. "next_steps" — list of next steps

Keep it concise. Output ONLY valid JSON, no markdown fences."""
        
        # Call Hermes via local API (which has all credentials)
        try:
            import urllib.request
            
            payload = json.dumps({
                "model": "google/gemma-2.5-flash-preview",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.3
            }).encode('utf-8')
            
            req = urllib.request.Request(
                f"{HERMES_CHAT_PROXY_URL}/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer life-os-dashboard-2026"
                }
            )
            
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            
            if 'choices' in data and data['choices']:
                content = data['choices'][0]['message']['content']
                try:
                    content = content.strip()
                    if content.startswith('```'):
                        content = content.split('\n', 1)[1] if '\n' in content else content[3:]
                        if content.endswith('```'):
                            content = content[:-3]
                    content = content.strip()
                    summary = json.loads(content)
                    return summary
                except json.JSONDecodeError:
                    return {"decisions": [], "discussion": [], "conclusion": content, "next_steps": []}
            
            return {"decisions": [], "discussion": [], "conclusion": "Failed to generate summary", "next_steps": []}
            
        except Exception as e:
            print(f"Summary generation error: {e}")
            return {"decisions": [], "discussion": [], "conclusion": f"Summary generation failed: {str(e)}", "next_steps": []}
    
    def _extract_action_items(self, transcript, agenda):
        """Extract action items from transcript via Hermes proxy"""
        transcript_text = "\n".join([f"[{s.get('time', '')}] {s.get('text', '')}" for s in transcript])
        
        prompt = f"""Extract action items from this meeting transcript.

TRANSCRIPT:
{transcript_text}

For each action item, provide:
- "task" — what needs to be done
- "assignee" — who is responsible (or "Unassigned")
- "due" — due date if mentioned (or "TBD")
- "source" — which agenda item this relates to

Output ONLY a JSON array. No markdown fences. Example:
[{{"task": "Review budget", "assignee": "Fadi", "due": "2026-06-30", "source": "Budget discussion"}}]"""
        
        try:
            import urllib.request
            
            payload = json.dumps({
                "model": "google/gemma-2.5-flash-preview",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.2
            }).encode('utf-8')
            
            req = urllib.request.Request(
                f"{HERMES_CHAT_PROXY_URL}/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer life-os-dashboard-2026"
                }
            )
            
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            
            if 'choices' in data and data['choices']:
                content = data['choices'][0]['message']['content']
                try:
                    content = content.strip()
                    if content.startswith('```'):
                        content = content.split('\n', 1)[1] if '\n' in content else content[3:]
                        if content.endswith('```'):
                            content = content[:-3]
                    content = content.strip()
                    items = json.loads(content)
                    if isinstance(items, list):
                        return items
                    return []
                except json.JSONDecodeError:
                    return []
            
            return []
            
        except Exception as e:
            print(f"Action item extraction error: {e}")
            return []
    
    def _check_coverage(self, transcript, agenda):
        """Check which agenda items were covered in the transcript"""
        if not agenda:
            return []
        
        transcript_text = " ".join([s.get('text', '') for s in transcript])
        transcript_lower = transcript_text.lower()
        
        coverage = []
        for i, item in enumerate(agenda):
            title = item.get('title', '')
            question = item.get('question', '')
            
            # Check coverage using keyword matching + semantic similarity
            title_keywords = [w.lower() for w in title.split() if len(w) > 3]
            question_keywords = [w.lower() for w in question.split() if len(w) > 3] if question else []
            all_keywords = title_keywords + question_keywords
            
            # Count keyword matches
            matches = sum(1 for kw in all_keywords if kw in transcript_lower)
            match_ratio = matches / len(all_keywords) if all_keywords else 0
            
            # Determine status
            if match_ratio >= 0.5:
                status = "covered"
            elif match_ratio >= 0.2:
                status = "partial"
            else:
                status = "missed"
            
            # Find a relevant snippet
            snippet = ""
            if status != "missed":
                # Find the first matching keyword context
                for kw in all_keywords:
                    idx = transcript_lower.find(kw)
                    if idx >= 0:
                        start = max(0, idx - 30)
                        end = min(len(transcript_text), idx + 80)
                        snippet = transcript_text[start:end].strip()
                        break
            
            coverage.append({
                "index": i,
                "title": title,
                "question": question,
                "status": status,
                "snippet": snippet
            })
        
        return coverage

    def _handle_meeting_file_upload(self):
        """Handle multipart file upload for meeting documents"""
        import cgi
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']})
        
        fileitem = form['file'] if 'file' in form else None
        if fileitem and fileitem.filename:
            fn = os.path.basename(fileitem.filename)
            upload_path = VAULT_DIR / "temp_uploads" / fn
            upload_path.parent.mkdir(parents=True, exist_ok=True)
            with open(upload_path, 'wb') as f:
                f.write(fileitem.file.read())
            
            # Try to read content
            text_content = ""
            if fn.endswith('.pdf'):
                try:
                    import subprocess
                    result = subprocess.run(['pdftotext', str(upload_path), '-'], capture_output=True, text=True, timeout=30)
                    text_content = result.stdout
                except Exception:
                    text_content = ""
            elif fn.endswith(('.txt', '.md')):
                with open(upload_path, 'r', errors='ignore') as f:
                    text_content = f.read()
            
            # Extract agenda from text
            agenda = []
            if text_content:
                for line in text_content.split('\n'):
                    line = line.strip()
                    if line and len(line) > 5 and len(line) < 200:
                        agenda.append({
                            "title": line,
                            "question": "",
                            "status": "pending"
                        })
            
            meeting = {
                "id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
                "title": fn.rsplit('.', 1)[0],
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "attendees": [],
                "source_file": str(upload_path)
            }
            
            meeting_store = VAULT_DIR / ".meeting_store.json"
            meeting_data = {
                "meeting": meeting,
                "agenda": agenda,
                "questions": [],
                "transcript": None,
                "summary": None,
                "actionItems": [],
                "coverage": [],
                "phase": "uploaded"
            }
            with open(meeting_store, 'w') as f:
                json.dump(meeting_data, f, indent=2, ensure_ascii=False)
            
            self._json_response({
                "success": True,
                "meeting": meeting,
                "agenda": agenda,
                "questions": []
            })
        else:
            self._json_error(400, "No file uploaded")


def run_server():
    """Run the Life OS dashboard server with threading support"""
    server_address = ('', PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, LifeOSHandler)
    print(f"Serving Life OS on 0.0.0.0:{PORT}")
    print(f"  Static files: {STATIC_DIR}")
    print(f"  Vault directory: {VAULT_DIR}")
    print(f"  /api/chat -> {HERMES_CHAT_PROXY_URL}/api/chat")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()