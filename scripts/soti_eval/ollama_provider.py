"""
OllamaProvider -- a real soti.providers.ModelProvider implementation
backed by a local Ollama server (http://127.0.0.1:11434), written only to
let issue #311's evaluation exercise the existing ModelProvider boundary
with a real model instead of soti.providers.MockProvider. This is
evaluation tooling, not the deferred "real ModelProvider implementation"
product work mentioned in docs/development/SOTI_MVP.md -- it deliberately
stays a thin, throwaway adapter (no retries, no streaming, no session
persistence beyond what soti.session already provides) so the eval
harness can be deleted or replaced without touching soti/.

Tool-calling: soti.tools.Tool carries a free-text `beskrivelse` and a
Python `handler`, not a JSON Schema, because SotiRuntime never needed one
before a real provider existed. Ollama's /api/chat tool-calling requires
a JSON Schema per tool, so _tool_to_ollama_schema() below supplies one,
keyed only by the one tool name issue #60 shipped
(hent_ingrediens_info) -- unknown tool names fall back to a permissive
open-object schema rather than failing, so this stays additive and never
forces a SotiRuntime/soti.tools change.
"""
import json
import time
import urllib.request

from soti.providers import ModelProvider, ProviderSvar, ToolKall

_DEFAULT_BASE_URL = "http://127.0.0.1:11434"

# Bare kjent skjema for MVP-verktøyet fra issue #60. Ukjente verktøynavn
# faller tilbake til et åpent objektskjema i stedet for å feile -- denne
# modulen skal aldri måtte endres for å legge til et nytt Sóti-verktøy.
_KJENTE_SKJEMA = {
    "hent_ingrediens_info": {
        "type": "object",
        "properties": {
            "datasett": {"type": "string", "enum": ["malt", "humle", "gjaer"]},
            "sok": {"type": "string"},
        },
        "required": ["datasett", "sok"],
    },
}


def _tool_to_ollama_schema(tool):
    return {
        "type": "function",
        "function": {
            "name": tool.navn,
            "description": tool.beskrivelse,
            "parameters": _KJENTE_SKJEMA.get(tool.navn, {"type": "object"}),
        },
    }


class OllamaMaalinger:
    """Rå ytelsesmålinger fra ett Ollama-svar -- se
    https://github.com/ollama/ollama/blob/main/docs/api.md for feltene.
    Alle tider er nanosekunder, som Ollama selv rapporterer dem;
    konvertering til sekunder skjer i rapporteringslaget, ikke her."""

    def __init__(self, raw):
        self.total_duration_ns = raw.get("total_duration")
        self.load_duration_ns = raw.get("load_duration")
        self.prompt_eval_count = raw.get("prompt_eval_count")
        self.prompt_eval_duration_ns = raw.get("prompt_eval_duration")
        self.eval_count = raw.get("eval_count")
        self.eval_duration_ns = raw.get("eval_duration")
        # Kun satt når kallet ba om think=True og modellen/runtimen støtter
        # det -- brukt av den avgrensede 8K/16K + thinking av/på
        # tuning-runden for de to finalistene (Chief execution note).
        self.thinking = raw.get("message", {}).get("thinking") if "message" in raw else raw.get("thinking")

    def tokens_per_sekund(self):
        if not self.eval_count or not self.eval_duration_ns:
            return None
        return self.eval_count / (self.eval_duration_ns / 1e9)


class OllamaProvider(ModelProvider):
    """En ekte ModelProvider mot en lokal Ollama-server. `siste_maalinger`
    holder OllamaMaalinger for forrige generate()-kall, slik at
    evalueringsscriptet kan lese ytelsestall uten at ProviderSvar/
    SotiRuntime må endres for å bære dem.

    `tool_kall_logg` er en append-only liste, ett element per generate()-
    kall i rekkefølge (`{"navn": ..., "argumenter": ...}`, eller
    `{"navn": None, "argumenter": None}` for kall uten verktøykall). Dette
    finnes fordi `siste_raw_response` alene ikke er nok til å rekonstruere
    verktøykall-argumenter i ettertid: SotiRuntime.handle_message kan gjøre
    flere generate()-runder per henvendelse (MAKS_VERKTOY_RUNDER), og hvert
    nytt kall overskriver `siste_raw_response` -- uten denne loggen ville
    det tidligere kallets faktiske argumenter (selektiv-kritisk telemetri,
    se Chief-gjennomgangen av PR #312) vært tapt allerede før
    evalueringsscriptet fikk lest dem."""

    def __init__(self, model, base_url=_DEFAULT_BASE_URL, temperature=0.2, seed=None, timeout_s=180, num_ctx=None, think=None):
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._seed = seed
        self._timeout_s = timeout_s
        self._num_ctx = num_ctx
        self._think = think
        self.siste_maalinger = None
        self.siste_raw_response = None
        self.tool_kall_logg = []

    def generate(self, meldinger, verktoy):
        payload = {
            "model": self._model,
            "messages": [self._oversett_melding(m) for m in meldinger],
            "stream": False,
            "options": {"temperature": self._temperature},
        }
        if self._seed is not None:
            payload["options"]["seed"] = self._seed
        if self._num_ctx is not None:
            payload["options"]["num_ctx"] = self._num_ctx
        if self._think is not None:
            payload["think"] = self._think
        if verktoy:
            payload["tools"] = [_tool_to_ollama_schema(t) for t in verktoy]

        start = time.monotonic()
        raw = self._post("/api/chat", payload)
        wall_s = time.monotonic() - start

        self.siste_maalinger = OllamaMaalinger(raw)
        self.siste_maalinger.wall_clock_s = wall_s
        self.siste_raw_response = raw

        message = raw.get("message", {})
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            forste = tool_calls[0]
            fn = forste.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, TypeError):
                    args = {}
            self.tool_kall_logg.append({"navn": fn.get("name", ""), "argumenter": args})
            return ProviderSvar(tekst=message.get("content", ""), tool_kall=ToolKall(navn=fn.get("name", ""), argumenter=args))
        self.tool_kall_logg.append({"navn": None, "argumenter": None})
        return ProviderSvar(tekst=message.get("content", ""))

    def _oversett_melding(self, melding):
        rolle = melding["role"]
        # SotiRuntime bruker "tool" for verktoyresultat-meldinger tilbake
        # til modellen; Ollamas /api/chat forventer samme rollenavn.
        return {"role": rolle, "content": melding["content"]}

    def _post(self, path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))


def raw_generate(model, prompt, base_url=_DEFAULT_BASE_URL, temperature=0.2, seed=None, timeout_s=180, system=None, num_ctx=None, think=None):
    """Direkte /api/generate-kall uten SotiRuntime/verktøy -- brukes av
    evalueringsscriptet for de rene språk-/resonnement-/JSON-testene der
    verktøyløkken ikke er relevant. Returnerer (svartekst, OllamaMaalinger)."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if seed is not None:
        payload["options"]["seed"] = seed
    if num_ctx is not None:
        payload["options"]["num_ctx"] = num_ctx
    if think is not None:
        payload["think"] = think
    if system:
        payload["system"] = system

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    wall_s = time.monotonic() - start

    maalinger = OllamaMaalinger(raw)
    maalinger.wall_clock_s = wall_s
    return raw.get("response", ""), maalinger
