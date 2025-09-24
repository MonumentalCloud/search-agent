# Custom Weaviate Build — README for Cursor & Agent Integration

This README tells Cursor exactly how to **stand up a Weaviate-based retrieval stack**, ingest your **internal PDFs**, and integrate with the **LangGraph agent** we designed (soft metadata priors, chunk memory, validator loop). It’s architecture-first and implementation-ready.

---

## 0) Objectives
- Stand up Weaviate with a **Document/Chunk** schema optimized for 1M+ chunks.
- Build an **ingestion pipeline** for PDFs → sections → chunks → entities → metadata.
- Implement **soft, schema-aware metadata guidance** using **per-facet-value vectors** (not brittle enums).
- Add **chunk-level memory** (decayed trust + query centroid) to reward proven passages.
- Wire Weaviate into the **LangGraph nodes** (candidate → facet planning → narrowed search → rerank → validator → memory update).

---

## 1) System Overview (boxes → arrows)

```
[ PDFs / Internal Docs ]
       |  (extract)
       v
[ Normalizer + Sectionizer ] --(headings)--> [ Sections ]
       |  (chunk 400–900 toks, +overlap)
       v
[ Chunker ] --(entities, facets, dates)--> [ Enriched Chunks ]
       |  (embed body)
       v
[ Embedding Pipeline ]
       |  (batch import)
       v
[ Weaviate ]  <--(facet-value vectors)--- [ Facet Vector Builder ]
       ^  ^
       |  |(search, agg, where)
       |  +------ [ Weaviate Adapter ]
       |
[ LangGraph Agent ]: listener → planner → candidate → facet_planner → narrowed → rerank+MMR+soft_priors+memory → validator → answer → memory_updater
```

---

## 2) Weaviate Setup (infrastructure)
- **Vectorizer**: external embeddings (recommended) or built-in (text2vec-xxx). Keep it simple for Cursor; start with **external**.
- **Hybrid Search**: enable BM25 + vector. Tune `alpha` per query type (planner sets this).
- **Batch Import**: import in batches of 200–1,000 objects, single client instance.
- **Persistence**: enable volume mounts; memory ≥ 8–16 GB for 1M+ chunks.

**ENV** (example names):
```
WEAVIATE_ENDPOINT=http://localhost:8080
WEAVIATE_API_KEY=...
EMBED_MODEL=openai/text-embedding-3-large
EMBED_API_KEY=...
```

---

## 3) Weaviate Schema

### 3.1 Classes
- **Document** (1 per source file / version)
  - `doc_id: string` (**filterable**, unique)
  - `title: text`
  - `doc_type: string` (**filterable**) — e.g., law, policy, faq, rfc, label
  - `jurisdiction: string` (**filterable**) — e.g., KR, EU, US
  - `lang: string` (**filterable**) — e.g., ko, en
  - `valid_from: date` (**filterable**)
  - `valid_to: date|null` (**filterable**)
  - `entities: [string]` (**filterable**) — canonical + spacing/alias variants

- **Chunk** (passage-level unit)
  - `chunk_id: string` (**filterable**, unique)
  - `doc_id: string` (**filterable**, FK to Document)
  - `section: string` (**filterable**) — normalized heading (e.g., eligibility, definitions)
  - `body: text` (vectorized)
  - `entities: [string]` (**filterable**)
  - `valid_from: date` (**filterable**)
  - `valid_to: date|null` (**filterable**)
  - `created_at: datetime` (**filterable**)
  - `updated_at: datetime` (**filterable**)
  - `of_doc: ref(Document)` (optional convenience link)

> All fields likely used in filters must be **filterable**. Dates should be proper date/datetime types.

### 3.2 Side Classes (optional but recommended)
- **FacetValueVector**
  - `facet: string` (e.g., section, doc_type, jurisdiction, lang)
  - `value: string` (e.g., eligibility, law, KR, ko)
  - `aliases: [string]` (spacing/typo variants)
  - `vector: float[]` (embedding)
  - `updated_at: datetime`

- **ChunkStats** (chunk-level memory)
  - `chunk_id: string`
  - `useful_count: int`
  - `last_useful_at: datetime`
  - `intent_hist: map[string,int]`
  - `entity_hist: map[string,int]`
  - `query_centroid: float[]` (embedding)
  - `decayed_utility: float`

> If you’d rather keep memory outside Weaviate, mirror **ChunkStats** in Postgres. Either is fine for v1.

---

## 4) Ingestion Pipeline (PDF → Weaviate)

### 4.1 Input contract
Your internal PDF(s) will be processed into a **NormalizedDocument**
```
NormalizedDocument {
  doc_id, source, title, url?, lang, jurisdiction?, doc_type?,
  valid_from?, valid_to?,
  raw_text, html?,
}
```

### 4.2 Extraction
- Use any PDF text extractor (e.g., pdfminer, PyMuPDF). Preserve paragraph breaks.
- Keep a sidecar `provenance` record (file path, SHA256, fetched_at).

