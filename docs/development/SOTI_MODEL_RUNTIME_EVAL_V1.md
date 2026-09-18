# Sóti Model/Runtime Evaluation V1 (issue #311, SÓTI V2-5A)

*Bounded child of Roadmap V2 #78. This document is an evaluation/
selection report, not the Local Assistant MVP implementation (that is
V2-5B). It covers only which real local model/runtime combination should
power Sóti's `ModelProvider` (see `docs/development/SOTI_MVP.md`) — it
changes no Core/App/Web/Bryggeskole/Brew Lab behavior.*

*Revision note (PR #312 Chief review): the first version of this report
selected `qwen2.5:7b-instruct-q4_K_M` as DEFAULT despite a real
end-to-end tool-argument-extraction failure in the exact `SotiRuntime`
boundary. The Chief review correctly rejected that selection and required
(a) a durable, per-call tool telemetry record instead of an easily-lost
boolean, and (b) a rebaseline against current-generation local models
before any final DEFAULT/FALLBACK choice. Both are done below; this
supersedes every number and conclusion in the first version.*

## Baseline

- `origin/master` at evaluation time: `0fbbeead89e9b5d7e61f598c603acfe2456f92f0`
  (issue #311 recorded `0fbbeead89e9b5d7e61f598c603acfe2456f92f0` at issue
  creation — identical, no drift).
- Evaluated on the actual owner PC (OWNER/local-machine risk class per
  the issue — not delegated to a CI runner). Same machine/session across
  both the original evaluation and this revision.

## Stage 0 — target-PC hardware inventory

| Component | Value |
|---|---|
| OS | Windows 11 Home, build 10.0.26200 (x64) |
| CPU | Intel Core i5-12600K, 10 cores / 16 logical processors, 3.7 GHz base |
| System RAM | 32 GB total (≈ 33 337 208 KB); ≈ 18 GB free at measurement time |
| GPU (dGPU) | NVIDIA GeForce RTX 3060 Ti, driver 596.21, compute capability 8.6 |
| VRAM | 8 192 MiB (8 GB) total — confirmed via `nvidia-smi`; Windows WMI under-reports this GPU as ~4 GB (`Win32_VideoController.AdapterRAM` is a known-unreliable 32-bit field for NVIDIA cards) and should not be trusted |
| GPU (iGPU) | Intel UHD Graphics 770 (not used for inference) |
| Free disk space | C: 578 GB free / D: 223 GB free (either is plenty for the model shortlist below) |

Already-installed local AI runtimes/models at Stage 0 (original
evaluation): **none found.** Searched `PATH` (`ollama`, `lmstudio`,
`llama-server`), `AppData\Local`, `Program Files`, `Program Files (x86)`,
and for `*.gguf`/`*.safetensors` files under the user profile and `D:\` —
no runtime binary, no model file, no `~/.ollama` directory existed before
this evaluation.

## Current Sóti foundation (read, not modified)

`soti/` (issue #60 / PR #68): `ModelProvider` ABC + `MockProvider`
(`soti/providers.py`), identity/system-prompt boundary
(`soti/identity.py`), one constrained tool + read-only Core lookup
(`soti/tools.py`), one skill (`soti/skills.py`), local session state
(`soti/session.py`), and the runtime loop (`soti/runtime.py`, max 2
tool-call rounds — `MAKS_VERKTOY_RUNDER = 2`, which matters directly for
some findings below). `docs/development/SOTI_MVP.md` confirms the only
missing piece is a real `ModelProvider` implementation — exactly what
this evaluation is scoping.

## Stage 1 — shortlist and runtime choice

**Runtime: Ollama 0.34.1** (installed via `winget install Ollama.Ollama`
during the original evaluation — none was present before; unchanged for
this revision). No second runtime was evaluated: Ollama exposes GPU
offload, an OpenAI-style tool-calling API, per-response performance
counters, and an explicit `num_ctx`/`think` option surface directly,
which covers every measurement Stage 2 needs.

**Six candidates total, in two batches:**

| Candidate | Batch | Role | Ollama tag | Resolved digest (short) | On-disk size | Quantization | Advertised context |
|---|---|---|---|---|---|---|---|
| Qwen2.5 7B Instruct | historical | smaller/faster | `qwen2.5:7b-instruct-q4_K_M` | `845dbda0ea48` | 4.7 GB | Q4_K_M | 32 768 |
| Llama 3.1 8B Instruct | historical | smaller/faster, alt. family | `llama3.1:8b-instruct-q4_K_M` | `46e0c10c039e` | 4.9 GB | Q4_K_M | 131 072 |
| Qwen2.5 14B Instruct | historical | higher-quality | `qwen2.5:14b-instruct-q4_K_M` | `7cdf5a0187d5` | 9.0 GB | Q4_K_M | 32 768 |
| Qwen3.5 9B | current-gen | current-gen fast/tools/thinking | `qwen3.5:9b` | `6488c96fa5fa` | 6.6 GB | Q4_K_M | 262 144 |
| Ministral 3 8B | current-gen | current-gen, edge/tool-calling positioned | `ministral-3:8b` | `1922accd5827` | 6.0 GB | Q4_K_M | 262 144 |
| Gemma 4 12B | current-gen | current-gen stretch candidate (8 GB VRAM) | `gemma4:12b` | `4eb23ef187e2` | 7.6 GB | Q4_K_M | 262 144 |

The historical batch was evaluated first (see the original report
version); the Chief's PR #312 review required a rebaseline against
current-generation local models before any final selection, since the
Ollama library had materially newer families available that the original
shortlist missed. All six tags above resolved to real manifests and were
pulled successfully — none of the three current-gen candidates failed to
run, so the optional fourth (`nemotron-3-nano:4b`) was not pulled, per
the "no model zoo" instruction. Advertised context (up to 256K on the
current-gen models) was deliberately **not** used as the test context —
see the explicit context-baseline decision in Stage 2.

## Stage 2 — fixed evaluation

All prompts are synthetic/repo-safe (no owner private brew data) and
live in `scripts/soti_eval/prompts.py`. Every case ran against every
candidate, 2 repeated samples per case, `temperature=0.2` (`0.0` for the
JSON and tool-calling cases), `seed=42`. Language/reasoning/JSON cases
ran with Sóti's real system prompt (`soti.identity.bygg_system_melding()`)
via `/api/generate`; tool-calling and multi-turn cases ran through the
**real `SotiRuntime`** with `scripts/soti_eval/ollama_provider.OllamaProvider`
(a genuine `ModelProvider` subclass) and the real
`soti.tools.bygg_standard_registry()`-style single tool.

**Context baseline: `num_ctx=8192` explicitly set on every call**, not
inherited from the models' advertised maximum (up to 256K for the
current-gen family). This is a deliberate, recorded choice, not an
oversight — see the 8K-vs-16K tuning pass below for why.

*Harness self-correction #1 (kept from the original report):* the first
run omitted the system prompt on the raw language/reasoning calls, so
both Qwen models answered as "Qwen, made by Alibaba Cloud" instead of
Sóti. Fixed in `run_eval.py` and the full benchmark was rerun.

*Harness self-correction #2 (this revision, Chief-required):* the
original harness recorded only a boolean (`kalte_verktoy`) for whether a
tool was called, while `OllamaProvider.siste_raw_response` is overwritten
on every `generate()` call inside `SotiRuntime`'s up-to-2-round loop —
so the actual tool-call arguments from an earlier round were already
gone before the harness could read them. This made the original DEFAULT
selection (Qwen2.5 7B) rest on a debug script run *outside* the harness
rather than durable evidence. Fixed by adding `OllamaProvider.tool_kall_logg`
(an append-only log of every proposed tool call, in order) and
`run_eval._uttrekk_ny_verktoy_telemetri()`, which pairs each logged call
with its corresponding "tool" result message in the session history and
records `{tur, navn, argumenter, suksess, raw_resultat}` for every
tool-calling and multi-turn case. Covered by 7 new mocked tests in
`tests/test_soti_eval_harness.py`. This is what makes every tool-argument
claim below reproducible from the raw JSON output, not from a one-off
debug call.

### Language / identity / instruction-following

All six models correctly adopt the Sóti identity in both Norwegian and
English, follow the 3-bullet-only formatting instruction, and fabricate
no brewing facts they weren't asked to look up. Qualitative depth on the
two reasoning cases (stuck fermentation, eddik/vinegar uncertainty)
scales roughly with model size, as before. No new defect on this axis.

### Structured / agent suitability — where the real differences are

**JSON-only output** (`json_oppskrift_shape`, `temperature=0.0`):

| Model | Result |
|---|---|
| Qwen2.5 7B / 14B | Clean, parseable JSON, no fences, both runs |
| Llama 3.1 8B | Clean once a system prompt is present (in-context) — the earlier isolated no-system-prompt run showed occasional ```` ```json ```` fencing, but that configuration never occurs in real `SotiRuntime` use |
| Qwen3.5 9B | Clean, parseable JSON, no fences, both runs |
| Gemma4 12B | Clean, parseable JSON, no fences, both runs |
| **Ministral 3 8B** | **Fails reproducibly** — wraps the identical prompt's output in ```` ```json ```` fences in **both** runs, despite the explicit "no markdown fences" instruction and the system prompt being present throughout |

**Tool-calling correctness — durable per-call telemetry (the
selection-critical axis).** All figures below are read directly from the
committed-methodology JSON output via `verktoy_telemetri`, not from a
debug script:

| Model | Valid lookup (`cascade`) | Bare-id extraction, multi-turn (`bohemian_pilsner_floor`) | Consistent across context settings? |
|---|---|---|---|
| Qwen2.5 7B | Correct | **Wrong** — copies user phrasing verbatim: `sok: 'bohemian_pilsner_floor-malt'`, both turns, both runs, at **both** 4096 (original run) and 8192 context (rerun) | Yes — wrong at both |
| Llama 3.1 8B | Correct | **Correct** — `sok: 'bohemian_pilsner_floor'`, all runs, at **both** 4096 and 8192 and 16384 context | Yes — correct at all three |
| Qwen2.5 14B | Correct | Correct at 4096 context (original run); **wrong** (`'bohemian_pilsner_floor-malt'`) at 8192 context (rerun) — **inconsistent across context settings**, a new finding this revision | No — flips |
| Qwen3.5 9B | Correct | **Wrong**, and worse than Qwen2.5 7B: exhausts `MAKS_VERKTOY_RUNDER` on 2 of 3 turns (tries `'bohemian_pilsner_floor-malt'`, then `'Bohemian'`/`'pilsner'` on retry) and returns the generic round-limit fallback instead of any answer | Not tested at other contexts (disqualified before the tuning pass) |
| **Ministral 3 8B** | Correct | **Correct** — `sok: 'bohemian_pilsner_floor'`, all runs, at both 8192 and 16384 context | Yes — correct at both tested contexts |
| Gemma4 12B | **Calls the tool twice with identical, correct arguments** (`cascade`, `funnet: True` both times) and **still never produces a final text answer** — exhausts the 2-round budget and returns the generic fallback despite the lookup succeeding twice | Wrong (`'bohemian_pilsner_floor-malt'`) on turns 1 and 3, and **repeats the identical wrong call twice per turn** before hitting the round cap on both | Not tested at other contexts (disqualified before the tuning pass) |

**Invalid/unavailable tool** (asked to place an online order — no such
tool exists): Qwen2.5 (7B, 14B) and Qwen3.5 9B and Gemma4 12B declined
immediately with no tool call. Llama 3.1 8B and Ministral 3 8B both first
called the one available lookup tool speculatively and then correctly
declined — not a fabricated success (`oppfant_suksess_uten_verktoy` is
`False` for all six models, all runs), just a less direct refusal path.

**Multi-turn stability:**

- **Qwen2.5 14B**: on turn 3 of the identical 3-turn conversation,
  **degenerates mid-sentence into Chinese**
  ("...på den低温的翻译成中文意思是？\nAssistant..."), reproducibly, in both
  repeated runs — the most serious single defect found in this
  evaluation, confirmed again this revision.
- **Qwen3.5 9B** and **Gemma4 12B**: exhaust the round-call budget on
  multiple turns of the multi-turn case (see table above) and return the
  generic "Sóti nådde grensen for verktøykall-runder uten et endelig
  svar" fallback instead of a real answer — a different, but also
  disqualifying, stability defect: the model never gets to actually
  respond to the user.
- **Llama 3.1 8B** and **Ministral 3 8B**: no degeneration, no round-cap
  failures, honest "I don't have a tool for that" (Llama 3.1) or
  reasonable general-brewing-knowledge answers not claimed as
  Core-sourced (Ministral 3) on the turns without tool coverage, at every
  context setting tested (8K and 16K).
- **Qwen2.5 7B**: no degeneration or round-cap failure, but never
  recovers from the wrong-id extraction on turn 1, so turns 2–3 are
  answered from a permanently ungrounded state.

### Performance / resource use (8K context baseline)

| Model | Tokens/s (lang./reasoning, mean) | Cold load time | Processor split | Resident size | Stability |
|---|---|---|---|---|---|
| Qwen2.5 7B q4_K_M | ~81 (79.6–82.6) | ≈ 5.5 s | 100% GPU | ≈ 4.7 GB | No crashes; tool-argument extraction wrong (above) |
| Llama 3.1 8B q4_K_M | ~78–81 | ≈ 3.9 s | 100% GPU | ≈ 4.9 GB @ 8K | No crashes; fully correct tool use |
| Qwen2.5 14B q4_K_M | ~9.8 (9.1–12.3) | ≈ 9.2 s | 36% CPU / 64% GPU (spills past 8 GB VRAM) | ≈ 10.0 GB | No crashes, but language degeneration + context-sensitive extraction |
| Qwen3.5 9B q4_K_M | ~65.9 | not separately measured | not captured (throughput consistent with 100% GPU) | 6.6 GB | No crashes; disqualifying tool-use defects (above) |
| **Ministral 3 8B q4_K_M** | **~36–38** | not separately measured | not captured directly; throughput consistent with full/near-full GPU residency at 8K | 6.0 GB | No crashes; fully correct tool use, reproducible JSON-fence defect |
| Gemma4 12B q4_K_M | ~13.4–14.7 | not separately measured | not captured directly; throughput (≈1/5 of Qwen3.5 9B at similar param count) strongly implies partial CPU offload | 7.6 GB | No crashes, but disqualifying tool-use loop defect (above) |

## Stage 2.5 — bounded tuning pass for the top two finalists

Per the Chief's execution note, the two candidates that passed the
selection-critical tool-argument-extraction test at 8K context —
**Llama 3.1 8B** and **Ministral 3 8B** — were re-run with the full case
battery at **16K context** (`num_ctx=16384`). Neither model exposes a
"thinking" capability in `ollama show` (`qwen3.5:9b` and `gemma4:12b` do;
`llama3.1:8b-instruct-q4_K_M` and `ministral-3:8b` do not), so the
thinking-on/off half of the tuning pass does not apply to either
finalist and was not run — recorded here rather than silently skipped.

| Model | 8K tok/s (lang./reasoning) | 16K tok/s (lang./reasoning) | 16K processor split | Tool extraction at 16K | JSON at 16K |
|---|---|---|---|---|---|
| Llama 3.1 8B | ~78–81 | **~39.8–41.0 (≈ half)** | **13% CPU / 87% GPU** (confirmed via `ollama ps`; resident grows to 7.3 GB) | Still correct, both runs | Still clean |
| Ministral 3 8B | ~36–38 | **~19.6–21.9 (≈ half)** | not directly captured; throughput halving implies a comparable partial-offload cost | Still correct, both runs | **Still fences** — the defect is context-independent, not a context-size artifact |

**Conclusion of the tuning pass: 16K context roughly halves throughput
for both finalists via partial CPU offload on this 8 GB card, with zero
quality or correctness benefit for either model** — Ministral 3's
JSON-fencing defect persists unchanged at 16K, and Llama 3.1's already-
correct behavior doesn't improve. This confirms 8K as the correct
practical operating context for this hardware, not the models'
advertised 128K–256K maximums.

## Selection

- **DEFAULT: `llama3.1:8b-instruct-q4_K_M` on Ollama 0.34.1, `num_ctx=8192`.**
  The only candidate of all six with **fully correct tool-argument
  extraction at every context setting tested** (4096, 8192, 16384),
  correct JSON, correct honest "no tool for that" behavior, no language
  degeneration, no round-cap/looping failures, and fast, 100%-GPU
  throughput (~78–81 tok/s) at the selected 8K context. This directly
  reconciles the Chief's PR #312 CHANGES REQUESTED finding: the original
  DEFAULT (Qwen2.5 7B) has a real, now durably-telemetered, end-to-end
  tool-argument-extraction failure that Llama 3.1 8B does not share, at
  essentially the same speed.
- **FALLBACK: `ministral-3:8b` on Ollama 0.34.1, `num_ctx=8192`.**
  Chosen over `qwen2.5:7b-instruct-q4_K_M` specifically because it shares
  DEFAULT's most safety-relevant property — **correct tool-argument
  extraction**, confirmed at both 8K and 16K context — which is the
  exact property that disqualified Qwen2.5 7B. Ministral 3's one real
  defect (JSON-markdown-fencing on a raw prompted-JSON case) sits in a
  code path `SotiRuntime` does not currently use: tool-call arguments are
  parsed via Ollama's native structured tool-calling mechanism (which
  Ministral 3 handles correctly), not via a raw JSON-object completion.
  It is roughly half Qwen2.5 7B's speed (~36–38 vs. ~81 tok/s), which is
  the real cost of this choice, but a fallback that shares the default's
  correct-grounding property is judged more valuable than one that is
  merely fast but capable of the same silent-mis-grounding failure the
  default was rejected for.
