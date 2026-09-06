# Bryggeskole Course Fact Registry V1

Version: 1.0
Status: Active
Governed by: GitHub issue #65 (locked Bryggeskole product direction —
"AI may research, compare, explain and write pedagogically — AI is
never the source") and GitHub issue #78 (`ROADMAP V2`, item **V2-2 —
Verified Knowledge Foundation / Course Fact Registry**). Implemented by
issue #89 (**V2-2A — registry contract + validation foundation only**).

This is not a locked text. It is a versioned document. Changes require
explicit review and a version increment.

---

## 0. Purpose and non-goals

**Purpose:** define a small, trustworthy, machine-readable substrate
for brewing-knowledge claims/facts that later Bryggeskole content,
questions, mastery logic, and (much later) Sóti tutoring can point
back to, so that "why does the course say this?" always has a
traceable, sourced answer.

**Non-goals for V1 (deliberately out of scope):**

- no course UI, no Web/App teaching surface, no question engine, no
  mastery model, no fermentation course content;
- no crawler/scraper, no automatic source ingestion;
- no RAG/vector database/knowledge graph, no runtime service;
- no LLM fact generation, no Sóti integration;
- no real factual corpus build — this round ships the container and
  guardrails, not the knowledge itself (see §9);
- no legal-regulation content;
- no network calls, no deployment, no auto-merge.