### 4.3 Sectionization (critical)
- Prefer heading-aware rules: numbered headings (1., 1.1, I., A.), Korean law patterns ("제\d+조"), RFC-style sections, SPL sections.
- If headings unclear, fallback: **density/length heuristic** + title-case lines + font-size cues (if available).
- Output **Sections** with `{section_id, heading_normalized, order, text}`.

### 4.4 Chunking
- Split each Section to **400–900 tokens**; overlap **50–100**.
- Carry `section` name to metadata.
- Compute **entities** (see 4.5) and **dates** for each chunk if available; else inherit from Document.

### 4.5 Entities & Aliases (KO-robust)
- Extract entities with your preferred NER or dictionary + LLM confirmation.
- Generate **spacing variants** and **aliases** at ingest: e.g., `출산 장려금`, `출산장려금`.
- Store all variants in `entities[]` for both Document and Chunk.

### 4.6 Temporal Fields
- For legal/policy docs, set `valid_from/valid_to` from revision dates (시행일, 개정일). If unknown: `valid_from = created_at`, `valid_to = null`.

### 4.7 Embeddings & Import
- Embed `Chunk.body` using the configured model.
- Batch import **Document** then **Chunk** objects into Weaviate.
- Ensure **doc_id** consistency and idempotent upserts (same IDs → update).

---

## 5) Facet-Value Vectors (soft metadata prior)

### 5.1 Why
LLMs are bad at copying exact labels; we use **vector similarity** on metadata to nudge retrieval, without hard filters.

### 5.2 Build
For each facet value (e.g., `section=eligibility`, `doc_type=law`):
- Create a short **typed description** prompt (e.g., "This is a *section* label meaning eligibility criteria…").
- Sample **3–10 sentences** from chunks that carry that value.
- Add **aliases/spacing variants**.
- Concatenate → **embed** → store in **FacetValueVector**.

### 5.3 Query-time weights
- Embed the **user query**.
- Compute cosine similarity to all relevant **FacetValueVector** rows.
- Take **top-M per facet** (e.g., M=2) to form weights `w ∈ [0,1]`:
  - Example: `section: {eligibility: 0.77, definitions: 0.31}`; `doc_type: {law: 0.82}`

### 5.4 Apply as soft prior
During rerank, add a small bump:
```
final_score = content_score
            + λ_meta * ( w(section=chunk.section)
                       + w(doc_type=chunk.doc_type)
                       + w(lang=chunk.lang) + ... )
```
- Cap λ so it **nudges** but doesn’t override relevance.

---

## 6) Chunk-Level Memory (what helped before)

### 6.1 Fields (ChunkStats)
- `useful_count`, `last_useful_at`
- `intent_hist` (e.g., legal/how-to/definition)
- `entity_hist` (from queries that validated this chunk)
- `query_centroid` (mean of past successful query embeddings)
- `decayed_utility` (recent wins count more; old wins fade)

### 6.2 Update Policy
- Only update when **Validator** approves the final answer.
- Decay weekly (half-life 4–8 weeks). Reset `last_useful_at` each win.

### 6.3 Ranking Bonus
- In rerank stage, add: `λ_mem * ( utility + cos(q, query_centroid) + intent_match_bonus )` (capped).
- Keep **exploration ratio** (e.g., 15%) so new chunks can surface.

---

## 7) Agent Integration (LangGraph nodes)

**Node responsibilities (match file names):**
- `listener`: normalize q; detect lang/time; extract light entities.
- `planner`: set `intent`, `alpha` (hybrid tilt), initial facet hypotheses.
- `candidate_search`: Weaviate hybrid search, `limit≈300`, optional time clamp.
- `facet_planner`: compute metadata weights via **FacetValueVector**; propose 1–3 facet sets (branches).
- `narrowed_search` (parallel): for each facet set, run aggregate count; pick branch yielding 80–300 candidates; run narrowed hybrid (`limit≈200`).
- `rerank_diversify`: cross-encoder rerank + MMR; add **soft metadata prior** + **chunk memory bonus**; keep top 20–40.
- `validator`: check grounding/time validity; if NO, return action (`DRILLDOWN`/`RELAX`/`PIVOT`).
- `answerer`: compose with citations + date qualifiers.
- `observer`: log timings, params, facet weights, chosen branch.
- `memory_updater`: write QueryProfile, RetrievalEvents, Outcome; update ChunkStats.

**Config knobs (YAML):**
```
weaviate:
  endpoint: ${WEAVIATE_ENDPOINT}
  api_key: ${WEAVIATE_API_KEY}
  classes: { document: Document, chunk: Chunk }
  stage1_limit: 300
  stage3_limit: 200
  default_alpha: 0.5
facets:
  names: [doc_type, section, jurisdiction, lang]
  soft_vector: { top_per_facet: 2, weight: 0.2 }
memory:
  weight: 0.15
  half_life_weeks: 6
  exploration_ratio: 0.15
rerank: { provider: local_or_api, mmr_lambda: 0.4 }
validator: { max_iters: 2, confidence_threshold: 0.75 }
```