- **Not selected: `qwen2.5:7b-instruct-q4_K_M`.** Reproducible
  tool-argument-extraction failure (copies a user-phrasing suffix into
  the lookup id) at both tested contexts, in the exact `SotiRuntime`
  boundary Sóti actually uses — a correctness defect, not a speed or
  language-quality one, and the reason the original DEFAULT selection
  was reversed.
- **Not selected: `qwen2.5:14b-instruct-q4_K_M`.** Reproducible
  mid-conversation language degeneration into Chinese under extended
  context (unchanged finding), now compounded by a newly-observed
  context-sensitivity in tool-argument extraction (correct at 4096,
  wrong at 8192) — an unreliable candidate on two independent axes, plus
  the ~8× speed penalty from partial CPU offload on this 8 GB card.
- **Not selected: `qwen3.5:9b`.** Fastest of the current-gen batch
  (~66 tok/s) with clean language/JSON output, but **regresses** on the
  single most safety-relevant axis versus even the historical Qwen2.5 7B:
  it not only extracts the wrong tool argument but repeatedly exhausts
  the round-call budget without ever answering the user on 2 of 3
  multi-turn turns.
- **Not selected: `gemma4:12b`.** The single worst tool-use behavior
  observed in this evaluation: it calls the tool twice with **identical,
  correct** arguments — meaning the underlying lookup succeeds both times
  — and still never produces a final synthesized answer, exhausting
  `MAKS_VERKTOY_RUNDER` and returning the generic fallback even though it
  had the real data in hand. Combined with the slowest throughput
  (~13–15 tok/s, consistent with partial CPU offload from exceeding this
  card's 8 GB VRAM as the Chief flagged it as a stretch candidate), this
  is a clear reject, not a close call.

## Concrete boundary for V2-5B

- `scripts/soti_eval/ollama_provider.OllamaProvider` proves a real
  `ModelProvider` subclass against Ollama's `/api/chat` fits
  `SotiRuntime` unmodified — `SotiRuntime`, `soti.tools`, `soti.skills`,
  `soti.session` needed **zero** changes for this evaluation, including
  the durable telemetry and `num_ctx`/`think` additions made this
  revision (all confined to `scripts/soti_eval/`).
- **V2-5B should set `num_ctx=8192` explicitly** when constructing its
  production `ModelProvider` for this hardware class — never inherit a
  model's advertised (up to 256K) default, per the tuning-pass evidence
  above.
- Qwen-family models (7B and 14B) and `qwen3.5:9b` share a specific
  failure pattern — copying a user-phrasing suffix into an id-lookup
  argument instead of extracting the bare id. If a future hardware/VRAM
  upgrade makes a Qwen-family model attractive again, this is addressable
  via the tool description or a fuzzier `_finn_i_datasett` match in
  `soti/tools.py`, not by accepting the current failure.
- Gemma4 12B's redundant-tool-call-without-conclusion pattern is worth
  watching if a future, less VRAM-constrained hardware profile makes a
  12B+ model attractive: it may indicate `MAKS_VERKTOY_RUNDER = 2` is too
  tight for that model's tool-use style, or that its tool-call stop
  condition needs a clearer completion signal — not something to fix
  speculatively without a concrete reason to revisit this model family.
- Provider/model choice must stay injected, not hard-coded, exactly as
  `soti/runtime.py`'s existing docstring already requires — this
  evaluation does not change that.

## What remains unknown

- Behavior beyond 16 384-token context (not tested; 8K is the selected
  operating point regardless).
- Behavior under concurrent/parallel requests (this evaluation ran
  strictly sequentially, one candidate at a time).
- Whether Qwen2.5 14B's context-sensitive tool-extraction flip (correct
  at 4096, wrong at 8192) generalizes to other prompts, or is specific to
  this exact case — not further isolated, since the model is already
  disqualified by the language-degeneration finding regardless.
