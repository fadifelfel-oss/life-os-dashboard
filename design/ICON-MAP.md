# ICON MAP — Emoji → Lucide Sweep (Phase 2.2)

> Fable, 2026-07-06. Sonnet executes. Rule from UI-MASTER-PLAN §2: **zero emoji in UI
> chrome** (nav, buttons, status, cards, headers). Emoji stay allowed inside CONTENT
> (vault text, chat messages, kanban card text written by Fadi).

## Delivery mechanics
1. Download the Lucide SVG sprite (or individual icons) — **self-host** as `assets/lucide-sprite.svg`. No CDN.
2. Usage everywhere: `<svg class="icon" width="16" height="16"><use href="assets/lucide-sprite.svg#icon-name"/></svg>`
3. Add to shared.css: `.icon { stroke: currentColor; fill: none; stroke-width: 2; vertical-align: -0.125em; }` — icons inherit text color, area colors come from the parent's `var(--area-*)`.
4. Status indicators are NOT icons: replace 🟢🔴🟡 with `<span class="status-dot" style="background:var(--status-live)"></span> live` (dot + label, never color alone).

## The map (top-frequency emoji, measured 2026-07-06)

| Emoji | Where | Lucide id | Note |
|-------|-------|-----------|------|
| ⚡ | Today nav, quick actions | `zap` | |
| 🧠 | Brain nav, wiki | `brain` | |
| 🤖 | Agents nav, personas | `bot` | |
| 💬 | Chat | `message-square` | |
| 🔧 | System nav, tools | `wrench` | `settings` for the Settings page itself |
| ⚙ | settings gear | `settings` | |
| 🎙 | voice | `mic` | |
| ✅ | done/success | `circle-check` | in status contexts use status-dot instead |
| ❌ / ✕ | error / close | `circle-x` / `x` | close buttons = plain `x` |
| ⚠ | warning | `triangle-alert` | |
| 🏗 | Construction area | `hard-hat` | |
| ⚖ | legal/contracts | `scale` | |
| 📋 | kanban/tasks | `clipboard-list` | |
| 📁 / 📄 | files / page | `folder` / `file-text` | |
| 🔍 | search | `search` | |
| 💻 | dev/code | `monitor` | |
| 📥 | inbox/capture | `inbox` | |
| 📊 / 📈 | charts / trend | `chart-column` / `trending-up` | |
| 🩺 | Health area | `stethoscope` | area color `--area-health` |
| 🏋 | fitness | `dumbbell` | |
| 🔑 | API keys | `key-round` | |
| 💡 | ideas/signals | `lightbulb` | Radar signals: `radar` exists — prefer it |
| 📦 | packages/models | `package` | |
| 🕊 / family | Family area | `heart` | area color `--area-family` |
| 🌉 | FieldBridge | `building-2` | interim until logo mark; area color `--area-fieldbridge` |
| 🌓 | theme toggle | `sun-moon` | becomes the 3-theme switcher trigger |
| 💾 | save | `save` | |
| 🗑 | delete | `trash-2` | |
| 🦉 | logo | **interim inline SVG below** | Phase 2.4 delivers the real mark |

## Life-area icon set (nav + area pages + kanban labels — always paired with `--area-*` color)
Career `briefcase` · FieldBridge `building-2` · Construction `hard-hat` · Trading `candlestick-chart` (fallback `trending-up`) · Health `heart-pulse` · Family `heart` · Knowledge `book-open` · Admin `inbox`

## Interim logo (replaces 🦉 until Phase 2.4)
Geometric owl, blueprint style — single path, inherits `--area-fieldbridge`:
```html
<svg class="logo" viewBox="0 0 24 24" width="22" height="22" fill="none"
     stroke="var(--area-fieldbridge)" stroke-width="1.8" stroke-linejoin="round">
  <path d="M4 8 L4 16 Q4 21 12 21 Q20 21 20 16 L20 8 L16.5 4.5 L14 8 L10 8 L7.5 4.5 Z"/>
  <circle cx="9" cy="12.5" r="1.9"/><circle cx="15" cy="12.5" r="1.9"/>
  <path d="M12 15.5 L12 17"/>
</svg>
```

## Anything not in this table
Pick the nearest Lucide concept; if genuinely none fits, use `circle` + a text label rather than keeping the emoji. Log unmapped cases in the session CAPTURE so the map gets amended.
