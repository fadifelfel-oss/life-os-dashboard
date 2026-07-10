# NEXT SESSION — UI Build (Sonnet handoff, updated 2026-07-09)

> **MODEL ROUTING (Fable, 2026-07-09 evening): no Fable needed from here.** All design/architecture
> decisions are made and persisted (vault: STANDARD — System Architecture.md · ROADMAP · agents.md;
> repo: UI-MASTER-PLAN.md · design/*.md · this file). Remaining work is execution-tier — fine for
> Sonnet or cheaper: live-QA fixes (R-items), Skills Hub click→side panel, card-anatomy sweep,
> Morning Brief card (ONLY once Hermes actually produces briefs), capture-pipeline plumbing,
> weekly trading/fitness journal reviews. Rule for any model: if a change would alter tool roles,
> writer lanes, or data stores, STOP and flag it against the STANDARD — that's a design change,
> not execution.

## 2026-07-09 EVENING session (Fable, Second Brain project) — Skills Hub + Trading/Fitness pages + /api/logs

Built after the system-architecture standard + trading/fitness vault systems were created the same day
(see vault: STANDARD — System Architecture.md, 010 Projects/Prop Trading/, 010 Projects/Fitness Rebuild/).

**Front-end (commit 1):**
- `skills.html` — **ARMS Skills Registry section added** (ROADMAP 4.3 / SKILLS-HUB-SPEC): reads `/api/arms`,
  stat strip (Active/Consolidating/Untested), rows grouped by registry section (FieldBridge amber border,
  Cowork purple via `--area-knowledge`), status dot + score chip + wired chip, "Internal — not client-facing"
  footer. Spec's click→side-panel deferred (needs live testing). Health Check + skill grids untouched.
- `trading.html` — **NEW** (ROADMAP 4.7, spec in vault Prop Trading hub): reads `/api/logs?kind=trading`.
  Guardrails banner (turns red if a `rules_followed: false` entry exists in last 7 days), stat cards
  (paper-gate X/50, win rate, total R, rule breaks), cumulative-R sparkline (inline SVG), trade table
  linking each row to files.html. Honest empty state.
- `fitness.html` — **NEW** (ROADMAP 4.7): reads `/api/logs?kind=fitness`. Phase 1 banner w/ safety rules,
  stat cards (sessions this week vs 3–4 target, program week, avg energy-after, last session), daily-anchors
  card, energy sparkline, session table (RPE > 7 highlighted red). PROGRAM_START const = 2026-07-09.
- `shared.js` — both `moduleFiles` maps: `area-trading` → trading.html, `area-health` → fitness.html
  (sidebar Life Areas buttons now hit real pages); drawer got a "Life" group (Trading/Fitness).
- `index.html` — Life Areas section title de-"coming soon"-ed.
- `assets/lucide-sprite.svg` — added missing `icon-lock` symbol (crm.html + trading.html use it; crm's was
  rendering blank before).

**Backend (commit 2 — separate, deploy after front-end looks right):**
- `server.py` — new `GET /api/logs?kind=trading|fitness`: parses journal-entry frontmatter from the vault
  mirror (`010 Projects/Prop Trading/Trade Journal/`, `010 Projects/Fitness Rebuild/Workout Log/`), strips
  the templates' inline `# comment` hints from values, skips entries whose `type` doesn't match, sorts newest
  first. Defensive (missing folder → empty, bad kind → 400).
- `server.py` — `_serve_projects` fix: the vault now stores journal entries/strategies/programs under
  010 Projects (typed `trade`/`workout`/`strategy`/`program`), which the old rglob would have rendered as
  fake project rows. Now hub-notes-only: typed `project`/`cowork-project-hub` pass; untyped files pass only
  if named like their folder.

**Verification done:** NUL scan clean (Grep, whole repo). Logic smoke-tested in the sandbox (node): trading
stats (win rate/total R/violation flag), fitness week/energy math, registry grouping/counts — all pass.
`_serve_logs` executed against a fake vault in python3: filtering, comment-stripping, 400-path all correct.
NOT eyeballed live (as usual) — Fadi walks skills/trading/fitness after deploy. Bash mount staleness
unchanged: verify with Read/Grep only.

**Vault-side same session (needs vault push too):** `agent-profiles/hermes-market-scanner.md` (05:15 scan
persona — Morning Brief card ROADMAP 4.8 stays deferred until Hermes actually produces output), trading +
fitness systems, architecture standard. Vault push = `sync-vault-to-git.bat`.

### Git — commands for Fadi (sessions never run git):
```
cd C:\Dev\life-os-dashboard
git status
# --- Commit 1: front-end ---
git add skills.html trading.html fitness.html shared.js index.html assets/lucide-sprite.svg NEXT-SESSION-UI.md
git commit -m "Skills Hub: ARMS registry section (/api/arms); new trading.html + fitness.html life-area pages (/api/logs); nav wiring (Life group, area-trading/health -> real pages); add missing lock sprite icon"
git push origin main
# eyeball live: skills.html registry, trading.html + fitness.html empty states, sidebar Trading/Health links
# --- Commit 2: backend ---
git add server.py
git commit -m "Add GET /api/logs (trade journal + workout log frontmatter from vault mirror); _serve_projects hub-notes-only filter (journal entries/strategies no longer render as projects)"
git push origin main
# then check http://<vps>:8090/api/logs?kind=trading returns {"data":[],"kind":"trading","count":0} until entries exist
```

## HANDOFF FOR FABLE (design/simplification pass) — state as of 2026-07-09
Fadi is taking the system to Fable next for a "simplest version of this" rethink. Current shipped/built state:
- **Connectors LIVE** (via /keys.html): Fireflies, Notion (read-only integration "Life OS Dashboard"), Gmail (fadi@fieldbridgehq.com). Keys page got a real **Save** button per card. Notion CRM DB share status = Fadi to confirm.
- **3D Brain**: node-click fixed, theme-matched colors, Force/Rings/Sphere/Grid layouts, Systems (ARMS) panel reading /api/arms.
- **Chat**: full theme migration, theme-aware markdown, owl/welcome block removed.
- **Today/Hub** (dashboard.html): rebuilt data-driven off /api/today.
- **Loops**: live-wired to /api/arms routines.
- **CRM** (crm.html, new): read-only pipeline board from /api/wiki/crm (Cowork's synced mirror). "Sync from Notion" button REMOVED (server is read-only per Decision Gate 1) → plain Refresh.
- **Projects** (projects.html + /api/projects, new): read-only registry from 010 Projects/ hub notes. Only FieldBridge HQ exists so far — source needs populating (Cowork OPERATION 7 hub notes for Obsidian OS, Hermes, Life OS Dashboard).
- **Global nav** (shared.js/shared.css): overlay drawer (menu FAB, bottom-left) on every standalone page; index.html keeps its sidebar (now also has Work: CRM/Projects). THIS is the last/highest-risk commit — touches every page; verify live.
- **Architecture locked** (see memory two-agent-architecture): Cowork & Hermes = separate single-writer lanes, cross read-only; Notion=system-of-record, UI reads live read-only; VPS NOTION_API_KEY is read-only.
- **NOT verified live end-to-end** — everything past connectors was verified by syntax/parse checks only; Fadi to walk the site. **Bash mount of C:\Dev\life-os-dashboard is unreliable after file-tool edits** (stale snapshots) — verify with Read/Grep, not bash.
- **Deliberately deferred** (Fadi said do eventually): card-anatomy standardization, per-life-area pages, Virtual PM persona, Hermes read/write Notion lane, back-button standardization, retiring dead pages (graph.html/hermes-map.html/tasks.html), Skills Hub wiring (skills.html → /api/arms skills — easy, data exists).


## 2026-07-08 session — 3D Brain (Stage 4 front-end) + /api/arms (Stage 4 backend) + chat.html full theme migration + color audit

Fadi directed an autonomous ~90% build pass (he was out). Decisions he set:
1) priority 3D Brain → Chat → sweep; 2) chat.html FULL theme migration;
3) build the backend too, in a SEPARATE commit he pushes/tests after the front-end.
All work verified statically (node --check / py_compile / NUL scan) — NOT yet
eyeballed live (he does that when back).

**graph3d.html (3D Brain) — front-end, DONE:**
- **Click bug FIXED (the known R-issue).** Root cause: `onMouseUp` opened the
  detail panel off a stale/null `hoveredNode`. Replaced with real click-vs-drag
  detection (`didDrag`, 4px threshold from `downMouse`) + a FRESH raycast at the
  release point. Clicks now reliably open the node detail panel.
- **Theme-responsive colors.** New `cssVar()` + `refreshThemeColors()` map each
  vault domain onto the shared `--area-*` tokens (career→career, fieldbridgehq→
  fieldbridge, ai-tools→knowledge, inbox/general→admin, etc.). Scene background/
  fog read `--bg-primary`; link colors read `--border-secondary` / `--area-career`;
  opportunity gold reads `--area-career`. Node colors now match nav/kanban and
  re-theme with Blueprint/Graphite/Light.
- **Layout toggle added:** Force / Rings / Sphere / Grid (Display panel). Force
  positions cached as `_fx/_fy/_fz`; opportunity glow meshes tracked as `node._glow`
  so they move with their node; `syncPositions()` rebuilds link geometry.
- Overlay/panel chrome moved off hardcoded rgba dark to `color-mix()` on
  `--bg-secondary` + `--bg-primary` (loading overlay, header gradient, sidebar
  panels, stats bar, tooltip). `.not-okf-badge` → `--status-stale`.

**server.py — backend, DONE (SEPARATE COMMIT):**
- Added `GET /api/arms` → parses `_system/registry/{applications,routines,skills}.md`
  from the vault mirror into JSON `{data:{applications,routines,skills}, counts}`.
  Defensive markdown-table parser (handles skills.md's `##` sections; missing/
  malformed file → empty arm, never 500). Verified against the real registry files:
  applications 14 / routines 8 / skills 20 (3 sections). Route wired in
  `_handle_api_get`. **A visible ARMS/Systems panel in graph3d was intentionally
  NOT built yet** — probe `/api/arms` live first to confirm the shape, then wire
  the consumer next session (kept front-end/back-end cleanly separable).

**chat.html — FULL theme migration, DONE:**
- Local `:root` `--chat-*` / `--health-*` vars re-aliased onto shared tokens
  (`--bg-*`, `--text-*`, `--border-primary`, `--accent`, `--accent-2`, `--status-*`,
  `--area-knowledge`). All hardcoded page backgrounds (#0f1118/#131620/#1a1d24/
  #0d1117), accent blue, `color:#fff`→`--on-accent`, white-overlay rgba, and
  accent-tint rgba converted to tokens / `color-mix()`. Chat now follows all 3
  themes. `.message-body` already 18px (R1 eyesight) — confirmed. JS untouched
  (node --check clean). **Known follow-up:** the CDN `github-markdown-dark.css`
  still forces dark rendered-markdown; a light-theme variant swap is a later task.

**Color audit (Stage 3 tail) — DONE for the fixable set:**
- Repo-wide grep for hardcoded CSS hex: only 29 left across 6 files, and all but
  two are intentional exemptions (use-cases per-area brand colors, chat persona
  dots, theme-preview swatches, artifacts preview-canvas #fff, token-with-fallback
  patterns). Fixed the two real gaps: graph3d `--warning` fallback and loops.html
  status dots (`--green/--blue/--yellow` → `--status-*`/`--accent-2`).

**Added in a follow-up commit same session (after the first deploy):**
- graph3d.html: **Systems (ARMS) panel** built — right sidebar, fetches `/api/arms`
  and renders Applications/Routines/Skills with status dots + kind chips, themed,
  graceful if the endpoint 404s. (`loadArms()` / `renderArmsGroup()`.)
- chat.html: rendered-markdown now **follows the theme** — a MutationObserver on
  `data-theme` swaps the github-markdown CDN css between light/dark.

**Also done later this session:**
- dashboard.html **Today/Hub rebuilt** — data-driven off `/api/today` (Power 3, Due
  Today, high signals, nightly digest w/ stale banner, in-progress, open wagers),
  quick-capture/voice/hermes-pilot kept, nav fixed. Dropped the old hardcoded
  job-KPI hero + fake priorities/alerts. Did NOT hardcode a tripwire card (belongs
  in FieldBridge folder; would rot after the date). Used Radar signals (real data)
  instead of the spec's calendar peek (no calendar source wired).
- loops.html **wired live** — reads the `routines` arm of `/api/arms`
  (`_system/registry/routines.md`) instead of the hardcoded array (kept as
  fallback). Status text → dot class via `statusMeta()`.

**Still NOT done (deliberately deferred — too risky blind):**
- Card-anatomy structural standardization (eyebrow/value/delta/footer) across the
  ~15 pages — restructures each page's card markup; needs live visual testing.
- Skills Hub (R11), per-life-area pages, nav restructure into 5 groups, Virtual PM
  persona — these are new Phase-5/6 builds, not fixes.

### Git — TWO commits this session (I never run git — hard rule). Run `git status` first.
```
cd C:\Dev\life-os-dashboard
git status
# FIRST resolve the pre-existing broken state if still present (see "Pre-existing
# repo issue" further down): the truncated use-cases.html rename + voice.html
# delete/re-add. Do that by hand BEFORE staging.

# --- Commit 1: front-end (safe to deploy + eyeball first) ---
git add graph3d.html chat.html loops.html NEXT-SESSION-UI.md
git commit -m "3D Brain: fix node-click (raycast on mouseup), theme-responsive colors, Force/Rings/Sphere/Grid layouts; chat.html full theme migration onto shared tokens; loops/graph3d color-token fixes"
git push origin main
# auto-pull deploys within ~1 min — open the live 3D Brain + Chat, click a node,
# switch themes, and confirm before pushing commit 2.

# --- Commit 2: backend (/api/arms) — push AFTER front-end looks good ---
git add server.py
git commit -m "Add GET /api/arms — parse _system/registry/*.md into JSON for ARMS panel/Loops/Skills hubs (defensive table parser)"
git push origin main
# then browse to https://<vps>/api/arms and confirm it returns the 3 arms.
```


## 2026-07-07 session — card anatomy (4 pages) + light-touch sweep (8 pages) + 2 real bugs fixed

**Why this session stopped here:** mid-sweep, flagged the $10k-by-Jul-24 FieldBridge
tripwire (17 days left, WMEG follow-up already overdue) against continued dashboard
polish. Fadi chose "finish all the light fixes now" — so this pass completed the
remaining 8 pages at light-touch depth (chrome emoji + obvious hardcoded colors only,
no card-anatomy rebuild) rather than the original full Stage 3 scope, then stopped.
Stage 4 (ARMS/graph3d) and Stage 5 (Hub rebuild) were NOT started.

**Card-anatomy + empty-state (full treatment, Task #10 — done):**
- `shared.css`: added `.card-kpi`/`.card-eyebrow`/`.card-value`/`.card-sparkline`/
  `.card-delta`/`.card-footer` (card anatomy) and `.empty-state`/`.empty-state-icon`/
  `.empty-state-text`/`.empty-state-action` (designed empty states). Also fixed a real
  bug: `--text-muted` was never defined in `:root` — added as alias for
  `--text-secondary` (was silently breaking 93 references across 11 pages since the
  R13 rename).
- `dashboard.html`: colors + emoji only (card-anatomy deferred to the eventual Stage 5
  Hub rebuild since it has bespoke hero/widget markup, not generic KPI cards).
- `files.html`, `skills.html`: full icon/color/empty-state sweep. `files.html` had a
  div-nesting regression from a 3-level-to-1-level empty-state collapse — caught and
  fixed (2 stray orphan `</div>` tags) before it shipped.
- `models.html` (largest page, ~1065 lines): full sweep — tab bar, sidebar filters,
  legend, JOBS array, categoryLabels, empty states, all hardcoded colors. Deliberately
  left `getModelIcon()`, `FALLBACK_MODELS.icon`, `speedIcon` as content (30+ per-model/
  provider brand identifiers, same exemption class as vault/chat/kanban content).
  Verified via `node --check` on the extracted script — `SYNTAX_OK`. A raw grep
  div-count showed 109 open/110 close; traced this by hand (static HTML 1-510 is
  exactly 80/80 balanced; every template-literal block in the script individually
  balances) and confirmed it's a known-pattern false positive from HTML-tag text
  living inside JS string literals, not a real bug.

**Light-touch sweep (Task #11+#12 collapsed, chrome-only depth — done):**
- `chat.html`: toolbar-only (KB/Think/Code-Blocks/Settings buttons + 2 close buttons)
  converted to sprite icons. Deliberately left everything else untouched — this page
  is a fully bespoke dark-only chat UI with its own hardcoded `:root` (not on the
  shared token system at all), and a full migration would be a rebuild, not a sweep.
- `mcp.html`: 4 status rows converted from `● Connected` text to the `.status-dot`
  component pattern used elsewhere.
- `keys.html`: header title, Refresh/Test All/Export/Remove All buttons, and the
  per-provider eye/test/trash buttons converted to sprite icons.
- `loops.html`: already clean, no changes needed.
- `imagegen.html`: already clean, no changes needed.
- `browser.html`: no chrome emoji or hardcoded colors present. **Found and fixed 2 real
  bugs while reading the file** (not part of the icon sweep, just noticed while in
  there): (1) a malformed `</>` closing tag instead of `</div>` after the action-type
  `<select>` — invalid HTML the browser was silently error-recovering from; (2) a
  missing closing backtick in `renderLogs()`'s template literal (`).join('')` instead
  of `` `).join('')` ``) — this made the entire script contents inside `<script>` after
  that point either become swallowed into a runaway string or throw a JS syntax error,
  which would have broken the whole page's JS depending on exact parse behavior.
  Also found `addLogEntry()` called 5 times but never defined anywhere — every
  automation run (success, error, or stop) would throw `ReferenceError` and silently
  break the log/status flow. Added the missing function. Verified with `node --check`
  AND an actual `node` execution of a stubbed-DOM version — both passed clean.
- `life-areas.html`: already clean, no changes needed. Per-area emoji (💼🌉🏗️📈🩺
  👨‍👩‍👧📚🗂️) left as content — each is the primary visual identifier for a distinct
  life area, same exemption class as models.html.
- `use-cases.html`: tab icons (Playbook/Saved Prompts), Re-scan button, empty-state
  icon, and one hardcoded `color:#fff` → `var(--on-accent)` fixed. Per-area brand
  colors (`color:'#7F77DD'` etc, one hex per life area) deliberately left as-is —
  intentional per-area accent colors, not accidental hardcoded grays.

**Verification done this pass:** NUL scan via Grep tool (not bash — mount is stale
again this session, confirmed by comparing `wc -l` output to the real file) on all 9
touched files — all clean. `node --check` + live execution on the browser.html fix.
`node --check` on the models.html script. Manual div-balance trace on models.html's
static HTML portion (80/80).

**Explicitly NOT done — real remaining scope:**
- Card-anatomy/empty-state treatment on chat/mcp/keys/loops/imagegen/browser/
  life-areas/use-cases — these got chrome-only fixes, not the full component
  standardization the original Stage 3 brief called for. chat.html in particular
  would need a full color-architecture migration (not a sweep) to join the shared
  theme system.
- Stage 4 (ARMS endpoint + graph3d rebuild) — not started.
- Stage 5 (Hub/dashboard rebuild) — not started.
- Full hardcoded-color audit of graph3d.html, index.html body chrome beyond what
  Stage 1/2 already covered.

## Stage 3 — IN PROGRESS (component standardization, Phase 2.3)

**Sub-task DONE: 4-page legacy migration onto shared design tokens.**
All 4 pages that were fully or partially off the shared design system
(flagged as a known gap at the end of Stage 1) are now migrated:

- `kanban.html` — done earlier this session. Local `:root` rewritten to
  alias-only tokens (`--bg`, `--bg-card`, `--text`, `--text-muted`, `--border`,
  `--amber`→`--orange`, `--blue`→`--accent-2`, column colors via `color-mix()`
  off `--area-*`/`--status-live`). Tags/hover/modal-overlay hardcoded rgba
  fixed. Emoji swept (header buttons, column headers, modal delete, JS
  template). NUL-clean, 99/99 braces balanced.
- `voice.html` — done earlier this session, **re-verified this pass**: ran
  `node --check` on the extracted `<script>` block in the outputs scratch
  folder (the only rigorous way, since raw `{`/`}` counts are unreliable for
  JS — this file showed a 153/149 discrepancy that turned out to be a false
  positive, now confirmed `SYNTAX_OK`). Also fixed 3 leftover hardcoded
  `color: #fff` in `.btn.green/red/primary:hover` → `var(--on-accent)` that
  were missed in the original pass. NUL-clean.
- `meetings.html` — migrated this pass. Local `:root` aliased
  (`--bg-elevated`/`--accent`/`--green`/`--red`/`--orange`(was `--amber`, now
  alias)/`--purple`/`--pink` fall through unchanged from shared.css since
  names already match; `--accent-light`→`--accent-hover`, `--blue`→`--accent-2`,
  4 kanban-style column colors derived via `color-mix()`). Fixed hardcoded
  rgba (`.upload-area:hover`, `.modal-overlay`, `.recording-indicator`) and
  `color: white` in checkbox states + button hovers → `var(--on-accent)`.
  Full emoji sweep: tabs, panel titles, status pills, empty states, process/
  upload modals, JS-rendered brief meta + process-status messages (added
  `icon-spin` loader for "processing" states, `--status-live`/`--status-failed`
  colored check/x icons for success/error). Added 3 new sprite symbols:
  `calendar`, `users`, `target`. Verified via `node --check` on the extracted
  script (`SYNTAX_OK`) + Grep brace balance (226/226) + NUL scan (clean).
- `artifacts.html` — migrated this pass. This was the "hybrid" page (linked
  shared.css but had its own conflicting local `:root`). Local tokens aliased
  (`--bg`, `--bg-card`, `--border`, `--text`, `--text-muted`; `--bg-editor` has
  no shared equivalent so it derives off `--bg-tertiary`; `--accent` omitted,
  already matches). Fixed `color:#fff` → `var(--on-accent)` in
  `.template-btn.active`/`.action-btn.primary`/inline Run button style.
  Status-dot JS colors (`#3fb950`/`#d29922`) now read live off
  `getComputedStyle(...).getPropertyValue('--green'|'--orange')` instead of
  hardcoded hex. Emoji swept (🎨 empty-state icon, ▶ Run buttons, and the
  previously-mangled blank Copy/Reset/Fullscreen action buttons — added new
  `copy` and `maximize` sprite icons for these). **Deliberately NOT touched**:
  the `templates` object's embedded HTML/CSS/JS strings (the code-playground
  demo content users edit — same "leave content alone" exemption as
  vault/chat/kanban card content) and `.preview-iframe`/`.empty-preview`'s
  `#fff` background (this simulates a real browser canvas rendering arbitrary
  user HTML — it should stay neutral white regardless of app theme, not
  flip with dark/light mode; left a code comment explaining this). Verified
  via `node --check` on the extracted script (`SYNTAX_OK`, had to extract
  carefully since the templates contain escaped `<\/script>` strings that
  would break a naive tag-based extraction) + Grep brace balance (59/59) +
  NUL scan (clean).

Sprite now has 58 symbols total (53 from Stage 2 + play, calendar, users,
target, copy, maximize added this pass).

### Still remaining in Stage 3 (not started this pass)
- Card anatomy standardization (eyebrow/value/delta/footer, left-aligned)
  across all ~15 shared-system pages — dashboard.html, files.html, skills.html,
  models.html, chat.html, etc. each have their own card markup patterns that
  haven't been unified to one anatomy yet.
- Systematic designed empty-states sweep beyond the 4 legacy pages (many
  other pages still have ad-hoc empty-state markup).
- Broader hardcoded-color audit of every remaining page's own `<style>`
  block (dashboard, files, skills, models, mcp, keys, loops, imagegen, chat,
  browser, life-areas, use-cases, graph3d) — only spot-checked, not
  exhaustively swept.
- `.status-dot`/`.status-line` component adoption where colored-text-only
  statuses still exist outside the 4 legacy pages.

## Stage 2 — DONE (icon sweep, Phase 2.2) — partial scope, see below

- Self-hosted `assets/lucide-sprite.svg`: 53 hand-authored Lucide-style icons
  (24x24, stroke=currentColor, fill=none, stroke-width=2). Could NOT fetch the
  real lucide-static SVGs — `web_fetch` returned empty bodies for unpkg,
  jsdelivr, and raw.githubusercontent (strips non-HTML payloads in this
  environment) — so these are hand-drawn approximations in the same visual
  language, not byte-identical to the official set. Swap in real files anytime
  by replacing the `<symbol>` bodies; ids (`#icon-name`) won't need to change.
- `shared.css`: added `.icon`/`.icon-sm`/`.icon-lg`/`.icon-spin` + the
  `.status-line`/`.status-dot` component (dot+label, keyed to
  `--status-live/stale/failed/orphan`) per ICON-MAP.md items 3-4.
- Swept ALL of `index.html`'s chrome: mobile bottom nav (5), sidebar nav (all
  sections incl. area-colored Life Areas icons via inline
  `style="color:var(--area-*)"`), sidebar logo (→ the interim SVG owl from
  ICON-MAP.md), context switcher, theme switcher trigger, command bar trigger,
  refresh button.
- Swept `shared.js` chrome that renders across every page: `ContextSwitcher`
  icons (now innerHTML svg, was textContent emoji — required an API change),
  `Notify.show()` icons — AND added a regex that auto-strips any leading
  emoji from toast messages passed in from anywhere in the codebase
  (`message.replace(/^[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}✅❌ℹ️⚠]+\s*/u,'')`)
  — this quietly cleans up dozens of scattered `Notify.success('✅ ...')`
  call sites without editing each one. Also: `CommandBar` default actions +
  render (icon field changed from emoji char to lucide icon-name string),
  QuickCapture FAB + modal header, ShortcutsOverlay header.
- Swept page `<h1>` headers on: voice, life-areas, loops, mcp (also fixed a
  mangled `�` encoding artifact), meetings, imagegen, use-cases, artifacts,
  browser, models, kanban — 11 pages. Also lightly touched graph3d.html's
  title/Display/Discovery panel + Reset/Auto-Rotate/Opportunities/Hub-Finder
  buttons (kept light since Stage 4 rebuilds this page's structure anyway).
- NUL scan clean; shared.css brace-balanced (291/291 via Grep); sprite
  `<symbol>`/`</symbol>` count matches (53/53 — the raw 54/53 Grep counts
  include one false match inside a code comment, verified by hand).

### Explicitly NOT done in Stage 2 (scope cut, not oversight)
The master plan counted ~183 emoji total; this pass covered the highest-
visibility chrome (global nav + shared.js UI + all page headers) but not:
- Per-page BODY chrome: buttons, status badges, and toasts inside each page's
  own `<script>`/inline handlers (dashboard.html's hero/quick-actions,
  files.html's file-type icons, skills.html's skill cards, chat.html's
  persona/message icons, kanban.html's card labels, models.html's model-list
  icons, etc.) — each page has its own icon-bearing JS render functions not
  touched here.
- The native `confirm()`/`prompt()` dialogs still have emoji in their text —
  unavoidable, browser dialogs can't render HTML/SVG.
- `<title>` tag emoji (browser tab icon) left as-is — not in-app chrome.
This is real remaining work for whoever continues Stage 2/3 — grep
`[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]` across `*.html` `*.js` (excluding
`assets/`) to find what's left; cross-reference `design/ICON-MAP.md` for the
icon name, or pick the nearest sprite symbol / add a new one.

## Stage 1 — DONE (theme system, R13)

- `shared.css`: `:root` rewritten to Blueprint Dark defaults; explicit
  `[data-theme="blueprint"|"graphite"|"light"]` blocks added, folded in from
  `theme-preview.html`. Derived tokens (`--border-secondary`, `--text-tertiary`,
  `--accent-hover/bg/border`, `--on-accent`, `--text-link`) are computed once
  via `color-mix()` in `:root` — a theme block only overrides ~8 base vars and
  everything else recomputes. Added `--accent-2` (secondary/link color),
  `--font-display` (Space Grotesk / Georgia / Segoe UI per theme), and 3 fixed
  `--swatch-*` reference tokens for the picker UI only.
- `shared.js`: `Theme` object rebuilt for 3-way switching (`Theme.LIST`,
  `.apply()`, `.toggleDropdown()`, `.renderDropdown()`). `g` `l` shortcut now
  cycles all three. Removed the old binary dark/light `matchMedia` listener.
- `index.html`: theme-toggle button replaced with a `.theme-switcher` dropdown
  (reuses the `.ctx-switcher` pattern) showing all 3 themes with swatch +
  checkmark. Anti-flash inline script added to `<head>`.
- **Anti-flash inline script added to `<head>` of all 15 pages that use
  `shared.css`**: index, dashboard, use-cases, skills, models, mcp, keys,
  loops, imagegen, files, graph3d, browser, life-areas, chat, artifacts.
  Reads `localStorage['fb-os-state'].theme` and sets `data-theme` before the
  stylesheet loads — no flash on any of them now, including on a hard
  refresh/direct link (every one of these is a real standalone document, not
  an SPA fragment — `navigateTo()` does `window.location.href`, only
  Dashboard loads inline).
- Fixed hardcoded colors I found while in `shared.css`: `.command-bar` (was
  `#1a1d24`/`#30363d`), `.voice-btn` + `.pulse-rec` keyframe (were raw
  `rgba(247,120,186,...)` etc — now `color-mix()` off `--pink`/`--purple`/
  `--red`), `.btn-primary`/`.fab-capture`/`.capture-modal-actions .btn-primary`
  (`color:#fff` → `var(--on-accent)`), and `graph3d.html`'s `body{background:
  #0d1117}` inline override that was defeating the whole theme system on the
  3D Brain page.