Ownership stays exactly as established in
[KBH_CORE_CONTRACT.md](KBH_CORE_CONTRACT.md) Section 1 and the ROADMAP
V2 issue (#78): Bryggeskole owns teaching use of verified knowledge;
this registry is a shared knowledge foundation, not a course page.
Core's own contracts/calculations/masterdata (`core/`, `data/master_*`)
remain separate — nothing here moves, mirrors, or reinterprets an
existing Core truth just to populate this registry. Brew Lab
observations/hypotheses remain a distinct domain from verified course
facts. Sóti gets no integration in this slice. Legal claims/research
remain outside Bryggeskole ownership and are not seeded here.

---

## 1. Where this lives

| Artifact | Path |
|---|---|
| This contract | `docs/development/BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md` |
| The registry itself (currently empty — see §9) | `bryggeskole/data/course_fact_registry.json` |
| Pure stdlib validator/reader | `bryggeskole/course_fact_registry.py` |
| Package entry point (re-exports the above) | `bryggeskole/__init__.py` |
| Tests | `tests/test_course_fact_registry.py` |
| Synthetic fixtures (valid + every invalid shape) | `tests/fixtures/course_fact_registry/*.json` |

No database, no vector store, no network dependency, no runtime
service: the registry is one deterministic, UTF-8, human-reviewable
JSON file, and the validator is a pure function over a parsed Python
object plus a thin file-reading wrapper — the same "container and
guardrails, not the knowledge corpus" shape the governing issue asks
for.

---

## 2. Record shape

A registry document is one JSON object:

```json
{
  "schema_version": 1,
  "records": [ /* zero or more record objects, see below */ ]
}
```

No other top-level field is accepted (see §13 on the unknown-field
policy). `schema_version` must currently be exactly `1`
(`REGISTRY_SCHEMA_VERSION` in the validator) — a future breaking change
to the record shape requires an explicit version bump, never a silent
reinterpretation of `1`.

One record:

```json
{
  "id": "FACT-BREW-0001",
  "claim": "…the actual claim text…",
  "classification": "documented_fact",
  "status": "verified",
  "sources": [
    { "tier": "A", "type": "manufacturer technical datasheet", "ref": "https://…", "note": "optional" }
  ],
  "verified_at": "2026-09-01T12:00:00Z",
  "notes": "optional free-text uncertainty/context",
  "concepts": ["gjaring.temperatur"],
  "modules": ["fermentation-101"]
}
```

A source object:

```json
{ "tier": "A", "type": "…", "ref": "…optional…", "note": "…optional…" }
```

---

## 3. Required vs optional fields

| Field | Required? | Notes |
|---|---|---|
| `id` | **Required** | See §4. |
| `claim` | **Required** | Non-empty string. The actual statement text. |
| `classification` | **Required** | One of §5's four values. |
| `status` | **Required** | One of §6's four values. |
| `sources` | Optional in general, **required in substance when `status == "verified"`** | List of source objects, see §7. |
| `verified_at` | Optional in general, **required when `status == "verified"`** | See §9. |
| `notes` | Optional | Free-text uncertainty/context, see §11. |
| `concepts` | Optional | List of concept/topic strings, see §10. |
| `modules` | Optional | List of course-module reference strings, see §10. |

No field beyond this table is accepted on a record — see §13.

---

## 4. Stable ID policy

**Format:** `FACT-<DOMAIN>-<4 digits>`, e.g. `FACT-BREW-0001`. `DOMAIN`
is free-form uppercase `A-Z0-9` (not an enumerated list in V1, so a new
knowledge domain never requires a validator change), and the numeric
suffix is exactly four digits. Enforced by `ID_PATTERN` in
`bryggeskole/course_fact_registry.py`.

By convention (not a rule the validator enforces), `TEST` is the
reserved domain for synthetic fixtures — e.g. `FACT-TEST-0001` — so a
fixture id can never be mistaken for a real domain id at a glance.

Rules, all fail-closed and tested (`tests/test_course_fact_registry.py`):

- **Stable once published** — an id, once it exists in the committed
  registry, is never reassigned to a different claim. Nothing in this
  round automates or enforces this across time (no diff-based
  "id reused" check); it is an editorial rule stated here.
- **Independent of wording edits** — an id never encodes the claim
  text itself, so wording refinements never require an id change.
- **Never derived from array position** — the id lives on the record,
  not implied by its index in `records`; reordering the array never
  changes an id.
- **Duplicate ids fail** the whole document (§13) — the validator
  collects every duplicate, not just the first.
- **Never silently regenerated by the reader** — `validate_registry()`
  and `read_registry_file()` only ever read; neither one ever mutates,
  renumbers, or invents an id.

---

## 5. Classification semantics (what kind of statement)

The exact four values required by issue #65, independent of §6:

| Value | Meaning |
|---|---|
| `documented_fact` | A directly documented, sourced fact. |
| `professional_interpretation` | A reasoned, domain-professional interpretation of underlying facts. |
| `practical_experience` | Practical/experiential knowledge (e.g. an established brewing practice), not necessarily a formally documented fact. |
| `hypothesis` | A hypothesis or input — e.g. sourced from a Tier D forum/video (§8) — not yet elevated to a documented fact. |

### 5.1 Deliberately not reusing Core's `claim_evidence_types`

[`CORE_STATUS_PROVENANCE.md`](CORE_STATUS_PROVENANCE.md) §3 already
defines a five-value `claim_evidence_types` axis
(`documented_fact` / `documented_observation` / `interpretation` /
`assumption` / `proposal`) for the **Core** masterdata domain. That
vocabulary is not reused here: it governs a different domain (Core
brewing masterdata) with a different shape, and issue #65 specifies its
own four-value list for Bryggeskole course knowledge. This mirrors the
precedent `CORE_STATUS_PROVENANCE.md` §3.1 already set for the separate
Vault Canon `source_layer` model — two genuinely different vocabularies
for two different domains are not harmonized just because both happen
to use the string `documented_fact` for their first value. No attempt
was made to unify them in this round; that would be a real governance
decision with no basis to make unprompted here.

---

## 6. Verification-status semantics (lifecycle, independent of §5)

| Status | Meaning |
|---|---|
| `draft` | Proposed or in progress. Must **not** be treated as verified canonical course knowledge. |
| `reviewed` | Reviewed by a human/professional process. Not necessarily sourced well enough yet to be `verified`. |
| `verified` | Kvernhaug's best current verified representation of this claim. Requires at least one source (§7) and a `verified_at` timestamp (§9). See §9 for exactly what this does and does not mean. |
| `deprecated` | Must not be used as current canonical course knowledge. Kept for history; should reference a replacement claim in `notes` where relevant. |

Only the forward path is defined in V1: `draft → reviewed → verified →
deprecated`. Rollback/reopen transitions are **not** defined in this
round — same precedent as `CORE_STATUS_PROVENANCE.md` §1.2: if a real
need for one arises, it should be proposed and reviewed explicitly
then, not pre-designed speculatively here.

**Nothing in this round promotes a record between statuses.** The
validator is read-only with respect to status: it checks that
`verified` records carry the provenance §9 requires, but it never
raises a record from `draft`/`reviewed` to `verified` itself, and nor
does anything else in this PR. That remains an explicit, external
editorial decision every time.

Classification (§5) and status (§6) are two independent axes — the
value sets are disjoint by construction and tested to remain so
(`TestValueSetsAreExplicitAndDistinct`), exactly as issue #89 requires:
a claim can be `hypothesis` + `draft`, `hypothesis` + `verified` (a
hypothesis that has itself been verified to genuinely originate from a
Tier D source, without becoming a `documented_fact`), `documented_fact`
+ `draft` (a fact whose sourcing is not yet reviewed), and so on — the
two never collapse into one meaning.

---

## 7. Source / provenance shape

Each entry in a record's `sources` list:

| Field | Required? | Meaning |
|---|---|---|
| `tier` | **Required** | One of the four §8 values `A`/`B`/`C`/`D`. |
| `type` | **Required** | Non-empty free-text description of the kind of source (e.g. `"manufacturer technical datasheet"`, `"peer-reviewed study"`). Not an enumerated vocabulary in V1. Must not be an AI/model name (§16). |
| `ref` | Optional in general, **required in substance on at least one source when `status == "verified"`** (§9) | A pointer to the actual source (URL, document name, citation) — not the source content itself. Must not be an AI/model name (§16). |
| `note` | Optional | Free-text context about this specific source. |

A source with `tier`/`type` but no `ref` is a legitimate provenance
entry for `draft`/`reviewed`/`hypothesis` records — it says "this is
the kind of source we expect to cite" without yet pointing at a
specific one. It is **not**, by itself, sufficient to reach `verified`
(§9): `type` only classifies what *kind* of source is claimed; `ref`
is what actually identifies *which* source it is.

No other field is accepted on a source object (§13). The registry
**never infers a tier automatically** — every source must declare its
own tier explicitly; there is no heuristic in `course_fact_registry.py`
that guesses a tier from a URL, domain name, or source type.

---

## 8. Source-tier semantics (A–D)

The existing #65 hierarchy, unchanged:

- **A** — research, universities, standards, manufacturer technical
  primary documentation.
- **B** — solid technical books and established secondary sources.
- **C** — retailers and market/industry material.
- **D** — forums, Reddit, YouTube, TikTok etc. — hypothesis/input
  sources, **never** authoritative by themselves.

A Tier D source is a legitimate provenance entry for a `hypothesis`
classification (§5) or a `draft`/`reviewed` status (§6) — it is simply
never, by itself, sufficient to reach `verified` status in the sense a
future editorial review process would require (that review process
itself is out of scope for this round; the validator only enforces the
structural minimum in §9, not an editorial tier-sufficiency policy).

---

## 9. Timestamp rules and what `verified` does / does not mean

`verified_at`, when present, must be an ISO 8601 timestamp with an
**explicit UTC offset** (`Z` or `±HH:MM`) — `_TIMESTAMP_PATTERN` in the
validator. "Verified at some unspecified local time" is not accepted:
a claim that is supposed to be independently checkable needs an
unambiguous verification instant.

**Required exactly when `status == "verified"`:** a record cannot be
`verified` without *all three* of: at least one entry in `sources`;
that at least one of those sources carries a concrete, non-empty `ref`
(§7) — a real pointer to the source, not merely its `tier`/`type`
metadata; and a valid `verified_at`. The validator rejects each gap
independently (a record missing more than one of these fails all of
the relevant checks at once and gets every applicable error message,
not just the first). A source with `tier`/`type` but no `ref` counts
toward "at least one entry in `sources`" but **not** toward the `ref`
requirement — `{"tier": "A", "type": "manufacturer technical
datasheet"}` alone is not enough to verify a claim; something has to
actually identify *which* datasheet.

**What `verified` means:** this is Kvernhaug's best current verified
representation of the claim, backed by at least one explicitly tiered
source with a concrete reference, as of `verified_at`.

**What `verified` does *not* mean:**

- it does **not** mean eternal, unrevisable truth — the same principle
  [`KBH_CORE_CONTRACT.md`](KBH_CORE_CONTRACT.md) already states for
  Core's own canonical master applies here too;
- it does **not** mean multiple independent sources were required — §7
  only requires *at least one*; issue #65's guidance that important or
  disputed claims *should* be backed by multiple independent sources
  "so far as practically possible" is an editorial best practice, not
  a structural minimum this validator enforces in V1;
- it does **not** mean the claim has been automatically fact-checked —
  nothing in this codebase calls the network or cross-references any
  external source; a human/professional review process outside this
  registry is what actually moves a record to `verified`;
  the registry only checks the *shape* of that claim after the fact;
  it never performs the review itself (see §0's non-goals);
  no fact-checking pipeline exists or is implied by this document;
- it does **not** mean a Tier D source is now authoritative — §8's
  hierarchy is unchanged; `verified` + a single Tier D source is
  structurally legal but is a `hypothesis`-classification record whose
  reviewer chose to record it as verified-to-have-been-said-by-that-
  source, not verified-as-brewing-fact — classification (§5) and
  status (§6) staying independent (§6) is exactly what keeps this
  distinction visible instead of collapsing it.

**No real brewing claim is marked `verified` by this PR.** The shipped
production registry (`bryggeskole/data/course_fact_registry.json`) has
zero records — this round ships the container and guardrails only, per
the governing issue's explicit preference for zero real verified
claims in V2-2A. `tests/test_course_fact_registry.py`
(`TestProductionRegistryFileIsValidAndHasNoRealVerifiedClaims`) asserts
this stays true for as long as this test exists unchanged.

---

## 10. Concept/topic and course-module references

`concepts` and `modules` are both optional lists of non-empty,
non-duplicated opaque strings (e.g. `"gjaring.temperatur"` for a
concept, `"fermentation-101"` for a module). V1 does **not** define an
enumerated vocabulary for either — no fixed concept taxonomy and no
course-module registry exist yet to validate against, so these are
free-form references today, structurally checked (non-empty, list
shape, no duplicates within the same record) but not checked against
any external list. A future round that introduces a real concept
taxonomy or module registry can add that cross-check without breaking
this shape.

---

## 11. Uncertainty / notes semantics

`notes`, when present, is a free-text string for uncertainty, caveats,
or context that does not fit any structured field above (e.g. "conflicting
sources exist for this temperature range", "confirmed only for ale
strains, not yet checked for lager strains"). It is not structured or
parsed by the validator, and it is not a substitute for `sources` —
uncertainty about a *documented* claim still needs its documentation in
`sources`; `notes` is for uncertainty *about* the claim itself.

---

## 12. Concept independent of Core's `confidence` exclusion

No `confidence` field exists in this record shape, for the same reason
[`CORE_STATUS_PROVENANCE.md`](CORE_STATUS_PROVENANCE.md) §4 excludes
one from Core's own model: a numeric/qualitative confidence score would
either duplicate `status` (how far a claim has been quality-assured) or
duplicate `classification` (what kind of claim it is), creating double
semantics for the same underlying question. If a genuine need for a
distinct confidence axis emerges later, it should be proposed and
reviewed explicitly then.

---

## 13. Validation / fail-closed rules

`bryggeskole/course_fact_registry.py` fails closed: `validate_registry()`
never repairs, guesses, or silently drops a malformed record — it
collects every problem it finds into a list of human-readable error
strings (empty list == valid) and returns them all, so a caller sees
everything wrong in one pass. `read_registry_file()` is the convenience
wrapper that raises `CourseFactRegistryError` (carrying that same
`.errors` list) when the list is non-empty, or on invalid JSON.

At minimum, the validator rejects, all covered by synthetic fixtures in
`tests/fixtures/course_fact_registry/` and asserted in
`tests/test_course_fact_registry.py`:

- a missing or invalid stable `id` (§4);
- a duplicate stable `id` anywhere in the document (§4);
- an invalid `classification` value (§5);
- an invalid `status` value (§6);
- a malformed `sources` collection — not a list, a non-object entry,
  or an entry missing `tier`/`type` (§7);
- an invalid source `tier` (§8);
- a `verified` record with no source at all (§9);
- a `verified` record whose source(s) carry `tier`/`type` metadata but
  no source has a concrete, non-empty `ref` (§7, §9);
- a `verified` record with a missing or invalid `verified_at` (§9);
- a malformed `concepts`/`modules` collection — not a list, an
  empty/non-string entry, or a duplicate entry (§10);
- an AI/model name presented as a source `type` or `ref` (§16);
- any unrecognized field at the document, record, or source level
  (§14 below);
- a document that is not a JSON object, whose `schema_version` is not
  the current `1`, or whose `records` is not a list at all.

The validator never calls the network, never performs automatic fact
checking beyond the structural checks above, and never promotes a
record's status (§6).

---

## 14. Forward-compatibility / unknown-field policy

**V1 policy: strict, no escape hatch.** Any field not explicitly listed
in §2/§3 (document level), §3 (record level), or §7 (source level) is
rejected outright — there is no reserved passthrough namespace (unlike,
e.g., `_kbh_passthrough` in `modules/kbh_contract.py`, which exists for
a genuinely different problem: preserving fields a *different* system
already owns across a round-trip). A future genuinely new field is a
deliberate schema change, expressed as a `schema_version` bump, not a
silently-accepted new key under the current version. This keeps a
malformed or drifted record visibly wrong instead of quietly widening
what "valid V1" means over time — consistent with "fail closed" being
the explicit design goal for this whole registry, not merely one of
its checks.

---

## 15. What `verified` does and does not mean

See §9 — kept together with the timestamp rules that structurally
enforce it, rather than duplicated as a separate section.

---

## 16. AI/model names are never accepted as a source

**Explicit statement, per issue #65's locked principle ("AI may
research, compare, explain and write pedagogically — AI is never the
source"):** no source `type` or `ref` may name an AI system or model as
the source of a claim. `_looks_like_ai_source()` in
`bryggeskole/course_fact_registry.py` checks a fixed, documented
word/phrase denylist (case- and diacritic-insensitive, whole-word
matched — e.g. `"ai"`, `"llm"`, `"gpt"`, `"chatgpt"`, `"claude"`,
`"anthropic"`, `"openai"`, `"gemini"`, `"copilot"`, `"mistral"`,
`"llama"`, `"bard"`, `"sóti"`/`"soti"`, `"large language model"`) after
folding accents and requiring word boundaries, so it rejects `"ChatGPT"`,
`"GPT-4"`, `"an LLM"`, and `"Sóti"` while not flagging ordinary words
that merely contain those letters as a substring (e.g. `"fair"`,
`"wait"`, `"chair"` never match, because `"ai"` only matches as a whole
token).

**Known, accepted limitation, stated plainly:** this is a fixed
heuristic denylist, not a real classifier — a genuine proper noun that
collides with a denylisted word (for example, a real person or
publication literally named "Claude") would be a false positive under
V1. This is an accepted trade-off for a hard "never" requirement in a
knowledge-integrity gate; a real collision, if it ever occurs, should
be reported and reviewed rather than worked around by silently loosening
the denylist.

This check applies to source `type`/`ref` only — it is not, and cannot
be, a general guarantee that no AI system was ever involved anywhere
upstream in how a human found or drafted a claim (e.g. AI-assisted
research is explicitly allowed by issue #65's own principle: "AI may
research, compare, explain and write pedagogically"). What it enforces
is narrower and structural: the **declared source of record** for a
claim can never itself be an AI/model name.

---

## 17. What this document does not do

- Does not build a course UI, question engine, mastery model, or any
  Bryggeskole content.
- Does not build a crawler, scraper, or automatic source-ingestion
  pipeline.
- Does not build a RAG/vector database/knowledge graph.
- Does not integrate Sóti in any way.
- Does not migrate, mirror, or reinterpret any existing Core masterdata
  (`core/`, `data/master_*.json`) into this registry.
- Does not introduce a real factual corpus — the shipped registry has
  zero records (§9).
- Does not define an editorial review workflow (who reviews, how many
  independent sources a disputed claim needs in practice, how a
  `draft → reviewed → verified` transition is actually performed) —
  only the structural minimum a valid `verified` record must satisfy.
- Does not harmonize this classification vocabulary with Core's
  `claim_evidence_types` or the Vault's Canon `source_layer` model
  (§5.1).
- Does not attempt automatic fact-checking, source-tier inference, or
  AI-authorship detection beyond the narrow declared-source-name check
  in §16.
