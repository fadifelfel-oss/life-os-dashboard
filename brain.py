"""
brain.py — Deterministic retrieval ladder for the Second Brain (BUILD SPEC v1, Part A / GAP A).

Replaces the "open every page, score raw content, send top-6 x 2000 chars to Hermes"
pattern in server.py's _handle_wiki_query and the full-vault rglob in _serve_kb_search.

The ladder (exact contract, see BUILD SPEC v1 A1):
  1. KEYWORDS      — parse_query(): lowercase, stopword-strip, quoted phrases kept whole.
  2. SCORE WITHOUT OPENING FILES — score index.md lines + 30_Context table rows +
     CRM/index.md lines. No wiki page body is ever opened in this step.
  3. OPEN ONE FILE — the single top-scoring page only.
  4. SECTION, NOT DOC — split on `##`, score sections with kw_score only, cap at 1500 chars.
  5. FOLLOW ONE POINTER — if the winning section is >50% a [[wikilink]]/"see X", resolve
     it once via the index path lookup, re-run step 4 there. Never recurse further.
  6. ONE MODEL CALL — left to the caller (server.py _handle_wiki_query); brain.py never
     calls Hermes itself.

brain.py only ever reads. It never writes into the vault (that's _system/store.py,
vault-side, run by Cowork/nightly sessions only — see BUILD SPEC v1 A3).

Public API:
    parse_query(question)              -> (tokens: list[str], phrases: list[str])
    load_candidates(vault_dir)         -> (candidates: list[dict], content_hash: str)
    score_index(question, vault_dir, data_dir=None, top_n=5) -> dict
    retrieve(question, vault_dir, data_dir=None)             -> dict (Evidence)
    get_counters() / reset_counters()  -> instrumentation for the A4 "zero page bodies
                                           opened during scoring" acceptance check.
"""

import re
import json
import time
import hashlib
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────
# STEP 1 — KEYWORDS
# ─────────────────────────────────────────────────────────────────────────

# Fixed ~120-word English stoplist, shipped inline — no NLTK download, no
# network dependency, deterministic across runs.
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "just", "me", "more", "most", "my", "myself", "no", "nor",
    "not", "now", "of", "off", "on", "once", "only", "or", "other", "our", "ours",
    "ourselves", "out", "over", "own", "same", "she", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "were",
    "weren't", "what", "when", "where", "which", "while", "who", "whom", "why",
    "will", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves", "does", "doing",
}


def parse_query(question):
    """Lowercase, strip stopwords, keep tokens len>2, plus quoted phrases kept whole."""
    q = question or ""
    phrases = [m.strip().lower() for m in re.findall(r'"([^"]+)"', q) if m.strip()]
    without_quotes = re.sub(r'"[^"]*"', ' ', q)
    raw_tokens = re.findall(r"[A-Za-z0-9']+", without_quotes.lower())
    tokens = [t for t in raw_tokens if len(t) > 2 and t not in STOPWORDS]
    return tokens, phrases


# ─────────────────────────────────────────────────────────────────────────
# Instrumentation — proves "zero page bodies opened during scoring"
# ─────────────────────────────────────────────────────────────────────────

_COUNTERS = {"index_reads": 0, "page_opens": 0}


def reset_counters():
    _COUNTERS["index_reads"] = 0
    _COUNTERS["page_opens"] = 0


def get_counters():
    return dict(_COUNTERS)


def _read_index_file(path: Path) -> str:
    """The ONLY function allowed to read index.md / CRM/index.md during scoring."""
    _COUNTERS["index_reads"] += 1
    return path.read_text(encoding="utf-8", errors="replace")


def _read_page_file(path: Path) -> str:
    """The ONLY function allowed to read a wiki/reference page body — step 3+ only."""
    _COUNTERS["page_opens"] += 1
    return path.read_text(encoding="utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────────────────
# STEP 2 — CANDIDATES (index.md domain tables + 30_Context table + CRM/index.md)
# ─────────────────────────────────────────────────────────────────────────

_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]")


_ESCAPED_PIPE_SENTINEL = "\x01"


