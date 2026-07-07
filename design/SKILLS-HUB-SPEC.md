# SKILLS HUB SPEC — skills.html rebuild (Phase 5.4 / R11)

> Fable, 2026-07-06. Source of truth = the VAULT (read-only mirror), not the dashboard.

## Data
- Registry file: `_system/registry/skills.md` in the vault (markdown table; seeded with
  structure + examples, populated/maintained by the nightly task and FieldBridge sessions).
- Columns per skill: name (internal) · source (cowork / fieldbridge / hermes) · one-line job ·
  status (active / consolidating / retired) · test score (FieldBridge: from SKILLS-GAP-REGISTER
  when present) · last-used (from log.md mentions where measurable) · wired-to (files/routines).
- Endpoint: extend `/api/arms` (skills[] already in its contract per BUILD SPEC C1) — the
  Skills Hub and the 3D Brain read the SAME data. No second parser.

## Layout
- Grouped list by source with area-colored group headers (FieldBridge amber, Cowork purple,
  Hermes teal). Each row: name · job · status dot+label · score chip (if any) · last-used.
- Click row → side panel: wired-to links (open wiki page / routine), gap-register note,
  improvement-loop status (last feedback line from log.md if present).
- Header stat strip: total active · consolidating (18→10 per Blueprint v3.1) · untested count.
- Empty/missing data renders as honest "not measured" — never fake counts.
- REMINDER banner rule: skill names are INTERNAL — this page must never be screenshotted
  into client material (put a small footer note: "Internal — not client-facing").
