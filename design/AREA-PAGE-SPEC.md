# AREA PAGE SPEC — Hub Digest Layout

Status: locked 2026-07-13 (Fable design, Fadi approved a mockup in-session; "PROMPT — Builder
Session 3 — Area Page Hub Redesign", executed by Sonnet the same day).

Cleared for: `area.html`, `fieldbridge.html`, `life-areas.html` (its cards already had the spine +
grid; this pass added count pills + radius alignment only — see the session write-up in
`NEXT-SESSION-UI.md`). **Any new area-like page follows this spec.** The remaining ~12 pages stay
gated behind Fadi naming them (queue item 4, `NEXT-SESSION-UI.md`) — this spec does not clear them.

## Why

The previous area pages were stacked long lists (hub note, then a flat panel per data source).
That's fine at low volume; it stops working once a single area (Knowledge: 234 notes) has more
material than anyone will scroll through. The hub digest pattern puts a summary first and hides
depth behind a click: **Brief → stat tiles → two-column digest (main = depth, side = compact
modules)**. Read the header line, glance at four numbers, skim eight cards, expand only what you
actually want to read.

## Layout recipe (top to bottom)

1. **Header** — back link (`.header-back`), page title with the area's color token, Refresh button.
2. **Area Brief** — one full-width card. Muted label row: `"Area brief · generated 2h ago"` +
   a refresh icon-button (regenerate on demand — never auto-refreshes on page load). Body: 2-4
   Hermes-generated sentences naming concrete items from this area's real data (see "Area Brief
   backend" below). Honest fallback wording when Hermes/backend is unavailable: **"Brief
   unavailable — Hermes is offline. Showing the raw panels below."** Never fabricate a brief.
3. **Stat tile row** — 4 metric tiles, count only. Label 11px muted, number 20px bold. Clicking a
   tile scrolls (`scrollIntoView`) to its module anchor. 2×2 grid under 640px.
   - `area.html`: Knowledge / Opportunities / Open tasks / Projects.
   - `fieldbridge.html`: Pipeline / Knowledge / Opportunities / Open tasks (Pipeline replaces
     Projects — it's FieldBridge's reason to exist).
4. **(fieldbridge.html only) Pipeline** — full-width module, inserted between the stat tiles and
   the two-column digest. Stage columns (existing crm.html-style board), cards re-skinned to the
   `.hub-tcard` anatomy below.
5. **Two-column digest** — `minmax(0,62%) minmax(0,1fr)` grid, single column under 640px.
   - **Main column — Knowledge**: header + client-side search (filters by title/description as you
     type) + a filter-chip row (one chip per `type` present in the data, area-colored active
     state — hidden entirely if fewer than 2 types) + note cards (anatomy below). Shows the 8
     newest by default; a "Show all N →" button expands the full filtered list in place (no
     navigation, no pagination).
   - **Side column — three compact modules** (Opportunity radar / Tasks / Projects for `area.html`;
     Opportunity radar / Plays / Tasks for `fieldbridge.html`): 12px/500 header with icon, top 3
     items, muted "All N →" footer. Opportunity radar's footer expands in place (toggles the full
     list into the same module). Tasks' footer is a real link to `kanban.html` (open tasks belong
     to the board, not a second read surface). Projects/Plays default to expand-in-place, matching
     Opportunity radar, unless a page has a more specific full-list destination (Plays →
     `use-cases.html`, since that's the actual Playbook page).

## Card anatomy — `.hub-tcard` (the shared language)

Established in `dashboard.html`'s Today-tab restyle (session #7, 2026-07-11) and now the anatomy
every note/pipeline card on an area page uses:

```css
.hub-tcard   { background: var(--bg-primary); border: 1px solid var(--border-primary);
               border-radius: 10px; padding: 11px 12px 11px 16px; }
.hub-tcard::before { /* 3px colored left spine */ width: 3px; height: 100%;
                      background: var(--area-<slug>) /* or var(--ar-accent) on area.html */; }
.hub-tcard:hover { border-color: <area color>; transform/shadow lift. }
.hub-tcard-title { font-size: 14px; font-weight: 600; }
.hub-tcard-desc  { font-size: 12px; color: var(--text-secondary); } /* one-line description */
.hub-tcard-meta  { font-size: 10px; uppercase; color: var(--text-tertiary); } /* type · date · expand ▾ */
```

Pill tags (`.hub-tag` / `.tg-<area>`) are the dashboard.html precedent for area-colored badges;
area pages use inline `.ah-opp-pill` / `.fb-opp-pill` for confidence badges (HIGH/MEDIUM/EMERGING/
signal) — same 9-10px uppercase pill shape, colored per confidence rather than per area since that's
the more useful signal in that context. There is no shared.css copy of `.hub-tcard` yet — each page
still carries its own inline `<style>` copy against shared tokens (`--bg-primary`, `--area-*`,
`--radius-*`); a future pass could promote it to shared.css once a 4th page needs it, per the
project's existing "each page owns its inline style block" convention.

**Filter chips** (`.ah-chip` / `.fb-chip` / `use-cases.html`'s `.pb-filter-chip`): pill button,
`border-primary` default, area-accent border on hover, filled area-accent background + `--on-accent`
text when active. Row hides itself entirely when there's nothing to filter (fewer than 2 distinct
values) — never show a filter row with one inert option.

## Expand-in-place pattern

Clicking a Knowledge card toggles an inline body panel under its meta row (no navigation):

1. First click: fetch `/api/wiki/page?path=<note path>` → `{data: {path, meta, body}}`.
2. Render `body` (raw markdown) through a **minimal client-side markdown renderer** — headings
   (`#`-`######` → `<h1>`-`<h4>`, collapsed to 4 visual levels), `**bold**`, `- `/`* ` lists, and
   `[text](url)` links. `[[wikilinks]]` render as plain italic styled text (`.ah-wikilink` /
   `.fb-wikilink`), never as a clickable link — Obsidian-only syntax, and the target may not be
   surfaced anywhere the dashboard can resolve.
3. Cache the fetched body in an in-memory JS map (`wikiBodyCache`, keyed by path) for the rest of
   the page session — re-expanding the same card never re-fetches.
4. Keep an "Open in vault ↗" link to `files.html?path=<path>` inside the expanded body, so a reader
   who wants the real file (with any formatting the mini-renderer flattens) can still get it.
5. Second click on the same card collapses it. Opening a different card does not auto-collapse the
   first (independent per-card state) — `expandedIdx` in the current implementation only tracks one
   at a time for simplicity (only one body fetch in flight); revisit if Fadi wants multiple open at
   once.

No new markdown library was added (no marked.js dependency here, unlike `chat.html`) — the brief
called the minimal renderer sufficient, and note bodies are short enough that headings/bold/lists/
links cover real vault content adequately.

## Area Brief backend

- `GET /api/areas/brief?area=<slug>` → `{brief, generated, available}`. Reads
  `DATA_DIR/.area_briefs.json` (keyed by slug). No cache entry → `available:false`; the UI shows the
  honest fallback + lets the user hit the refresh button. Pure read, no side effects.
- `POST /api/areas/brief {area}` → builds a prompt from (all read in-process via
  `_build_areas_index()`, no second parser): the area's 10 newest note titles + descriptions, its
  Opportunity Radar signals, and its open kanban task titles (`DATA_DIR/.kanban_store.json` filtered
  by `tag===area`). `fieldbridge` additionally feeds CRM pipeline stage counts + `next` fields (CRM
  mirror only — nothing from the unsynced FieldBridge HQ vault). Calls Hermes via the same
  `HERMES_CHAT_PROXY_URL` proxy pattern as `/api/braindump` (same auth header, same ``` fence
  stripping). Stores `{brief, generated}` in the cache and returns it. Hermes unreachable, empty
  response, or nothing to summarize → honest `{available:false, error}`, never a fabricated brief.
- **Data-store note**: `.area_briefs.json` is the same operational class as `.kanban_store.json` /
  `playbook-usage.jsonl` (dashboard's own compute-cache lane, `DATA_DIR`) — architect-pre-approved
  in the builder prompt for this session, not a new STOP-and-flag surface. Compute + cache only; no
  vault write, no new writer lane.
- Regeneration is on-demand only (the refresh button/icon). No cron, no auto-refresh on page load —
  a stale brief with a visible timestamp is safer than a surprise Hermes bill on every page visit.

## API contract note

`/api/areas`'s per-note shape gained one additive key: `description` (from frontmatter, `''` if
absent). All prior keys (`title, path, date, type`) and the response envelope are unchanged — this
was the one API surface touched by this pass, and it's additive-only per the standing STANDARD.

## What this pass deliberately dropped

The pre-existing `area.html` rendered the area's authored vault "hub note"
(`020 Areas/0X <Area>.md`) as its own top panel. The approved mockup replaces that role with the
generated Area Brief and does not include a hub-note panel in the digest. To avoid losing access to
that authored content, a small `"Area note ↗"` link was added next to the Brief's refresh button
(links to `files.html?path=<hub note path>`) — not part of the original mockup, but a low-risk,
additive way to keep that content one click away. Flagging here in case Fadi wants the hub note
rendered inline again; easy to re-add as a collapsed panel under the Brief if so.