def _split_row(line):
    """Split a markdown table row on '|', respecting the '\\|' escape Obsidian
    uses inside wikilink aliases (e.g. [[path\\|Title]]) -- a naive split would
    shatter those cells at the escaped pipe."""
    m = _ROW_RE.match(line.strip())
    if not m:
        return None
    protected = m.group(1).replace("\\|", _ESCAPED_PIPE_SENTINEL)
    cells = [c.strip().replace(_ESCAPED_PIPE_SENTINEL, "|") for c in protected.split("|")]
    return cells


def _parse_index_md(vault_dir: Path):
    """Domain-table rows in index.md — one candidate per wiki page.
    Table shape: | [[path|title]] | Core Insight | Date |
    Also captures the '## 30_Context Reference' table (Document | Contents)."""
    index_path = vault_dir / "index.md"
    candidates = []
    if not index_path.exists():
        return candidates, ""
    text = _read_index_file(index_path)

    current_domain = None
    in_context_ref = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            in_context_ref = heading.lower().startswith("30_context reference")
            if not in_context_ref:
                current_domain = heading
            continue
        if not stripped.startswith("|"):
            continue
        cells = _split_row(line)
        if not cells or len(cells) < 2:
            continue
        # skip header/separator rows
        if cells[0].lower() in ("page", "document") or set(cells[0]) <= {"-", ":"}:
            continue

        if in_context_ref:
            # | `path` | Contents description |
            doc_cell, contents = cells[0], cells[1]
            path_match = re.search(r"`([^`]+)`", doc_cell)
            path = path_match.group(1) if path_match else doc_cell.strip("`")
            title = Path(path).stem
            candidates.append({
                "kind": "context",
                "domain": "30_Context Reference",
                "title": title,
                "path": path,
                "insight": contents,
                "filename": Path(path).name,
            })
        else:
            # | [[path|title]] | insight | date |
            link_cell = cells[0]
            insight = cells[1] if len(cells) > 1 else ""
            wl = _WIKILINK_RE.search(link_cell)
            if not wl:
                continue
            path = wl.group(1).strip()
            title = (wl.group(2) or path.split("/")[-1]).strip()
            full_path = path if path.endswith(".md") else f"{path}.md"
            candidates.append({
                "kind": "wiki",
                "domain": current_domain or "general",
                "title": title,
                "path": full_path,
                "insight": insight,
                "filename": Path(full_path).name,
            })

    return candidates, text


def _parse_crm_index(vault_dir: Path):
    """CRM/index.md rows — pipeline + contact tables. Wikilinks here have no
    folder prefix (Obsidian short-link convention) — they resolve to CRM/<name>.md."""
    crm_index_path = vault_dir / "CRM" / "index.md"
    candidates = []
    if not crm_index_path.exists():
        return candidates, ""
    text = _read_index_file(crm_index_path)

    current_table = "CRM"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current_table = stripped[3:].strip()
            continue
        if not stripped.startswith("|"):
            continue
        cells = _split_row(line)
        if not cells or len(cells) < 2:
            continue
        if cells[0].lower() in ("name",) or set(cells[0]) <= {"-", ":"}:
            continue
        wl = _WIKILINK_RE.search(cells[0])
        if not wl:
            continue
        raw_path = wl.group(1).strip()
        title = (wl.group(2) or raw_path).strip()
        # short-link convention: resolves inside CRM/
        rel_path = raw_path if "/" in raw_path else f"CRM/{raw_path}"
        full_path = rel_path if rel_path.endswith(".md") else f"{rel_path}.md"
        insight = " | ".join(cells[1:])
        candidates.append({
            "kind": "crm",
            "domain": f"CRM — {current_table}",
            "title": title,
            "path": full_path,
            "insight": insight,
            "filename": Path(full_path).name,
        })

    return candidates, text


def load_candidates(vault_dir):
    """Return (candidates, content_hash). content_hash covers every source line
    fed into scoring, so the embedding cache invalidates whenever ANY of them
    changes — not just index.md (spec's 'index_md_sha256' extended to cover the
    CRM/index.md candidates it also names as a candidate source)."""
    vault_dir = Path(vault_dir)
    index_candidates, index_text = _parse_index_md(vault_dir)
    crm_candidates, crm_text = _parse_crm_index(vault_dir)
    candidates = index_candidates + crm_candidates
    combined = (index_text + "\x00" + crm_text).encode("utf-8")
    content_hash = hashlib.sha256(combined).hexdigest()
    return candidates, content_hash


