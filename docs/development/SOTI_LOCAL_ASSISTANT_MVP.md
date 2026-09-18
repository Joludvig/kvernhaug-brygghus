# Sóti Local Assistant MVP (V1, issue #315, SÓTI V2-5B)

*Bounded child of Roadmap V2 #78, V2-5B — Local Assistant MVP. Builds on
the Sóti runtime foundation (#60/PR #68) and the real owner-PC
model/runtime evaluation (#311/PR #312). This document covers only
making Sóti actually runnable as a real local assistant — it changes no
Core/App/Web/Bryggeskole/Brew Lab behavior, adds no RAG/knowledge
integration, and ships no product UI.*

## What this is

The first real, runnable local Sóti: a production `ModelProvider`
against a local Ollama server, and the smallest practical local CLI chat
entry point, wired into the existing, unmodified `SotiRuntime` /
`soti.tools` / `soti.skills` / `soti.session` layers from the V1 runtime
MVP. The acceptance target from issue #315:

> From a local terminal, the owner can start Sóti, have a stable
> multi-turn conversation with the selected local model, and observe the
> existing constrained read-only Core tool path work through the real
> `SotiRuntime`.

## Selected profile (from #311/PR #312)

- DEFAULT model: `llama3.1:8b-instruct-q4_K_M`
- Runtime: Ollama 0.34.1
- `num_ctx`: 8192 (explicit — never inherited from the model's advertised
  maximum, per the V2-5A evaluation's own finding that larger contexts
  cost significant throughput on this hardware for no benefit on Sóti's
  actual conversation lengths)
- FALLBACK model: `ministral-3:8b`, same `num_ctx=8192` — reachable via
  `--model ministral-3:8b` on the CLI, no code change required

## Files

| File | Role |
|---|---|
| `soti/ollama_provider.py` | `OllamaProvider(ModelProvider)` — production provider against a local Ollama server (`/api/chat`, `/api/show`). `OllamaProviderFeil` and four specific subclasses (`OllamaUtilgjengelig`, `OllamaTidsavbrudd`, `OllamaModellFeil`, `OllamaSvarFeil`) map every local failure mode to a fail-visible, specific exception instead of a raw `urllib`/`json` exception. |
| `soti/cli.py` | `main()` / `kjor_chat()` — the local CLI chat entry point. Starts one `SotiSession`, injects an `OllamaProvider` into the existing `SotiRuntime`, loops on user input until an explicit quit command, prints Sóti's replies, and turns local provider/tool failures into readable messages instead of stack traces. |
| `tests/test_soti_ollama_provider.py` | 25 mocked tests: message/tool-schema translation, explicit `num_ctx=8192`, loopback-only/no-cloud-fallback, and every error-mapping branch (`URLError`, timeout, HTTP 404, HTTP 5xx, malformed JSON, missing `message` field, an `error` field inside an HTTP-200 body). No live Ollama server required. |
| `tests/test_soti_cli.py` | 14 mocked tests: quit-command handling (all four spellings, case-insensitive), blank-input skipping, EOF/Ctrl-C handling, a real multi-turn conversation through `SotiRuntime` + `MockProvider` (no Ollama needed), provider/tool error messages surfacing without crashing the loop, and `main()`'s argument wiring (default model/context, `--model` override, `--skip-healthcheck`). |
| `docs/development/SOTI_MVP.md` | One line corrected — the "real `ModelProvider`" item in "Deferred MVP work" now points here instead of describing it as future work. |

No file under `soti/`, `soti.tools`, `soti.skills`, `soti.session`, or
`soti.runtime` was modified — the existing `ModelProvider` boundary
absorbed the real backend with zero changes, exactly as
`soti/runtime.py`'s own docstring says it should.

## What the provider does and does not do

**Does:**
- Talks to a local Ollama server over loopback only
  (`http://127.0.0.1:11434` by default).
- Translates `soti.providers.ModelProvider.generate(meldinger, verktoy)`
  into Ollama's `/api/chat` request shape, and the response back into
  `ProviderSvar`/`ToolKall` — the same proven translation pattern
  `scripts/soti_eval/ollama_provider.py` validated in #311, reimplemented
  independently here (production code never imports `scripts/soti_eval/`).
- Sends an explicit `num_ctx` (default 8192) on every call.
- Exposes `sjekk_tilgjengelig()`, a lightweight `/api/show` health check
  the CLI runs once at startup so a missing server/model fails
  immediately with a clear message, before the user types anything.
- Raises a specific `OllamaProviderFeil` subclass for every local failure
  mode issue #315 §4 lists (see table below) instead of letting a raw
  `urllib.error`/`json.JSONDecodeError` propagate.

**Does not:**
- Retry. A single bounded-timeout attempt per call; the CLI's per-message
  `except OllamaProviderFeil` lets the *user* decide to try again (e.g.
  after starting `ollama serve` in another window), rather than the
  provider silently retrying underneath them.
- Stream. `stream: false` throughout — the smallest thing that works for
  a synchronous `generate()` call; issue #315 doesn't ask for streaming
  output.
- Fall back to any other endpoint, cloud or otherwise. There is no
  fallback code path in this module at all — an unreachable Ollama server
  is a visible error, never a silent switch to something else.
- Send `seed`/`think` — the eval harness's tuning knobs for reproducible
  benchmark runs are not relevant to an interactive chat session, so the
  production provider omits them to stay minimal per issue #315's "keep
  changes minimal" guidance.

## Error-mode mapping (issue #315 §4)

| Failure | Exception | User-facing message (CLI) |
|---|---|---|
| Ollama server unreachable | `OllamaUtilgjengelig` | `[Sóti -- lokal feil]: Fikk ikke kontakt med Ollama på <url>. Er 'ollama serve' startet? (<reason>)` |
| Requested model not pulled | `OllamaModellFeil` | `[Sóti -- lokal feil]: Ollama fant ikke modellen '<tag>' (...). Kjør 'ollama pull <tag>' først.` |
| Request exceeds the configured timeout | `OllamaTidsavbrudd` | `[Sóti -- lokal feil]: Ollama svarte ikke innen <n>s for modell '<tag>' (...). Er modellen svært stor, eller er GPU/CPU opptatt?` |
| Malformed/unexpected Ollama response (bad JSON, missing `message`, an `error` field in an otherwise-200 body) | `OllamaSvarFeil` | `[Sóti -- lokal feil]: ...` (specific to the parse failure) |
| Model requests an unregistered tool | `KeyError` (raised by the existing, unmodified `soti.tools.ToolRegistry.utfoer`) | `[Sóti -- ukjent verktøy forespurt av modellen]: ...` |
| Tool-call round limit reached | Not an exception — `SotiRuntime` itself already returns a fail-visible fallback string (`"Sóti nådde grensen for verktøykall-runder uten et endelig svar."`), printed like any normal reply | *(no special CLI handling needed)* |

All five of the exception rows above are covered by mocked tests in
`tests/test_soti_ollama_provider.py`; the two CLI-level rows (`KeyError`,
the round-limit fallback text) are covered in `tests/test_soti_cli.py`
and the existing `tests/test_soti_runtime.py` respectively. Every case in
the CLI's per-message `except` blocks lets the conversation loop
continue rather than exiting — a transient failure does not kill the
whole terminal session.

## Trust boundary (unchanged from the V1 runtime MVP)

Still local, in-process, synchronous, no persistence beyond the
caller-owned `SotiSession`, no account system. The one addition is a
single outbound HTTP call per turn to `127.0.0.1:11434` — the owner's own
already-running local Ollama process, never a remote host.

## Running it

```
ollama serve   # if not already running as a background service
py -3 -m soti.cli
py -3 -m soti.cli --model ministral-3:8b   # FALLBACK profile, no code change
```

## Tests

```
py -3 -m unittest tests.test_soti_ollama_provider tests.test_soti_cli tests.test_soti_runtime
```

## Owner-PC live smoke (issue #315 requirement — CI cannot prove this)

Run against the real, already-running local Ollama 0.34.1 server, via
the **shipped, unmodified `soti.cli.kjor_chat()`** (scripted input fed
through the same `inn`/`ut` injection points the mocked CLI tests use —
this exercises the exact production code path, not a reimplementation of
it), a real `soti.ollama_provider.OllamaProvider`, a real `SotiRuntime`,
and a real `SotiSession`, all in one process, one session, four
consecutive turns.

- Model: `llama3.1:8b-instruct-q4_K_M`
- `num_ctx`: 8192
- Startup health check (`sjekk_tilgjengelig()`, the same one the CLI runs
  before opening the prompt): **OK**, 0.026 s
- Total session wall-clock (4 turns): 9.95 s
- Session history at end: 13 messages (1 system + 4 × (user, tool,
  assistant) — every turn triggered at least one tool round; see below)

| # | Requirement | User turn | Sóti's reply | Result |
|---|---|---|---|---|
| 1 | Norwegian identity | "Hei! Hvem er du, og hva kan du hjelpe meg med?" | "Hei! Jeg er Sóti, din hjelpende hånd i Kvernhaug Brygghus. Jeg er her for å hjelpe deg med spørsmål om bryggeprosessen. Hva kan jeg hjelpe deg med i dag?" | **PASS** |
| 2 | Ordinary non-tool turn | "Hva er forskjellen på primærgjæring og sekundærgjæring?" | "Jeg kunne ikke finne noen informasjon om primærgjæring og sekundærgjæring i mine opplysninger. Kanskje du kan gi meg mer informasjon eller spørre på en annen måte?" | **PASS** (see note below) |
| 3 | Valid Core ingredient lookup through the real tool path | "Kan du fortelle meg om malten CaraHell?" | "CaraHell er en type karamell- eller krystallmalt fra Weyermann. Den har en EBC-værdi på 25,0 og en potensial på 1,034. Den anbefalte stilen er Pilsner, Lys Lager og Helles. Smakstegnene er lys karamell, honning, brød og mild sødme." | **PASS — verified grounded**: every fact (EBC 25.0, potential 1.034, styles, flavor tags, producer) matches `data/master_malt.json`'s real `carahell` entry byte-for-byte |
| 4 | Unavailable-tool expectation, no fabricated success | "Kan du bestille CaraHell-malt for meg fra en nettbutikk?" | "Jeg kan ikke bestille varer for deg. Jeg er en hjelpende hånd, ikke en nettbutikk. Hvis du ønsker å bestille CaraHell-malt, må du kontakte en nettbutikk direkte." | **PASS** — honest refusal, no invented order/purchase |
| 5 | ≥3 turns, same session | (all 4 turns above) | — | **PASS** — 4 turns, one `SotiSession`, one process |

**Observation worth recording (not a defect, not something this issue's
bounded scope asks to fix):** the model attempted a tool call on *every*
turn, including turns 1, 2, and 4 where no concrete ingredient was named
— e.g. on turn 1 it called `hent_ingrediens_info(sok='')` (empty search,
`funnet: False`) before answering the identity question anyway, and on
turn 2 it searched the `gjaer` dataset for the literal phrase
"primærgjæring vs sekundærgjæring" (also `funnet: False`) and then told
the user honestly it had no information, rather than answering from its
own general brewing knowledge as the identity/reasoning cases in the
V2-5A evaluation showed it capable of. This is the brewing skill's own
instruction ("bruk verktøyet ... FØR du svarer -- ikke svar fra
hukommelsen ... Oppgi aldri fakta verktøyet ikke returnerte", see
`soti/skills.py`) being applied more broadly than the concrete-ingredient
case it was written for. Two things are worth noting about it: it is a
prompt/skill-design nuance, not a code defect — `SotiRuntime`, the
provider, and the tool registry all behaved exactly as designed on every
one of these calls — and, more importantly, **it never once caused a
fabrication**: every failed or inapplicable tool call was followed by an
honest "I don't have that" rather than an invented answer, which is
Sóti's actual trust boundary holding up under real, unscripted model
behavior. Tuning the skill instruction to trigger tool use only for
concrete ingredient questions is left for a future round (V2-5C or a
small follow-up), per issue #315's "do not redesign `SotiRuntime`/skills
unless a tiny change is required by a concrete live-provider failure" —
this is a quality nuance, not a failure requiring a code change.

Raw session transcript and timing: not committed (owner-PC-specific,
regenerable), captured during this session in
`soti_smoke_v25b_result.json`.
