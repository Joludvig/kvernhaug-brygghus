# Sóti Model/Runtime Evaluation V1 (issue #311, SÓTI V2-5A)

*Bounded child of Roadmap V2 #78. This document is an evaluation/
selection report, not the Local Assistant MVP implementation (that is
V2-5B). It covers only which real local model/runtime combination should
power Sóti's `ModelProvider` (see `docs/development/SOTI_MVP.md`) — it
changes no Core/App/Web/Bryggeskole/Brew Lab behavior.*

## Baseline

- `origin/master` at evaluation time: `0fbbeead89e9b5d7e61f598c603acfe2456f92f0`
  (issue #311 recorded `0fbbeead89e9b5d7e61f598c603acfe2456f92f0` at issue
  creation — identical, no drift).
- Evaluated on the actual owner PC (OWNER/local-machine risk class per
  the issue — not delegated to a CI runner).

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

Already-installed local AI runtimes/models at Stage 0: **none found.**
Searched `PATH` (`ollama`, `lmstudio`, `llama-server`), `AppData\Local`,
`Program Files`, `Program Files (x86)`, and for `*.gguf`/`*.safetensors`
files under the user profile and `D:\` — no runtime binary, no model
file, no `~/.ollama` directory existed before this evaluation.

## Current Sóti foundation (read, not modified)

`soti/` (issue #60 / PR #68): `ModelProvider` ABC + `MockProvider`
(`soti/providers.py`), identity/system-prompt boundary
(`soti/identity.py`), one constrained tool + read-only Core lookup
(`soti/tools.py`), one skill (`soti/skills.py`), local session state
(`soti/session.py`), and the runtime loop (`soti/runtime.py`, max 2
tool-call rounds). `docs/development/SOTI_MVP.md` confirms the only
missing piece is a real `ModelProvider` implementation — exactly what
this evaluation is scoping.

## Stage 1 — shortlist and runtime choice

**Runtime: Ollama 0.34.1** (installed via `winget install Ollama.Ollama`
during this evaluation — none was present before). No second runtime was
evaluated: the issue only requires comparing runtimes "if there is a
concrete reason to," and no such reason surfaced — Ollama exposes GPU
offload, an OpenAI-style tool-calling API, and per-response performance
counters (`eval_count`, `eval_duration`, `load_duration`) directly, which
covers every measurement Stage 2 needs.

**Models (all pulled fresh during this evaluation, all Apache-2.0/Llama-3.1-license, all actively maintained families):**

| Candidate | Role | Ollama tag | Resident size | Exact quantization |
|---|---|---|---|---|
| Qwen2.5 7B Instruct | smaller/faster | `qwen2.5:7b-instruct-q4_K_M` | 4.7 GB | q4_K_M |
| Llama 3.1 8B Instruct | smaller/faster, alternate family | `llama3.1:8b-instruct-q4_K_M` | 5.3 GB (reports 4.9 GB on disk) | q4_K_M |
| Qwen2.5 14B Instruct | higher-quality | `qwen2.5:14b-instruct-q4_K_M` | 10.0 GB resident (9.0 GB on disk) | q4_K_M |

Three candidates, two size classes, deliberately including a same-size
cross-family comparison (Qwen vs. Llama at ~7–8B) because Norwegian
quality and tool-argument precision turned out to vary by family at a
fixed size (see Stage 2) — this is the "concrete reason" the issue asks
for before adding a fourth candidate, and the shortlist stops at three.

## Stage 2 — fixed evaluation

All prompts are synthetic/repo-safe (no owner private brew data) and
live in `scripts/soti_eval/prompts.py`. Every case ran against every
candidate, 2 repeated samples per case, `temperature=0.2` (`0.0` for the
JSON case), `seed=42`, Ollama default context `4096`. Language/
reasoning/JSON cases ran with Sóti's real system prompt
(`soti.identity.bygg_system_melding()`) via `/api/generate`; tool-calling
and multi-turn cases ran through the **real `SotiRuntime`** with a new
`scripts/soti_eval/ollama_provider.OllamaProvider` (a genuine
`ModelProvider` subclass) and the real `soti.tools.bygg_standard_registry()`-style single tool.

*Harness self-correction:* the first run omitted the system prompt on the
raw language/reasoning calls, so both Qwen models answered as "Qwen,
made by Alibaba Cloud" instead of Sóti — a harness bug, not a model
finding. Fixed in `run_eval.py` (system prompt now passed) and the full
benchmark was rerun; the numbers below are from the corrected run.

### Language / identity / instruction-following

All three correctly adopt the Sóti identity once the system prompt is
present, in both Norwegian and English, and follow the 3-bullet-only
formatting instruction. No model fabricated brewing facts it wasn't
asked to look up.

### Brewing-domain reasoning

All three separated observation from hypothesis reasonably on the stuck-
fermentation and eddik/vinegar-uncertainty cases. Qualitative depth
scaled roughly with size (14B gave the most structured, caveat-aware
answers; 7B/8B were shorter but not wrong).

### Structured / agent suitability — where the real differences are

- **JSON-only output:** all three produced parseable JSON with the
  required fields in the corrected run. Note: Llama 3.1 8B was
  **inconsistent** — in an earlier isolated run (no system prompt in
  context) it wrapped the identical prompt's output in ```` ```json ````
  fences despite an explicit "no markdown fences" instruction, then
  complied cleanly once a system prompt was present. Qwen2.5 (both
  sizes) never added fences in any run. This is a real, if narrow,
  instruction-following reliability gap for Llama 3.1 on strict-format
  output.