# ─────────────────────────────────────────────────────────────────────────
# A2 — EMBEDDINGS (sentence-transformers/all-MiniLM-L6-v2, CPU, self-hosted)
# ─────────────────────────────────────────────────────────────────────────

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_embedder = None
_embedder_failed = False


def _get_embedder():
    """Lazy-load the embedding model once per process. On any failure, mark
    it failed permanently for this process — brain.py degrades to kw_score
    only and retrieval never goes down because of the embedding layer."""
    global _embedder, _embedder_failed
    if _embedder_failed:
        return None
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer(_MODEL_NAME, device="cpu")
        except Exception as e:
            print(f"⚠ brain.py: embedding model failed to load ({e}) — degrading to kw_score only")
            _embedder_failed = True
            return None
    return _embedder


def _embed_texts(texts):
    """Returns list[list[float]] or None if the model isn't available."""
    model = _get_embedder()
    if model is None:
        return None
    try:
        vectors = model.encode(list(texts), convert_to_numpy=True, show_progress_bar=False)
        return [v.tolist() for v in vectors]
    except Exception as e:
        print(f"⚠ brain.py: embedding failed at runtime ({e}) — degrading to kw_score only")
        return None


def _cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class EmbeddingCache:
    """DATA_DIR/.brain_embeddings.json — {content_hash, model_name, vectors: {path: [floats]}}.
    Rebuilt automatically whenever the candidate corpus hash changes (i.e. after
    every nightly ingest). Query embeddings are always computed fresh at runtime."""

    def __init__(self, data_dir):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent / ".brain_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.data_dir / ".brain_embeddings.json"

    def _load_raw(self):
        if not self.cache_path.exists():
            return None
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _save_raw(self, obj):
        try:
            self.cache_path.write_text(json.dumps(obj), encoding="utf-8")
        except Exception as e:
            print(f"⚠ brain.py: failed to write embedding cache ({e})")

    def get_vectors(self, candidates, content_hash):
        """Returns {path: vector} for the given candidates, rebuilding the cache
        if the hash or model changed. Returns None entirely if embeddings are
        unavailable (caller should treat this as 'no semantic scoring')."""
        cached = self._load_raw()
        if (cached and cached.get("content_hash") == content_hash
                and cached.get("model_name") == _MODEL_NAME
                and set(cached.get("vectors", {}).keys()) >= {c["path"] for c in candidates}):
            return cached["vectors"]

        # (Re)build — one embedding call per candidate line's scoring text.
        texts = [f"{c['title']} — {c['insight']}" for c in candidates]
        vectors = _embed_texts(texts)
        if vectors is None:
            return None
        vec_map = {c["path"]: v for c, v in zip(candidates, vectors)}
        self._save_raw({
            "content_hash": content_hash,
            "model_name": _MODEL_NAME,
            "vectors": vec_map,
        })
        return vec_map


# ─────────────────────────────────────────────────────────────────────────
# kw_score
# ─────────────────────────────────────────────────────────────────────────

def _norm_tokens(text):
    return set(t for t in re.findall(r"[a-z0-9']+", (text or "").lower()) if len(t) > 2)


def kw_score(tokens, phrases, candidate):
    """title x3, insight line x1, filename x2, domain x1 — normalized 0-1,
    +0.15 bonus for an exact title-phrase match."""
    if not tokens and not phrases:
        return 0.0

    title_tokens = _norm_tokens(candidate["title"])
    insight_tokens = _norm_tokens(candidate.get("insight", ""))
    filename_tokens = _norm_tokens(candidate.get("filename", ""))
    domain_tokens = _norm_tokens(candidate.get("domain", ""))

    query_set = set(tokens)
    if not query_set:
        weighted_hit = 0
        weighted_total = 1
    else:
        def overlap(field_tokens, weight):
            if not query_set:
                return 0.0
            hit = len(query_set & field_tokens)
            return weight * (hit / len(query_set))

        weighted_hit = (
            overlap(title_tokens, 3)
            + overlap(insight_tokens, 1)
            + overlap(filename_tokens, 2)
            + overlap(domain_tokens, 1)
        )
        weighted_total = 3 + 1 + 2 + 1

    score = weighted_hit / weighted_total

    # Exact title-phrase match bonus
    title_lower = candidate["title"].lower()
    for phrase in phrases:
        if phrase in title_lower:
            score += 0.15
            break
    if not phrases:
        # also treat the raw question as a soft phrase for the bonus check
        pass

    return min(score, 1.0)


