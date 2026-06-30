# Life OS Dashboard

Personal automation dashboard. Self-hosted, single-file Python server with 20+ modular HTML/JS frontends. Runs on a Vultr VPS, proxies to Hermes Agent.

**Tech stack:** Python 3 stdlib (no frameworks), vanilla HTML/CSS/JS, Whisper STT (local), Hermes API proxy.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Browser (Chrome/Edge on Windows PC)         │
│  http://45.63.19.249:8090/                    │
└──────────────┬──────────────────────────────┘
               │ HTTP/WebSocket
               ▼
┌─────────────────────────────────────────────┐
│  server.py  (port 8090)                      │
│  ┌─────────────────────────────────────────┐ │
│  │ Static file serving (life-os/*.html)     │ │
│  │ API endpoints (/api/*)                   │ │
│  │ Vault file serving (/knowledge/*)        │ │
│  │ WebSocket chat proxy (/api/chat)         │ │
│  │ Multipart file upload (/api/upload)       │ │
│  │ Whisper STT (/api/transcribe)            │ │
│  │ Meeting pipeline (/api/meetings/*)        │ │
│  └─────────────────────────────────────────┘ │
└──────────────┬──────────────────────────────┘
               │ proxy to Hermes
               ▼
┌─────────────────────────────────────────────┐
│  Hermes Agent (port 8642)                    │
│  OpenRouter / Anthropic / Google backends    │
└─────────────────────────────────────────────┘
```

---

## File Map

### Backend (1 file)

| File | Lines | Responsibility |
|------|-------|----------------|
| `server.py` | ~2,800 | HTTP server (ThreadingHTTPServer), all API routes, WebSocket proxy, file serving, Whisper STT, meeting pipeline |

### Frontend (20+ files)

| File | Purpose | Key Features |
|------|---------|--------------|
| `index.html` | Dashboard landing | Vault stats, quick links, model carousel |
| `dashboard.html` | Unified command center | Tasks, kanban, calendar, priority views |
| `chat.html` | Hermes chat interface | Model selector, streaming responses, coach mode |
| `meetings.html` | Meeting recording & summarization | Recorder → Whisper STT → Hermes summary → vault storage |
| `graph.html` | 2D knowledge graph | Force-directed vault visualization |
| `graph3d.html` | 3D knowledge graph | Three.js, orbit controls, node interaction |
| `hermes-map.html` | System architecture map | Static SVG/HTML diagram of agent ecosystem |
| `models.html` | Model catalog | 34 models across 6 categories with pricing from OpenRouter |
| `files.html` | Vault file browser | Tree view, search, preview |
| `kanban.html` | Kanban board | Drag-and-drop, priority tags, team filters |
| `voice.html` | Voice input interface | Whisper-powered voice-to-text |
| `cron-jobs.html` | Cron job manager | Create/edit/pause/resume jobs, logs |
| `tasks.html` | Task tracker | Checkbox-based, vault scanning |
| `shared.js` | Shared UI framework | State management, API client, theme, component system |
| `shared.css` | Design system | Dark theme, responsive grid, component styles |
| `artifacts.html` | Hermes artifacts viewer | Live artifacts, HTML preview |
| `browser.html` | Web browser tool | URL navigation, page snapshots |
| `keys.html` | API key manager | Provider key storage |
| `tokens.html` | Token usage tracking | Cost monitoring |
| `skills.html` | Skill library | Available Hermes skills |
| `use-cases.html` | Use case gallery | Pre-built workflow cards |
| `clip.html` | Web clipper interface | Clip management |
| `live.html` | Live artifact dashboard | Real-time data |
| `imagegen.html` | Image generation | Model-based image prompts |
| `mcp.html` | MCP tool configuration | MCP server setup |
| `chat_proxy.py` | Hermes API proxy | Bearer auth proxy for `/v1/chat/completions` |
| `command-bar.js` | Command palette | Keyboard shortcut overlay |
| `command-bar.css` | Command bar styles | |

---

## Key Design Decisions

### 1. Single-file backend (stdlib only)
No FastAPI, Flask, or Django. `http.server.ThreadingHTTPServer` handles all routing via manual URL dispatch. Keeps deployment to `python3 server.py` — zero dependencies beyond Python 3.11+ and `faster-whisper`.

### 2. Background Whisper loading
Whisper model loads in a daemon thread at startup so the server is immediately responsive. First transcription request may wait ~2s while the model finishes loading.

### 3. Manual multipart parsing
`cgi.FieldStorage` breaks in threaded Python servers. File uploads use raw `urllib.parse` + streaming byte buffer.

### 4. WebSocket chat proxy
Chat streams from browser → server.py → Hermes Agent (`ws://127.0.0.1:8642`) → OpenRouter. The proxy handles auth (Bearer token: `life-os-dashboard-2026`), stream parsing, and error recovery.

### 5. Path traversal protection
All file serving under `/knowledge/` checks the resolved path stays within `/root/knowledge/` using `Path.resolve().relative_to()`.

---

## Deployment

```bash
# Start
cd /root/knowledge/life-os && python3 server.py

# Background (screen)
screen -S life-os -d -m python3 server.py

# Auto-restart on crash
while true; do python3 server.py; sleep 2; done
```

Runs on port **8090**. Points to vault at `/root/knowledge` and Hermes proxy at `127.0.0.1:8642`.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard UI |
| GET | `/api/models` | Model catalog (OpenRouter pricing) |
| GET | `/api/tasks` | Task list (markdown + kanban) |
| GET | `/api/wiki` | Wiki page index |
| GET | `/api/tree` | Vault directory tree |
| GET | `/api/file?path=` | Vault file content |
| GET | `/api/clippings` | Clipping list |
| GET | `/api/meetings` | Meeting list |
| GET | `/api/state` | Server state |
| POST | `/api/chat` | Hermes chat proxy (WebSocket upgrade) |
| POST | `/api/upload` | File upload |
| POST | `/api/transcribe` | Audio → text (faster-whisper) |
| POST | `/api/meetings/process` | Meeting audio → summary → vault |
| POST | `/api/clippings/process` | Process clippings |
| POST | `/api/task` | Save task |
| GET/POST | `/api/cron` | Cron job management |

---

## Security

- **Auth:** Bearer token `life-os-dashboard-2026` on `/api/chat` proxy and sensitive endpoints
- **Path safety:** All file reads validate within `/root/knowledge/`
- **No exposed secrets:** API keys stored in Hermes config, not in Life OS files
- **No Apple dependencies** — Windows + Android only

---

*Part of Fadi's personal automation stack. Vultr VPS, Hermes Agent, Obsidian vault.*