- NUL scan: clean (`grep -rlP '\x00' *.html *.js *.css` — zero matches,
  verified via the Grep tool, not bash — see gotcha below).
- Brace/syntax integrity verified: `shared.css` 280/280 braces balanced;
  `shared.js` verified with `node --check` (copied real content out to a
  scratch file and ran node — passed clean).

## Known gaps / NOT done in Stage 1 (deliberate scope cuts, not oversights)

1. **Three pages are fully off the shared design system**: `kanban.html`,
   `voice.html`, `meetings.html` each hardcode their own `:root` (different
   variable names — `--bg-card`, `--text-muted`, etc. — not `--bg-primary`
   etc.) and don't link `shared.css` at all. The anti-flash script would do
   nothing there. `artifacts.html` is a hybrid: links `shared.css` (got the
   anti-flash script) but ALSO defines its own local `:root` fallback
   (`--bg`, `--bg-card`, `--bg-editor`...) that its body content actually
   uses — so it may not fully respond to the theme switch either. **This is
   real migration work — rewrite these 4 pages onto the shared token names —
   and belongs in Stage 3 (component standardization, "sweep all pages"), not
   Stage 1.**
2. Font self-hosting (Inter/Space Grotesk/JetBrains Mono/Noto Arabic, task
   2.1) is explicitly FABLE's task per UI-MASTER-PLAN, not mine — I wired
   `--font-display` as a variable with web-safe fallback stacks so the actual
   `@font-face` work later is a drop-in swap, but no font files are hosted
   yet.