# ─────────────────────────────────────────────────────────────────────────
# STEP 2 (continued) — score_index: the deterministic, file-body-free ranking
# ─────────────────────────────────────────────────────────────────────────

# Below this score, treat as "nothing genuinely matches" rather than force a
# weak coincidental keyword hit into an answer (BUILD SPEC A4 bench question 10:
# a known-gap question must answer "not in vault").
MIN_SCORE = 0.08


def score_index(question, vault_dir, data_dir=None, top_n=5):
    """Ladder steps 1-2 only. Returns:
    {
      "results": [ {..candidate fields.., kw_score, sem_score, score}, ... top_n ],
      "semantic": bool,               # whether embeddings actually ran
      "candidates_scored": int,
      "ladder_ms": int,
    }
    No wiki page body is ever opened here — only index.md / CRM/index.md.
    """
    t0 = time.time()
    vault_dir = Path(vault_dir)
    tokens, phrases = parse_query(question)
    candidates, content_hash = load_candidates(vault_dir)

    sem_scores = {}
    semantic_ran = False
    if candidates:
        cache = EmbeddingCache(data_dir)
        vec_map = cache.get_vectors(candidates, content_hash)
        if vec_map is not None:
            q_vec = _embed_texts([question])
            if q_vec:
                q_vec = q_vec[0]
                for c in candidates:
                    v = vec_map.get(c["path"])
                    sem_scores[c["path"]] = _cosine(q_vec, v) if v else 0.0
                semantic_ran = True

    scored = []
    for c in candidates:
        kw = kw_score(tokens, phrases, c)
        sem = sem_scores.get(c["path"], 0.0)
        if semantic_ran:
            total = 0.55 * sem + 0.45 * kw
        else:
            total = kw
        entry = dict(c)
        entry["kw_score"] = round(kw, 4)
        entry["sem_score"] = round(sem, 4)
        entry["score"] = round(total, 4)
        scored.append(entry)

    scored.sort(key=lambda e: e["score"], reverse=True)
    ladder_ms = int((time.time() - t0) * 1000)

    return {
        "results": scored[:top_n],
        "semantic": semantic_ran,
        "candidates_scored": len(candidates),
        "ladder_ms": ladder_ms,
    }


# ─────────────────────────────────────────────────────────────────────────
# STEP 3-5 — open one file, section not doc, follow one pointer
# ─────────────────────────────────────────────────────────────────────────

_SECTION_SPLIT_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_EVIDENCE_CAP = 1500


def _split_sections(body):
    """Split page body on '##' headings. Returns list of (heading, text)."""
    matches = list(_SECTION_SPLIT_RE.finditer(body))
    if not matches:
        return [("(full page)", body.strip())]
    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections.append((m.group(1).strip(), body[start:end].strip()))
    return sections


def _pick_best_section(body, tokens, phrases):
    sections = _split_sections(body)
    best = None
    best_score = -1.0
    for heading, text in sections:
        pseudo_candidate = {"title": heading, "insight": text[:400], "filename": "", "domain": ""}
        s = kw_score(tokens, phrases, pseudo_candidate)
        if s > best_score:
            best_score = s
            best = (heading, text)
    if best is None:
        return "(full page)", body.strip()[:_EVIDENCE_CAP]
    heading, text = best
    return heading, text[:_EVIDENCE_CAP]


def _is_mostly_pointer(text):
    """>50% of the section content is a [[wikilink]] or a 'see X' reference."""
    stripped = text.strip()
    if not stripped:
        return False
    wikilinks = _WIKILINK_RE.findall(stripped)
    link_chars = sum(len(w[0]) + len(w[1] or "") + 4 for w in wikilinks)
    see_match = re.search(r"\bsee\s+\[\[([^\]|#]+)", stripped, re.IGNORECASE)
    if link_chars / max(len(stripped), 1) > 0.5:
        return True
    if see_match and len(stripped) < 200:
        return True
    return False