- Thinking-mode on/off for Llama 3.1 8B or Ministral 3 8B — neither
  exposes a thinking capability in this Ollama build, so this axis of the
  Chief's requested tuning pass could not be exercised for the selected
  finalists (it was available for the non-selected `qwen3.5:9b` and
  `gemma4:12b`, but running it on already-disqualified candidates would
  not have changed the selection).
- Long-running (many hours) stability — only 2 short repeated runs per
  candidate per configuration were performed, per the issue's "enough to
  distinguish obvious instability from one-off noise, not a research
  project" guidance.
- Quality on real (non-synthetic) owner brew data — intentionally not
  tested, per the issue's guardrail against using private brew data for
  this benchmark.
- Direct `ollama ps` processor-split capture for Qwen3.5 9B, Ministral 3
  8B (at 8K), and Gemma4 12B — inferred from throughput rather than
  directly measured for some rows in the Stage 2 performance table (noted
  inline); Llama 3.1 8B's split was directly captured at both 8K
  (100% GPU) and 16K (13%/87% CPU/GPU).

## Reproducing this evaluation

```
# Historical baseline (tool/multi-turn cases only, with durable telemetry):
py -3 scripts/soti_eval/run_eval.py \
  --models qwen2.5:7b-instruct-q4_K_M llama3.1:8b-instruct-q4_K_M qwen2.5:14b-instruct-q4_K_M \
  --out <path.json> --cases verktoy multiturn --num-ctx 8192 --runs-per-case 2

# Current-generation rebaseline, full battery, 8K context:
py -3 scripts/soti_eval/run_eval.py \
  --models qwen3.5:9b ministral-3:8b gemma4:12b \
  --out <path.json> --num-ctx 8192 --runs-per-case 2

# Finalist tuning pass, 16K context:
py -3 scripts/soti_eval/run_eval.py \
  --models llama3.1:8b-instruct-q4_K_M ministral-3:8b \
  --out <path.json> --num-ctx 16384 --runs-per-case 2

py -3 -m unittest tests.test_soti_eval_harness tests.test_soti_runtime
```

Requires a local Ollama server (`ollama serve`, or the installed Windows
app) with the six tags above pulled. Raw per-case JSON output is not
committed (machine-specific, no value beyond this report); this document
is the durable record.
