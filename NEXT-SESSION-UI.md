# NEXT SESSION — UI Build (Sonnet handoff, updated 2026-07-10)

## ⚡ QUEUE FOR NEXT SONNET SESSION (planned by Fable 2026-07-10 — execute top to bottom)

> Session rules: git READ-ONLY (print commands for Fadi) · verify with Read/Grep, never bash on
> C:\Dev (stale mount) · NUL-scan every touched file before handing off · UI work = idle hours
> only, the $10k/Jul-24 tripwire owns prime hours · any change touching tool roles / writer
> lanes / data stores → STOP, flag against vault STANDARD — System Architecture.md.

**Items 1-3 SHIPPED 2026-07-10 (Sonnet) — see session write-up below for detail.** Items 4-8
remain gated exactly as before; nothing gated was touched this pass.

1. ~~**Registry hygiene.**~~ DONE — `model-catalog-refresh` now has a live row in
   `_system/registry/routines.md` (confirmed as a real registered Cowork scheduled task, cron
   `0 9 1,15 * *`); the old stale "monthly model-picks review" backlog row (superseded) was
   removed. `hermes-vault-search` + `hermes-market-scanner` confirmed correctly NOT registered
   as routines — both are `spec-ready`, not live yet, so no orphan risk. Vault edit → **remind
   Fadi to run sync-vault-to-git.bat.**
2. ~~**Skills Hub click→side panel.**~~ DONE — clicking an ARMS registry row in skills.html now
   opens a right-side panel: status/score chips, job, Wired-to (linkified to
   `files.html?path=...` for anything path-shaped), and the last log.md line mentioning that
   skill (fetched client-side from the existing `/api/file?path=log.md`, cheap at today's
   ~47KB/144 lines — no new backend endpoint). Added minimal `?path=` deep-link support to
   files.html so those links actually open something (best-effort — some Wired-to values name
   dashboard-repo files like `server.py`, not vault paths, and will 404 gracefully).
