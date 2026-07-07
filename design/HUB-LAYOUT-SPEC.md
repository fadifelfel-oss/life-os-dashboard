# HUB LAYOUT SPEC — Today Page (Phase 3.2)

> Fable, 2026-07-06. Rebuild of dashboard.html per UI-MASTER-PLAN Phase 3 (zones decided
> 2026-07-05). Data: ONE fetch of `/api/today` (already live) + kanban store. No other
> endpoints. All colors via `var(--area-*)` / `var(--status-*)` — zero hardcoded hex.

## Grid
Desktop (≥1024px): 12-col grid, three horizontal bands. Mobile: single column, band order preserved.

```
┌──────────────────────────────────────────────────────────┐
│ BAND 1 — MORNING LAUNCH (grid: 4/4/4)                     │
│ ┌ Power 3 ────┐ ┌ Due Today ───┐ ┌ Calendar peek ──────┐  │
│ │ from journal │ │ kanban due   │ │ next 3 events       │  │
│ └──────────────┘ └──────────────┘ └─────────────────────┘  │
│ ┌ Nightly digest (12-wide, collapsible, 1 line summary) ┐  │
├──────────────────────────────────────────────────────────┤
│ BAND 2 — EXECUTION (grid: 8/4)                            │
│ ┌ Kanban (quick-add + drag) ──┐ ┌ Ship-Today tracker ──┐  │
│ │ THE task board              │ │ tripwire counter      │  │
│ └─────────────────────────────┘ └──────────────────────┘  │
├──────────────────────────────────────────────────────────┤
│ BAND 3 — ACCOUNTABILITY (grid: 6/6)                       │
│ ┌ Open WAGERs ────────────────┐ ┌ Evening check ───────┐  │
│ └─────────────────────────────┘ └──────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Cards (anatomy per §2: eyebrow → value → delta → footer action; left-aligned)
- **Power 3** — eyebrow "POWER 3"; three checkbox rows parsed from today's journal note; empty state: "No Power 3 yet — open today's journal" + button. Area-colored left border per item's tagged area if present, else `--area-admin`.
- **Due Today** — kanban cards due/overdue; overdue rows get `--status-failed` dot + "overdue" label. Footer: "Open board →".
- **Calendar peek** — next 3 events today (from /api/today if wired; else hide the card entirely — no dead placeholders).
- **Nightly digest** — one summary line ("5 channels · 3 ingested · 1 flag") + expand to the full digest block from log.md. Channel chips use status dots. If last run >26h ago: `--status-stale` banner "Nightly didn't run last night" — this is the Part B health surface.
- **Kanban** — existing board embedded, quick-add input at top. Labels colored by area palette.
- **Ship-Today tracker** — THE FieldBridge card: eyebrow "TRIPWIRE — $10K BY JUL 24"; big number = collected-to-date (manual value in DATA_DIR/tripwire.json, editable inline); delta = days remaining; below: today's ship checklist (sent/held/published counters wired to the existing shared.js ship tracker). Card border `--area-fieldbridge`. After Jul 24 the card flips to VERDICT state (hit → green "WON — set next target"; missed → red "Job search resumes today" + link to Job Search project note).
- **Open WAGERs** — rows from log.md WAGER lines lacking an "Actual:" resolution; each row: prediction (truncated), age in days, "resolve" button that pre-fills a log capture.
- **Evening check** — after 17:00 becomes prominent: "What did you ship today?" + one-line input that appends a CAPTURE line to a pending-notes file the nightly sweeps into log.md (dashboard never writes the vault directly — DATA_DIR only, per Decision Gate 1). Saturday: swap to Review card (week's Failed/Surprised lines + "one rule edit" prompt).

## Behavior
- Single `/api/today` fetch on load; skeletons while loading; every card has a designed empty state (§2 — small illustration + one action).
- Time-aware emphasis: before 12:00 Band 1 full-height; after 17:00 Band 3 moves visually above Band 2 (order swap via flex order, not re-render).
- 18px minimum body text (R1 — fixed constraint). RTL-test all three bands (Arabic toggle).
- /GOAL: first paint <2s on the VPS, zero console errors, correct in all 3 themes.
