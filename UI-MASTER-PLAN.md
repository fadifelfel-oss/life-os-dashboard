# LIFE OS — UI MASTER PLAN v1.0

> Produced 2026-07-04 by Claude (Fable 5) after full review of the repo, all 25 pages,
> shared.css, server.py (3,703 lines, 39 API routes), and the Second Brain vault.
> Status: DRAFT — pending Fadi's sign-off on Decision Gate 1. Execution follows the
> task tables below; each task names its owner.
> Governing standard: Second Brain vault → "STANDARD — The Improvement Loop.md".

---

## 1. ASSESSMENT SUMMARY

**Strengths (keep, build on):**
- Real design-token system in shared.css (spacing/radius/shadow/motion scales, dark + light themes)
- Serious backend: wiki query/lint/graph, chat sessions, kanban store, live OpenRouter catalog, ingestion adapters
- Chat already has a persona/coach architecture with vault-context injection — the Virtual PM slot exists
- Dashboard already tracks job-search KPIs — the "life, not tools" instinct was already there
- Arabic/English toggle, mobile nav, command bar (Ctrl+K) — good bones

**Structural problems (fix before beauty):**
- P1 — Two brains: VPS reads the OLD 344-page OKF vault at /root/knowledge; the real brain is the 108-page Second Brain (OneDrive). Server-side ingest adapters + vault-side agents.md operations = two writers, two schemas, guaranteed drift.
- P2 — Backwards sync: sync_gdrive.sh pushes from the soon-to-be-archived Google Drive copy INTO the repo; two competing write paths caused 10,525 lines of CRLF churn.
- P3 — Jackman Construction is a first-class context in the top bar (violates the hard exclusion rule; dead weight).
- P4 — Tool-organized nav, not life-organized. Duplicates: 3 graph pages, 2 task boards, 2 token views, live.html vs use-cases.html.
- P5 — Mixed SPA/hard-redirect navigation; some state localStorage-only (per-browser, fragile).

**Aesthetic assessment (the honest one):**
The current look is a competent GitHub-dark clone — clean, legible, and completely generic. Specific tells:
- **183 emoji used as UI icons** (29 in the nav alone). Emoji render differently per OS, have no consistent stroke/weight/alignment, and are the single loudest "hobby project" signal. This is the highest-impact visual fix in the entire plan.
- No typographic identity: system font stack; chat.html *names* Inter but never loads it. Numbers (KPIs, tokens, prices) render in the same face as body text — no tabular figures, no display weight.
- No brand: the logo is an owl emoji; the accent color is GitHub's default blue (#58a6ff).
- No unifying visual idea connecting the pages: graph domain colors, kanban labels, and nav share no system.
- Center-aligned KPI cards, colored-text statuses, unstyled empty states — functional, not designed.

---

## 2. DESIGN DIRECTION — "BLUEPRINT DARK"

The unifying idea: **one color per life area, everywhere.** The same eight area colors drive the nav, the Today cards, the 3D Brain domains, kanban labels, and the chat personas. The UI stops being a shelf of tools and reads as one organism. This is the design soul the current UI lacks.