3. ~~**Back-button standardization.**~~ DONE — sweep only, no redesign. `kanban.html`,
   `meetings.html`, `graph3d.html` had a "← Life OS" link but with 3 different classes
   (`btn btn-sm` / `back-btn` / `toggle-btn`) and inconsistent placement; all 3 now use
   `.header-back` (crm.html's class) as the leftmost header element. `chat.html` had NO back
   link at all — added one to the chat-toolbar (compact size to fit the 48px bar).
   `dashboard.html` and `index.html` deliberately left alone (dashboard.html is an SPA fragment
   injected into index.html, never navigated to directly — no page links to it; index.html
   IS the home it would point back to). `theme-preview.html` confirmed orphaned (not linked
   from anywhere, its own decision already shipped into shared.css) — left untouched.

**BUILD NOW (added by Fable 2026-07-10 — Fadi feature request, approved):**
9. **Chat activity trace (replaces the thinking dots).** Two parts:
   (a) ~~UNBLOCKED — server-side stage streaming for dashboard chat~~ DONE 2026-07-10 (Sonnet) —
   see session write-up below. Real client-side vault-search stages + a real server-side
   elapsed-time heartbeat while Hermes is in flight, via an SSE-lite stream (`stream_ui:true`
   opt-in on `/api/chat`). Collapses into a "▸ activity" toggle on the finished message.
   (b) ~~STILL GATED on Hermes cooperation~~ GATE CLEARED 2026-07-11 (Hermes confirmed via
   Telegram) and DONE same day — see session write-up below. Read-only `/api/hermes/activity`
   endpoint + a global "Hermes Activity" toolbar panel in chat.html (deliberately NOT
   per-message — see write-up for why).

**BUILD NOW (added by Fable 2026-07-11 — Fadi feature request, approved):**
10. ~~**Playbook goes live (use-cases.html).**~~ DONE 2026-07-11 (Sonnet) — see session write-up
    below. The hardcoded `PLAYBOOK` object is stale (job-search-
    era). The play library now lives in the vault: **`_system/playbook/*.md`** — 16 files, one per
    play, frontmatter `title / area / tier / status` + body = the prompt (Cowork owns content).
    Build:
    (a) `server.py`: `GET /api/playbook` — read `_system/playbook/*.md` from the vault mirror
        (same defensive frontmatter pattern as `/api/logs`), return plays incl. body as `prompt`.
        Skip `status: retired`.
    (b) `server.py`: `POST /api/playbook/run` `{key}` → append `{ts, key}` JSON line to
        `DATA_DIR/playbook-usage.jsonl` (dashboard's own data lane, NOT the vault). `GET
        /api/playbook` merges usage: per play `run_count` + `last_run`.
    (c) `use-cases.html`: delete the hardcoded PLAYBOOK; render from `/api/playbook` grouped by
        tier (income/life) then area. Area colors from the shared `--area-*` tokens (fieldbridge,
        career, construction, trading, health, family, knowledge) — kill the hardcoded hex.
        Each card: title, first line of prompt as desc, "▶ Run in Hermes" (keeps the existing
        sessionStorage 'hermes-prefill' handoff, and now ALSO fires POST /api/playbook/run),
        plus a muted "used N× · last X ago" line when usage exists. Honest empty state if the
        endpoint 404s (backend not deployed yet).
    (d) Saved Prompts tab: unchanged.
    Requires Fadi's vault push first (the 16 play files) — verify /api/playbook returns 16 before
    wiring the front-end final pass.

**BUILD NOW (added by Fable 2026-07-11 evening — Playbook/Saved-Prompts enrichment):**
11. ~~**Saved Prompts tab upgrade (use-cases.html).**~~ DONE 2026-07-11 (Sonnet) — see session
    write-up below. Content note: the vault playbook grew to
    24 plays (10 FieldBridge — deliberate revenue weighting); /api/playbook should now return 24
    after Fadi's vault push. Build, dashboard-side only:
    (a) Each saved-prompt card gets a **Copy** button (clipboard) and shows when it was captured
        (date from the extraction data if present) — sort newest first.
    (b) **"Promote to Playbook" button** per card: copies the prompt to clipboard AND shows a
        toast: "Copied — paste into any Cowork session and say 'add this to the playbook as a
        play'". NO vault writes from the dashboard (read-only mirror rule) — promotion happens
        through Cowork, the vault's only writer. Do NOT build a write endpoint for this.
    (c) Playbook tab: add a small area filter row (All / per-area chips using --area-* colors)
        — 24 cards benefits from filtering; keep tier grouping within the filtered view.
    (d) OPTIONAL if trivial: sort plays within an area by run_count desc so earned plays rise.

**BUILD NOW (added by Fable 2026-07-12 — Fadi decisions on Voice + Meetings):**
12. ~~**Retire Voice, redefine Meetings.**~~ DONE 2026-07-11 (Opus, life-os-dashboard session) — see
    session write-up below. Both parts (a) + (b) shipped. One spec/code conflict surfaced and
    resolved with Fadi (Option A): the kept `/api/meetings/process` writes into the vault, which
    contradicted the required "DATA_DIR lane" banner — banner reworded to the truth, and the
    write-lane fix logged as new flagged item 13. Decisions made with Fadi (2026-07-12):
    (a) **voice.html RETIRED** — its transcription was a mock, and every voice job has a real
        owner (Wispr Flow, phone capture → 000 Inbox, Fireflies, chat voice). Remove the sidebar
        nav button (index.html, data-page="voice") and the 'voice' entries from BOTH moduleFiles
        maps in shared.js. Do NOT touch voice-chat.js (that's chat.html's voice feature) and do
        NOT delete voice.html itself — dead file stays until the close-out sweep, like tasks.html.
    (b) **meetings.html = "Meeting Workbench: pre-call prep + ad-hoc transcripts".** Its ONE role:
        meetings Fireflies does NOT catch (phone calls, WhatsApp voice notes, site conversations)
        plus pre-call prep. Build:
        - Banner stating the role: Fireflies meetings flow to the vault automatically via the
          nightly — never duplicate them here; this page is working copies only (DATA_DIR lane).
        - **"Prep brief" button**: dropdown of prospects from /api/wiki/crm → renders a one-screen
          brief from the mirror (stage, pains, last interactions, next/next_date fields) + an
          "Open in Hermes" button that prefills chat (sessionStorage 'hermes-prefill') with a
          prep prompt embedding that CRM context.
        - Keep upload + /api/meetings/process for ad-hoc transcripts; after processing, add a
          "Copy for Cowork" button (clipboard + toast, promote-pattern) so decisions/actions/CRM
          impact reach the vault through its writer. NO vault writes from this page.
        - Page title "Meeting Assistant" → "Meeting Workbench".

**FLAGGED — architecture decision (raised 2026-07-11, item 12 pass):**
> **RULING (Fable, architect, 2026-07-12): APPROVED — execute as specced.** This is not just a
> lane violation, it's silent data loss: the VPS vault mirror is PULL-ONLY (git), so anything the
> server writes into VAULT_DIR is stranded on the VPS and never reaches the real vault — it only
> survives until the next conflicting pull. Move ALL of it to DATA_DIR. Execution notes:
> (1) before switching reads, check whether `VAULT_DIR/30_Meetings/` or `.meeting_store.json`
> exist on the VPS with real content — if yes, the migration is a one-time copy into DATA_DIR
> (print the copy command for Fadi/Hermes to run on the VPS, sessions can't reach it);
> (2) keep both API response shapes identical; (3) after the move, `30_Meetings/` should never
> be recreated — add it to the close-out sweep list. Any Sonnet session may now execute this.
13. ~~**Move `/api/meetings/process` writes out of the vault.**~~ DONE 2026-07-11 (Opus,
    life-os-dashboard session) — see session #6 write-up below. All meeting writes redirected
    `VAULT_DIR` → `DATA_DIR`; read path follows; close-out sweep note recorded (see below). The endpoint (kept per item 12b)
    currently writes ad-hoc meeting artifacts INTO the vault: `VAULT_DIR/30_Meetings/<id>/*.md`
    (server.py ~L3966) and `VAULT_DIR/.meeting_store.json` (~L3947, L4026). This violates the
    read-only-mirror STANDARD (dashboard = reader; Cowork = the vault's only writer) and is why
    item 12b's banner had to be reworded rather than claim "DATA_DIR lane." FIX: redirect those
    writes to `DATA_DIR` (same class as `.skill_usage.json` / `.kanban_store.json` / `playbook-
    usage.jsonl`) and update `_serve_meetings_get` to read from there. GATE: this is a writer-
    lane/data-store change → STOP-and-flag territory; confirm nothing (nightly sync, any reader of
    `30_Meetings/`) depends on the current vault location before moving it. Fadi chose "ship now,
    fix under review" (Option A) — do not do this blind in an execution pass.

**GATED — do NOT build until the named gate clears:**
4. **Card-anatomy standardization** across ~15 pages — GATE: Fadi finishes live visual QA
   (roadmap 3.4) and names which pages look wrong. Was explicitly deferred as too risky blind.
   **PARTIAL CLEAR 2026-07-13 (Sonnet, "PROMPT — Builder Session 3 — Area Page Hub Redesign"):**
   Fadi named `area.html` / `fieldbridge.html` / `life-areas.html` explicitly and approved the hub
   digest + `.hub-tcard` language for them in-session with Fable — see session write-up below and
   `design/AREA-PAGE-SPEC.md`.
   **GATE FULLY CLEARED 2026-07-13 (Fable, architect, same date) — "PROMPT — Builder Session 4 —
   Design Language Standardization (All Pages)":** Fadi named all remaining pages this date,
   clearing item 4's gate in full for every page listed in the STANDARDIZATION TRACKER below.
   Execute ONE BATCH PER SESSION (push + Fadi's 2-minute live QA between batches — this sweep was
   once deferred as "too risky blind"; batching is the risk control, not a suggestion). See
   session #12 write-up below for Batch A (items 1-4, shipped) and session #13 for Batch B
   (items 5-9, shipped) — see the tracker for what's left.

   **STANDARDIZATION TRACKER** (16 items — check off what shipped, one line each, keep in sync
   with the session write-ups):
   - [x] 1. Promote `.hub-tcard`/stat-tile/chip-row/side-module-card/empty-state CSS to shared.css — session #12
   - [x] 2. crm.html — session #12
   - [x] 3. use-cases.html (chip row = the S4 reference, aligned to shared) — session #12
   - [x] 4. projects.html — session #12
   - [x] 5. trading.html — session #13
   - [x] 6. fitness.html — session #13
   - [x] 7. meetings.html — session #13
   - [x] 8. skills.html — session #13
   - [x] 9. models.html — session #13
   - [ ] 10. files.html
   - [ ] 11. loops.html
   - [ ] 12. mcp.html
   - [ ] 13. artifacts.html
   - [ ] 14. browser.html
   - [ ] 15. imagegen.html
   - [ ] 16. keys.html
   - Explicitly OUT of this sweep (per the builder prompt): kanban.html (reference implementation
     — only swap to shared classes if byte-equivalent), chat.html (toolbar/header only, never the
     message stream), graph3d.html (header + empty states only, no feature work — shiny-object
     flagged), index.html/dashboard.html (Today tab already done; only the Batch-A shared.css
     de-dup touched dashboard.html), voice.html/tasks.html/theme-preview.html (dead/orphaned, skip
     — close-out sweep's job).
5. **Morning Brief card on Home** — GATE: Hermes actually produces a brief. First help Fadi set
   up Hermes's 05:15 scheduled task per vault `agent-profiles/hermes-market-scanner.md` (click-by-
   click, Hermes side), verify a real brief exists in Hermes's lane, THEN build the card.
6. **3D Brain link-density bridge** (Smart Connections → real [[wikilinks]] → more edges; memory:
   life-os-ui-backlog / task 4.1) — GATE: Fadi says go. He named the 3D Brain as shiny-object
   risk vs the revenue tripwire; do not auto-run.
7. ~~**Remaining life-area pages** (6 of 8) — GATE: a real data source exists per area.~~ GATE
   CLEARED + DONE 2026-07-13 (Sonnet, "PROMPT — Builder Session — UI Dashboards + Knowledge
   Backlinking") — see session write-up below. The real data source is a new `GET /api/areas`
   endpoint reading `relates_to:` frontmatter backfilled onto 453 vault notes in the same session.
   life-areas.html and area.html now render real per-area counts/knowledge/opportunities; no static
   placeholders remain. FieldBridge additionally got its own dedicated `fieldbridge.html` (not just
   the generic area.html treatment).
8. **Capture-pipeline full strength** — GATE: Fadi enters credentials (roadmap 3.2). Nothing for
   Sonnet to build; just re-verify channel watermarks after he does.

**NOT in scope for any session:** new tools/stores (see Recall decision 2026-07-10: capture-slot
alternative at most, vault stays the spine), Hermes write-lane token (build when Hermes writes),
anything on UI-MASTER-PLAN already marked done.

> **MODEL ROUTING (Fable, 2026-07-09 evening): no Fable needed from here.** All design/architecture
> decisions are made and persisted (vault: STANDARD — System Architecture.md · ROADMAP · agents.md;
> repo: UI-MASTER-PLAN.md · design/*.md · this file). Remaining work is execution-tier — fine for
> Sonnet or cheaper: live-QA fixes (R-items), Skills Hub click→side panel, card-anatomy sweep,
> Morning Brief card (ONLY once Hermes actually produces briefs), capture-pipeline plumbing,
> weekly trading/fitness journal reviews. Rule for any model: if a change would alter tool roles,
> writer lanes, or data stores, STOP and flag it against the STANDARD — that's a design change,
> not execution.

## 2026-07-13 session #13 (Sonnet, life-os-dashboard folder mounted) — Design Language Standardization, Batch B (items 5-9)

Continuation of session #12 in the same conversation. Fadi confirmed "Yes, deployed and QA'd" for
Batch A before authorizing Batch B — the builder prompt's one-batch-per-session risk control was
honored by pausing and asking rather than chaining straight through. RESTYLE-ONLY, same as Batch A:
no endpoint changes, no new data stores, no behavior changes beyond presentation. No further
shared.css changes were needed this batch — Batch A's promotions already covered everything reused
(`.hub-tile-row/-tile/-num/-label`, `.hub-panel`, `.hub-digest-empty/-loading`, `.hub-tcard*`,
`.hub-tag*`).

**Batch B.5 — trading.html:** `.tr-stats`→`.hub-tile-row`, `.tr-stat*`→`.hub-tile*` (kept a local
override: tiles are non-clickable and center-aligned/trading-colored, unlike dashboard's default
tile). `.tr-panel`→`.hub-panel`, `.tr-empty`/`.tr-loading`→`.hub-digest-empty`/`.hub-digest-loading`.
**Deliberately NOT converted:** the trade log stays a 9-column `<table>` — dense reference data,
matching the spec's own "bordered-row for dense reference lists" guidance rather than forcing it
into card anatomy.

**Batch B.6 — fitness.html:** Same stat-tile/panel/empty pattern as trading.html
(`.ft-stats`→`.hub-tile-row`, etc., health-accent color kept via local override). **Deliberately NOT
converted:** `.ft-ex-card` (today's-circuit exercise reference cards) — a centered icon-topped grid,
a genuinely different shape than the left-spined anatomy; forcing it would look worse. Session log
table stays a `<table>`, same reasoning as trading.html. Both exclusions documented in code comments
so future sessions read them as deliberate, not overlooked.

**Batch B.7 — meetings.html:** Narrower restyle than other pages, matching this page's own bespoke
design system and the "keep banner and handlers truthful" instruction: `.panel`→`.hub-panel`
(container-shape-only rename, 3 HTML usages; `.panel-title` left untouched — different, page-specific
label class). The `.brief` card (prep-brief output) got hub-tcard-*style* treatment without a class
rename — `position:relative;overflow:hidden`, adjusted padding, and a new `.brief::before` 3px
left-spine bar in `var(--area-fieldbridge)` — kept as its own `.brief` class since its internal
structure (name/chips header + labeled fields + actions) is richer than hub-tcard's title/desc/meta
anatomy. Zero JS edits — `<script>` block, `.empty-state`, `.role-banner`, `.tabs`, and every
`onclick` handler left completely untouched, consistent with dashboard.html's Batch A precedent of
not re-touching working scripts that weren't part of the ask.

**Batch B.8 — skills.html:** ARMS registry rows got a bordered-row treatment (not full cards — too
heavy for a dense ~20+ row list): `.reg-row` gained a `border-left: 3px solid transparent` accent,
set per-row from a new shared `REG_STATUS_COLORS` map (`active`/`consolidating`/`retired`) via a new
`regRowAccent()` helper — same map `regStatusChip()` already used for the chip dot, refactored so the
two colors can never drift out of sync. The slide-in detail side panel's Job/Wired-to/Log fields
adopted `.hub-side-item` (the shared muted-box side-module treatment) in place of this page's bespoke
bare-text/one-off-box styling. `.skill-card` grid (Vault Skills / Installed Skills) deliberately left
untouched — not named in the batch instruction for this page.

**Batch B.9 — models.html:** By-Job tab's `.pick-card` recommendation cards (rec/premium/budget)
fully re-skinned onto `.hub-tcard`/`-title`/`-desc`/`-meta` — the `pick-badge` role pill is now a
`.hub-tag` styled inline from a new `PICK_ROLE_TAG` map, and the spine color comes from a matching
`PICK_ROLE_ACCENT` map set via inline `--ar-accent`, so spine and pill share one source of truth per
role. Content and the `setDefaultModel()` onclick handler are unchanged — only the DOM structure
changed (badge/name/provider/price/why → title+pill/desc/meta). Removed the now-unused
`.pick-badge`/`.pick-name`/`.pick-provider`/`.pick-price`/`.pick-why` CSS. **All Models tab's**
`.model-card` grid **deliberately NOT** converted to the title/desc/meta anatomy — same reasoning as
trading/fitness's log tables: a genuinely different data shape (score bar + dual price stat + rank/
speed badges) that would need a JS rewrite beyond a restyle. What WAS adopted: the anatomy's
signature visual language — added a colored left spine in pure CSS (`.model-card::before`, grey by
default, green for the free tier, accent for the selected/compare state) so the page still reads as
part of the same design system without touching the render logic.

**Verification (Read/Grep — authoritative, same methodology as session #12):**
- NUL-scan (`Grep` tool, `\x00` pattern) across all 5 touched files individually as each was
  finished, then again as a consolidated pass across all 5 together: **0 matches.**
- `<script>` blocks extracted byte-for-byte via `Read` (never the bash mount) and run through
  `node --check`: `trading.html`, `fitness.html`, `skills.html`, `models.html` — all `SYNTAX_OK`.
  `meetings.html` had zero JS edits this batch (see B.7 above) so it wasn't re-extracted, consistent
  with the same call made for dashboard.html in session #12.
- Full `Read` re-read of `skills.html` after all 5 of its edits (CSS + HTML + JS) landed, to confirm
  the `.reg-row` accent, `hub-side-item` additions, and `REG_STATUS_COLORS`/`regRowAccent` refactor
  are internally consistent before running the syntax/NUL checks.
- Class-collision check for `models.html`'s new tokens (`PICK_ROLE_ACCENT`, `PICK_ROLE_TAG`,
  `pick-price-mono`): page-local, not shared-namespace, so no repo-wide collision risk.

**Not touched:** Batch C (items 10-16) — see the STANDARDIZATION TRACKER above; `kanban.html`/
`chat.html`/`graph3d.html`/`index.html`/`voice.html`/`tasks.html`/`theme-preview.html` (out of this
sweep); `shared.css` (no further promotions needed this batch); any backend/server.py change (none
needed); any tool role, writer lane, or data store (none changed).

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add trading.html fitness.html meetings.html skills.html models.html NEXT-SESSION-UI.md
git commit -m "Design Language Standardization Batch B (items 5-9): trading.html + fitness.html stat tiles/panel/empty-state onto shared .hub-tile/.hub-panel/.hub-digest-* classes, trade/session log tables kept as dense-reference tables per spec; meetings.html .panel container onto .hub-panel + .brief card gets hub-tcard-style spine (no class rename, banner/handlers untouched); skills.html ARMS registry rows get a status-colored bordered-row accent (regRowAccent(), shared with the existing status chip color map) + side panel onto .hub-side-item; models.html By-Job pick-cards fully onto .hub-tcard/.hub-tag with per-role spine+pill color maps, All-Models cards get the hub-tcard spine visual language in CSS only (score-bar/price-stat layout kept, too dense to force into title/desc/meta). Restyle-only, no endpoint/data-store/writer-lane changes, no further shared.css promotions needed. STANDARDIZATION TRACKER items 5-9 checked off. Batch C (files/loops/mcp/artifacts/browser/imagegen/keys, items 10-16) next -- needs a fresh push+QA checkpoint first per the one-batch-per-session rule"
git push origin main
# auto-pull deploys within ~1 min — run a 2-minute live-QA pass: open trading.html (stat tiles +
# guard banner still triggers on rule breaks), fitness.html (stat tiles + circuit cards unchanged),
# meetings.html (Workbench panels + prep-brief still generates and all buttons still work),
# skills.html (click a registry row — side panel opens with the new box styling + colored row
# accent), models.html (By-Job tab cards look re-skinned, "Set as chat default" button still works,
# All Models tab still filters/compares normally).
```

## 2026-07-13 session #12 (Sonnet, life-os-dashboard folder mounted) — Design Language Standardization, Batch A (items 1-4)

Executed "PROMPT — Builder Session 4 — Design Language Standardization (All Pages)" Batch A only,
per the prompt's own resumable-batch rule (push + Fadi's 2-minute live QA between batches). This is
a RESTYLE-ONLY sweep — no endpoint changes, no new data stores, no behavior changes beyond
presentation; confirmed nothing here touches tool roles, writer lanes, or data stores. First action
taken: recorded the STANDARDIZATION TRACKER above (item 4's gate is now fully cleared for all
pages) and read `design/AREA-PAGE-SPEC.md` + the `.hub-tcard` CSS in `dashboard.html` +
`area.html`'s digest CSS before touching anything, per the prompt's own instructions.

**Batch A.1 — promote `.hub-tcard` + digest CSS to shared.css (the keystone):**
- New `shared.css` section `/* == Hub design language (AREA-PAGE-SPEC) == */` (inserted after the
  existing Phase-2.3 `.empty-state` block, kept deliberately separate — not merged with the older
  `.card`/`.card-kpi`/`.stat-card` system per the spec doc). Contains: card anatomy
  (`.hub-tcard`/`-title`/`-desc`/`-meta`, `.hub-tag`/`.tg-<area>` pills, `sp-*` spine modifiers),
  stat tiles (`.hub-tile-row`/`.hub-tile`/`.hub-tile-label`/`.hub-tile-num`), filter chips
  (`.hub-filter-chip-row`/`.hub-filter-chip`), side-module panel
  (`.hub-panel`/`.hub-side`/`.hub-side-list`/`.hub-side-item`/`.hub-side-footer`/`.hub-sub`), and
  empty/loading states (`.hub-digest-empty`/`.hub-digest-loading`).
- **Naming note (deviation from the prompt's literal "keep class names exactly as they are"):**
  area.html used an `ah-` prefix and fieldbridge.html used an `fb-` prefix for what turned out to
  be the SAME underlying stat-tile/chip-row/panel/side-module/empty-state CSS — two different names
  for identical rules, not a shared name to preserve. Promoting required picking one; used a new
  `hub-` prefix (`hub-tile-row`, `hub-filter-chip`, `hub-panel`, `hub-side-*`, `hub-digest-*`) and
  renamed both pages onto it. Checked for collisions first: dashboard.html already had unrelated
  `.hub-stat`/`.hub-stat-num`/`.hub-stat-label` (header stat, different shape) and `.hub-chip`
  (a small pill decorator, different purpose) and `.hub-empty`/`.hub-loading` (Today-tab specific,
  different layout) — the new names were chosen specifically to avoid colliding with any of those;
  verified via `Grep` that the new class tokens (`hub-tile-row`, `hub-tile-label`, `hub-tile-num`,
  `hub-filter-chip*`, `hub-panel`, `hub-side-list/item/footer`, `hub-digest-empty/loading`, `hub-sub`)
  appear ONLY in the 5 files intentionally touched this session — zero hits elsewhere in the repo.
- **Per-page accent color, unified via one CSS variable:** every promoted rule that needs a
  page-local accent reads `var(--ar-accent, var(--accent))` (or `var(--ar-accent, var(--area-admin))`
  for the default spine). `dashboard.html` never sets `--ar-accent` → falls back to `--accent`,
  reproducing its pre-promotion look exactly. `area.html` already set `--ar-accent`/`--ar-accent-bg`
  on `document.documentElement` via JS per selected area (unchanged) — its rules already used this
  exact fallback pattern pre-promotion, so nothing to reconcile. `fieldbridge.html` previously
  hardcoded `var(--area-fieldbridge)` everywhere instead of using a variable — added one static line
  `:root { --ar-accent: var(--area-fieldbridge); --ar-accent-bg: var(--area-fieldbridge-bg); }` so
  the shared rules resolve to the identical color without per-rule overrides.
- **Known, deliberate, minor visual deltas** (documented rather than silently forced to zero-diff):
  (1) `.hub-tcard-title` margin-bottom converges from area/fieldbridge's 4px to dashboard's 6px
  (2px, imperceptible). (2) `.hub-tcard:hover` gains dashboard's `translateY(-1px)` + accent-tinted
  box-shadow on area.html/fieldbridge.html's knowledge cards, which previously only changed
  border-color on hover — this is the S2 spec's own required "hover-lift," so the addition brings
  those cards INTO compliance rather than away from it. Local deltas kept where behavior genuinely
  differs: `#knowledgeBody .hub-tcard { cursor: pointer }` (area/fieldbridge's cards are
  click-to-expand; dashboard's Today-tab cards aren't) and a `.hub-tcard-meta` typography override
  (10px uppercase muted text — area/fieldbridge show "type · date · expand" as styled text in the
  meta row; dashboard's meta row is a bare flex container for pill tags, no typography of its own).
- Deleted the now-duplicate CSS blocks from `dashboard.html`, `area.html`, `fieldbridge.html` and
  renamed both pages' HTML/JS class references (including JS-generated template-string class names,
  e.g. the chip-row `.map()` calls) onto the shared names.

**Batch A.2 — crm.html:** Pipeline cards re-skinned onto `.hub-tcard` (title + plain-text
trade/region meta line, matching fieldbridge.html's own embedded Pipeline mini-cards exactly — same
underlying CRM data, now the same look). Added a `:root { --ar-accent: var(--area-fieldbridge); }`
static line (CRM is FieldBridge-only, same pattern as fieldbridge.html). Added a stage-count tile
row (S5) above the board — one `.hub-tile` per stage (dynamic count, not a fixed 4), each click
scrolls to that stage's column. Empty/error states moved to `.hub-digest-empty`/`.hub-digest-loading`.
Stage columns/board (`.crm-board`/`.crm-col*`) stayed page-local, matching the `fb-board`/`fb-col`
precedent — that layout is CRM/FieldBridge-specific, not part of the promoted family.

**Batch A.3 — use-cases.html:** This page's `.pb-filter-row`/`.pb-filter-chip` was the ORIGINAL S4
reference implementation the spec was written from (per `design/AREA-PAGE-SPEC.md`'s own text) — now
aligned to the promoted `.hub-filter-chip-row`/`.hub-filter-chip` instead of keeping its own local
copy, closing the loop. Playbook + Saved-Prompts cards re-skinned onto `.hub-tcard`/`-title`/`-desc`.
Since this page shows MANY areas' plays at once (not one page-wide accent like a single-area page),
each Playbook card's spine color is set per-card via an inline `style="--ar-accent:<area color>"` —
the shared `.hub-tcard::before`/`:hover` rules read that per-card variable automatically, so no CSS
changes were needed to support per-card coloring. Saved-Prompts cards (no area) get the default grey
spine. Chip active/hover per-area coloring stays as inline `style` (unchanged) — inline always wins
over the shared class's default color, so no conflict.

**Batch A.4 — projects.html:** Project cards re-skinned onto `.hub-tcard`. Area pill now reuses the
SAME shared `.hub-tag`/`.tg-<area>` classes as dashboard.html's Today-tab tags (previously a plain
uncolored grey pill) — added a small `areaSlug()` helper mapping the raw area string to one of the
nine canonical slugs, falling back to the default grey pill for anything unrecognized. Card spine
set per-card via inline `--ar-accent` (same trick as use-cases.html) matching the project's area
color. Priority pill kept local (`.pr-prio`, not an area concept) with its existing red/orange
semantic tokens. Status columns/board (`.pr-board`/`.pr-col*`) stayed page-local. No stat-tile row
added — not requested for this page, avoided gold-plating.

**Verification (Read/Grep — authoritative; the C:\Dev bash mount was cross-checked and caught
serving stale/truncated content again this session, consistent with every prior session's notes):**
- NUL-scan (`Grep` tool, pattern `\x00`, the proven method — bash `grep`/python `bytes.count` via
  the mount both produced false readings again this session: bash reported non-zero hits via the
  documented `$'\x00'` degrade-to-match-all bug, and python's `bytes.count` via the stale mount
  reported 1873 NULs in `dashboard.html` that do not exist in the real file) — ran across every
  `.html` file in the repo, not just the touched ones: **0 matches, repo-wide.**
- `shared.css` brace balance: the stale bash mount reported an off-by-2 `{`/`}` count; the
  authoritative `Grep` tool (host-side, not the mount) confirmed 380 open / 380 close — balanced.
  The promoted block itself was also manually re-read and hand-verified rule-by-rule.
- Every touched page's inline `<script>` block extracted byte-for-byte (`Read` tool, not the mount)
  into standalone `.js` files and run through `node --check`: `area.html`, `fieldbridge.html`,
  `crm.html`, `use-cases.html`, `projects.html` — all five `SYNTAX_OK`. (`dashboard.html`'s script
  was not touched this pass — only its `<style>` block changed — so it wasn't re-extracted.)
- Class-collision audit: grepped the whole repo for every newly-promoted class token
  (`hub-tile-row`, `hub-tile-label`, `hub-tile-num`, `hub-filter-chip*`, `hub-panel`,
  `hub-side-list/item/footer`, `hub-digest-empty/loading`, `hub-sub`, bare `hub-tile`) — each one
  appears ONLY in the 5 files intentionally touched, confirmed via `Grep` across `*.html`.
- 3-page shared.css canary (per the hard rule): grepped `kanban.html`, `index.html`, `meetings.html`
  (none touched this session) — all three still correctly link `shared.css`, confirming the shared
  stylesheet edit didn't break anything for untouched pages.
- **Not eyeballed live** — Fadi's per-batch QA (2 min, per the builder prompt): after auto-pull,
  open `crm.html` (stage tiles + re-skinned pipeline cards), `use-cases.html` (Playbook tab —
  per-card colored spines, chip row still filters correctly), `projects.html` (colored area pills,
  re-skinned cards), and re-check `area.html`/`fieldbridge.html`/dashboard.html's Today tab still
  look exactly as they did before this session (the de-duplication should be invisible on those
  three). **The shared.css canary: if ANY page's nav or layout breaks, stop and report before
  Batch B.**

**Not touched:** gated items 5, 6, 8; the capture-inbox build; Batch B (5-9) and Batch C (10-16)
pages — see the STANDARDIZATION TRACKER above for what's left; `kanban.html`/`chat.html`/
`graph3d.html`/`index.html`/`voice.html`/`tasks.html`/`theme-preview.html` (explicitly out of this
sweep per the builder prompt, see tracker); any backend/server.py change (none needed — pure
CSS/HTML/JS restyle); any tool role, writer lane, or data store (none changed).

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add shared.css dashboard.html area.html fieldbridge.html crm.html use-cases.html projects.html NEXT-SESSION-UI.md
git commit -m "Design Language Standardization Batch A (items 1-4): promote .hub-tcard/stat-tile/filter-chip/side-panel/empty-state CSS from dashboard.html+area.html+fieldbridge.html into shared.css under one hub- prefixed naming (collision-checked repo-wide); crm.html pipeline cards + new per-stage tile row re-skinned onto .hub-tcard/.hub-tile; use-cases.html's .pb-filter-chip (the original S4 reference) aligned to the shared .hub-filter-chip classes, Playbook/Saved-Prompts cards onto .hub-tcard with per-card --ar-accent spine coloring; projects.html cards onto .hub-tcard with area pills reusing the shared .hub-tag/.tg-<area> classes. Restyle-only, no endpoint/data-store/writer-lane changes. Item 4 (card-anatomy standardization) gate fully cleared this date by Fadi for all remaining pages -- STANDARDIZATION TRACKER added to this file, Batch B (trading/fitness/meetings/skills/models) next"
git push origin main
# auto-pull deploys within ~1 min — run the 2-minute live-QA script above, especially the
# shared.css canary (any page's nav/layout breaking = stop before Batch B).
```

## 2026-07-13 session #11 (Sonnet, life-os-dashboard folder mounted) — Area Page Hub Redesign, item 4 partial clear

Executed "PROMPT — Builder Session 3 — Area Page Hub Redesign" (Fable design, Fadi-approved
mockup, 2026-07-13) end to end: `area.html`, `fieldbridge.html`, `life-areas.html` touch-up, the
new Area Brief backend, and `design/AREA-PAGE-SPEC.md`. Builds on session #10's `/api/areas` +
Opportunity Radar work (same day, prior session) — this pass is the front-end redesign the brief
called out as a separate build once that data source existed.

**server.py (additive only, no response-shape breaks):**
- `/api/areas`'s per-note entries gained one new key, `description` (frontmatter `description`,
  `''` fallback) — `title/path/date/type` and the envelope are unchanged.
- Refactored `_serve_areas`'s body into a new `_build_areas_index()` (pure builder, no
  `_json_response` call) so the new brief endpoint can reuse it in-process instead of a self-HTTP
  round trip. `_serve_areas` itself is now a 3-line wrapper — behavior identical, confirmed by the
  behavior tests below.
- New `GET /api/areas/brief?area=<slug>` — reads `DATA_DIR/.area_briefs.json`, returns
  `{brief, generated, available}`. No cache entry → honest `available:false`. Pure read.
- New `POST /api/areas/brief {area}` — builds a digest (10 newest notes' title+description, up to
  10 Opportunity Radar signals, open kanban tasks for that area's tag from
  `DATA_DIR/.kanban_store.json`; `fieldbridge` additionally folds in CRM pipeline stage counts +
  `next` fields, CRM mirror only) and calls Hermes via the exact `HERMES_CHAT_PROXY_URL` proxy
  pattern already proven in `/api/braindump` (same auth header, same ``` fence stripping, same
  `google/gemma-2.5-flash-preview` model). Caches `{brief, generated}` into
  `DATA_DIR/.area_briefs.json` and returns it. Every failure path (nothing to summarize, Hermes
  unreachable, empty/unparseable response) returns `{available:false, error}` — never a fabricated
  brief. Data-store note: `.area_briefs.json` is the same operational class as
  `.kanban_store.json`/`playbook-usage.jsonl` — pre-approved by the architect in this session's
  builder prompt (cited verbatim in `design/AREA-PAGE-SPEC.md`), not a fresh STOP-and-flag item.
- Routing: added `/api/areas/brief` to both the GET dispatcher (`_handle_api_get`) and the POST
  dispatcher (`do_POST`).

**area.html (full rebuild):** Header (unchanged) → Area Brief card (label + generated-timestamp +
refresh icon-button + a small "Area note ↗" link to the vault hub note, added because the mockup's
digest has no room for the old hub-note panel — see "what this pass dropped" in the spec doc) →
4 stat tiles (Knowledge/Opportunities/Open tasks/Projects, click-to-scroll) → two-column digest:
Knowledge main column (search input, type filter chips hidden under 2 types, `.hub-tcard` note
cards showing 8 newest with "Show all N →", click-to-expand-in-place via `/api/wiki/page?path=`
through a hand-rolled minimal markdown renderer — headings/bold/lists/links, `[[wikilinks]]` as
plain italic text not links, response bodies cached in a JS map for the page session, "Open in
vault ↗" kept in the expanded body); side column with Opportunity radar (expand-in-place footer),
Tasks (real link to kanban.html per spec), Projects (expand-in-place, spec didn't specify so this
followed the Opportunity radar precedent — noted in the spec doc as an inference, not a literal
instruction). `AREAS` dict, `AREA_TASK_TAG`, and the `?area=` routing/`--ar-accent` CSS variable
wiring were carried over unchanged from the pre-existing file.

**fieldbridge.html (full rebuild):** identical recipe — Brief → 4 stat tiles (Pipeline/Knowledge/
Opportunities/Open tasks) → Pipeline as its own full-width module first (stage-column board kept,
mini-cards re-skinned onto `.hub-tcard`) → two-column digest (Knowledge main, same search/chip/
expand-in-place language as area.html; side column Opportunity radar / Plays / Tasks — Plays kept
its `sessionStorage['hermes-prefill']` + `POST /api/playbook/run` Run-in-Hermes handoff, footer
links to `use-cases.html`). Brief generation additionally feeds CRM stage counts + `next` fields
per the spec (server-side, see above).

**life-areas.html (touch-up only, per the brief's explicit "grid layout already works" scope):**
its cards already had the 3px colored spine and note/signal/task counts from session #10 — the
gap was styling (16px radius, plain-text counts) vs. the new `.hub-tcard` language (10px radius,
pill-badge counts). Tightened `border-radius` to `10px` and converted `.area-stats` from plain
inline text to small pill badges (`.area-stat-pill`). Grid, emoji, title, hover-lift, and the
JS count-loading logic (`loadAreaCounts`) were untouched — only the one CSS rule + one `innerHTML`
template string changed.

**design/AREA-PAGE-SPEC.md (new):** codifies the layout recipe, `.hub-tcard` anatomy, chip
behavior, expand-in-place pattern, and Area Brief backend contract — "any new area-like page
follows this spec." Notes item 4 (card-anatomy standardization) is now cleared for these three
pages only; the other ~12 stay gated until Fadi names them (recorded in the queue item 4 line
above and in the spec doc itself).

**Verification (Read/Grep — authoritative; the C:\Dev bash mount's documented staleness/truncation
was not relied on for anything):**
- Backend logic (`_build_areas_index`, `_serve_area_brief`, `_handle_area_brief_post`'s core digest/
  cache/error-path logic) extracted into a dummy class in the sandbox with synthetic fixtures —
  6 behavior tests, all passed: no-cache → `available:false`; unknown area → 400; nothing-to-
  summarize → honest `available:false` (no fabrication); real vault note + kanban task → Hermes
  fence-stripped, cached, `available:true`; GET reflects what POST just cached; Hermes-down path →
  honest `available:false`. Full `server.py` re-read via the Read tool around every edit site to
  confirm indentation/nesting (the class-level `_serve_areas`/`_build_areas_index`/brief methods
  and the two new dispatcher lines) — no truncation, no stray indentation.
- `area.html` and `fieldbridge.html`'s inline `<script>` blocks each extracted byte-for-byte (Read
  tool, not the mount) into standalone `.js` files and run through `node --check` — both
  `SYNTAX_OK`. `life-areas.html`'s one changed JS line re-read in place, no new syntax introduced.
- NUL-scan (ripgrep `\x00`, per the standing gotcha that bash `grep`/`python3 bytes.count` on this
  repo have both produced false positives/negatives in past sessions) on every touched file —
  `server.py`, `area.html`, `fieldbridge.html`, `life-areas.html`, `design/AREA-PAGE-SPEC.md`,
  `NEXT-SESSION-UI.md` — 0 matches on all six.
- Icon audit: every `lucide-sprite.svg#icon-*` reference in the two rebuilt pages was carried over
  from the pre-existing files (already validated against the sprite in session #10's icon audit —
  none of the three previously-renamed IDs, `icon-library`/`icon-git-branch`/`icon-alert-triangle`,
  were reintroduced).
- **Not eyeballed live** — see the 5-minute QA script below. One live dependency to watch: Area
  Brief generation requires Hermes reachable at `HERMES_CHAT_PROXY_URL`; if it's down the UI shows
  the honest "Brief unavailable — Hermes is offline" fallback per spec, never a fake brief.

**Not touched:** gated queue items 5, 6, 8; the capture-inbox build; Today tab; 3D Brain; any vault
edit; the other ~12 ungated pages; Notion (nothing new reads/depends on it).

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add server.py area.html fieldbridge.html life-areas.html design/AREA-PAGE-SPEC.md NEXT-SESSION-UI.md
git commit -m "Area Page Hub Redesign (item 4 partial clear): area.html + fieldbridge.html rebuilt as brief -> stat tiles -> two-column digest (search/chips/expand-in-place Knowledge, compact side modules); life-areas.html card anatomy touch-up (radius + pill counts); new GET/POST /api/areas/brief (Hermes-generated area brief, cached in DATA_DIR/.area_briefs.json, same operational class as .kanban_store.json); /api/areas notes gained additive 'description' key; new design/AREA-PAGE-SPEC.md codifies the pattern for future pages"
git push origin main
# auto-pull deploys within ~1 min
```

### 5-minute live-QA script (once deployed):

1. Open `area.html?area=knowledge` — Brief card shows "Loading…" then either a generated brief or
   the honest "Brief unavailable" fallback; click its refresh icon to force a regeneration and
   confirm the timestamp updates. Stat tiles show real numbers; clicking one scrolls to its module.
   Knowledge shows 8 cards with "Show all 234 →" (or whatever the live count is); typing in the
   search box narrows the list; clicking a card expands its body inline (markdown rendered, a
   `[[wikilink]]` if present shows as plain italic text, "Open in vault ↗" present) and a second
   click collapses it.
2. Reload the same page — the Brief's timestamp should persist (read from the cache, not
   regenerated) until the refresh icon is clicked again.
3. Open `fieldbridge.html` — Pipeline renders first as a stage board with `.hub-tcard`-style mini
   cards; Brief, stat tiles, and the Knowledge/Opportunities/Plays/Tasks digest follow the same
   language as `area.html`; a Play's "Run in Hermes" still lands on `chat.html` with the prompt
   prefilled.
4. Open `life-areas.html` — cards look the same as before (spine, emoji, grid) but the note/
   signal/task counts now render as small pill badges instead of plain text.
5. Check `area.html` or `fieldbridge.html` at phone width (~375px) — stat tiles go 2×2, the
   two-column digest stacks to one column, search/chip row wraps cleanly.

## 2026-07-13 session #10 (Sonnet, Second Brain + life-os-dashboard, both folders mounted) — Knowledge Backlinking Phase 1 (vault) + UI Dashboards Phase 2 (repo), item 7 gate cleared

Executed the full "PROMPT — Builder Session — UI Dashboards + Knowledge Backlinking" (vault root)
end to end, both phases, per Fadi firing that exact prompt into a fresh session. Phase 1 (vault
backfill) ran first and fully, per the prompt's own sequencing rule ("dashboards render the
classification; without it they're empty shells"), before any repo code was touched.

**Phase 1 — vault backfill (Second Brain folder, Cowork is the vault's only writer):**
- Classified 453 of 454 notes across `10_Sources/processed` (306), `030 Resources` (131),
  `30_Context` (16), `20_Wiki` (1) with a `relates_to:` frontmatter list (1-3 of the nine canonical
  slugs) + mirrored `area/*` tags. 1 note skipped (`20_Wiki/09-Project-Register.md`, a 0-byte empty
  stub — left untouched, flagged for Fadi to decide delete-vs-populate).
- Hybrid method: mechanical Pass A (domain/tag/folder signal mapping, script-assisted, 217 notes)
  + judgment Pass B (title+desc review against the digest, keyword rules + hand-classification for
  structurally important notes, 236 notes). All edits frontmatter-only via a ruamel.yaml round-trip
  writer (preserves comments/quote-style/existing formatting) with a raw-text fallback for 10 files
  that had pre-existing broken YAML (unquoted `[[wikilink]]` values) — those 10 got the same two
  fields inserted via string surgery instead of a full parse, leaving the pre-existing corruption
  untouched rather than "fixing" something out of scope.
- Final distribution: knowledge 234, fieldbridge 169 (175 once CRM/playbook folders are counted by
  the new endpoint — see below), construction 69, admin 19, trading 10, career 8, health 4, family
  4, finances 2 (notes can carry up to 3 areas).
- Opportunity Radar.md: added a new "🌍 Other Life-Area Signals" section (7 rows: trading×3,
  career×2, knowledge×2) — the Radar was 100% FieldBridge-only before this pass; existing
  HIGH/MEDIUM/EMERGING FieldBridge sections were left untouched/not duplicated (the spec's worked
  example, Claude Code + Clay lead-gen, was already a MEDIUM row from 2026-07-12's nightly ingest).
- Forward path: `agents.md` OPERATION 1 (step 3a + revised step 4) and
  `_Templates/Web Clip Processed.md` frontmatter updated so every future clip gets classified at
  ingest time — no drift between backfilled and new notes going forward.
- Discovered (not caused by this session, flagged to Fadi): `30_Context/FieldBridge/pricing-guide.md`
  has ~7,744 trailing NUL bytes after its visible text, dating from its 2026-07-12 supersede edit —
  low priority since the file is already marked superseded/do-not-use.
- Full detail: `log.md` entries dated 2026-07-13 (BACKFILL / OPPORTUNITY RADAR / PERSIST / CAPTURE).
- **Fadi action required:** run `sync-vault-to-git.bat` so the VPS mirror picks up the 453 changed
  files — Phase 2's `/api/areas` endpoint reads the MIRROR, not the local vault, so live QA below
  is blocked until this runs.

**Phase 2 — two dashboards (life-os-dashboard repo, git read-only, session never ran git):**
- `server.py`: new `GET /api/areas` (read-only, same defensive-frontmatter pattern as
  `/api/playbook`/`/api/wiki/crm`, reuses the existing `_parse_frontmatter` helper — no new parser
  dependency). Walks `10_Sources/processed`, `030 Resources`, `30_Context`, `20_Wiki`,
  `_system/playbook`, `CRM` for `relates_to:` (fallback `area/*` tags), returns
  `{areas: {<slug>: {count, total, notes:[{title,path,date,type}], opportunities:[{text,confidence}]}}}`,
  newest-first, capped 50 notes/area. New `_parse_opportunity_radar()` parses `Opportunity
  Radar.md`'s two table shapes (fixed-area FieldBridge HIGH/MEDIUM/EMERGING tables + the new
  per-row-area "Other Life-Area Signals" table) into the same response — one file, one parser, no
  second opportunity store. Bodies never ship in the payload (stays behind the existing
  `/api/wiki/page?path=`).
- `shared.css`: added `--area-finances` / `--area-finances-bg` (copper/bronze) to `:root` and
  `[data-theme="light"]` (graphite inherits from `:root` per the file's existing convention — see
  its own comment at the graphite block). `--area-admin` already existed from an earlier pass.
- `fieldbridge.html` (new page): Pipeline (crm.html's board pattern against `/api/wiki/crm`),
  Knowledge feeding FieldBridge (`/api/areas` fieldbridge bucket — explicitly labeled as the
  cross-vault bridge per Brief §2, since Obsidian wikilinks can't cross into the FieldBridge HQ
  vault), Opportunity Radar (same bucket's `opportunities`), Plays (`/api/playbook` filtered
  `area===fieldbridge`, reuses the existing `hermes-prefill` Run-in-Hermes handoff + usage POST),
  Tasks (`/api/tasks` filtered `tag===fieldbridge`, kanban.html-style mini cards). No revenue/
  tripwire widgets — that's the FieldBridge folder's job, not this UI, per the brief.
- `life-areas.html` (rebuilt): same two-group static grid (Income engines / Life & system) but every
  card now pulls real counts (notes/signals/open-tasks) + 3 newest note titles from `/api/areas` +
  `/api/tasks` client-side. Open-task count only rendered for career/fieldbridge/trading — the only
  three canonical areas with a matching kanban tag today (`project/fieldbridge/career/trading/
  personal/urgent`); other areas honestly omit the stat rather than showing a fake zero. FieldBridge
  card now links straight to `fieldbridge.html` instead of the generic area template.
- `area.html` (rebuilt): kept the existing hub-note-from-vault + related-projects panels, added
  Knowledge and Opportunity Radar panels (same `/api/areas` bucket) and a Tasks panel (honest empty
  state for the 5 areas with no matching kanban tag). **Renamed the `AREAS` dict key `work` →
  `construction`** to match `/api/areas`'s canonical slug — the sidebar's `moduleFiles` hash target
  was already `life-areas.html#construction` (not `#work`), so this was a latent mismatch between
  the two files, now aligned; nothing else referenced `?area=work`.
- `index.html` + `shared.js`: sidebar's existing "FieldBridge" nav item relabeled "FieldBridge HQ"
  and repointed (`moduleFiles`, both occurrences in `shared.js`) from `life-areas.html#fieldbridge`
  to `fieldbridge.html`. No new sidebar button added — the existing area-fieldbridge item now goes
  to the real dashboard instead of the generic grid anchor. Trading/Health nav items untouched
  (already route to their own dedicated pages, unaffected by this pass).

**Verification (Read/Grep — never the bash mount of C:\Dev, confirmed stale again this session:
`wc -l`/`stat` on server.py, life-areas.html and area.html all returned pre-edit byte counts/mtimes
minutes after successful Write/Edit calls; Grep tool, which is host-side like Read/Write/Edit,
correctly showed the new content and was used for everything below):**
- `_serve_areas`/`_extract_note_areas`/`_parse_opportunity_radar` extracted into a standalone dummy
  class in the sandbox (exact text of the edit, not a mount copy) — `py_compile` clean, then run
  against synthetic fixtures (assertions passed) AND against a live copy of the real vault +
  Opportunity Radar.md via the mounted Second Brain folder: returned correct counts (knowledge 234,
  fieldbridge 175, construction 69, career 8, trading 10, finances 2, health 4, family 4, admin 19)
  and correct opportunity rows (26 fieldbridge signals from the three fixed tables, 7 cross-area
  signals matching Phase 1's new Radar section exactly).
- server.py routing addition (`elif path == "/api/areas":`) and the full new method block re-read
  via the Read tool (authoritative) directly in place in the real file — correct indentation,
  correctly nested inside `LifeOSHandler`, no truncation.
- `fieldbridge.html` / `life-areas.html` / `area.html` inline `<script>` blocks reconstructed
  byte-for-byte from what was written (not read back through the stale mount) and run through
  `node --check` — all three `SYNTAX_OK`.
- NUL-scan on every touched file (server.py, shared.css, shared.js, index.html, fieldbridge.html,
  life-areas.html, area.html) via the Grep tool with pattern `\x00` — 0 matches on all seven (the
  bash-mount `python3 bytes.count` version falsely reported NULs on stale/cached content for two
  files; Grep tool result is the authoritative one per the standing verification-gotcha notes).
- Icon audit: cross-checked every `lucide-sprite.svg#icon-*` reference used in the three new/rebuilt
  pages against the sprite's actual symbol IDs — `icon-library`, `icon-git-branch`, and
  `icon-alert-triangle` don't exist (renamed to `icon-book-open`, `icon-zap`, `icon-triangle-alert`
  respectively before shipping).
- **Not eyeballed live** — blocked on Fadi's `sync-vault-to-git.bat` run (Phase 1 action item
  above) since `/api/areas` reads the VPS mirror, not the local vault. 5-minute live-QA script once
  that's run and the repo is deployed:
  1. Open `fieldbridge.html` — Pipeline populated from the CRM mirror, "Knowledge feeding
     FieldBridge" shows real note titles/dates, Opportunity Radar shows both old HIGH/MEDIUM rows
     and confirms none of the new cross-area rows leaked in (fieldbridge-only).
  2. Open `life-areas.html` — all 9 cards show non-zero note counts (except any genuinely-empty
     area), 3 newest titles per card, FieldBridge card click lands on `fieldbridge.html` not the
     generic area page.
  3. Click into any non-FieldBridge card (e.g. Construction) → `area.html?area=construction` —
     hub note renders, Knowledge panel lists real construction-tagged notes, Opportunity panel is
     honestly empty (no construction rows exist yet), Career's Tasks panel shows real open
     career-tagged kanban cards if any exist.
  4. Confirm the sidebar's "FieldBridge HQ" nav item opens `fieldbridge.html` directly (not the old
     `life-areas.html#fieldbridge` anchor-scroll behavior).

**Not touched:** gated queue items 4-6, 8 (untouched); Notion (nothing new reads/depends on it, per
Brief §8); the FieldBridge HQ vault; Hermes write-lane token; any new data store beyond the
`/api/areas` read (no writer, no new DATA_DIR file); the 3D Brain; the capture inbox build.

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add server.py shared.css shared.js index.html fieldbridge.html life-areas.html area.html NEXT-SESSION-UI.md
git commit -m "Knowledge Backlinking Phase 2: new GET /api/areas (relates_to/area-tag index + Opportunity Radar parser, read-only), --area-finances CSS tokens, new fieldbridge.html dashboard (pipeline/knowledge/opportunities/plays/tasks), life-areas.html + area.html rebuilt with real per-area data (item 7 gate cleared), sidebar FieldBridge nav repointed to the new dashboard, area.html AREAS key work->construction rename to match canonical slugs"
git push origin main
# auto-pull deploys within ~1 min — but /api/areas will return all-zero counts until the vault
# mirror has the Phase 1 classification. Run sync-vault-to-git.bat FIRST (vault change, separate
# from this repo push), confirm the VPS mirror picks it up, THEN do the live-QA script above.
```

### Vault — reminder for Fadi (separate from the repo push above):

```
Run sync-vault-to-git.bat (pushes the Second Brain vault, which is OneDrive-sync only, no .git of
its own, to the git repo that feeds the VPS mirror). This is what makes the 453-note relates_to
backfill and the new Opportunity Radar section visible to /api/areas. Do this before the live-QA
script above — without it, both new dashboards will look empty even though the code is correct.
```

## 2026-07-12 session #9 (Opus, scheduled unattended run) — Productivity Hub v1 architecture ruling + HTTPS/push prep (NO code shipped)

Scheduled follow-up (queued 2026-07-11). Ran unattended — Fadi not present — so per the run rules
this was an analysis/prep pass, **not** an execution pass. The main build (item 1, Productivity
Hub v1) is explicitly gated on Fadi's architecture sign-off (item 1a: "state the decision
explicitly to Fadi and confirm consistent with the STANDARD before building… Only proceed once
confirmed"). A new server-side data store is textbook STOP-and-flag territory, so no code was
written. What this pass produced instead:

**(1) ARCHITECTURE RULING — capture inbox `DATA_DIR/.capture_inbox.json` (item 1a). APPROVE, with
one framing condition.** Checked against `STANDARD — System Architecture.md` (vault root). The
dashboard's ONE role is "UI hub… renders the vault mirror + Notion, read-only — Never: becoming a
data store." The precedent that reconciles this: the dashboard already owns an OPERATIONAL lane in
DATA_DIR (`.kanban_store.json`, `playbook-usage.jsonl`, `.skill_usage.json`, and now
`.meeting_store.json` from item 13) — distinct from the vault's KNOWLEDGE spine. "Never a data
store" means never a second home for knowledge/business data that belongs in the vault; it does not
forbid the dashboard's own transient operational files.
- **Ruling:** `.capture_inbox.json` is the same CLASS as `.kanban_store.json` — dashboard-owned,
  single-writer, operational. Consistent with the STANDARD **provided it is framed as a TRIAGE
  BUFFER, not a capture store.** Items must always DRAIN: → a kanban task (dashboard lane), → a
  vault note/project via the clipboard+Cowork promote-pattern (no vault write), or → dismissed.
  Nothing knowledge-bearing rests permanently in the inbox.
- **The one real tension to name to Fadi:** the STANDARD's capture-flows section already routes
  "phone quick capture → `000 Inbox/`" (the vault, the knowledge spine). The new inbox adds a
  SECOND capture front-door (dashboard DATA_DIR). That's acceptable **only** under the triage-buffer
  framing above — the vault's `000 Inbox/` stays the destination for anything that is knowledge;
  DATA_DIR is the fast operational staging area that empties into either kanban or (via Cowork) the
  vault. Single-writer preserved: dashboard is the only file writer; Hermes DROPS items via
  `POST /api/capture` (an API call, not a cross-lane file write).
- **Recommended addition to the STANDARD** when Fadi approves: one line under Tool roles / capture
  flows distinguishing "capture-of-knowledge → vault 000 Inbox" from "operational triage buffer →
  dashboard DATA_DIR, drains, never retains." Cowork writes that line (vault = Cowork's lane).
- **Build is READY to execute the moment Fadi signs off** — spec in the scheduled-task file
  (server.py endpoints `POST/GET /api/capture` + `POST /api/capture/update`; consolidate the two
  localStorage silos `fb-captures`/`cmd-inbox` onto it; new `admin.html` triage page). v1 scope
  only (no Hermes auto-triage cron, no SaaS, no vault-first routing — Fadi picked the two-tier
  model). Deferred-by-design, logged: auto-triage cron, vault-first routing, SaaS.

**(2) HTTPS via Caddy (item 2) — BLOCKED on Fadi's domain.** Cannot proceed without a domain/
subdomain A-record'd to 45.63.19.249. Full click-by-click prepared and handed to Fadi in-session
(get/point a domain → install Caddy → 3-line Caddyfile `reverse_proxy 127.0.0.1:8090` → reload →
open `https://<domain>` on iPhone Safari, mic works). server.py binds `('', 8090)` — no server
change needed. Runs ON the VPS; sessions can't reach it.

**(3) Push/run reminders (item 3) — ALL CLEAR on git.** Read-only `git log origin/main..main`
returned **empty**: local `main` is at `414f02c` (session #8) and NOT ahead of origin — so every
#5–#8 commit (item 12 retire-voice, item 13 meeting-writes-off-vault, Today-tab restyle, global
voice brain-dump) is **already pushed**. Nothing outstanding to push. The only remaining item-3
action is the **one-time VPS migration copy** (session #6, still run-once on the VPS) — re-printed
for Fadi below.
- **Mount-artifact warning (not a real change):** the bash mount served a TRUNCATED `server.py`
  (cut at ~L4472), so `git diff` in-session falsely showed "114 deletions." Verified with the
  authoritative Read tool that server.py continues intact past L4472 — this is exactly the
  stale/truncated C:\Dev mount the rules warn about, NOT a real uncommitted change. Fadi's working
  tree is fine; **do not commit any such phantom deletion.** (`?? brain_v2_check.py` is a stray
  untracked local file, harmless.)

**Not touched:** all code (analysis-only pass); items 4–8 (gated); the Productivity Hub build
(gated on 1a sign-off above).

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status   # expect "up to date with origin/main"; if it shows server.py modified with a
             # ~114-line DELETION, that's the mount phantom — do NOT commit it, discard with:
             #   git checkout -- server.py
git add NEXT-SESSION-UI.md
git commit -m "Session #9 (scheduled, analysis-only): Productivity Hub v1 architecture ruling (capture inbox = DATA_DIR triage buffer, approved pending Fadi sign-off), Caddy HTTPS prep (blocked on domain), git push audit (all #5-#8 already on origin), mount-truncation phantom flagged"
git push origin main
```

### VPS — one-time migration, still outstanding from session #6 (run ON the VPS; sessions can't reach it):

```
# Copy any already-captured ad-hoc meeting data out of the stranded pull-only mirror
# into the dashboard's real write lane. Guarded + idempotent (cp -n) — safe even if nothing
# was captured. NO deletion here (close-out sweep's job).
mkdir -p /root/life-os-data
if [ -f /root/second-brain/.meeting_store.json ]; then
  cp -n /root/second-brain/.meeting_store.json /root/life-os-data/.meeting_store.json && echo "copied .meeting_store.json"
fi
if [ -d /root/second-brain/30_Meetings ]; then
  mkdir -p /root/life-os-data/30_Meetings
  cp -rn /root/second-brain/30_Meetings/. /root/life-os-data/30_Meetings/ && echo "copied 30_Meetings/"
fi
```

## 2026-07-11 session #8 (Opus, life-os-dashboard session) — Global voice brain-dump → tasks (Fadi request, not a queue item)

Fadi request (outside the queue): "can the quick capture button everywhere have a voice input
option for brain dumps, then summarize and change into tasks." Chose flow = **review, then
create** (MC question, recommended option). Not a queue item; items 4–8 untouched.

**Probe first (Read/Grep):** found the plumbing already mostly exists, just unwired —
- Global capture already runs on every page: `QuickCapture` in `shared.js` (the `+` FAB / Ctrl+N)
  — but text-only, saved to `localStorage['fb-captures']`, no voice, no tasks.
- Voice already works: the Today capture hits `POST /api/transcribe` (local Whisper) — that mic
  just wasn't on the global FAB.
- Task creation already works: kanban cards are created by `POST /api/task` → `_handle_task_save`
  → upsert to `DATA_DIR/.kanban_store.json`. Card shape: `{id,title,description,priority,tag,
  column,source,created}`; columns `backlog/progress/review/done`; tags `project/fieldbridge/
  career/trading/personal/urgent`.
- Summarize-into-structure already works: the meeting processor's `_generate_summary` Hermes
  pattern (`HERMES_CHAT_PROXY_URL` + `Bearer life-os-dashboard-2026`, model gemma-2.5-flash).
So the build was three wires, no new architecture: mic on the global FAB, an extract endpoint,
and a review step that reuses the existing `/api/task` write path.

**Built:**
- `server.py` — new `POST /api/braindump` (`_handle_braindump`, wired in `do_POST` next to
  `/api/task`). Takes `{text}`, calls Hermes with a constrained prompt, returns
  `{tasks:[{title,tag,priority}], available}`. Defensive: strips ``` fences, coerces any tag
  outside the 6-tag set → `project`, any priority outside high/medium/low → `medium`, drops empty
  titles, returns `available:false` with an honest error on unparseable output. **Read/compute
  only — it does NOT write any store**; the front-end creates the approved cards via the existing
  `/api/task` lane. No new data store, no new writer lane (STANDARD respected — reuses the kanban
  DATA_DIR lane).
- `shared.js` — upgraded the global `QuickCapture` modal (so this works on EVERY page, not just
  Today): (1) a **Speak** mic button — MediaRecorder → `/api/transcribe` → appends the transcript
  to the textarea (borrowed from the Today capture's proven pattern; idle/recording/busy states).
  (2) a **Summarize into tasks** button → `POST /api/braindump` → renders a **review panel**: one
  row per extracted task with a checkbox (checked), an editable title input, a tag `<select>`, and
  a remove ✕. (3) **Add to board** → for each checked row, `POST /api/task` as a card in the
  `backlog` column, `source:'Brain dump'`, carrying the Hermes-suggested priority; toast with the
  count; refreshes the board via `loadTasks()` if we're on kanban. Kept **Save to Inbox** intact
  (still `localStorage['fb-captures']`). Nothing hits the board without an explicit click.
- `shared.css` — mic recording-state style (`.cap-mic.recording`, pulse) + the review-panel styles
  (`.capture-review*` rows, tag select, add button) using existing shared tokens.
- Did not touch tool roles / writer lanes / data stores — the only write is via the pre-existing
  `/api/task` endpoint into the existing kanban store; `/api/braindump` is compute-only.

**Note — capture fragmentation (not fixed this pass, worth a future cleanup):** there are still
two capture surfaces with two different localStorage inboxes — the global FAB (`fb-captures`) and
the Today-tab capture (`cmd-inbox`). This pass added voice+tasks to the global FAB only. A later
pass could consolidate the Today capture onto the same `QuickCapture` so there's one inbox and one
voice/brain-dump path. Flagging, not doing (out of this request's scope).

**Verification (Read/Grep + sandbox, never bash-edit on C:\Dev):**
- `shared.js`: copied from the mount, `node --check` → `SHAREDJS_SYNTAX_OK`; mount fresh (7 hits
  for the new methods/endpoint).
- `server.py`: full-file `py_compile` on the bash mount FAILED with a truncated-file IndentationError
  at L4474 — but the Read tool shows that exact line well-formed with content continuing past it, so
  it's the **documented stale/truncated-mount gotcha**, not a real error (the mount serves a cut-off
  copy after file-tool edits). Verified the real change instead: extracted `_handle_braindump` into
  a dummy-class scratch and ran it — `PY_SYNTAX_OK` AND a behavior test passed (fenced JSON parsed;
  bad tag `nonsense`→`project`; bad priority `urgent`→`medium`; empty title dropped). The route add
  is a one-line `elif`; the file was valid pre-edit.
- NUL scan (python `bytes.count`) on all three touched files → 0 / 0 / 0.
- **Not eyeballed live** — after deploy, Fadi: open any page, click the `+` (or Ctrl+N), hit
  **Speak** and talk a brain dump (or type one), click **Summarize into tasks**, confirm the review
  rows appear, uncheck/edit a couple, click **Add to board**, then open Kanban and confirm the new
  cards are in Backlog tagged as expected. Also confirm plain **Save to Inbox** still works. One
  live dependency to watch: `/api/transcribe` (Whisper) and Hermes must be up on the VPS — if either
  is down the UI shows an honest toast/empty-state rather than fabricating tasks.

**Not touched:** items 4–8 (gated), the Today-tab `cmd-inbox` capture (fragmentation noted above),
any server data store / writer lane (none changed — braindump is compute-only, tasks use the
existing `/api/task` lane).

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add server.py shared.js shared.css NEXT-SESSION-UI.md
git commit -m "Global voice brain-dump -> tasks: add Speak mic (->/api/transcribe) and Summarize-into-tasks to the everywhere QuickCapture modal (shared.js/css); new compute-only POST /api/braindump (server.py) extracts discrete tasks via Hermes with tag/priority coercion; review panel lets you edit/uncheck before Add-to-board creates kanban cards in Backlog via the existing /api/task lane (no new store/writer). Save-to-Inbox unchanged"
git push origin main
# auto-pull deploys within ~1 min — open any page, hit + (or Ctrl+N), Speak or type a brain dump,
# Summarize into tasks, review, Add to board, then check Kanban Backlog for the new cards.
```

## 2026-07-11 session #7 (Opus, life-os-dashboard session) — Today tab task-card restyle (Fadi request, not a queue item)

Out-of-band UI request from Fadi (outside the queue): "the font and the card style on the Today
tab don't look as presentable as the kanban card tab." Not a queue item; items 4–8 untouched.

**Diagnosis (Read only):** `dashboard.html`'s Today data cards rendered their items as flat
`.hub-row` list rows — a tiny 8px dot + oversized 18px text + plain grey `.r-meta` text for the
tag. `kanban.html`'s `.card` is a contained mini-card: darker surface, 1px border, 10px radius,
a 3px colored priority spine (`::before`), 14px/600 title, hover-lift, and filled uppercase pill
tags (`.card-tag` + `.tag-*`). That whole gap was the "not presentable" complaint.

**Decision (asked Fadi, one MC question):** scope = **task cards only** — apply the kanban card
language to the four task-like cards (Due Today / In progress / High signals / Open wagers) and
**leave Power 3 as its numbered 1-2-3 list** (a deliberately distinct pattern). Confirmed live via
a before/after mockup in the true blueprint-theme colors before touching code.

**Built (dashboard.html only — client-side render + CSS, no server/response/data change):**
- New `.hub-tcard` CSS block (mirrors kanban `.card`): `background: var(--bg-primary)` (the darker
  page surface, same trick as `.hub-launch-btn`), `1px solid var(--border-primary)`, 10px radius,
  `::before` 3px spine, hover border-accent + `translateY(-1px)` + accent shadow. Spine modifiers:
  `.sp-due` (status-stale), `.sp-overdue` (status-failed), `.sp-wip` (accent-2), `.sp-fieldbridge`
  (area-fieldbridge), `.sp-trading` (area-trading). Title `.hub-tcard-title` 14px/600. Pill classes
  `.hub-tag` + `.tg-<area>` colored from the SHARED `--area-*` / `--area-*-bg` tokens
  (fieldbridge/career/construction/trading/health/family/knowledge, admin as neutral default) so
  Today pills match CRM/kanban/graph area colors and auto-adapt across all three themes; plus
  `.tg-overdue` and a muted `.hub-tag-muted` for non-tag meta (signal action text, wager age).
- Two JS helpers: `tagPill(tag)` (slugs the tag, maps to `tg-<area>` only if it's a known area,
  else neutral pill — escapes the label) and `tcard(spineCls, title, metaHtml)` (escapes title,
  omits the meta row entirely when empty so there's no dangling gap).
- Rewrote `renderDue` / `renderSignals` / `renderWip` / `renderWagers` to emit `tcard(...)` instead
  of `.hub-row`. Info parity kept: Due shows tag pill + overdue pill; WIP shows tag pill; Signals
  shows the fieldbridge spine + action as muted meta; Wagers shows the trading spine + "Nd open"
  muted meta. `renderPower3` untouched (still `.hub-row` + `.r-num`).
- `.hub-row` CSS retained (Power 3 still uses it); the now-unused `.r-dot.due/.overdue` rules left
  as harmless dead CSS (tight diff, no behavior change).
- Did not touch tool roles / writer lanes / data stores — pure front-end rendering against the
  existing `/api/today` payload; no endpoint, no write path changed.

**Verification (Read/Grep + sandbox, never bash-edit on C:\Dev):**
- Bash mount FRESH this pass — grep confirmed 11 `hub-tcard` refs, 4 `tcard(` call sites, both
  helpers present. Extracted the main `<script>` block to `/tmp` and `node --check` → `JS_SYNTAX_OK`.
- NUL scan: ripgrep `\x00` → 0 matches; python `bytes.count(b'\x00')` → 0. (Note: a bash
  `grep -c $'\x00'` false-positived at 428 = the file's line count, because bash can't hold a NUL
  in `$'\x00'` so the pattern degrades to empty/match-all — use ripgrep or python for NUL scans,
  not bash `grep`, on this repo. Adds to the standing verification-gotcha notes.)
- Grep confirmed the only remaining `.hub-row` render is Power 3 (intended).
- **Not eyeballed live** — Fadi opens the Today home after deploy: confirm Due/WIP/Signals/Wagers
  render as mini-cards with a colored left spine + pill tags matching the kanban board, hover lifts
  them, and Power 3 still shows the 1-2-3 numbered list. Spine/pill palette is easy to re-tune if
  he wants Due colored by area instead of by due/overdue status.

**Not touched:** items 4–8 (gated), item 13 (shipped session #6 above), any server/data change.

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add dashboard.html NEXT-SESSION-UI.md
git commit -m "Today tab: restyle Due/WIP/Signals/Wagers as kanban-matched task cards (contained card + colored priority spine + 14px title + area-tinted pill tags from shared --area-* tokens, hover-lift), replacing the flat 18px dot-rows; Power 3 left as the numbered list"
git push origin main
# auto-pull deploys within ~1 min — open the Today home, confirm the four data cards now render as
# mini-cards matching the Kanban board and Power 3 still shows the 1-2-3 numbered list.
```

## 2026-07-11 session #6 (Opus, life-os-dashboard session) — Move meeting writes off the vault (item 13)

Executed queue item 13 only, per session instruction. The architect's RULING above item 13
(Fable, 2026-07-12) explicitly APPROVED execution as specced with three execution notes and
stated "Any Sonnet session may now execute this" — so the STOP-and-flag writer-lane gate was
already cleared by the architect; this pass is authorized execution, not a blind design change.
Did not touch any gated item (4–8).

**Probe first (Read/Grep, never bash on C:\Dev):** grepped every `meeting_store` / `30_Meetings`
/ `meetings` reference in `server.py`. The item's line estimates had drifted; the real write
surface is larger than the two sites it named:
- `.meeting_store.json` — **8** sites (read in `_serve_meetings_get`; read+write across
  `_handle_meeting_upload` / `_confirm` / `_start_recording` / `_stop_recording` / `_regenerate_brief`
  / `_handle_meeting_process` / `_handle_meeting_file_upload`), all `VAULT_DIR / ".meeting_store.json"`.
- `30_Meetings/<id>/*.md` — **1** site (`_handle_meeting_process`, transcript/summary/action-items/
  coverage `.md` files).
- `temp_uploads/` audio+doc scratch — **3** sites (two audio process handlers + the doc file-upload
  handler), also written into `VAULT_DIR` — same pull-only-mirror data-loss class, so moved too.
Confirmed via full-file grep that **no other reader anywhere in `server.py` reads any of these
paths** — the only consumer is `_serve_meetings_get` (`.meeting_store.json`), which was moved in
lockstep. The nightly Fireflies→vault sync is Cowork-side against the REAL vault, not this VPS
pull-only mirror, so it does not depend on the server's mirror writes (GATE satisfied).

**Built (server.py only — mechanical constant redirect, no logic/response-shape change):**
- All `VAULT_DIR / ".meeting_store.json"` → `DATA_DIR / ".meeting_store.json"` (8 sites).
- `VAULT_DIR / "30_Meetings"` → `DATA_DIR / "30_Meetings"` (1 site).
- `VAULT_DIR / "temp_uploads"` → `DATA_DIR / "temp_uploads"` (3 sites).
- `DATA_DIR` is the dashboard's existing own write lane (`/root/life-os-data`, same class as
  `.skill_usage.json` / `.kanban_store.json` / `playbook-usage.jsonl`), `.mkdir(exist_ok=True)` at
  module load — so no new data store was introduced; the writes just stop landing in the pull-only
  vault mirror where they were silently stranded.
- **Note 2 honored — response shapes byte-identical.** Only the path constant changed. The
  `_handle_meeting_process` response still returns a `vault_path` key (now a DATA_DIR path); the key
  NAME was deliberately left as-is to preserve the exact response contract per the ruling, even
  though it's now a mild misnomer. Every `_json_response({...})` body is otherwise untouched.

**Note 1 — VPS migration (sessions can't reach the VPS; command for Fadi/Hermes below).** The
old server wrote ad-hoc meetings into `VAULT_DIR` on the VPS. Because the mirror is pull-only,
anything there is stranded, but any real ad-hoc meeting content already captured should be
copied once into `DATA_DIR` so the moved read path still sees it. Copy-only, guarded, idempotent
(`cp -n`) — no deletion of vault content in this command (that's the close-out sweep's job, and
`30_Meetings/` in the real vault may legitimately hold Fireflies-synced content that a blind `rm`
must not touch). See the VPS block in the Git section below.

**Note 3 — close-out sweep.** There is no single formal "close-out sweep list" file in the repo
(the sweep is tracked as a concept — dead files like `tasks.html` / `voice.html`). Recording the
addition here so the next sweep picks it up: **after this move, `VAULT_DIR/30_Meetings/`,
`VAULT_DIR/.meeting_store.json`, and `VAULT_DIR/temp_uploads/` must never be recreated by the
dashboard** — the server no longer writes them; if they reappear on the VPS mirror they are stale
and should be removed during the close-out sweep (checking first that `30_Meetings/` doesn't hold
git-tracked Fireflies vault content).

**Verification (Read/Grep + sandbox py_compile — never bash-edit on C:\Dev):**
- Post-edit grep of `server.py`: **0** remaining `VAULT_DIR /` references to `.meeting_store.json`
  / `30_Meetings` / `temp_uploads`; DATA_DIR counts confirmed 8 / 1 / 3.
- Bash mount was FRESH this pass (grep of the mounted `server.py` showed the new DATA_DIR refs and
  zero old VAULT_DIR meeting refs) — copied to `/tmp` and `python3 py_compile(doraise=True)` →
  `PY_SYNTAX_OK`.
- `server.py` NUL-scanned via Grep — clean (0).
- **Not eyeballed live** — after deploy + the VPS migration command, Fadi opens meetings.html,
  Ad-hoc tab, processes a short audio, and confirms the working copy still renders (proving the
  moved read/write round-trips through DATA_DIR), then confirms `git status` on the VPS vault
  mirror no longer shows new `30_Meetings/` or `.meeting_store.json` churn after processing.

**Not touched:** items 4–8 (gated), any response-shape/tool-role change (none — pure write-lane
relocation on the already-approved item), `voice.html` / `voice-chat.js`.

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add server.py NEXT-SESSION-UI.md
git commit -m "Item 13 — move /api/meetings writes off the pull-only vault mirror into DATA_DIR: all .meeting_store.json (8 sites), 30_Meetings/<id>/*.md, and temp_uploads/ scratch (3 sites) now write to DATA_DIR (dashboard's own lane, same class as .skill_usage.json), _serve_meetings_get reads from there; response shapes byte-identical (vault_path key name kept per architect note 2). Closes the silent-data-loss lane violation flagged in item 13"
git push origin main
# auto-pull deploys within ~1 min
```

### VPS — one-time migration (run ON the VPS; sessions can't reach it):

```
# Copy any already-captured ad-hoc meeting data out of the stranded pull-only mirror
# into the dashboard's real write lane. Guarded + idempotent (cp -n) — safe to run even
# if nothing was ever captured (the guards just skip). NO deletion here (see close-out sweep).
mkdir -p /root/life-os-data
if [ -f /root/second-brain/.meeting_store.json ]; then
  cp -n /root/second-brain/.meeting_store.json /root/life-os-data/.meeting_store.json && echo "copied .meeting_store.json"
fi
if [ -d /root/second-brain/30_Meetings ]; then
  mkdir -p /root/life-os-data/30_Meetings
  cp -rn /root/second-brain/30_Meetings/. /root/life-os-data/30_Meetings/ && echo "copied 30_Meetings/"
fi
# (temp_uploads is disposable scratch — nothing to migrate.)
```

## 2026-07-11 session #5 (Opus, life-os-dashboard session) — Retire Voice + Meeting Workbench (item 12)

Executed queue item 12 only, both parts (a) + (b), per session instruction. Did not touch any
gated item (4–8). Session opened against `C:\Dev\life-os-dashboard` directly (not the Second Brain
folder) so the queue file and repo were reachable — the earlier scope-boundary block was because
this repo wasn't mounted.

**Conflict surfaced + resolved before shipping (Option A, Fadi's call):** item 12b says KEEP
`/api/meetings/process` AND its banner says "working copies only (DATA_DIR lane) / NO vault writes."
But probing `server.py` showed that endpoint writes INTO the vault (`VAULT_DIR/30_Meetings/<id>/*.md`
+ `VAULT_DIR/.meeting_store.json`). Shipping the dictated banner verbatim would have been a false
claim, and silently moving the write lane would violate the session's own STOP rule. Asked Fadi;
he chose "ship now, reword banner to the truth, log the write-lane fix as a flagged item" → new
item 13 above. No writer-lane/data-store change was made this pass.

**12(a) — voice.html retired from nav (not deleted):**
- `index.html` — removed the `data-page="voice"` sidebar button (was between Meetings and Browser).
- `shared.js` — removed the `'voice': 'voice.html'` line from BOTH `moduleFiles` maps (the
  `navigateTo` map and the `loadModule` map). Left `voice-chat.js` untouched, left `voice.html`
  itself on disk (dead file until the close-out sweep, like tasks.html), and deliberately left the
  unrelated `VoiceMemo` object + the `voice`/`voiceBtn` i18n strings in shared.js alone — the spec
  scoped 12a to the nav button + the two moduleFiles entries only.

**12(b) — meetings.html rebuilt as "Meeting Workbench":**
- Title "Meeting Assistant" → "Meeting Workbench" (page `<title>` + `<h1>`).
- Role banner added, worded truthfully (Option A): states Fireflies meetings auto-flow to the vault
  via the nightly and must not be duplicated here; this page is for what Fireflies misses (phone
  calls, WhatsApp voice notes, site conversations) + pre-call prep; and that **nothing done in the
  browser writes to the vault** — the honest claim, since the browser genuinely never writes (the
  server-side save is what item 13 will relocate).
- **Prep brief** (new): prospect `<select>` populated from `/api/wiki/crm` (the folder `index.md`
  is filtered out client-side). Selecting one renders a one-screen brief — stage + geo chips, and
  Pain / Last interaction / Next step / Status fields, each with an honest "Not recorded in the CRM
  note." fallback when the source note lacks that field. "Open in Hermes" builds a prep prompt and
  hands off via `sessionStorage['hermes-prefill']` → `chat.html` (identical pattern to fitness.html
  / use-cases.html / graph3d.html). Plus a "Copy brief" convenience button.
- **Ad-hoc transcript** (kept): the audio upload → `POST /api/meetings/process` flow is retained
  as-is (drag-drop + click), results rendered via the existing `GET /api/meetings` read. Dropped
  the old in-meeting "assistant" machinery (Upload-Agenda/`/api/meetings` brief, the mock Record
  button + recording timer, Coverage tracker, Live Agenda Check) — that was the retired role and,
  like voice.html, the Record path was a mock. Added the spec's **"Copy for Cowork"** button:
  builds a markdown block (decisions / discussion / conclusion / next steps / action items + a CRM-
  impact stub) and copies it with a toast telling Fadi to paste into Cowork so the vault's real
  writer records it. No write endpoint was added — clipboard + toast only, per spec.
- meetings.html now loads `shared.js` (it didn't before) so `Notify` + `copyToClipboard` and the
  standard nav drawer are available — matches every other standalone page.

**Server (read-only, for the prep brief):** `_serve_crm_snapshot` (`GET /api/wiki/crm`) enriched to
also return `name, role, geo, status, type, next, next_date, pain, last_interaction`. The original
five keys (`company, stage, trade, region, path`) are byte-for-byte unchanged so `crm.html`'s
contract is untouched. `pain` and `last_interaction` are parsed from the note body by two new
`@staticmethod` helpers (`_extract_crm_pain` prefers a `## Pain…` section, falls back to an inline
`**Pain:**` clause; `_extract_crm_last_interaction` takes the last row of the `## Interaction Log`
table). Both return `''` honestly when the note lacks the field. This is a read-only projection
enrichment (same lane, same store) — NOT a tool-role/writer-lane/data-store change.

**Verification (Read/Grep + sandbox, never bash on C:\Dev — standing staleness gotcha):**
- meetings.html `<script>` copied to `/tmp` and `node --check` → `MEETINGS_JS_SYNTAX_OK`.
- server.py additions copied to `/tmp` and `python3 -m py_compile` → `PY_SYNTAX_OK`; the two
  parsers were then run against the REAL vault CRM notes: pain + last-interaction extracted
  correctly for Atef / Bassam / Brett / Michael, honest empty for Karim / Ramy (no `## Pain`
  section), and `index.md` → all-empty (filtered from the dropdown). Enriched method re-read in
  server.py to confirm decorators/indentation are well-formed.
- All four touched files (index.html, shared.js, server.py, meetings.html) NUL-scanned via Grep —
  clean. Confirmed 0 remaining `data-page="voice"` / `'voice': 'voice.html'`, and VoiceMemo/i18n
  left intact (3 expected matches).
- **Not eyeballed live** — Fadi walks meetings.html after deploy: Prep-brief tab, pick a prospect,
  confirm the brief fills from CRM and "Open in Hermes" lands on chat.html with the prep prompt
  prefilled; Ad-hoc tab, process a short audio, confirm the working copy renders and "Copy for
  Cowork" copies the markdown + shows the toast; and confirm the Voice item is gone from the
  sidebar. Also confirm `/api/wiki/crm` still renders crm.html unchanged (added keys are additive).

**Not touched:** items 4–8 (gated), item 13 (newly flagged — architecture decision, not this pass),
`voice.html` / `voice-chat.js` (per spec), the `/api/meetings*` write behavior (kept, flagged).

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add index.html shared.js server.py meetings.html NEXT-SESSION-UI.md
git commit -m "Item 12 — retire Voice from nav (index.html + both shared.js moduleFiles maps; voice.html/voice-chat.js left on disk) and rebuild meetings.html as Meeting Workbench: truthful role banner, Prep-brief (prospect dropdown from /api/wiki/crm -> one-screen brief -> Open in Hermes prefill), kept /api/meetings/process ad-hoc transcript flow with a Copy-for-Cowork button (clipboard+toast, no vault write, no new endpoint); enrich GET /api/wiki/crm read-only with name/role/geo/status/next/pain/last_interaction (original 5 keys unchanged). Flagged item 13: move /api/meetings/process writes off the vault into DATA_DIR under architecture review"
git push origin main
# auto-pull deploys within ~1 min — open meetings.html: title reads "Meeting Workbench", Prep-brief
# tab lists your CRM prospects, picking one fills the brief and "Open in Hermes" prefills chat;
# Ad-hoc tab still processes audio and now shows "Copy for Cowork". Confirm the Voice button is gone
# from the home sidebar, and that crm.html still renders unchanged.
```

## 2026-07-11 session #4 (Sonnet, Second Brain project) — Saved Prompts tab upgrade (item 11)

Executed queue item 11 only, per session instruction. Did not touch items 4–8 (still gated).

**Probe first:** read `use-cases.html` in full (260 lines — small enough for one Read) to find
the existing Playbook/Saved-Prompts render functions and area-color helpers, then read
`server.py`'s `_handle_extract_prompts`/`_serve_prompts_library` to see the actual shape of
`/api/wiki/prompts` data. Found candidates carry only `{text, source_session, source_title}` —
no dedicated capture timestamp field. Item 11(a) says "date from the extraction data **if
present**" and the item's own build note says dashboard-side only — so no `server.py` change to
add a real timestamp field. Instead: `server.py`'s chat-session save path (`_handle_chat_sessions`
area, ~line 3573) defaults `session_id` to `sess_YYYYMMDDHHMMSSffffff` when chat.html doesn't
supply one, and `source_session` is exactly that session id — so the capture time is already
latently present in the existing data for sessions that used the fallback id shape. Also checked
`shared.js` for existing reusable primitives before building new ones: found `copyToClipboard(text)`
(already used elsewhere, wraps `navigator.clipboard` + the `Notify` toast system) and confirmed
`assets/lucide-sprite.svg` has `icon-copy` and `icon-rocket` symbols.

**Built (use-cases.html only — dashboard-side, no backend/vault change, per the item's own scope):**
- (a) New `parseCapturedDate(sourceSession)` — regexes the `sess_<14-digit>` prefix out of
  `source_session` and parses it into a `Date`; returns `null` if the session id doesn't match that
  shape (older/irregular ids), so the UI only shows a captured date "if present" instead of
  fabricating one. `renderPrompts()` now sorts newest-first by that parsed date, with
  undated entries sorted to the end (stable, no crash on a fully-undated list). Cards with a
  parseable date show a muted "captured Xh/d ago" line (reuses the existing `timeAgo()` helper
  already used by the Playbook tab, avoids adding a second date-formatting function).
- (a) Copy button — reuses `shared.js`'s existing `copyToClipboard()` (already wired to the
  `Notify` toast system as "Copied to clipboard!"), so no new clipboard/toast plumbing needed for
  this one.
- (b) "Promote to Playbook" button — new `promoteToPlaybook(text)`: writes to clipboard directly
  (separate from `copyToClipboard()` because the toast copy is different) and shows
  `Notify.success('Copied — paste into any Cowork session and say "add this to the playbook as a
  play"', 6000)` — the exact wording from the spec, longer 6s duration since it's a longer message.
  **No backend call at all** — confirmed no new endpoint was added anywhere in `server.py`, matching
  "Do NOT build a write endpoint for this."
- (c) New `#playbook-filters` chip row above the Playbook tab's card grid. `renderPlaybookFilters()`
  builds an "All" chip plus one chip per area actually present in the live data (skips areas with
  zero plays — no empty chips), using `areaColorVar()` (already existed, reused as-is) for
  per-chip color via the shared `--area-*` tokens. Chip row hides itself entirely if fewer than 2
  areas are present (not worth filtering a single-area list). `setAreaFilter()` re-renders both the
  chip row (for the active state) and the card grid. `renderPlaybook()` now filters by
  `activeAreaFilter` before the existing tier/area grouping loop — tier grouping within the
  filtered view is unchanged, per spec. Added a filter-aware empty state ("No plays yet in
  <Area>.") distinct from the original all-plays empty state.
- (d) Trivial, so done: `renderPlaybook()`'s per-area play list now sorts by `run_count` (desc)
  before rendering, so earned/used plays float to the top of their area/tier group.
- Did not touch tool roles / writer lanes / data stores — every change is client-side rendering
  logic in `use-cases.html` against data already served by the existing `/api/playbook` and
  `/api/wiki/prompts` endpoints; no new endpoint, no new write path, no vault write.

**Verification done (Read/Grep only, not bash — standing gotcha for this repo):**
- Full `use-cases.html` re-read via Read tool after all edits — well-formed HTML, tags balanced,
  new `<div>`/`<button>` blocks all properly closed.
- Full `<script>` block copied to the sandbox outputs folder (functionally identical, cosmetic-only
  string trims to sidestep heredoc/emoji quoting) and run through `node --check` — `SYNTAX_OK`.
- NUL-scanned the whole file via Grep — clean, 0 matches.
- **Not eyeballed live** — Fadi opens `use-cases.html` after deploy: Saved Prompts tab shows Copy +
  Promote buttons on every card, newest-captured prompts (if any have a `sess_<timestamp>` sourced
  id) sort first with a "captured X ago" line, clicking Promote copies the prompt and shows the
  exact toast wording; Playbook tab shows area filter chips above the grid, clicking one narrows
  the grid to that area only, and within any area/tier group the most-used plays now appear first.

**Not touched:** items 4–8 (still gated), any tool-role/writer-lane/data-store change (none —
pure front-end rendering against existing read-only endpoints).

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add use-cases.html NEXT-SESSION-UI.md
git commit -m "Saved Prompts tab upgrade (item 11): Copy + Promote-to-Playbook buttons per card (promote is clipboard+toast only, no vault write, no new endpoint), captured-date parsing from sess_<timestamp> session ids with newest-first sort; Playbook tab gets an area filter chip row (--area-* colors, hides itself under 2 areas) and within-area sort by run_count desc"
git push origin main
# auto-pull deploys within ~1 min — open use-cases.html, Saved Prompts tab: confirm Copy button
# copies the prompt text, Promote button copies + shows the "paste into any Cowork session..."
# toast, and any prompt with a sess_<timestamp>-shaped source shows "captured X ago" with newest
# first. Then check the Playbook tab: confirm area filter chips appear above the grid, clicking
# one narrows to that area, and a play with run_count > 0 sits above lower-usage plays in the
# same area.
```

## 2026-07-11 session #3 (Sonnet, Second Brain project) — Chat default model kept drifting (bug fix, not a queue item)

Fadi flagged (outside the queue): "why does the default model keep changing... we said we
will lock it to nemotron... why does the model selection in chat not persist." Investigated
and found three independent, compounding bugs in chat.html + model-catalog.js:

1. **`setModel()` never persisted anything.** Picking a model in the chat toolbar dropdown only
   set the in-memory `currentModel` JS variable for that page view — it never wrote to
   `localStorage`. Reload chat.html (or navigate away and back) and the pick was gone.
2. **The silent fallback wasn't actually Nemotron.** `loadChatModels()` derived its computed
   default from the `'everyday'` job category's `rec` pick in `model-catalog.js` — which is
   **Claude Haiku**, a legitimate recommendation for admin writing on models.html, but never
   the model anyone decided should be the chat page's silent default. The actual "lock to
   Nemotron" decision was already recorded in the file — under the `'agent'` job's `rec` pick,
   with a 2026-07-10 comment saying so — but chat.html was reading the wrong job entry.
3. **Even the correct pick would have failed to resolve.** All 4 occurrences of the nemotron
   `match` fragment across `model-catalog.js` were `'nemotron-3-ultra-550b:free'` — stale. The
   real live/fallback model id (confirmed against `server.py`'s `_FALLBACK_MODELS` and
   `_call_hermes`'s own default) is `'nvidia/nemotron-3-ultra-550b-a55b:free'` — note the
   `-a55b` segment sitting between `550b` and `:free`. `lifeosResolvePick()`'s substring match
   never found the stale fragment inside the real id, so every nemotron pick, in every job
   category, silently resolved to `null` and fell through to whatever `models[0]` happened to
   be that day — an arbitrary, unstable pick from the live OpenRouter response. Verified with a
   standalone repro: old fragment → `null`, fixed fragment → the real id.

**Built:**
- `chat.html` — `setModel()` now calls `window.lifeosSetDefaultModel(model)` on every change,
  writing to the same `localStorage['lifeos-default-model']` key models.html's "Set default"
  button already uses, so a pick made in either page sticks everywhere.
- `chat.html` — `loadChatModels()`'s locked-default computation now reads the `'agent'` job's
  `rec` pick (Nemotron, already correctly documented there) instead of `'everyday'`'s. Priority
  order is unchanged in spirit: an explicit saved choice (`lifeos-default-model`) still wins if
  it's live-resolvable, then the locked Nemotron default, then `models[0]`, then the hardcoded
  literal string as a last resort.
- `model-catalog.js` — fixed all 4 stale `'nemotron-3-ultra-550b:free'` match fragments to
  `'nemotron-3-ultra-550b'` (drops the trailing `:free`, which IS a valid contiguous substring
  of the real id). Added a dated header comment explaining the fix for future sessions, per the
  file's own "verify match fragments resolve live" instruction.
- Did not touch tool roles / writer lanes / data stores — this is a client-side persistence +
  catalog-data fix, no new backend surface.

**Verification done (Read/Grep only, not bash — standing gotcha for this repo):**
- Standalone repro of `lifeosResolvePick` against the real fallback model list (mirroring
  `server.py::_FALLBACK_MODELS`): old fragment → `null` (confirmed broken), fixed fragment →
  `nvidia/nemotron-3-ultra-550b-a55b:free` (confirmed fixed).
- Standalone repro of the `'agent'` job's `rec` pick resolving end-to-end against a fake live
  `/api/models` response — resolves to the correct nemotron id.
- Full `chat.html` `<script>` block (lines 1329–2401) re-read via Read tool, then copied to
  the sandbox outputs folder (with browser globals stubbed) and run through `node --check` —
  `SYNTAX_OK`. `model-catalog.js` re-read in full via Read tool (well-formed) and separately
  syntax-checked the same way — `SYNTAX_OK`.
- Both files NUL-scanned via Grep — clean.
- **Not eyeballed live** — Fadi picks a model in chat.html, reloads the page, and confirms it's
  still selected; then clears `localStorage['lifeos-default-model']` (or opens a private window)
  and confirms a fresh load lands on Nemotron 3 Ultra, not Claude Haiku or something else.

**Not touched:** the actual queue in this file (items 4–8 still gated, item 10 already shipped
in session #2 above) — this was an out-of-band bug report, not a queue item.

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add chat.html model-catalog.js NEXT-SESSION-UI.md
git commit -m "Fix chat default model drift: setModel() now persists to localStorage (was in-memory only), loadChatModels()'s locked default now reads the 'agent' job's rec pick (Nemotron, already documented there) instead of 'everyday' (Claude Haiku), and all 4 stale nemotron match fragments in model-catalog.js fixed to actually resolve against the real live/fallback model id"
git push origin main
# auto-pull deploys within ~1 min — open chat.html, pick a model, reload the page, confirm it
# stuck; then clear localStorage['lifeos-default-model'] and reload again, confirm it lands on
# Nemotron 3 Ultra by default.
```

## 2026-07-11 session #2 (Sonnet, Second Brain project) — Playbook goes live (item 10)

Executed queue item 10 only, per session instruction. Confirmed the vault push landed first
(`_system/playbook/*.md` — exactly 16 files, all `status: active`, none `retired`) before
touching the front-end, per the item's own gate.

**Probe first:** read `_serve_logs`/`_serve_arms`/`_serve_projects` in `server.py` for the
established pattern (defensive frontmatter parse off `VAULT_DIR`, never writes there; usage/
counters go to `DATA_DIR`, e.g. `.skill_usage.json`'s counts+last_used shape). Built
`/api/playbook` and `/api/playbook/run` to match.

**Built:**
- `server.py` — `_serve_playbook()`: `GET /api/playbook` reads `_system/playbook/*.md` from
  `VAULT_DIR`, reuses the existing `_parse_frontmatter` helper, skips `status: retired`, returns
  `{key, title, area, tier, status, prompt (=body), run_count, last_run}` per play. Merges usage
  from `DATA_DIR/playbook-usage.jsonl` (parsed defensively line-by-line, corrupt lines skipped,
  never 500s). `_handle_playbook_run()`: `POST /api/playbook/run {key}` appends one
  `{ts, key}` JSON line to that same file — dashboard's own data lane, never written into
  `VAULT_DIR` (Decision Gate 1 respected, same boundary as `.skill_usage.json`/`.kanban_store.json`).
  Wired into both dispatch tables (`_handle_api_get` GET route + 405 guard for the POST-only
  path; `do_POST` route for the actual handler).
- `use-cases.html` — deleted the hardcoded `PLAYBOOK` object entirely. `loadPlaybook()` fetches
  `/api/playbook` and `renderPlaybook()` groups live plays by `tier` (income/life, matching the
  old top-level structure) then by a fixed `area` display order, using `AREA_META` for label/
  sub-label only (no more hardcoded hex — colors are `var(--area-<area>)`, one of the 8 shared
  tokens already in `shared.css`, confirmed all 7 areas actually present in the vault files map
  cleanly: fieldbridge/career/construction/trading/health/family/knowledge). Each card shows
  title, first line of the vault prompt as the description, a muted "used N× · last X ago" line
  only when `run_count > 0`, and "▶ Run in Hermes" — which now both sets the existing
  `sessionStorage 'hermes-prefill'` handoff AND fires `POST /api/playbook/run` (fire-and-forget,
  `.catch(()=>{})`, never blocks the redirect to chat.html). Three honest states: HTTP-error
  (backend not deployed — explicit "returned {status}" message), 200-but-empty (no plays in the
  vault), and the real 16-play render. Saved Prompts tab untouched.
- Did not touch tool roles / writer lanes / data stores in a new way — `/api/playbook` is
  read-only against `VAULT_DIR` (existing pattern), `/api/playbook/run` writes only to
  `DATA_DIR`, the dashboard's pre-existing own lane (same class of write as `.skill_usage.json`).

**Verification done (bash mount of `C:\Dev\life-os-dashboard` not used for verification — Read/
Grep only, per the standing gotcha):**
- **Backend logic simulated against the REAL vault files** (not the VPS — network-unreachable
  from this sandbox, consistent with prior sessions): copied `_parse_frontmatter` +
  `_serve_playbook`'s exact logic into a sandbox scratch script pointed at the real
  `_system/playbook/` folder in the OneDrive-synced vault mirror. Result: **16/16 plays**, all
  with non-empty title/area/prompt, `tier` ∈ {income, life}, all 7 areas map to a known
  `--area-*` token (fieldbridge×5, career×2, construction×2, trading×2, health×2, family×1,
  knowledge×2 — 11 income / 5 life). Also simulated the usage-merge path with fake JSONL lines —
  `run_count`/`last_run` aggregate correctly per key, untouched plays stay at 0/null. This
  satisfies the item's own gate ("verify /api/playbook returns 16 plays... before wiring the
  front-end final pass") as rigorously as is possible without live VPS access.
- `server.py`: both new methods copied into a dummy-class scratch file (stubbed
  `_json_response`/`_json_error`/`self.headers`/`self.rfile` surface) and run directly —
  `SYNTAX_OK`, no exceptions. Dispatch-table edits re-read via the Read tool at both seams
  (GET `_handle_api_get`, POST `do_POST`) — correctly indented, no stray branches.
- `use-cases.html`: full file re-read via Read tool — well-formed HTML/CSS/JS, no stray tags.
  Full `<script>` block copied to the sandbox outputs folder and run through `node --check` —
  `SYNTAX_OK`.
- Both touched files (`server.py`, `use-cases.html`) NUL-scanned via Grep — clean.
- **Not eyeballed live** — Fadi opens `use-cases.html` after deploy and confirms: the Playbook
  tab renders 16 real cards grouped Income engines → FieldBridge/Career/Construction/Trading
  then Life and system → Health/Family/AI tools; clicking "Run in Hermes" lands on chat.html
  with the prompt prefilled; a second click on the same play later shows the "used N× · last X
  ago" line. Also worth testing the empty-state path once (e.g. temporarily rename the vault
  folder) to confirm the honest "backend not deployed" vs "no plays" messages render distinctly
  — not done here since it would require touching the live vault mirror.

**Not touched:** items 4–8 (still gated), item 9 (already shipped in the prior same-day
session), any tool-role/writer-lane/data-store change (this session's `/api/playbook/run` write
is the same existing DATA_DIR-write pattern already used by `.skill_usage.json` etc. — not new).

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add server.py use-cases.html NEXT-SESSION-UI.md
git commit -m "Playbook goes live (item 10): GET /api/playbook reads _system/playbook/*.md from the vault mirror (16 plays, defensive frontmatter parse, skips status:retired), POST /api/playbook/run logs usage to DATA_DIR/playbook-usage.jsonl; use-cases.html Playbook tab now renders live from the API (hardcoded PLAYBOOK object deleted) grouped by tier then area, area colors from shared --area-* tokens, run-count/last-run shown per play"
git push origin main
# auto-pull deploys within ~1 min — open use-cases.html, confirm 16 real cards render grouped
# Income engines (FieldBridge/Career/Construction/Trading) then Life and system
# (Health/Family/AI tools), click "Run in Hermes" on one, confirm it lands on chat.html with
# the prompt prefilled, then revisit the Playbook tab and confirm that card now shows
# "used 1× · last just now".
```

## 2026-07-11 session (Sonnet, Second Brain project) — Hermes Activity panel (9b, gate cleared)

Continuation of the same-day 9(a) session — Fadi sent the Telegram message from the write-up
below and Hermes confirmed back. Gate cleared, built same session.

**Hermes's confirmation (Telegram):** writes one JSON line per tool call to
`/root/.hermes/activity_log.md` (JSONL despite the `.md` extension — Hermes's own choice).
Append-only, always `patch`/`mode='replace'` targeting the end-of-file marker, never a
rewrite. Lives in Hermes's own fixed-profile filesystem (`~/.hermes/`) — no rotation needed;
Hermes's own estimate is ~200 bytes/turn, ~100KB/day worst case (500 turns/day). Sample lines
confirmed real, e.g. `{"ts": "2026-07-11T13:45:12.123Z", "action": "search_files", "detail":
"Searched fadi-vault for..."}`.

**Design question resolved before building the front-end (see AskUserQuestion in this
session):** the original queue wording ("activity panel under Hermes replies") implied a
per-message trace. But probing 9(a) already established that `server.py`'s `/api/chat` sends
Hermes's gateway a plain completion request with **no `tools` schema** — so a dashboard chat
reply structurally cannot itself trigger a tool call. `/root/.hermes/activity_log.md` is
Hermes's **global** trace across every channel it works in (Telegram, cron, etc.). Attaching
its tail under one specific chat reply would visually imply "this is what happened for your
message," which isn't true and would violate the "no fabricated traces" rule in spirit even
though the data itself is real. Asked Fadi; he picked **global toolbar toggle**, not
per-message.

**Built:**
- `server.py` — `HERMES_ACTIVITY_LOG = Path("/root/.hermes/activity_log.md")` constant
  (module-level, next to `HERMES_CHAT_PROXY_URL`) and new `_serve_hermes_activity(query)`:
  `GET /api/hermes/activity?tail=N` (N clamped 1–200, default 20). Reads the log directly
  (server.py already runs on the same VPS Hermes does), parses JSONL defensively (skips
  malformed/partial lines, never 500s), returns `{data, available, count}`. `available:false`
  (not just an empty array) when the file doesn't exist yet, so the front-end can render an
  honest "hasn't written a log yet" state instead of a bare empty list. Read-only — never
  writes to this path, respecting the two-agent single-writer-lane boundary (Hermes writes
  its own lane; this dashboard only reads it). Wired into the GET dispatch table next to
  `/api/hermes/morning-brief`.
- `chat.html` — new toolbar button "Hermes Activity" (wrench icon, next to Think), opening a
  slide-in panel reusing the existing `.artifacts-panel` chrome (`#hermesActivityPanel`,
  `toggleHermesActivity()` / `loadHermesActivityPanel()`). Fetches fresh every time it opens
  (never cached, never stale). Copy is explicit that this is global, cross-channel activity,
  not scoped to the current conversation — both in the toolbar button's title tooltip and the
  panel's subhead. Three honest states: log missing (`available:false`), log exists but empty,
  and real entries (newest first, timestamp + action + detail). New `.hermes-activity-row`
  CSS block (mono timestamp, bold action, muted detail) added near the 9(a) `.activity-*`
  rules.
- Did not touch tool roles / writer lanes / data stores — new endpoint is read-only against a
  path Hermes itself already owns and writes to; no new writer, no new data store on the
  dashboard side.

**Verification done (bash mount was stale again this session — including, newly, on the
sandbox `outputs` scratch folder itself for one Edit-tool write; retried under a fresh
filename and it checked out clean — worth noting as a slightly broader instance of the
existing gotcha, not just C:\Dev):**
- `server.py`: new constant + `_serve_hermes_activity` + dispatch wiring all read back clean
  via Read/Grep; copied into a dummy-class scratch file and ran `python3 -m py_compile` —
  `SYNTAX_OK`.
- `chat.html`: full `<script>` block (now ~1059 lines) re-read via Read tool and copied to a
  fresh outputs scratch file; `node --check` — `SYNTAX_OK`. New HTML (toolbar button + panel
  markup) and CSS block confirmed well-formed by direct read.
- Both files re-NUL-scanned via Grep — clean.
- **Not eyeballed live** — Fadi opens chat.html, clicks "Hermes Activity" in the toolbar,
  confirms real entries render (or an honest empty state if Hermes hasn't written anything
  since the confirmation message), and confirms the panel does NOT appear under any individual
  chat reply (by design).

**Not touched:** items 4–8 (still gated), item 10 (new Playbook item added to the queue after
9a shipped — out of scope for this pass, next session's to pick up).

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add server.py chat.html NEXT-SESSION-UI.md
git commit -m "Hermes Activity panel (9b): read-only GET /api/hermes/activity tails /root/.hermes/activity_log.md (Hermes's own JSONL lane, server.py already runs on the same VPS); chat.html gets a global toolbar toggle + slide-in panel, deliberately NOT per-message since dashboard chat can't itself trigger tool calls"
git push origin main
# auto-pull deploys within ~1 min — open chat.html, click "Hermes Activity" in the toolbar,
# confirm real entries render (or the honest empty state), confirm it's global (not attached
# to any single reply).
```

## 2026-07-10 session #2 (Sonnet, Second Brain project) — Chat activity trace (9a) + Hermes tool-trace ask (9b, gated)

Executed queue item 9(a) only, per session instruction. Did not touch item 9(b) beyond
drafting the Telegram message below — no dashboard endpoint/panel built for it.

**Probe first (before choosing SSE vs polling):** read chat.html's actual send path.
Found `chat_proxy.py` (port 8091, standalone OpenRouter proxy) is dead code — already
flagged deprecated in its own file header, not wired to anything. The real path is
`chat.html` → `fetch('/api/chat')` → `server.py`'s `_handle_chat_proxy` → a single
blocking `urlopen()` to Hermes's own gateway (`HERMES_CHAT_PROXY_URL`, :8642), timeout
150s, `stream:False`. Also found the "Searching vault…" / "Found N files" stages the
brief described are NOT server-side at all — `chat.html` already does its own KB search
client-side (`/api/kb/search`) *before* ever calling `/api/chat`. So the only genuinely
server-side stage is the Hermes round-trip itself, and `server.py` runs on
`ThreadingHTTPServer` (confirmed — each request gets its own thread), which makes a
held-open streaming response practical without touching any other request.

**Built (9a):**
- `server.py` — new `_handle_chat_proxy_stream_ui(model, messages, data)`, called from
  `_handle_chat_proxy` only when the POST body sets `stream_ui:true` (opt-in; default
  behavior for any other `/api/chat` caller is byte-for-byte unchanged). Sends
  `Content-Type: text/event-stream` immediately, then real events only — never
  fabricated: `connecting` → `asking` → a `waiting` heartbeat every real elapsed second
  while the actual Hermes call runs on a background thread (`threading.Thread`, already
  imported module-level) → `done` (carries Hermes's real parsed JSON reply) or `error`
  (carries the real HTTPError/URLError detail, same messages as the non-streaming path).
  Uses `Connection: close` instead of hand-rolled chunked framing — simplest way for
  `BaseHTTPRequestHandler` to push incremental writes that a browser's `fetch()`
  streaming reader picks up.
- `chat.html` — replaced `addTyping()`/`removeTyping()` (the plain 3-dot indicator) with
  `addActivity()`/`updateActivity()`/`removeActivity()`: a muted 12px mono status line
  (`.activity-trace`, new CSS block after `.typing-indicator`) that updates through the
  real stages — "Searching vault…" → "Found N files: <names>" (or "No relevant vault
  notes found.") → "Asking `<model>`…" → "Asking `<model>`… (Ns)" ticking → "Done.".
  `sendMessage()` now posts `stream_ui:true` and parses the SSE-lite stream itself
  (`resp.body.getReader()`, manual `data: {...}\n\n` framing — no library). On completion,
  `addMessage()` (new optional 3rd `activityLines` param) folds the captured stage log
  into a collapsed `▸ activity` toggle above the reply — click to expand, never shown
  expanded by default so it doesn't compete with the actual answer. Old `.typing-indicator`
  CSS rule is now unused dead code (left in place, harmless — not part of this task's scope
  to remove).
- No token-level model streaming — Hermes's own gateway call is still one blocking
  `stream:False` request. This only replaces the previous silent up-to-150s wait with a
  live, honest status line. A true token stream would need Hermes's gateway itself to
  support `stream:True` SSE passthrough — bigger change, not attempted tonight.
- Did not touch tool roles / writer lanes / data stores — this is a transport/presentation
  change on an existing proxy endpoint, opt-in via a new flag, backward compatible.

**Verification done (bash mount of this repo was confirmed stale again this session —
see below — verified via Read/Grep only, per the standing gotcha):**
- `server.py`: `bash`'s own `py_compile` on the live mount failed with a truncated file
  (cut off mid-line at `with open(tmp_p`, ~65 lines short of the real EOF) — cross-checked
  with Grep, which showed the real content at that exact location fully-formed and correct.
  This is the documented stale-bash-mount gotcha, not a real bug. Copied the two new/changed
  methods (`_handle_chat_proxy`, `_handle_chat_proxy_stream_ui`) via Read into the sandbox
  outputs scratch folder wrapped in a dummy class and ran `python3 -m py_compile` there —
  `SYNTAX_OK`.
- `chat.html`: copied the full `<script>` block (lines 1284–2295, ~1000 lines) via Read into
  the outputs scratch folder and ran `node --check` — `SYNTAX_OK`.
- Both files NUL-scanned via Grep (not bash) — clean.
- CSS block eyeballed (every new rule opens/closes); a whole-file brace-count via Grep is
  noisy on this file (JS destructuring `{ done, value }` and template literals throw off
  naive `{`/`}` counts) — not a reliable check here, consistent with what prior sessions
  already noted for this repo.
- **Not eyeballed live** — Fadi walks chat.html after deploy: send a message with KB on,
  watch the activity line go Searching vault → Found N files → Asking `<model>` → ticking
  seconds → Done, then click "▸ activity" on the finished reply to confirm the log folds in
  correctly. Also worth testing one error path (e.g. temporarily wrong model name) to see
  the `error` stage render in red.

**Item 9(b) — NOT built, per gate.** Exact Telegram message for Fadi to send Hermes:

> Feature request for the dashboard: I want a live "Activity" trace under your replies
> showing what you actually did (tools used, files touched, commands run) while working —
> no more black box.
>
> New standing rule for your lane: every time you use a tool or run a command while
> processing a request, append one line to an activity log file in your own workspace
> (not the life-os-dashboard repo — keep this in your lane). Suggested format, one JSON
> line per action:
> `{"ts": "<ISO8601>", "action": "<tool or command name>", "detail": "<short description>"}`
>
> Pick whatever path makes sense in your own workspace — your call. Reply back with:
> 1. The exact file path you're writing to
> 2. A sample of 3–5 real lines it's produced
> 3. Whether you can keep it append-only and bounded (rotate or cap old entries) so a
>    dashboard endpoint could later tail just the last N lines
>
> I won't build the dashboard-side reader or panel until a real log file exists with real
> content — no fabricated traces. Once you confirm, I'll wire a read-only endpoint +
> collapsible panel to it.

**Not touched:** items 4–8 (still gated), any tool-role/writer-lane/data-store change
(none of this session's work qualifies).

### Git — commands for Fadi (sessions never run git):

```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add server.py chat.html NEXT-SESSION-UI.md
git commit -m "Chat activity trace (9a): SSE-lite stream_ui opt-in on /api/chat (server.py) with real connecting/asking/elapsed-heartbeat/done events; chat.html renders a live mono status line replacing the plain typing dots, folds into a collapsed activity toggle on the finished reply"
git push origin main
# auto-pull deploys within ~1 min — open chat.html, send a message with KB on, confirm the
# activity line goes Searching vault -> Found N files -> Asking <model> -> ticking -> Done,
# then click "activity" on the finished reply to confirm the log expands correctly.
```

## 2026-07-10 session (Sonnet, Second Brain project) — Registry hygiene + Skills Hub side panel + back-button sweep

Executed items 1-3 of the queue above, top to bottom, per session rules. Did not touch any
GATED item (4-8).

**1. Registry hygiene (vault):**
- `_system/registry/routines.md` — added a row for `model-catalog-refresh` (Cowork scheduled
  task, confirmed live via the scheduler: cron `0 9 1,15 * *`, next run 2026-07-15), replacing
  the stale "monthly model-picks review" backlog row it supersedes.
- Confirmed `agent-profiles/hermes-vault-search.md` and `agent-profiles/hermes-market-scanner.md`
  are correctly `spec-ready` (not live routines) — market-scanner isn't a registered Cowork
  scheduled task (it would be a Hermes-side VPS cron, not built yet — gated item 5) and
  vault-search is a standing behavior, not a scheduled job. Neither needs a registry row yet;
  no drift found.

**2. Skills Hub click→side panel (dashboard repo — skills.html, files.html):**
- `skills.html`: ARMS registry rows are now clickable (mouse + keyboard) and open a right-side
  slide-in panel (`#regDetailOverlay`) showing status/score chips, the job description, a
  linkified Wired-to line, and a "Last log.md mention" block. `linkifyWired()` only turns a
  Wired-to token into a link if it looks path-shaped (has a file extension, trailing slash, or
  a `NNN Name` vault-folder pattern like `010 Projects`) — vague tokens like "client bases" stay
  plain text. `findLastLogMention()` fetches `/api/file?path=log.md` (existing endpoint, no
  backend change), strips the rendered HTML to text, and shows the last paragraph mentioning the
  skill name, or an honest "no mention yet" — never opens any other wiki page body.
- `files.html`: added `?path=` query-param support so a Skills Hub link (or any future deep
  link) can open a specific file on load; falls back gracefully to the existing "Failed to load
  file" error if the path doesn't resolve (e.g. a Wired-to value naming a dashboard-repo file
  like `server.py` rather than a vault path).
- Verified: extracted skills.html's script to the sandbox outputs folder and ran `node --check`
  — `SYNTAX_OK`. NUL-scanned both files via Grep — clean.

**3. Back-button standardization (dashboard repo — kanban.html, meetings.html, graph3d.html, chat.html):**
- Reclassed the existing back link to `.header-back` (crm.html's shared class) and moved it to
  the leftmost header position in `kanban.html` (was `btn btn-sm`, sat in header-actions on the
  right), `meetings.html` (was `.back-btn` with an `onclick="history.back()"` — now a
  deterministic `href="index.html"` like every other page), and `graph3d.html` (was
  `.toggle-btn`, sat inside `.graph-controls` on the right).
- `chat.html` had no back link anywhere — added one to `.chat-toolbar` (compact sizing to fit
  the 48px bar).
- Left `dashboard.html` (SPA fragment, no page links to it directly) and `index.html` (it IS the
  home) without a back link — consistent with why they weren't already in scope. Confirmed
  `theme-preview.html` is unlinked anywhere in the app (orphaned Fable design artifact, decision
  already shipped into shared.css) and left it alone.
- Verified: NUL-scanned all 4 files via Grep — clean. Read back each edited header block to
  confirm well-formed HTML (no stray tags).

**Not touched:** anything gated (4-8), any tool-role/writer-lane/data-store change (none of this
session's work qualifies — pure front-end + a registry-table edit).

### Git — commands for Fadi (sessions never run git):

**Commit 1 — dashboard repo (6 files):**
```
cd /c/Dev/life-os-dashboard
pwd   # must print /c/Dev/life-os-dashboard before continuing
git status
git add skills.html files.html kanban.html meetings.html graph3d.html chat.html NEXT-SESSION-UI.md
git commit -m "Skills Hub: registry row click -> side panel (wired-to linkified, log.md mention); files.html ?path= deep-link support; back-button sweep (kanban/meetings/graph3d/chat now use .header-back like crm.html)"
git push origin main
# auto-pull deploys within ~1 min — open skills.html, click a registry row, confirm the panel;
# check the 4 back-button pages; confirm files.html deep-link from a Wired-to link.
```

**Commit 2 — vault (registry hygiene, separate location — run in the vault's own sync):**
The vault lives in your OneDrive Second Brain folder, not this repo. Its push is the existing
`sync-vault-to-git.bat` — double-click it in File Explorer (Second Brain folder root) to push
the `_system/registry/routines.md` change to the second-brain-vault repo. No manual git needed.

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
