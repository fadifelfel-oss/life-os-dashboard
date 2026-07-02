---
type: Schema
title: Vault Wiki Schema
description: The constitution for how Hermes reads, writes, and maintains this vault. Deployed automatically into 00_Kernel/OKF-WIKI-SCHEMA.md on first OKF migration run.
tags: [system, schema, okf]
timestamp: "2026-07-01T00:00:00Z"
---

# Vault Wiki Schema

This vault follows the **LLM-wiki pattern** (Karpathy) written in the **Open Knowledge Format (OKF v0.1)** (Google, June 2026). This file is the schema layer: it tells any agent (Hermes, Claude, or a future tool) how the vault is organized and how to behave in it. Read this before doing any Ingest, Query, or Lint operation.

## The three layers

**Raw sources** — `Clippings/`, `10_Sources/`, anything dropped in via web clip, PDF upload, or voice note. Immutable. Never edit or delete a raw source; only read from it.

**The wiki** — every other markdown file in the vault. Agent-owned. This is where summaries, entity pages, and synthesis live. Update it freely; that's the job.

**This schema** — co-evolves with Fadi. If a convention below stops fitting how the vault is actually used, propose a change rather than silently drifting from it.

## Frontmatter (required on every concept page)

```yaml
---
type: <string>            # REQUIRED. e.g. Playbook, Reference, Entity, Log, Clipping, Skill, Opportunity
title: <string>            # display name
description: <one sentence>
domain: <career|fieldbridgehq|trading|construction|ai-tools|health|general>
tags: [<tag>, <tag>]
timestamp: <ISO 8601>       # last meaningful update
resource: <URL>             # optional — canonical external source (clip URL, PDF path)
---
```

`type` is the only field that MUST be present. `domain` drives the 3D Brain's node coloring and stays the existing vault convention (career/fieldbridgehq/trading/construction/ai-tools/health/general) rather than switching to OKF's more open-ended `type` for that purpose — don't conflate the two: `type` describes *what kind of document*, `domain` describes *which area of Fadi's life it belongs to*.

## Cross-linking

Keep using Obsidian-style `[[Page Title]]` wikilinks, not OKF's raw markdown link syntax — this vault is read in Obsidian and the 3D Brain's graph already parses wikilinks. This is a deliberate, documented deviation from strict OKF §5; every other OKF convention (frontmatter shape, index.md, log.md) is followed as specified.

A link asserts a relationship — the surrounding sentence explains what kind (references, contradicts, depends-on, monetization-adjacent, etc.). Broken links are not errors; they're a marker that a page hasn't been written yet.

## Operations

### Ingest
When a new source lands in `Clippings/` or `10_Sources/`:
1. Read the source. Do not summarize blindly — decide what's actually worth keeping.
2. Check the index (`20_Wiki/<domain>/index.md` or nearest one) for existing pages this source should update, not just a new page it should create.
3. Write or update the relevant wiki page(s) with required frontmatter, a body, and `[[wikilinks]]` to related concepts.
4. Update the directory's `index.md` (one-line entry, description pulled from frontmatter).
5. Append an entry to the nearest `log.md`: `## YYYY-MM-DD` heading, then `* **Ingest**: <what happened>, see [[page]]`.
6. Move the raw source from `Clippings/` to `10_Sources/processed/` once its wiki page exists.

### Query
When Fadi or the dashboard asks a question:
1. Check `index.md` files first to find candidate pages before reading full content — cheaper and usually sufficient.
2. Read the full candidate pages, not just snippets, before answering.
3. Answer with citations — reference the specific page(s) the claim came from.
4. If the answer is worth keeping (a synthesis, a comparison, a decision), offer to file it back into the wiki as a new page rather than letting it evaporate in chat.

### Lint
On request (or once automated later): scan the vault for
- **Orphan pages** — no inbound wikilinks from anywhere else in the vault.
- **Dangling links** — a `[[wikilink]]` whose target page doesn't exist yet.
- **Stale pages** — `timestamp`/`last_reviewed` older than 60 days on a page in an active domain (career, fieldbridgehq, trading).
- **Missing type** — pages with no `type` field (not yet OKF-conformant).
- **Cross-domain opportunities** — pages linked across two different `domain` values with 3+ shared links; these are candidates for monetization or use-case ideas (this is the heuristic the 3D Brain already visualizes as glowing nodes).

When asked to analyze the results, don't just report the list — cross-reference it against what's known about Fadi (see [[fadi-profile]] equivalent context: job search + FieldBridge HQ + prop trading priorities, August 6 2026 deadline) and propose: (a) new use cases Hermes could support, (b) monetization angles where knowledge intersects the CRM/pipeline, (c) the highest-value gap to fill next — not an exhaustive list, the single best one.

## Indexing and logging conventions

`index.md` — content-oriented, one per directory that has more than a handful of pages. Lists children with a one-line description pulled from frontmatter `description`. Regenerate/update on every Ingest.

`log.md` — chronological, append-only, newest entries at the bottom or top (pick top for this vault, consistent with `## YYYY-MM-DD` then bullet entries prefixed **Ingest**/**Update**/**Lint**). Gives a fast way to see what changed recently with `grep "^## " log.md | tail -5`.

## What this schema deliberately does not cover yet

Automated (unattended) Ingest — watched folders that auto-process new PDFs/voice notes without a human trigger — and scheduled Lint runs are documented above as target behavior but not yet wired up. Phase 2 work. Until then, Ingest and Lint are triggered on demand from the 3D Brain page or a chat request.