def _extract_pointer_target(text):
    wl = _WIKILINK_RE.search(text)
    if wl:
        return wl.group(1).strip()
    return None


def _resolve_path_from_candidates(link_target, candidates):
    """Resolve a [[wikilink]] target to a candidate's path via index lookup
    (title or filename match) — never a filesystem scan."""
    target_lower = link_target.lower().strip()
    target_name = target_lower.split("/")[-1]
    for c in candidates:
        if c["title"].lower() == target_lower or c["path"].lower().rstrip(".md") == target_lower.rstrip(".md"):
            return c
    for c in candidates:
        if Path(c["path"]).stem.lower() == target_name or c["title"].lower() == target_name:
            return c
    return None


def retrieve(question, vault_dir, data_dir=None):
    """Full ladder, steps 1-5. Returns the Evidence dict (step 6 — the single
    Hermes call — is the caller's responsibility, per the refactor map)."""
    t0 = time.time()
    reset_counters()
    vault_dir = Path(vault_dir)
    tokens, phrases = parse_query(question)

    index_result = score_index(question, vault_dir, data_dir=data_dir, top_n=5)
    results = index_result["results"]

    if not results or results[0]["score"] < MIN_SCORE:
        return {
            "page_title": None,
            "page_path": None,
            "domain": None,
            "section_heading": None,
            "text": None,
            "followed_pointer": False,
            "runner_up": None,
            "ladder_ms": int((time.time() - t0) * 1000),
            "candidates_scored": index_result["candidates_scored"],
            "semantic": index_result["semantic"],
            "found": False,
        }

    top = results[0]
    runner_up = None
    if len(results) > 1 and (top["score"] - results[1]["score"]) <= 0.03:
        runner_up = results[1]["path"]

    # STEP 3 — open exactly the top-scoring file
    page_path = vault_dir / top["path"]
    if not page_path.exists():
        return {
            "page_title": top["title"], "page_path": top["path"], "domain": top["domain"],
            "section_heading": None, "text": None, "followed_pointer": False,
            "runner_up": runner_up, "ladder_ms": int((time.time() - t0) * 1000),
            "candidates_scored": index_result["candidates_scored"],
            "semantic": index_result["semantic"], "found": False,
        }
    raw = _read_page_file(page_path)
    body = raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            body = raw[end + 4:]

    # STEP 4 — section, not doc
    heading, text = _pick_best_section(body, tokens, phrases)

    followed_pointer = False
    current_title, current_path, current_domain = top["title"], top["path"], top["domain"]

    # STEP 5 — follow one pointer, exactly once
    if _is_mostly_pointer(text):
        link_target = _extract_pointer_target(text)
        if link_target:
            _, all_candidates_hash = None, None
            candidates, _ = load_candidates(vault_dir)
            target_candidate = _resolve_path_from_candidates(link_target, candidates)
            if target_candidate:
                target_path = vault_dir / target_candidate["path"]
                if target_path.exists() and target_path != page_path:
                    raw2 = _read_page_file(target_path)
                    body2 = raw2
                    if raw2.startswith("---"):
                        end2 = raw2.find("\n---", 3)
                        if end2 != -1:
                            body2 = raw2[end2 + 4:]
                    heading2, text2 = _pick_best_section(body2, tokens, phrases)
                    heading, text = heading2, text2
                    current_title = target_candidate["title"]
                    current_path = target_candidate["path"]
                    current_domain = target_candidate["domain"]
                    followed_pointer = True

    ladder_ms = int((time.time() - t0) * 1000)
    return {
        "page_title": current_title,
        "page_path": current_path,
        "domain": current_domain,
        "section_heading": heading,
        "text": text,
        "followed_pointer": followed_pointer,
        "runner_up": runner_up,
        "ladder_ms": ladder_ms,
        "candidates_scored": index_result["candidates_scored"],
        "semantic": index_result["semantic"],
        "found": True,
    }