---

## 8) Ingestion Tasks for Cursor (CLI specs)

Implement these minimal commands (FastAPI/Click—developer’s choice). Each task should be idempotent.

1. `ingest register-source --path <pdf> --doc-type <law|policy|...> --jurisdiction <KR|EU|...> --lang <ko|en> --valid-from <YYYY-MM-DD> [--valid-to <YYYY-MM-DD>]`
   - Extract text; create NormalizedDocument; store provenance.

2. `ingest sectionize --doc-id <id>`
   - Produce Sections with headings.

3. `ingest chunk --doc-id <id> --maxlen 900 --overlap 80`
   - Create Chunks from Sections.

4. `ingest enrich --doc-id <id>`
   - Entities, spacing/alias expansion; fill `entities[]`.

5. `ingest embed --doc-id <id>`
   - Compute embeddings for `Chunk.body`.

6. `ingest upsert --doc-id <id>`
   - Batch import Document then Chunks to Weaviate.

7. `facets rebuild-vectors --facet <name|all>`
   - Rebuild **FacetValueVector** from label+aliases+sample sentences.

8. `verify sanity --doc-id <id>`
   - Run probe queries; confirm filters/time clamps work.

> Provide a `jobs/` folder with JSONL manifests to run these in order for many PDFs.

---

## 9) Acceptance Tests (must pass)

1. **Schema Check**: Both classes created with filterable fields; aggregates and where-filters succeed.
2. **Hybrid Sanity**: For a simple query, `alpha=0.25` (entity-heavy) and `alpha=0.6` (semantic) produce different but plausible candidate sets.
3. **Soft Metadata Prior**: With facet vectors enabled, candidates whose metadata matches top weights rise ≥5 ranks on average (vs. disabled).
4. **Chunk Memory Effect**: After 3 validated runs of a similar question, a historically helpful chunk rises ≥5 ranks on average.
5. **Temporal Clamp**: `as of <date>` queries exclude chunks outside `valid_from/valid_to`.
6. **KO Spacing Robustness**: `"출산 장려금"` vs `"출산장려금"` share ≥60% of top-20 after rerank.
7. **Validator Loop ≤ 2**: Hard queries cause at most two plan/relax loops before answer or fallback.

---

## 10) Observability & Telemetry
- Per-stage latency, alpha, facet weights, branch counts.
- Rerank top-K with scores before/after soft priors + memory bonus.
- Validator verdict & reason.
- Memory deltas (which chunks updated).

Store these under a `trace_id` and expose `GET /debug/trace/{id}`.

---

## 11) Performance Notes
- Keep Stage-1 `limit ≤ 500` to cap vector scoring cost.
- Use Document-level aggregates (smaller cardinality) to estimate branch sizes when possible.
- Batch size auto-tune (start 256); reuse a single Weaviate client.
- If latency high: add a **hotset** (top decayed-utility chunks) as a fast-path first hop.

---

## 12) Security & Governance
- PDFs may include sensitive info. Ensure:
  - No raw content in logs.
  - PII scrub in entities (if applicable).
  - Provenance retained for audits.

---

## 13) Roadmap (after v1)
- Add **dynamic facet discovery** node (optional; complements soft priors).
- Add **bandit selection** (UCB/Thompson) for exploration vs exploitation.
- Weekly micro-tuning of reranker with collected RetrievalEvents/Outcomes.
- Plug a **KGAdapter** later; memory loop stays identical.

---

## 14) Glossary (plain language)
- **Facet**: a metadata field like `doc_type` or `section`.
- **Facet-value vector**: an embedding representing a particular value (e.g., `section=eligibility`), built from examples and aliases.
- **Soft prior**: a small score bonus based on metadata similarity; not a hard filter.
- **Chunk memory**: tiny per-chunk stats that reward passages that worked before.
- **Hybrid search**: mix of keyword (BM25) + vector similarity.
- **MMR**: de-dup/diversify similar results.

---

## 15) Hand-off to Cursor
- Scaffold `adapters/weaviate_adapter.py` with methods: `ensure_schema()`, `batch_upsert_documents()`, `batch_upsert_chunks()`, `hybrid_query()`, `aggregate_group_by()`, `build_where()`.
- Scaffold `ingestion/` CLI tasks matching Section 8.
- Implement `FacetValueVector` store + similarity routine.
- Implement LangGraph nodes listed in Section 7 with clean interfaces.
- Add tests matching Section 9 acceptance criteria.

> Keep prompts minimal and explicit; prefer tool outputs (facet weights, counts) over free-form LLM text. This ensures determinism and debuggability.

