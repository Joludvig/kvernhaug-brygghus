# Bryggeskole Quiz Design Standard V1.1

Version: 1.1
Status: Active
Scope: every quiz question in the Kvernhaug Bryggeskole (`bryggeskole/data/pilot_*.json`), in Norwegian and English.
Adopted by: Chief decision after the Quiz Design Standard v1 review and the 12-question pilot (PR #511). Related earlier work: Phase 2 fact/terminology corrections (PR #509) and the answer-position fix (PR #510).

This is a versioned document. Changes require explicit review and a version increment.

---

## 0. How to read this document

Three kinds of statement are kept apart on purpose.

| Kind | Meaning | Effect |
|---|---|---|
| **Requirement** (MUST / MUST NOT) | A property a good question or the delivery layer must have. | A failure blocks acceptance. Judged by a reviewer. |
| **Guideline** (SHOULD / SHOULD NOT / MAY) | A default. | A deviation needs a one-line reviewer note. |
| **Diagnostic** | An automated or sampled measurement that tells reviewers where to look. | Raises a warning. A reviewer decides. Never blocks on its own, and never becomes a writing quota. |

Numeric measurements (length ratios, counts) are **diagnostics and health indicators, not quotas**. Nobody rewrites natural language only to silence a warning.

Section 13 lists what is new in v1.1 compared with v1.

Rule codes (A–F in section 4, G in section 5, H in section 6, I in section 7, R in section 3, T in section 11) are stable identifiers used for cross-references; sections are numbered separately.

---

## 1. Why this standard exists

A mechanical audit of the 99 active questions found the correct answer could often be found without the knowledge: it was the longest option in 93 of 99, it was the only hedged ("kan", "ofte", "avhenger") option in about a third, wrong options often contained absolutes ("alltid", "aldri", "ingenting"), and many stems were a friend making a false claim. A learner who ignored the lesson and chose the longest, most careful option scored about 90 %.

These numbers are historical context for the rules below. They are **not targets** and not acceptance criteria. The cure for the symptom (length) is not a length cap; it is the requirement that the answer cannot be identified from form (C2/E1), tested by a cue audit (section 9).

---

## 2. How the quiz system works (facts the standard relies on)

| Aspect | Fact |
|---|---|
| Format | Single choice. **Exactly 3 options** on every question. |
| Correct answer | Exactly one `correct: true` per question (validator-enforced). Evaluation is by option id, never by displayed position. |
| Feedback | One `feedback_correct` and one shared `feedback_incorrect` per question, NO + EN. Feedback does not depend on which wrong option was chosen. |
| Types | `scenario` and `concept_check`. |
| `difficulty` | `beginner` / `intermediate` in use; `advanced` allowed but unused. Independent of the course stage. |
| Course stage | Foundation / Kompetent live in `bryggeskole/data/course_stage_map.json`. Independent of `difficulty`. |
| `basis` | `fact` (claims resolve to verified registry records), `methodology` (Kvernhaug method content, no source claim), or unset in older modules (validated through `source_claims`). |
| Mastery | Per concept, keyed by question ID and the question's `concepts`. A first-attempt correct answer gains more than a recovery. A wrong answer never lowers mastery. No score, grade or lock. |
| Stakes | Formative. The learner can retry. |
| IDs | `Q-<MODULE>-NNN`. The ID is the key to stored learner state. |

---

## 3. Delivery and randomization requirements (not content design)

These are requirements on the app, not on question authors. The best-written question is still weakened if the delivery layer leaks the answer. Implemented in `bryggeskole/answer_order.py` and `ui/bryggeskole_panel.py` (PR #510).

| # | Requirement |
|---|---|
| **R1** | **MUST.** The displayed order of the options carries no information about which option is correct. |
| **R2** | **MUST.** The correct option's displayed position is drawn independently for each question. The previous question's position does not constrain the next one. The same position on consecutive questions is allowed, and natural streaks are acceptable. |
| **R3** | **MUST NOT.** No cross-question memory of correct positions: no "avoid the last position" and no "balance A/B/C over a round". Both make the next position predictable from the history. |
| **R4** | **MUST.** The order of the distractors is also drawn uniformly at random. |
| **R5** | **MUST.** The order chosen for a question stays stable within that question and round (reruns, submit and back/resume), so the learner cannot re-roll it. |
| **R6** | **MUST.** Evaluation is by option id, never by displayed index. |
| **R7** | **SHOULD.** Source order carries no meaning once R1–R4 hold, so authors may write options in any order. Keep a test showing the shuffle is applied on every delivery path. |

Background: the earlier rule "never the same correct position as the previous question" (issue #338) was deliberately reversed because it leaked information. After the feedback showed where the last correct answer sat, a learner could rule that position out and guess between two options instead of three.

---

## 4. Content design

### A. Learning objective

- **A1. MUST.** One primary objective per question, written as one sentence before drafting ("The learner can tell hot break from cold break."). The `concepts` list contains that concept.
- **A2. MUST NOT.** Two decisions in one item. Options like "ja til begge / nei til begge / bare …" are a sign to split (section 8 for IDs).
- **A3. MAY.** Test a reason together with a fact only when the reason is the objective. Otherwise the reason goes in the feedback.
- **A4.** The author's note names the cognitive level (section 6). It is not stored in the data.
- **A5. Concepts and mastery credit.** A question's `concepts` field states what the question intentionally assesses and what mastery credit is awarded for.
  - Do NOT add a concept merely because it appears in the feedback, is supporting knowledge, is needed to explain why a distractor is wrong, or is used incidentally while solving another objective.
  - Add a secondary concept only when (a) the learner genuinely must demonstrate that concept to answer, AND (b) awarding mastery credit for it is intentional.
  - If uncertain, keep the primary concept only and escalate to the Chief.

### B. Question wording

- **B1. MUST.** Natural bokmål, short and direct. No word-for-word English. Read it aloud once.
- **B2. MUST.** The stem contains no clue: no absolute word (*alltid, aldri, ingen, ingenting, uansett*) used as a signal, no CAPS emphasis, no phrasing only the correct option echoes. A negated stem ("Hvilket er IKKE …") only with IKKE emphasised, and only at L3 or above.
- **B3. MUST.** The stem states every assumption the answer depends on ("etter at gjæringen er i gang", "i en godt fylt kjele").
- **B4. MUST.** Every technical term in the stem or options was introduced in this module's lesson or a prerequisite. If a term is only there to be tested, introduce it in the lesson first. Otherwise the question tests vocabulary.
- **B5. SHOULD.** Prefer a neutral question to the "friend claims X — stemmer det?" frame. The frame is acceptable when recognising a *common belief* is itself the objective; then the claim must be plausible and free of absolutes. Drop filler such as "basert på det du har lært".
- **B6. SHOULD.** Prefer a concrete brewing situation at L3/L4. A scenario stem is 1–3 sentences at most.
- **B7. MUST.** Follow the glossary and person-reference conventions (section 7).

### C. Correct answer

- **C1. MUST.** Clearly and fully correct from the taught material alone; a learner who has read the lesson can defend it.
- **C2. MUST NOT.** Identifiable as correct from *form*: length, amount of detail, caution or hedging, a professional or technical register, grammatical shape, or information density. Tested by the cue audit (section 9).
- **C3. SHOULD.** One idea, stated plainly. Reasons, caveats and "but …" belong in `feedback_correct`.
- **C4. MUST.** If the truth needs a qualifier to be correct, the stem sets the context so the plain statement is true.

### D. Distractors

- **D1. MUST.** Each distractor is a *named misconception*: something a real beginner might believe, mis-remember or do. The review note writes the misconception down in one phrase. If it cannot be named, delete the distractor.
- **D2. MUST.** Each distractor is wrong for a meaningful reason the lesson explains. "It contains *aldri*" is not a reason.
- **D3. MUST NOT.** Joke or strawman distractors. Test: would a careful but unprepared reader consider it for a moment?
- **D4. SHOULD NOT.** Use gratuitous absolutes (*alltid, aldri, ingenting, uansett, ubegrenset, helt sikkert*). An absolute is allowed when it *is* the misconception, then at most one per question, and none when the stem already carries one.
- **D5. MUST NOT.** Introduce a concept the module has not taught merely to make a distractor wrong. Every concept word in a distractor is taught or an everyday word.
- **D6. MUST.** Grammatical form and information density comparable to the correct option. Distractors are not "the same sentence plus a negation", and not "a short wrong sentence" next to "a long careful sentence".
- **D7. SHOULD.** The two distractors are *different kinds* of wrong (for example one wrong fact, one right fact applied to the wrong situation).
- **D8. MUST NOT.** "All of the above / none of the above / both A and B". **MUST NOT** let the structure of a group of questions train a test-taking habit: if the wrong options in a group all sound overconfident and the right one always sounds careful, restructure the group (section 10).
- **D9. MUST.** No distractor is also correct under a reasonable reading. Review adversarially: argue for each distractor for 30 seconds.

### E. Option balance

- **E1. MUST.** The correct option cannot be identified from length, detail, caution, professionalism, grammar or information density. A reviewer applies the cue audit (section 9); the diagnostics in section 9.3 are prompts, not pass/fail numbers.
- **E2. SHOULD.** Epistemic form is comparable across options. See hedge balancing (technique T2, section 11). Where the objective is the *limit of a claim*, the wrong options overclaim or dismiss in the ordinary, confident voice of a real beginner, not in a cartoon voice.
- **E3. MUST NOT.** Ja/Nei prefixes on a question that is not yes/no. For a genuine yes/no question the options differ in substance after the same prefix.
- **E4. MUST NOT.** Make the correct option the only one with a different shape (a list, a quotation, two sentences, a clause break).
- **E5. MUST NOT.** Option text that refers to position or to other options ("Begge …", "som ovenfor").
- **E6. MUST.** Exactly 3 options. A harder question gets its difficulty from what the learner must do (section 6), never from a fourth option or from cleverer-sounding distractors.
- **E7.** Natural wording wins. Never lengthen a distractor with filler, or cut a correct answer to something unnatural, to satisfy a measurement.

### F. Feedback

The current shared `feedback_incorrect` model stays. Per-option feedback is deferred: the pilot did not justify it (section 13).

- **F1. MUST.** `feedback_correct` confirms *why* the answer is right in one or two sentences and does not just repeat the option. It MAY add at most one *grounded extra*: a boundary, a link to a neighbouring lesson idea, or a pointer to where to read more.
- **F2. MUST.** `feedback_incorrect` is written for *both* wrong options. It names the shared error (or, with two different errors, uses the two-part pattern in F4), states the correct idea, and points to the lesson. It does not argue against only one distractor.
- **F3. Grounding principle. MUST.** Feedback MAY clarify, connect or reinforce information that is already supported by the lesson or the fact ground. Feedback MUST NOT introduce an ungrounded new fact, or anything learners are later expected to know without having been taught it. Test: every factual claim in the feedback has a sentence in a lesson chunk (or a verified registry record), and the review note cites it. A "useful extra" that fails this test is a teaching gap (G4 in section 5), not feedback.
  Allowed: restating the lesson in plainer words; connecting to another idea the course already teaches; stating the limit of a claim already in the lesson; naming the misconception.
  Not allowed: a new number, a new mechanism, a new term, or a new rule of thumb.
- **F4. Two-part pattern for shared feedback_incorrect. MAY.** When the two distractors fail for different reasons, write:
  1. a short correction of misconception A;
  2. a short correction of misconception B;
  3. a grounded statement of the correct principle.
  The learner may read about an error they did not choose. Keep each part to one clause or one short sentence, and keep the whole feedback concise.
- **F5. MUST.** In a "what can be inferred" question the feedback states the limit explicitly ("lukten alene beviser ikke …").
- **F6. MUST NOT.** Grades, scores or shaming. "Ikke helt." is fine.
- **F7.** Where one shared feedback forces a distortion, do not distort the question. Record the case; it is evidence for or against a future per-option model.

---

## 5. Teaching-ground rule

- **G1. MUST.** Every knowledge claim in the stem, the correct option and the feedback is traceable to (a) a sentence in the module's teaching chunks and (b) for `basis: fact`, a verified registry record. The review note lists the chunk id and sentence.
- **G2. MUST.** Every concept in a distractor is taught or an everyday word.
- **G3. MUST.** The question requires no inference step the lesson did not model.
- **G4. When the wanted question exceeds the lesson** (the most important rule in this section):
  1. Do not write the question, and do not quietly widen the claim.
  2. Mark it **TEACHING GAP**: concept, the missing sentence, the likely fact source.
  3. If a verified fact already exists, propose the chunk text change (needs approval).
  4. If not, it goes through the fact-registry process (source, tier, Chief spot-check).
  5. Until then, restrict the question to what is taught, or defer it.
- **G5. `basis: methodology`** items test Kvernhaug's own method (observation vs interpretation, one change at a time). They are grounded in the methodology chunks. They MUST NOT imply a scientific fact.
- **G6.** Do not edit a teaching chunk merely to make a desired question work.

---

## 6. Authoring levels and progression (guidance only)

L1–L5 live in author notes and review tables. There is **no `level` field** in the data, no validator, and no schema change. The existing `difficulty` and the course stage are unchanged and remain independent.

| Level | What the learner does | What the wrong options look like | Typical home |
|---|---|---|---|
| **L1 Recognise** | Picks the taught fact or term. One step. | Two wrong ideas from the same lesson, each plausible to someone who skimmed. | Foundation |
| **L2 Understand** | Chooses the reason, or tells two ideas apart. | One reverses the relationship; one confuses two taught terms. | Foundation |
| **L3 Apply** | Chooses an action or prediction in a short scenario. | One is the usual beginner shortcut; one applies the right idea to the wrong situation. | Foundation (simple) / Kompetent |
| **L4 Diagnose** | Reads a symptom or a log and reasons about it. | One overclaims certainty; one dismisses or underclaims. Both are in the confident voice of a real person. | Kompetent |
| **L5 Reason** | Weighs trade-offs, compares causes, chooses what to measure next. | Several defensible options differing in cost or risk. | Reserved for an advanced track; no content yet |

- **H1.** Difficulty comes from the demand, not from distractor quality. A beginner item is not an advanced item with easier distractors.
- **H2. Concept repetition.** A concept may be tested again, in the same or another module, **when the cognitive demand genuinely differs.** Example, the sanitation boundary: L2 understand where the boundary lies; L3 apply it to an unwashed hose; L4 diagnose where a described process violated it. Reworded duplicates at the same demand are still undesirable: merge or retire them (section 8).
- **H3.** Do not raise difficulty with a fourth option, with more absolutes to avoid, or with subtler wording. Raise it by changing what must be done.
- **H4. Beginner threshold.** A foundation item SHOULD be answerable from one lesson paragraph, with a stem of at most two sentences, no unfamiliar abbreviation, and distractors drawn from the same paragraph. It SHOULD NOT depend on spotting "the careful option".
- **H5. L4 variety.** L4 must not become synonymous with "What can you conclude?". Across a module, vary the demand:
  - what follows from the observation?
  - what is one plausible cause?
  - what would you check next?
  - which observation best distinguishes two explanations?
  - what can and cannot be inferred?
  Every L4 question must still be answerable from the taught material (G3).

---

## 7. Language and glossary

- **I1. MUST.** NO and EN test the same concept at the same level, with the same distractor structure and option order. Translate meaning, not words. A hedge in one language ("ofte") is a hedge in the other ("often").
- **I2. MUST.** Terms follow the glossary below, in both languages.
- **I3. MUST.** Person references follow the style rule below.

| Concept | Use (NO, learner-facing) | May also appear | Avoid | EN |
|---|---|---|---|---|
| How much sugar the yeast eats | **utgjæring** | **attenuering** as a later technical synonym, alongside or after: "utgjæring (attenuering)" | attenuering as the first, unexplained term for beginners | attenuation |
| Adding yeast (beginner text) | **tilsette gjæren** | **pitche** later, or in parentheses when the brewing term is useful: "tilsette gjæren (pitche)" | "pitche" as the unexplained first term in foundation text | pitch the yeast / pitching |
| The beer | **ølet** (written standard) | – | "ølen" | the beer |
| Break and haze terms | **hot break**, **cold break**, **chill haze** (kept in English) | – | "kjøldis" for cold break | hot break, cold break, chill haze |
| Measured vs recipe values | **målt OG/FG** and **planlagt OG/FG** | – | bare "OG/FG" when the distinction matters | measured vs planned OG/FG |
| Gravity | **tetthet** | – | – | gravity |

**Person-reference style rule (project decision).** Do not use the gender-neutral third-person pronoun in learner-facing text, quiz text, feedback, glossary or authoring examples. When a person's sex/gender is known and relevant, use *han* or *hun*. When it is unknown or irrelevant, use *du*, a role noun (*bryggeren*, *eleven*, *personen*), or rewrite the sentence so no third-person pronoun is needed. This rule is not debated inside this standard.

**Conformance scope.** The glossary applies to new and rewritten text. Teaching chunks that still use older terms are changed only through a separate approved teaching change (G6).

Not yet decided (do not enforce): *vørteren / vørten / vørter*; the name of the traditional mash/lauter vessel; *gjæringslås / luftlås*.

---

## 8. Question IDs and learner state

| Case | Rule |
|---|---|
| Objective unchanged, wording rewritten | **Keep the ID.** |
| Double-barrel item split | The **old ID keeps the primary original objective.** A genuinely separate objective may receive a **new ID** (next free number in that module). Each item's `concepts` matches its own objective (A5). |
| Two items test the same objective at the same demand | May be merged; the redundant one may be **retired** (removed from the active set). The stronger item keeps its ID. |
| The tested concept changes | A different objective: new ID. Never reuse an old ID for a different concept. |
| Orphaned historical IDs | Existing learner state **must keep tolerating** IDs that no longer exist in the active set. Confirm this with a test before the first retirement lands. |
| Mastery | Per-concept mastery is unaffected by a rewrite that keeps the concept. A new ID for the same concept gives the learner a fresh first attempt for that item. |

---

## 9. Quality gate

The gate has three tiers. Only Tier 1 can block. Tier 3 never blocks.

### 9.1 Tier 1 — hard blockers (reviewer-judged; any "no" rejects the question)

| # | Check | Rule |
|---|---|---|
| 1 | One primary objective, stated in one sentence, matching `concepts` | A1, A5 |
| 2 | Not two decisions in one item | A2 |
| 3 | No clue in the stem; every assumption stated | B2, B3 |
| 4 | Every technical term was taught first | B4 |
| 5 | The correct answer is correct from the taught material alone | C1, C4 |
| 6 | **The correct answer cannot be identified from length, detail, caution, professionalism, grammar or information density** (cue audit + reviewer reading) | C2, E1 |
| 7 | Each distractor is a named misconception, wrong for a real reason | D1, D2 |
| 8 | No joke or strawman distractor; no "all/none/both" | D3, D8 |
| 9 | No untaught concept in a distractor | D5, G2 |
| 10 | No distractor is also defensible as correct | D9 |
| 11 | Exactly 3 options; exactly one correct | E6 |
| 12 | Every claim in stem, options and feedback is grounded (chunk id and sentence; fact id for fact-based items) | G1, F3 |
| 13 | A question that exceeds the lesson is marked TEACHING GAP and not written | G4 |
| 14 | `feedback_incorrect` covers both wrong options; neither feedback adds an ungrounded fact | F2, F3 |
| 15 | NO/EN parity; glossary and person-reference rule followed; ID policy followed | I1–I3, section 8 |

### 9.2 Tier 2 — reviewer advisory (SHOULD; a miss needs a one-line note)

| # | Check | Rule |
|---|---|---|
| 16 | Natural bokmål, read aloud | B1 |
| 17 | The "friend claims …" frame is justified, or replaced | B5 |
| 18 | The two distractors are different kinds of wrong | D7 |
| 19 | Epistemic form is comparable across options (hedge balancing) | E2 |
| 20 | No Ja/Nei prefix unless the question is yes/no | E3 |
| 21 | The correct option has the same shape as the others | E4 |
| 22 | The level (L1–L4) fits the stage and the lesson; a foundation item is answerable from one paragraph | H4 |
| 23 | `feedback_correct` explains why and offers at most one grounded extra | F1 |
| 24 | Questions on the same concept climb levels instead of repeating | H2 |

### 9.3 Tier 3 — automated diagnostics (warnings only; never gates; never quotas)

Each warning asks a reviewer to look. "Warning reviewed, acceptable because …" is a valid outcome. These word lists are heuristics for a script, **not** author-maintained lists of forbidden words.

| Diagnostic | Computed on | Warning trigger (attention level, not a rule) |
|---|---|---|
| Length asymmetry | NO and EN option text | Correct option strictly longest by a clear margin (suggested attention level about 1.5×, adjustable) |
| Detail asymmetry | Clause breaks, semicolons, second sentences | Only the correct option has them |
| Hedge asymmetry | Words such as *kan, ofte, vanligvis, generelt, avhenger, ikke nødvendigvis, sannsynligvis, beviser ikke* | Only the correct option hedges |
| Absolute words | Words such as *alltid, aldri, ingenting, uansett, ubegrenset, i det hele tatt, helt sikkert* | In a distractor but not in the correct option; or in the stem |
| Ja/Nei prefix | First word of options | Two or more options start with Ja/Nei on a non-yes/no question |
| Frame | Stem pattern | "friend claims … stemmer det" frame |
| Redundancy | `concepts` and `source_claims` overlap | Same concept and same fact in two questions at the same stage and demand |
| Parity | NO/EN | Different option count or order; EN/NO length ratio far outside about 0.7–1.4 |
| Glossary | Section 7 | A "must avoid" term appears |

**Health indicators** (reported per batch to see drift; never targets): the share of questions where the correct option is the longest, where only the correct option hedges, where a distractor has an absolute, where options start with Ja/Nei, and where the stem is a friend frame.

### 9.4 Cue audit (the operational test for Tier 1 gate 6)

Purpose: find out whether the wording or style of a question reveals the correct answer to someone who does not know brewing.

- The reviewer or author reads the stem and the three options and asks, for each question: *could a person who does not know brewing plausibly pick the correct option from wording style alone?* The reviewer writes down which cue it would be (length, a hedge, a reason clause, tone, grammar, density) or "none found".
- **It is a cue audit, not a blind experiment.** If the same author or reviewer has read the lesson and knows the correct answers, the review cannot be called blind. Do not describe it as one.
- An independent *blind check* (a solver who has seen neither the lesson nor the answers, such as a colleague or a model given only the stem and shuffled options) is optional and gives extra evidence. Over a small batch it is noisy: read the solver's stated reasons, which show what leaks. Never use a score as a pass mark.
- Record the result per question in the sign-off table (9.5).

### 9.5 Review sign-off

One table per PR, one row per question: objective, level, the misconception behind each distractor, chunk and sentence cited, Tier 1 yes/no, Tier 2 notes, Tier 3 warnings reviewed, cue-audit result.

### 9.6 Module tests and guardrails

- Run the affected module tests **early** while rewriting, not only at the end.
- Treat a guardrail failure as a signal to inspect, not as an instruction to change the words.
- Module tests may check for specific words (for example a banned token) as a proxy for an invariant. If natural, correct wording trips an over-broad test (a false positive, such as an ordinary English phrase matching a banned token), **do not distort the question only to satisfy the test.** Flag the test for a separate technical correction so it validates the real invariant instead of the raw word.
- This standard does not maintain a list of forbidden words for authors.

---

## 10. Restructuring "cautious equals correct" groups

If the structure of a group of questions trains "choose the cautious, nuanced answer", restructure it and keep the intended taught concept where possible. Shortening the correct option alone is not enough.

Techniques (each needs the teaching-ground check):

1. **Give the wrong options the same voice.** Distractors are calm and careful in tone but wrong in substance.
2. **Vary the demand** (see H5), so the cautious reflex is not always the answer.
3. **Put the evidence in the stem.** Give a small log, a taste description and a process fact, and ask what follows. Sometimes the evidence supports a firm conclusion and sometimes it does not; only the content tells which. Only if the lesson models that reasoning.
4. **Test the discrimination, not the attitude.** For example "which of these sentences is an observation?"
5. **Separate the habit from the knowledge.** Writing a descriptor as an observation is one concept; recognising a fault is another. Do not let one answer pattern carry both.
6. **Drop cartoon overconfidence.** A real learner's overreach sounds like "Dette er diacetyl, og gjæren sviktet", not "helt sikkert ødelagt".

---

## 11. Recommended authoring techniques

These are techniques, not rigid templates. Use them when they help.

- **T1. Parallel option form.** When useful, give the options comparable grammatical and informational form, for example: *"Med tyngdekraft …; med pumpe …"* or *"Det trengs ofte …, fordi …"*. This reduces style leakage and makes the learner distinguish the concept, not the shape of the option.
- **T2. Hedge balancing.** If a word such as *kan, ofte, vanligvis, avhenger av* is necessary in the correct answer, do not automatically remove every hedge from the distractors. Where natural, give the alternatives a comparable epistemic form so that "the careful answer" does not become an answer cue. Do not add a misleading hedge merely for symmetry.
- **T3. Two-part shared feedback.** See F4.
- **T4. L4 variety.** See H5.
- **T5. Restructuring.** See section 10.

### Common anti-patterns (what the rules above exist to prevent)

| Pattern | Rule |
|---|---|
| The correct option carries the whole lesson (qualifiers, reasons, "but …") while the distractors are one-liners | C2, C3, E1, D6 |
| Wrong options built on absolutes ("alltid", "aldri", "ingenting") that nobody believes | D3, D4 |
| A false claim with an absolute in the stem, so the answer is "no" | B2, B5 |
| Ja/Nei-prefixed options where the first word is the clue | E3 |
| Two decisions in one item | A2 |
| A distractor that needs knowledge the module never taught | D5, G2 |
| Feedback that only restates the correct option, or teaches something the lesson did not | F1, F3 |
| A group of questions where the careful, hedged option is always right | D8, E2, section 10 |
| Several questions on one concept at the same demand | H2, section 8 |
| An answer position that depends on the previous question | R1–R3 |

Example from the pilot (real, merged wording; Q-COOLXFER-006, gravity vs pump):
- Before: one long, qualified correct option against two one-line absolutes ("Tyngdekraft er alltid den beste metoden …").
- After: three parallel options of the form "Med tyngdekraft må mottakerkaret stå lavere; med pumpe slipper du det, men får mer utstyr å rengjøre." / "… og rengjøringen blir enklere." / "Med tyngdekraft blir det mer sprut og luft; med pumpe blir overføringen lukket …". The pump limits from the fact registry stay as one grounded extra in `feedback_correct`.

Example of two-part shared feedback (Q-COOLXFER-001): "Ikke helt. Nedkjølingen gjør ikke vørteren steril, og farten er ikke bare et spørsmål om å bli ferdig: jo raskere vørteren kjøles, jo kortere står den i et temperaturområde der uønskede mikroorganismer kan vokse. Det reduserer risikoen, men garanterer ikke null infeksjonsrisiko."

---

## 12. Process for rewrite batches

- Normal batches are about 6–10 questions, normally one module at a time, one PR per batch, no merge without Chief review.
- Roles: Sonnet for mechanical form fixes with a clear objective and clear misconceptions, feedback reshaping, and the EN parity pass. Opus for naming misconceptions, replacing joke distractors, restructuring (section 10), L4 items, splits and merges. The Chief for teaching gaps (G4), glossary conformance in teaching chunks, ID retirements, concept changes (A5), and any schema, UI, or feedback-model change. A native-speaker check on glossary choices and a sample per batch.
- Validation after each batch: the module validators, the fact registry and the course-stage map; the module's unit tests (early and at the end); the Bryggeskole UI suites that load the data; the NO/EN parity check; Tier 3 diagnostics before and after; the cue audit; the sign-off table; CI and Playwright as usual. Search the tests for old wording before changing text, and update only tests that genuinely pin the question.
- Pilot evidence and diagnostics are health indicators, never acceptance quotas.

---

## 13. Version history and rationale

### v1.1 changes (compared with v1)

1. **Parallel option form** added as a recommended technique (T1).
2. **Hedge balancing** added as a recommended technique (T2, E2).
3. **Two-part shared feedback** pattern allowed (F4). The shared `feedback_incorrect` schema is unchanged; per-option feedback is deferred.
4. **L4 variety** (H5): L4 is not "what can you conclude?" only.
5. **Concept repetition** across modules is valid when the demand differs (H2).
6. **Concepts and mastery credit** rule (A5): a secondary concept only when it is genuinely required and mastery credit for it is intentional; otherwise keep the primary concept and escalate.
7. **Module test guardrails** (9.6): run module tests early; do not distort natural wording to satisfy an over-broad lexical test; flag the test for a separate correction. No author-maintained list of forbidden words.
8. **Cue audit** terminology (9.4): a review by someone who has read the lesson is a cue audit, not a blind experiment.
9. **Pilot evidence** recorded below.

### Pilot evidence (12 questions: cleaning/safety, cooling/transfer, sensory evaluation; PR #511)

- 2 questions could be kept unchanged; 10 required rewrite.
- 0 teaching gaps.
- All hard gates passed after the rewrite.
- Strong style leakage (length, one-sided hedging, absolutes, Ja/Nei prefixes, friend frames) was removed.
- The shared `feedback_incorrect` remained workable, including where the two distractors failed for different reasons.
- No per-option feedback schema change was justified.
- Concept repetition can be valid when the demand changes; the two questions sharing the sanitation boundary were kept.

These findings explain the v1.1 additions. They are not acceptance quotas, and none of the numbers in this document is a target.

### v1 decisions preserved in v1.1

Exactly 3 options; one primary objective per question; L1–L5 as authoring guidance with no `level` field; hard gates separated from diagnostics; ratios are warnings and never writing quotas; no answer may win by length, detail, caution, professionalism, grammar or information density; plausible, misconception-based distractors and no joke or strawman options; teaching and fact grounding; natural NO/EN parity; the glossary conventions; the ID policy; the independent answer-position requirement; the feedback grounding rule; the shared-feedback model; restructuring is allowed when the question form itself leaks the answer.

### Open items

- Glossary calls still open: *vørteren / vørten / vørter*, the traditional vessel name, *gjæringslås / luftlås* (section 7).
- Whether a rewrite may add a secondary concept is decided case by case by the Chief (A5).
- A validated `level` field is not planned; it may be reconsidered separately.
- Per-option feedback is deferred and may be re-evaluated after normal batches have run.
