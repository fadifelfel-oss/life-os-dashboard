# NEXT SESSION — UI Build (Sonnet handoff, 2026-07-06 evening)

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

**If you already ran the Stage 1+2 commit (`2f9c2f1` per your screenshot),
use this block instead — it covers everything since then (Stage 3's 4-page
legacy migration: kanban/voice/meetings/artifacts + sprite additions):**

```
cd C:\Dev\life-os-dashboard
git status
# review the pre-existing use-cases/voice rename+deletion mess above BEFORE staging
git add kanban.html voice.html meetings.html artifacts.html assets/lucide-sprite.svg NEXT-SESSION-UI.md
git commit -m "Stage 3 (Phase 2.3) partial: migrate kanban/voice/meetings/artifacts onto shared design tokens, fix remaining hardcoded colors, full emoji sweep on all 4 pages, add calendar/users/target/copy/maximize icons to sprite"
git push origin main
```

**If you have NOT yet run any commit this session**, use the full block below
instead (includes Stage 1+2+3 in one commit):

```
cd C:\Dev\life-os-dashboard
git status
# review the pre-existing use-cases/voice rename+deletion mess above BEFORE staging
git add shared.css shared.js index.html dashboard.html use-cases.html skills.html models.html mcp.html keys.html loops.html imagegen.html files.html graph3d.html browser.html life-areas.html chat.html artifacts.html voice.html meetings.html kanban.html assets/lucide-sprite.svg NEXT-SESSION-UI.md
git commit -m "Phase 2.1 + R13 theme system + Phase 2.2 icon sweep + Phase 2.3 partial: three-theme system, anti-flash pre-paint, self-hosted Lucide-style sprite, chrome emoji swept, 4-page legacy migration onto shared tokens"
git push origin main
```
