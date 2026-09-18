"""
Sóti -- produksjons-`ModelProvider` mot en lokal Ollama-server (issue
#315, V2-5B). Bygger på det bevist riktige meldings-/verktøyoversettelses-
mønsteret fra `scripts/soti_eval/ollama_provider.py` (issue #311's
evaluering), men er en egen, uavhengig modul: produksjons-runtimen skal
aldri importere `scripts/soti_eval/`, og denne modulen legger til det
evalueringsverktøyet bevisst ikke trengte -- synlige, spesifikke feil når
Ollama/modellen ikke er tilgjengelig, i stedet for en rå
urllib-unntakstype.

Snakker kun med Ollama over loopback som standard (`base_url` peker på
`http://127.0.0.1:11434`); denne modulen gjør aldri noe nettverkskall til
noe annet endepunkt, og har ingen skyfallback -- hvis Ollama er
utilgjengelig, feiler kallet synlig (se unntakene under) i stedet for å
stille prøve noe annet.
"""
import json
import socket
import urllib.error
import urllib.request

from soti.providers import ModelProvider, ProviderSvar, ToolKall

STANDARD_BASE_URL = "http://127.0.0.1:11434"
STANDARD_NUM_CTX = 8192
STANDARD_TIMEOUT_S = 120.0

# Samme resonnement som i evalueringsversjonen (scripts/soti_eval/ollama_provider.py):
# soti.tools.Tool bærer en fritekst-beskrivelse, ikke et JSON-skjema, så
# Ollamas /api/chat-verktøykalling trenger et eksplisitt skjema her.
# Ukjente verktøynavn faller tilbake til et åpent objektskjema i stedet
# for å feile, slik at denne modulen aldri må endres for å legge til et
# nytt Sóti-verktøy.
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


def _tool_til_ollama_skjema(tool):
    return {
        "type": "function",
        "function": {
            "name": tool.navn,
            "description": tool.beskrivelse,
            "parameters": _KJENTE_SKJEMA.get(tool.navn, {"type": "object"}),
        },
    }


class OllamaProviderFeil(Exception):
    """Basisklasse for alle feil denne provideren kaster. Fanges av
    soti.cli (eller annen kallende kode) for å vise en lesbar
    feilmelding i stedet for en rå traceback -- se issue #315 §4."""


class OllamaUtilgjengelig(OllamaProviderFeil):
    """Fikk ikke kontakt med Ollama-serveren i det hele tatt (nektet
    tilkobling, DNS-feil e.l.) -- vanligvis fordi `ollama serve` ikke
    kjører."""


class OllamaTidsavbrudd(OllamaProviderFeil):
    """Forespørselen tok lengre tid enn den konfigurerte timeouten."""


class OllamaModellFeil(OllamaProviderFeil):
    """Ollama svarte, men meldte en feil knyttet til selve modellen
    (typisk: taggen er ikke pullet lokalt)."""


class OllamaSvarFeil(OllamaProviderFeil):
    """Ollama svarte med noe HTTP-/JSON-laget ikke klarte å tolke som et
    gyldig chat-svar (ugyldig JSON, uventet toppnivåform, e.l.)."""