- **Tool-calling correctness (multi-turn, real data):** asked to use the
  malt named `bohemian_pilsner_floor` across 3 turns —
  - **Qwen2.5 7B copied the user's phrasing literally** into the tool
    argument (`sok: "bohemian_pilsner_floor-malt"`, including the
    Norwegian suffix "-malt" the user's sentence happened to end with)
    instead of extracting the bare id, so the lookup returned
    `funnet: False` and the model never grounded on real data for the
    entire conversation (confirmed via a direct debug call outside the
    harness).
  - **Llama 3.1 8B and Qwen2.5 14B both extracted the correct id**
    (`bohemian_pilsner_floor`), got real Weyermann/EBC/flavor data back
    on turn 1, and gave an honest "no tool for that" answer on turns 2–3
    instead of inventing a fermentation temperature from the tool result.
- **Invalid/unavailable tool:** asked to place an online order (no such
  tool exists). Qwen2.5 (7B, 14B) declined immediately with no tool call.
  Llama 3.1 8B first called the one available lookup tool speculatively
  (plausibly trying to find product info) and then correctly declined —
  not a fabricated success, but a slightly less direct refusal.
- **Multi-turn stability — the most important finding:** on turn 3 of the
  identical 3-turn Norwegian conversation, **Qwen2.5 14B degenerated
  mid-sentence into Chinese** ("...på den低温的翻译成中文意思是？\nAssistant..."),
  reproducibly, in **both** repeated runs with `seed=42`. Neither Qwen2.5
  7B nor Llama 3.1 8B showed this in any run.

### Performance / resource use

| Model | Tokens/s (lang./reasoning, mean of 2 runs × 7 prompts) | Cold load time | Processor split | Peak VRAM (approx.) | Stability |
|---|---|---|---|---|---|
| Qwen2.5 7B q4_K_M | **81.4** (79.6–82.6) | ≈ 5.5 s | 100% GPU | ≈ 4.7 GB | No crashes; tool-argument extraction miss (above) |
| Llama 3.1 8B q4_K_M | **77.8** (77.0–78.6) | ≈ 3.9 s | 100% GPU | ≈ 5.3 GB | No crashes; JSON-format inconsistency (above) |
| Qwen2.5 14B q4_K_M | **9.8** (9.1–12.3) | ≈ 9.2 s | **36% CPU / 64% GPU** (spills past the 8 GB VRAM ceiling — resident size 10.0 GB) | ≈ 7.7 GB VRAM + CPU/RAM overflow | No crashes, but reproducible language-degeneration under extended context (above) |

Context actually tested: Ollama default `4096` tokens (not pushed
further — no candidate needed more for these cases).
No candidate crashed, hung, or failed to unload; the 14B model's
CPU/GPU split (not a crash) is exactly why it is 8× slower, and is
recorded rather than forced through further load.

## Selection

- **DEFAULT: `qwen2.5:7b-instruct-q4_K_M` on Ollama.** Fastest (100% GPU,
  ~81 tok/s), correct identity/instruction adherence, correct JSON,
  correct honest refusal on the invalid-tool case, no stability or
  language-degeneration issues in any run. Its one real defect —
  copying a user's phrasing verbatim into a tool argument instead of
  extracting the bare id — is a scoped, addressable tool-description/
  prompt problem for V2-5B (e.g. an explicit "id has no suffix" hint or
  a fuzzier `_finn_i_datasett` match), not a language-quality or
  stability defect, and it never produced wrong-language or malformed
  output.
- **FALLBACK: `llama3.1:8b-instruct-q4_K_M` on Ollama.** Comparable
  speed (100% GPU, ~78 tok/s), and it is the candidate that **did**
  extract the tool argument correctly and grounded on real data across
  the multi-turn case where the default failed — a good fallback
  specifically for the failure mode the default has. Its own weakness
  (occasional markdown-fenced JSON without a system prompt in context)
  is the kind of thing a consistent system-prompt-always-present
  boundary (which `SotiRuntime` already guarantees, see
  `soti/runtime.py:handle_message`) makes moot in practice.
- **Not selected: `qwen2.5:14b-instruct-q4_K_M`.** Disqualified primarily
  by the reproducible mid-conversation language degeneration under
  extended context (a real correctness/UX failure for a Norwegian-first
  assistant, not a one-off), compounded by the ~8× speed penalty from
  partial CPU offload on this 8 GB card. Recorded here rather than
  discarded silently, in case a future GPU upgrade or a smaller
  quantization changes the resource picture.

## Concrete boundary for V2-5B

- `scripts/soti_eval/ollama_provider.OllamaProvider` proves a real
  `ModelProvider` subclass against Ollama's `/api/chat` fits
  `SotiRuntime` unmodified — `SotiRuntime`, `soti.tools`, `soti.skills`,
  `soti.session` needed **zero** changes for this evaluation.
  `OllamaProvider` is evaluation-only scaffolding (see its module
  docstring); V2-5B should design its own production `ModelProvider`
  (retry/error handling, streaming, etc. were deliberately left out
  here) but can reuse the same message/tool translation shape.
- The one known tool-argument-extraction gap (default model copying a
  user-phrasing suffix into an id lookup) should be addressed in
  V2-5B's tool description or `_finn_i_datasett` matching, not by
  switching models.
- Provider/model choice must stay injected, not hard-coded, exactly as
  `soti/runtime.py`'s existing docstring already requires — this
  evaluation does not change that.

## What remains unknown

- Behavior beyond a 4096-token context window (not tested).
- Behavior under concurrent/parallel requests (this evaluation ran
  strictly sequentially, one candidate at a time).
- Whether the Qwen 14B language-degeneration is specific to this exact
  quantization/context combination or a broader Qwen2.5-14B issue —
  not re-tested at a different quantization, since the issue's own
  hardware constraint (8 GB VRAM) already disqualifies this size class
  on this machine regardless.
- Long-running (many hours) stability — only 2 short repeated runs per
  candidate were performed, per the issue's "enough to distinguish
  obvious instability from one-off noise, not a research project"
  guidance.
- Quality on real (non-synthetic) owner brew data — intentionally not
  tested, per the issue's guardrail against using private brew data for
  this benchmark.

## Reproducing this evaluation

```
py -3 scripts/soti_eval/run_eval.py \
  --models qwen2.5:7b-instruct-q4_K_M llama3.1:8b-instruct-q4_K_M qwen2.5:14b-instruct-q4_K_M \
  --out <path-to-json> --runs-per-case 2
py -3 -m unittest tests.test_soti_eval_harness tests.test_soti_runtime
```

Requires a local Ollama server (`ollama serve`, or the installed Windows
app) with the three tags above pulled. Raw per-case JSON output is not
committed (machine-specific, no value beyond this report); this document
is the durable record.