3. Did NOT do a full hardcoded-color audit of every page's internal `<style>`
   block (each page has its own, some 400+ lines) — only fixed what I found
   in `shared.css` itself plus the one `graph3d.html` body background that
   directly broke theming. Full per-page sweep is Stage 3's job.

## IMPORTANT — environment gotcha discovered this session

**The bash sandbox's mount of `C:\Dev\life-os-dashboard` goes stale and does
NOT reflect edits made via Read/Write/Edit/Grep tools.** Concretely: after
editing `shared.css` and `shared.js` via the file tools, `bash`'s `wc -l`,
`grep`, and `git diff/status/show` on this same folder returned a snapshot
from BEFORE the edits (missing ~180 lines of real content, wrong git diff
stats). The Grep tool and Read/Write/Edit tools ARE reliable (they hit the
real host filesystem). **Verification in future sessions on this repo must
use Grep/Read, not bash, for anything touched via file tools this session.**
If this is still true next session, worth flagging to Fadi as a Cowork/host
sync issue outside this repo's control.

## Pre-existing repo issue (NOT caused by this session — flag to Fadi)

`git status` showed this BEFORE any edits tonight: a staged rename
`use-cases.html -> use-` (truncated filename, looks like an interrupted
`git mv`), staged deletions of `voice-chat.js` and `voice.html` with both
also present as untracked new files, and working-tree modifications to
`command-bar.js`, `models.html`, and `UI-MASTER-PLAN.md` that this session
never touched. This looks like a previous session's git operation got cut
off mid-way. Per the 2026-07-06 hard rule I never ran any `git add`/`restore`/
`checkout` to fix it — needs Fadi (or Hermes) to look at `git status` by hand
before the next commit.

