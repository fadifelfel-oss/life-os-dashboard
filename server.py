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
import mimetypes
import asyncio
import urllib.parse
from pathlib import Path
import threading

# Configuration
STATIC_DIR = Path(__file__).parent
VAULT_DIR = Path("/root/knowledge")
PORT = 8090
HERMES_CHAT_PROXY_URL = "http://127.0.0.1:8642"  # Hermes API Server

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
    
    def _serve_models(self):
        """Serve model catalog — pricing from OpenRouter API (openrouter.ai/api/v1/models)"""
        models = [
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
        self._json_response({"data": models})
    
    def _serve_tasks(self):
        """Serve tasks: combine vault markdown checkboxes + kanban store"""
        tasks = []
        
        # Load kanban store (manual tasks)
        store_path = VAULT_DIR / ".kanban_store.json"
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
    
    def _serve_wiki_index(self):
        """Serve wiki page index"""
        try:
            wiki_dir = VAULT_DIR / "20_Wiki"
            pages = []
            if wiki_dir.exists():
                for md_file in wiki_dir.rglob("*.md"):
                    if md_file.is_file():
                        # Extract title from first line or filename
                        title = md_file.stem.replace('-', ' ').title()
                        raw_content = ""
                        try:
                            with open(md_file, 'r', encoding='utf-8') as f:
                                first_line = f.readline().strip()
                                if first_line.startswith('#'):
                                    title = first_line.lstrip('#').strip()
                                raw_content = f.read(50000)
                        except Exception:
                            pass
                        rel_path = str(md_file.relative_to(VAULT_DIR))
                        folder = str(md_file.relative_to(wiki_dir)).split('/')[0] if '/' in str(md_file.relative_to(wiki_dir)) else 'general'
                        pages.append({
                            "title": title,
                            "name": md_file.name,
                            "file": rel_path,
                            "path": rel_path,
                            "id": md_file.stem,
                            "folder": folder,
                            "domain": folder,
                            "words": len(raw_content.split()),
                            "links": len(re.findall(r'\[\[([^\]]+)\]\]', raw_content)),
                            "rawContent": raw_content
                        })
            self._json_response({"data": pages})
        except Exception as e:
            self._json_error(500, f"Failed to serve wiki index: {str(e)}")
    
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
            
            self._json_response({"data": skills})
        except Exception as e:
            self._json_error(500, f"Failed to serve skills: {str(e)}")
    
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
            clips_dir = VAULT_DIR / "Clippings"
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
            
            # Create frontmatter
            frontmatter = f"""---
title: "{data['title']}"
source_url: "{data.get('source_url', '')}"
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
            clips_dir = VAULT_DIR / "Clippings"
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
            src = VAULT_DIR / "Clippings" / filename
            processed_dir = VAULT_DIR / "10_Sources" / "processed" / "clippings"
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
                store_path = VAULT_DIR / ".kanban_store.json"
                if store_path.exists():
                    with open(store_path, 'r') as f:
                        store = json.load(f)
                    store = [t for t in store if t.get('id') != task_id]
                    with open(store_path, 'w') as f:
                        json.dump(store, f, indent=2)
                self._json_response({"ok": True, "deleted": True})
                return
            
            # Upsert task to store
            store_path = VAULT_DIR / ".kanban_store.json"
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