**Identity**
- Theme name: Blueprint Dark — construction-blueprint blue-greys as the base, warm amber/gold as the signature accent (already the 3D Brain's opportunity color — promote it to brand), safety-orange reserved for alerts only.
- Proper SVG logo mark (owl or FB-adjacent mark), replacing the emoji.
- Area palette (Income engines warm, Life & System cool): Career gold · FieldBridge amber-orange · Construction steel-blue · Trading green · Health teal · Family rose · Knowledge purple · Admin/Inbox grey.

**Typography (self-hosted on the VPS — no CDN dependency)**
- UI text: Inter (actually loaded, 400/600/800)
- Display/numbers: Space Grotesk (KPIs, page titles, graph labels — with tabular-nums)
- Data/code: JetBrains Mono
- Arabic: Noto Sans Arabic; all new components RTL-tested

**Components**
- Icons: one set — Lucide static SVG sprite, self-hosted. Zero emoji in chrome (emoji stay allowed in content).
- Card anatomy standardized: eyebrow label → value (display font) → delta → footer action. Left-aligned, sparkline where a trend exists.
- Status = colored dot + text label (never colored text alone).
- Designed empty states: small illustration + one action button ("No signals today — clip something worth knowing").
- Motion: 150ms enter fade/slide, existing hover-lift, existing skeletons. Nothing else. Restraint is the aesthetic.
- 3D Brain is the visual centerpiece: node colors = the area palette; keep July 2 contrast fixes; subtle bloom on opportunity gold; the rest of the UI should feel like the graph's control room.

---

## 3. TARGET INFORMATION ARCHITECTURE

| Nav group | Contents | Replaces |
|-----------|----------|----------|
| ⚡ **Today** (home) | Radar HIGH signals · Kanban due · nightly digest · open wagers · job-search KPIs · Hermes Pilot card · calendar peek | dashboard.html (rebuilt) |
| 🧭 **Life Areas** | Income engines: Career, FieldBridge, Construction, Trading · Life & System: Health, Family, Knowledge, Admin — each: goals, tasks, radar signals, related wiki nodes | (new) |
| 🧠 **Brain** | 3D graph + page reader + search + clipper + wiki health | graph3d, files, clip (graph.html, hermes-map.html RETIRE) |
| 🤖 **Agents** | Chat (personas incl. **Virtual PM**) · Playbook (use-cases) · Loops (cron-jobs, reframed Trigger→Signal→Action→Eval→Stop with wager status) · Skills · Models (tokens merged in) | chat, use-cases, cron-jobs, skills, models+tokens |
| ⚙️ System | API Keys · MCP · backup · meetings/voice/browser/imagegen/artifacts utilities | keys, mcp, etc. |

Deletions: tasks.html · graph.html · hermes-map.html · live.html-vs-use-cases duplication · Jackman context · tokens.html (merged). Mobile nav: 8 → 5 (Today, Areas, Brain, Chat, Kanban). Navigation unified to one SPA pattern.

---

## 4. VIRTUAL PM PERSONA — SPEC

A third coach profile in chat.html: **"Virtual PM (FieldBridge)"**.
- System prompt file lives in the vault: `agent-profiles/virtual-pm.md` — distilled from FB-CORE procedures, the jurisdiction personas (Marcus/Tarek/Khalid/Sherif), the Role & Side-of-Table rule, and current pricing rules (pointer, not copy).
- Context injection: existing /api/kb/search + CRM pages (already wiki nodes after CRM sync).
- Honest boundary: Claude skills do NOT execute in Hermes/OpenRouter chat. The persona advises, drafts, and analyzes; real skill execution (FB-DISCOVER processing, document generation) hands off to a FieldBridge Cowork session. Advisor in the UI, executor in Cowork.
- Same pattern then extends: one persona per life area (Health Coach exists; add Family, Career, Reinvention as thin profiles reading their vault context).

---

## 5. EXECUTION PLAN — TASKS AND OWNERS

Owners: **FADI** (you) · **FABLE** (me, design/architecture sessions in Cowork) · **SONNET** (execution model in Cowork, mechanical) · **HERMES** (on the VPS, ops) · **NIGHTLY** (scheduled task).

### DECISION GATE 1 (before anything) — owner: FADI
Approve the read-only mirror rule: vault writes happen ONLY via Cowork/agents.md; the VPS is a read-only mirror + view layer; server-side ingest buttons retire or route into 10_Sources/raw. **This is the one one-way door in the plan.**

### PHASE 0 — Plumbing (one session)
| # | Task | Owner |
|---|------|-------|
| 0.1 | Remove sync_gdrive.sh cron from VPS crontab; delete script from repo | HERMES (remove cron) + SONNET (repo) |
| 0.2 | Create private repo `second-brain-vault`; initial push of the Second Brain vault | SONNET (prepare) + FADI (create repo, push) |
| 0.3 | VPS cron: pull second-brain-vault → /root/knowledge every 15 min (replaces old vault) | HERMES |
| 0.4 | Adapt server.py to the new vault structure (domains from 030 Resources folders, index.md as catalog; retire OKF migrate/normalize or make it a no-op) | SONNET, spec by FABLE |
| 0.5 | Add .gitattributes (LF normalize) — kills the 10k-line CRLF churn | SONNET |
| 0.6 | Remove Jackman context from ContextSwitcher (index.html, shared.js incl. Arabic strings); contexts become the two life-area groups | SONNET |
| 0.7 | Delete tasks.html + nav/mobile references | SONNET |
| 0.8 | Verify old-vault content fully covered by new vault before /root/knowledge swap (diff page inventory; anything missed → 10_Sources/raw) | SONNET, verified by FABLE |
| 0.9 | Archive H:\ LifeOS-Vault + old AIOS vault on Drive (rename _archive-) — only AFTER 0.1–0.3 confirmed | FADI |

### PHASE 1 — IA restructure
| # | Task | Owner |
|---|------|-------|
| 1.1 | New nav (5 groups per §3), unify SPA navigation, mobile nav → 5 items | SONNET, spec by FABLE |
| 1.2 | Merge tokens.html into models.html; retire graph.html + hermes-map.html; resolve live/use-cases naming | SONNET |

### PHASE 2 — Design language rollout
| # | Task | Owner |
|---|------|-------|
| 2.1 | Blueprint Dark tokens: area palette, amber accent, self-hosted fonts (Inter/Space Grotesk/JetBrains Mono/Noto Arabic) in shared.css | FABLE |
| 2.2 | Lucide SVG sprite; replace all 183 emoji icons in chrome | SONNET (mechanical sweep, FABLE picks the icon map) |
| 2.3 | Card/status/empty-state component standardization in shared.css + sweep pages | SONNET |
| 2.4 | SVG logo mark | FABLE (+ FADI pick between 2–3 options) |

### PHASE 3 — Today page (rebuilt dashboard.html)
| # | Task | Owner |
|---|------|-------|
| 3.1 | Server endpoints: /api/today aggregating radar signals, kanban due, nightly digest (from vault log.md), open WAGER lines | SONNET, spec by FABLE |
| 3.2 | Today page UI per §3 | FABLE (layout) + SONNET (wiring) |

### PHASE 4 — 3D Brain v3
| # | Task | Owner |
|---|------|-------|
| 4.1 | Graph data from new vault: [[wiki-links]] as edges, 030 Resources domains as colors (area palette), inbound-link degree as size | FABLE |
| 4.2 | Fly-to-note on click/search; radar-signal nodes glow amber (verify July 2 fixes still read) | FABLE |
| 4.3 | Fold file reader + clipper into the Brain view | SONNET |

### PHASE 5 — Agent hub + Virtual PM
| # | Task | Owner |
|---|------|-------|
| 5.1 | Write `agent-profiles/virtual-pm.md` in the vault (per §4) | FABLE |
| 5.2 | Persona picker UI in chat.html (area-colored profiles); add Virtual PM + thin life-area personas | SONNET, prompt files by FABLE |
| 5.3 | Loops page: cron-jobs reframed with Trigger/Signal/Action/Eval/Stop + wager status | SONNET |

### PHASE 6 — Life-area pages + backlog sweep
| # | Task | Owner |
|---|------|-------|
| 6.1 | Area page template (goals, tasks, signals, wiki nodes) + 8 instances | SONNET, template by FABLE |
| 6.2 | life-os-ui-backlog leftovers: prompts library backend already built (verify), /knowledge path-traversal hardening, OKF-migrate retirement cleanup | SONNET |
| 6.3 | Credentials still outstanding: Fireflies API key, Gmail App Password, Notion integration token, youtube-transcript-api pip install | FADI (keys) + HERMES (pip) |
| 6.4 | Final visual QA on the live VPS (screens on desktop + phone), round of fixes | FADI (eyes) + FABLE (fixes) |

### Standing per-phase routine
Each phase ends with: git push (FADI or Sonnet prints the exact command per the standing rule) → auto-pull deploys → FADI eyeballs the live page → three-line capture in the vault (Improvement Loop). WAGER for the whole plan: logged in vault log.md at kickoff.

---

## 6. AUTOMATION REGISTRY — every scheduled job, who runs it, where

One table = the whole robot workforce. The Loops page (task 5.3) renders this live; until then this table is the source of truth. Rule: every new automation gets a row here BEFORE it's created — no orphan crons.

| Job | Runs where | Schedule | What it does | Status |
|-----|-----------|----------|--------------|--------|
| `nightly-second-brain-sync` | Claude Cowork (scheduled task) | Daily 21:00 | Vault ingest + project sync + mini-lint + digest | ✅ Live (created 2026-07-04; needs one "Run now" to pre-approve tools) |
| `fieldbridge-kanban-nightly-cleanup` | Claude Cowork (scheduled task) | Daily 21:00 | Reconciles FieldBridge Notion Kanban vs CRM/Home/session-logs | ✅ Live |
| `sync-to-git-nightly.bat` | Windows Task Scheduler (Fadi's PC) | Daily 22:00 | Pushes FieldBridge HQ project folder → fieldbridgehq-skills repo | ✅ Live |
| `auto-pull.sh` | VPS cron | Every minute | Pulls life-os-dashboard repo; restarts server.py if changed | ✅ Live — the deploy pipe |
| `sync_gdrive.sh` | VPS cron | ~15 min | rclone Google Drive LifeOS-Vault → repo → push | 🔴 KILL in task 0.1 (backwards, feeds from soon-archived folder) |
| Vault mirror pull (`second-brain-vault` → /root/knowledge) | VPS cron | 15 min | Read-only mirror of the Second Brain vault for the dashboard | 🔜 NEW in task 0.3 (replaces old vault) |
| Vault → git push (`second-brain-vault`) | Windows Task Scheduler OR folded into nightly Cowork task | Daily (after 21:00 sync) | Pushes the OneDrive vault to its private repo so the VPS mirror updates | 🔜 NEW in task 0.2 — decide mechanism at Decision Gate 1 |
| OpenRouter catalog refresh | server.py (in-process) | 6h cache | Live model catalog for models.html | ✅ Live |
| Monthly model-picks review | Claude Cowork (scheduled task) | Monthly | Review By-Job `match[]` picks in model-catalog.js | 🟡 Backlogged (low priority) |

**Division of labor rule:** Cowork scheduled tasks own anything that touches the VAULT's content or Notion (they run under agents.md with connectors). Hermes/VPS crons own anything that touches the SERVER (pull, restart, mirror). Windows Task Scheduler owns anything that must run even when the Claude app is closed (git pushes of local folders). Never give two runners the same job.

---

## 7. WHAT THIS PLAN DELIBERATELY EXCLUDES
- Voice/JARVIS layer — after the above ships (roadmap discipline; it was the seductive trap named in the wiki)
- Airtable/Notion as live graph nodes (old Phase 2 idea) — CRM sync via the vault covers the need for now
- Any new page not listed — additions go to the backlog memory first