## BUILD ORDER — remaining

**STAGE 2 — Icon sweep (Phase 2.2, per design/ICON-MAP.md):** self-host
`assets/lucide-sprite.svg`, add `.icon`/`.status-dot` CSS (spec already
written in ICON-MAP.md), replace the ~183 emoji in chrome across all pages'
nav/buttons/status — start with `index.html`'s sidebar+mobile nav (highest
visibility), then sweep page headers. Status emoji (🟢🔴🟡) → dot+label
component using `--status-*` tokens (already exist). Leave emoji inside
vault/chat/kanban CONTENT untouched. Log any emoji not in the map's table.

**STAGE 3 — Component standardization (Phase 2.3):** card anatomy
(eyebrow/value/delta/footer, left-aligned), status dot+label everywhere,
designed empty states, sweep all pages — AND fold in the 4-page legacy
migration noted above (kanban/voice/meetings/artifacts onto shared tokens).

**STAGE 4 — Part C ARMS (BUILD SPEC §C1-C4):** `/api/arms` endpoint in
`server.py` (aggregates memory from `/api/wiki` + `_system/registry/*.md`
already seeded in the vault — read all three registry files, they're ready).
Rebuild `graph3d.html`: Rings default layout, Force/Circle/Hex/Rings toggle,
registry side panels, all colors via `getComputedStyle` off the new
`--area-*`/`--status-*` tokens (already in shared.css from tonight).

**STAGE 5 — Hub rebuild** (`dashboard.html` per `design/HUB-LAYOUT-SPEC.md`,
`/api/today` already live) — only if time allows per the original brief.

## Git — I never ran git add/commit/push (hard rule). Exact commands for Fadi:

**Always run `git status` first and read it** — this session's bash mount was stale
(confirmed again), so I can't tell you exactly what's already committed vs not. Below
is everything I personally touched this session (2026-07-07); some of it may already
be in a prior commit if you ran one mid-session.

```
cd C:\Dev\life-os-dashboard
git status
# review the pre-existing use-cases/voice rename+deletion mess (noted earlier in this
# file, under "Pre-existing repo issue") BEFORE staging anything, if still present
git add shared.css assets/lucide-sprite.svg dashboard.html files.html skills.html models.html chat.html mcp.html keys.html imagegen.html browser.html life-areas.html use-cases.html NEXT-SESSION-UI.md
git commit -m "Stage 3: card anatomy + empty-state components (shared.css), full sweep of dashboard/files/skills/models, light-touch chrome sweep of chat/mcp/keys/imagegen/browser/life-areas/use-cases, fix broken --text-muted CSS var, fix 2 real bugs in browser.html (malformed closing tag, missing template-literal backtick, missing addLogEntry function)"
git push origin main
```

If `git status` shows `loops.html` as modified, it wasn't touched this session
(reviewed, already clean) — don't stage it unless you know why it's dirty.