class OllamaProvider(ModelProvider):
    """En ekte `ModelProvider` mot en lokal Ollama-server. Modell/profil
    injiseres i konstruktøren -- denne modulen hardkoder ingen bestemt
    modell, og `SotiRuntime` vet ingenting om Ollama i det hele tatt."""

    def __init__(
        self,
        model,
        base_url=STANDARD_BASE_URL,
        num_ctx=STANDARD_NUM_CTX,
        temperature=0.2,
        timeout_s=STANDARD_TIMEOUT_S,
    ):
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._num_ctx = num_ctx
        self._temperature = temperature
        self._timeout_s = timeout_s

    def generate(self, meldinger, verktoy):
        payload = {
            "model": self._model,
            "messages": [self._oversett_melding(m) for m in meldinger],
            "stream": False,
            "options": {"temperature": self._temperature},
        }
        if self._num_ctx is not None:
            payload["options"]["num_ctx"] = self._num_ctx
        if verktoy:
            payload["tools"] = [_tool_til_ollama_skjema(t) for t in verktoy]

        raw = self._post("/api/chat", payload)
        message = raw.get("message")
        if not isinstance(message, dict):
            raise OllamaSvarFeil(
                f"Ollama-svaret manglet et gyldig 'message'-felt for modell {self._model!r}: {raw!r}"
            )

        tool_kall = self._uttrekk_tool_kall(message)
        return ProviderSvar(tekst=message.get("content", ""), tool_kall=tool_kall)

    def _uttrekk_tool_kall(self, message):
        """Validerer og oversetter Ollamas `tool_calls[0]` til en `ToolKall`.
        Kaster `OllamaSvarFeil` for enhver uventet form (feil type på
        `tool_calls`/`function`, tomt/manglende funksjonsnavn, argumenter
        som ikke er eller ikke tolkes til et JSON-objekt) i stedet for å
        la en rå `AttributeError`/`TypeError`/`IndexError` lekke ut til
        `SotiRuntime`/`ToolRegistry`, eller å stille normalisere en
        ugyldig verdi (f.eks. ugyldig JSON i argumentene) til `{}` som om
        modellen faktisk ba om et tomt, gyldig kall -- se Chief-
        gjennomgangen av PR #316. Returnerer `None` når det ikke var noe
        verktøykall i svaret."""
        tool_calls = message.get("tool_calls")
        if not tool_calls:
            return None
        if not isinstance(tool_calls, list) or not isinstance(tool_calls[0], dict):
            raise OllamaSvarFeil(
                f"Ollama sendte et uventet 'tool_calls'-format for modell {self._model!r}: {tool_calls!r}"
            )

        fn = tool_calls[0].get("function")
        if not isinstance(fn, dict):
            raise OllamaSvarFeil(
                f"Ollama sendte et uventet 'function'-felt i tool_calls for modell {self._model!r}: {fn!r}"
            )

        navn = fn.get("name")
        if not isinstance(navn, str) or not navn.strip():
            raise OllamaSvarFeil(
                f"Ollama sendte et verktøykall uten et gyldig funksjonsnavn for modell {self._model!r}: {fn!r}"
            )

        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except (json.JSONDecodeError, TypeError) as e:
                raise OllamaSvarFeil(
                    f"Ollama sendte ugyldig JSON i verktøyargumentene for {navn!r} (modell {self._model!r}): {e}"
                ) from e
        if not isinstance(args, dict):
            raise OllamaSvarFeil(
                f"Ollama sendte verktøyargumenter som ikke var et JSON-objekt for {navn!r} "
                f"(modell {self._model!r}): {args!r}"
            )

        return ToolKall(navn=navn, argumenter=args)

    def sjekk_tilgjengelig(self):
        """Rask helsesjekk: bekrefter at Ollama-serveren svarer og at den
        valgte modelltaggen er kjent lokalt, FØR en hel samtale startes --
        gir en tydelig, tidlig feilmelding i stedet for først ved første
        brukertur. Kaster en av unntakene over ved feil; returnerer stille
        ved suksess."""
        payload = {"name": self._model}
        self._post("/api/show", payload)

    def _oversett_melding(self, melding):
        # SotiRuntime bruker "tool" for verktøyresultat-meldinger tilbake
        # til modellen; Ollamas /api/chat forventer samme rollenavn, så
        # dette er en ren viderelevering, ikke en oversettelse.
        return {"role": melding["role"], "content": melding["content"]}

    def _post(self, path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:
                raw_bytes = resp.read()
        except urllib.error.HTTPError as e:
            detalj = self._les_feildetalj(e)
            if e.code == 404 or "not found" in detalj.lower():
                raise OllamaModellFeil(
                    f"Ollama fant ikke modellen {self._model!r} (HTTP {e.code}): "
                    f"{detalj or e.reason}. Kjør 'ollama pull {self._model}' først."
                ) from e
            raise OllamaSvarFeil(
                f"Ollama svarte med feil (HTTP {e.code}) for modell {self._model!r}: {detalj or e.reason}"
            ) from e
        except (socket.timeout, TimeoutError) as e:
            raise OllamaTidsavbrudd(
                f"Ollama svarte ikke innen {self._timeout_s}s for modell {self._model!r} "
                f"({self._base_url}). Er modellen svært stor, eller er GPU/CPU opptatt?"
            ) from e
        except urllib.error.URLError as e:
            raise OllamaUtilgjengelig(
                f"Fikk ikke kontakt med Ollama på {self._base_url}. "
                f"Er 'ollama serve' startet? ({e.reason})"
            ) from e

        try:
            parsed = json.loads(raw_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise OllamaSvarFeil(f"Ollama svarte med noe som ikke var gyldig JSON: {e}") from e

        if not isinstance(parsed, dict):
            raise OllamaSvarFeil(
                f"Ollama svarte med et uventet JSON-format for modell {self._model!r} "
                f"(forventet et objekt, fikk {type(parsed).__name__}): {parsed!r}"
            )

        if "error" in parsed and "message" not in parsed:
            feiltekst = str(parsed["error"])
            if "not found" in feiltekst.lower():
                raise OllamaModellFeil(
                    f"Ollama meldte en modellfeil for {self._model!r}: {feiltekst}. "
                    f"Kjør 'ollama pull {self._model}' først."
                )
            raise OllamaSvarFeil(f"Ollama meldte en feil for modell {self._model!r}: {feiltekst}")

        return parsed

    @staticmethod
    def _les_feildetalj(http_error):
        try:
            body = http_error.read()
        except Exception:
            return ""
        try:
            parsed = json.loads(body.decode("utf-8"))
            return str(parsed.get("error", ""))
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            try:
                return body.decode("utf-8", errors="replace")
            except Exception:
                return ""
