# Sóti Runtime MVP (V1, issue #60)

*Sóti is its own domain in the five-domain ownership model
(`docs/development/KBH_CORE_CONTRACT.md` §1: "The AI/agent layer"). This
document covers only the Sóti Runtime MVP vertical slice — it does not
change Core/App/Web/Bryggeskole/Brew Lab ownership or behavior.*

## What this is

The smallest coherent, runnable vertical slice of a local Sóti runtime:
a model-provider abstraction, an identity boundary kept separate from
Core's canonical truth, one constrained tool interface with one
read-only Core lookup tool, one Brewing skill, and local/testable session
state. Code lives in `soti/` (a new top-level package, alongside `core/`,
`modules/`, `ui/`, `web/` — one package per domain, matching the existing
repo layout).

## Files

| File | Role |
|---|---|
| `soti/providers.py` | `ModelProvider` ABC + `ProviderSvar`/`ToolKall` dataclasses + `MockProvider` (deterministic, scriptable, no network/model download). |
| `soti/identity.py` | `SOTI_IDENTITET` (system-prompt text) + `bygg_system_melding()`. Contains no ingredient/recipe facts. |
| `soti/tools.py` | `Tool`/`ToolRegistry` (constructed-content tool interface — an unregistered tool name raises `KeyError`, it is never silently ignored) + `hent_ingrediens_info()`, the one read-only Core lookup tool. |
| `soti/skills.py` | `BryggeSkill` dataclass + `BRYGGE_OPPSLAG_SKILL` (the one Brewing skill) + `registry_for_skill()`, which scopes a `ToolRegistry` down to exactly the tools a skill declares. |
| `soti/session.py` | `SotiSession` — a plain, local, in-memory dataclass. No global state, no persistence, no account system. |
| `soti/runtime.py` | `SotiRuntime` — ties a provider + a skill + a session together into one loop: take a user message, run at most `MAKS_VERKTOY_RUNDER` (2) provider/tool rounds, return the final text. |
| `tests/test_soti_runtime.py` | 21 focused tests, one class per acceptance point below. |

## How the six acceptance points are proven

1. **A local runtime interface accepts a user message and returns a
   response through a provider abstraction** — `SotiRuntime.handle_message()`,
   proven end-to-end with `MockProvider` in
   `TestProviderAbstraksjonIkkeHardkodet` and the full tool round-trip in
   `TestVerktoyRundtripGjennomRuntime`.
2. **Sóti's identity/instructions are separated from product/Core
   truth** — `soti/identity.py` contains no ingredient data at all;
   `TestIdentitetAtskiltFraCoreSannhet` asserts no real malt display name
   from `data/master_malt.json` appears in the identity text, and that
   `soti/identity.py`'s own source never references
   `modules.master_data_io` or a masterdata filename.
3. **One read-only Core lookup/tool can be called through a constrained
   tool interface** — `hent_ingrediens_info()` reads `core/manifest.json`
   to find a dataset's canonical `source_path`, then
   `modules/master_data_io.les_master_json()` (the same reader App/Web
   already use) to load it; it returns only a small, explicit field
   whitelist (never `butikk_match`/pricing). `ToolRegistry.utfoer()`
   rejects any name that was not explicitly registered.
   `TestCoreOppslagVerktoy` proves the lookup, the whitelist, and that
   the source file's bytes are unchanged after a lookup (read-only).
4. **One Brewing skill can package instructions/tool access without
   duplicating canonical Core data** — `BRYGGE_OPPSLAG_SKILL` instructs
   the model to call `hent_ingrediens_info` before answering an
   ingredient question, and contains no ingredient facts itself;
   `registry_for_skill()` scopes the tool registry to exactly the
   skill's declared tools. `TestBryggeSkillOgVerktoytilgang` proves both.
5. **Session state is local and testable** — `SotiSession` is a plain
   dataclass owned by the caller; `TestLokalSesjonstilstand` proves two
   sessions never share state and that history grows correctly turn by
   turn.
6. **Provider/model choice is not hard-coded** — `SotiRuntime.__init__`
   takes any `ModelProvider` by injection;
   `TestProviderAbstraksjonIkkeHardkodet` proves two different providers
   (including a hand-written `ModelProvider` subclass, not just
   `MockProvider`) produce different runtime behavior from the same
   code path.

## Trust boundary

Everything in this slice is local, in-process, and synchronous: no
network call, no cloud backend, no account system, no persistence beyond
the caller-owned `SotiSession` object. `MockProvider` never performs I/O.
A real local/remote model backend is future work (see below) and would
be added as a new `ModelProvider` subclass — `SotiRuntime` and the tool/
skill/session layers do not need to change for that.

## Explicitly not in this slice (per issue #60)

No generic RAG, no vector DB/embeddings/knowledge graph, no autonomous
broad agent permissions, no cloud backend/account system, no model
lock-in, no Web/App ownership takeover, no production deployment, no
merge.

## Deferred MVP work

- A real `ModelProvider` implementation (local runtime such as a
  llama.cpp/Ollama backend, or an API-backed provider) — this slice
  proves the abstraction and ships only the deterministic mock.
- A second Core lookup tool covering `humle`/`gjaer` end-to-end from a
  live provider (the tool itself already supports all three datasets via
  `core/manifest.json`; only malt is exercised in the shipped tests).
  test would extend the same pattern.
- A second skill beyond `brygge_oppslag`, and a mechanism for a runtime
  to select between skills instead of one being wired in at
  construction time.
- Any UI/product surface (Streamlit page, Web page) that lets a user
  actually talk to Sóti — this issue is runtime-only, per "No Web/App
  ownership takeover."
- Multi-turn tool budgets beyond `MAKS_VERKTOY_RUNDER = 2`, and richer
  tool-call error recovery (today an invalid tool call from a provider
  raises `KeyError` and aborts the turn — a real provider integration
  will need to decide how to surface that back to the model instead of
  to the caller).

## How to run

```
pip install -r requirements.txt
python3 -m unittest tests.test_soti_runtime
python3 -m unittest discover -s tests -b
```
