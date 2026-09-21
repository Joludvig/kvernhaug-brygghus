#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge -- permission-denial diagnostics (issue #348).

BAKGRUNN: issue #344/PR #345s kontrollerte retry (Agent Bridge run #749)
fullførte prosessen med `conclusion: success` -- men PR #345s HEAD stod
fortsatt stille, og kjøringens egen prosess-record viste
`permission_denials_count: 2`. INGENTING i denne workflowen fanget
FØR dette hvilke to verktøykall som faktisk ble avvist -- det tallet var
kun synlig ved å åpne selve Actions-kjøringens rå-logg for hånd, ikke i
noen varig, repo-synlig rapport (issue #348s kjerneproblem). Samme mønster
er dokumentert flere ganger tidligere i AGENT_WORKFLOW.md (issue #11, #200,
#257) -- alltid oppdaget i etterkant, aldri fanget av kjøringen selv.

MERK (ærlighet om usikkerhet, samme prinsipp som branch_setup_diagnosis.py):
denne modulen antar at `anthropics/claude-code-action` sitt
`execution_file`-output peker til en fil med Claude Code sitt vanlige
`--output-format stream-json`-meldingsformat (Anthropic Messages API sine
`tool_use`/`tool_result`-blokker) -- enten som en JSON-liste eller som
JSON-linjer (JSONL). Dette kunne IKKE bekreftes mot handlingens egen
dokumentasjon i denne runden (ingen nettverkstilgang var tilgjengelig).
Modulen er derfor bevisst DEFENSIV: en manglende `execution_file`, en tom
fil, eller et uventet format gir aldri en feil -- kun en tydelig
"utilgjengelig"-rapport, slik at dette aldri kan blokkere eller endre
leveranse-porten, branch/push-reglene eller noen annen eksisterende
kontroll. Treffsikkerheten bekreftes/forbedres på neste reelle
forekomst, ikke gjettet fram nå.

SIKKERHET (Chief-review på PR #349, issue #348): denne modulen publiseres
til en repo-synlig issue-kommentar, så den kopierer ALDRI et avvist
verktøykalls rå input-verdier direkte inn i rapporten. For `Bash`-kall
gjengis kommandolinjen (identifiserer selve den avviste operasjonen), men
kun etter at kjente hemmelighetsformer (GitHub-/AWS-/Anthropic-lignende
nøkler, samt `token=`/`password=`/`secret=`/`Authorization: Bearer
...`-mønstre) er erstattet med `[REDIGERT]`. For andre verktøy (f.eks.
`Write`/`Edit`) gjengis KUN et kjent trygt felt som `file_path`/`path`, og
ALDRI fritekst-felter som `content`/`new_string`/`old_string`/`prompt` --
uten et slikt trygt felt vises kun feltnavnene input hadde, ikke verdiene.
Samme redigering kjøres på selve avslagsteksten før den kuttes til et
sammendrag, siden noen handlinger ekko-er deler av det avviste kallet
tilbake i avslagsmeldingen.

Ren, avhengighetsfri stdlib-Python -- kalt fra
.github/workflows/claude-agent-bridge.yml (steget "Capture Claude
permission-denial diagnostics (issue #348)") og enhetstestet i
tests/test_agent_bridge_permission_denial_diagnostics.py uten å kjøre noe
mot GitHub eller den ekte actionen.
"""
import json
import os
import re
import sys

_AVSLAG_MONSTER = re.compile(
    r"(requested permissions to use|permission denied|not allowed to (run|use)"
    r"|requires approval|haven'?t granted|denied by (the )?permission)",
    re.IGNORECASE,
)

# Kjente hemmelighetsformer med et gjenkjennelig, faste prefiks/format --
# trygt å maskere uansett kontekst (issue #348, Chief-review blokker 1).
_KJENTE_HEMMELIGHETER = re.compile(
    r"ghp_[A-Za-z0-9]{36,}"  # GitHub personal access token (classic)
    r"|gh[ousr]_[A-Za-z0-9]{36,}"  # GitHub OAuth/App/user/refresh token
    r"|github_pat_[A-Za-z0-9_]{20,}"  # GitHub fine-grained PAT
    r"|(?:AKIA|ASIA)[0-9A-Z]{16}"  # AWS (temp) access key id
    r"|sk-ant-[A-Za-z0-9_-]{20,}"  # Anthropic API key
    r"|sk-[A-Za-z0-9]{20,}"  # generic sk-* style API key
)

# `<label><verdi>`-tildelinger der bare LABELEN er trygg å beholde --
# f.eks. `--token abc123`, `password=hunter2`, `Authorization: Bearer xyz`,
# `AWS_SECRET_ACCESS_KEY=...`. Verdien maskeres, ikke labelen.
_HEMMELIG_TILDELING = re.compile(
    r"(?i)((?:authorization\s*:\s*bearer"
    r"|aws_secret_access_key"
    r"|aws_session_token"
    r"|--?(?:token|password|passwd|secret|api[-_]?key|access[-_]?key)\S*)"
    r"[\s:=]+)(\S+)"
)

_MAKS_EXCERPT = 200
_MAKS_SAMMENDRAG = 500


def _redigert(tekst):
    """Erstatter kjente hemmelighetsformer/-tildelinger med `[REDIGERT]`."""
    if not tekst:
        return tekst
    tekst = _KJENTE_HEMMELIGHETER.sub("[REDIGERT]", tekst)
    tekst = _HEMMELIG_TILDELING.sub(lambda m: m.group(1) + "[REDIGERT]", tekst)
    return tekst


def _kort(tekst, maks=_MAKS_EXCERPT):
    if tekst is None:
        return ""
    enlinje = " ".join(str(tekst).split())
    enlinje = _redigert(enlinje)
    if len(enlinje) <= maks:
        return enlinje
    return enlinje[: maks - 1].rstrip() + "…"


_UGYLDIG_JSON = object()  # sentinel: skiller "parsing feilet" fra ekte JSON `null`


def les_meldinger(sti):
    """Leser execution-loggfilen på `sti`.

    Returnerer (rader, feilmelding). `rader` er `None` hvis loggen ikke er
    tilgjengelig/lesbar/tolkbar -- eller tolkbar, men uten en eneste
    meldings-dict -- i det hele tatt; ellers en IKKE-tom liste med allerede
    parsede meldings-dict-er (Chief-review blokker 2, issue #348: en tom
    eller kun-søppel-logg skal aldri late som et gyldig "0 avslag"-resultat
    -- den skal rapporteres `available=false`, samme som en manglende
    fil).
    """
    if not sti:
        return None, "Ingen execution_file-sti oppgitt for denne kjøringen."
    if not os.path.isfile(sti):
        return None, f"Fant ingen execution-loggfil på {sti!r}."
    try:
        with open(sti, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        return None, f"Kunne ikke lese execution-loggfilen: {e}"

    stripped = raw.strip()
    if not stripped:
        return None, "Execution-loggfilen var tom."

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = _UGYLDIG_JSON

    if parsed is not _UGYLDIG_JSON:
        if isinstance(parsed, list):
            rader = [r for r in parsed if isinstance(r, dict)]
        elif isinstance(parsed, dict) and isinstance(parsed.get("messages"), list):
            rader = [r for r in parsed["messages"] if isinstance(r, dict)]
        elif isinstance(parsed, dict):
            rader = [parsed]
        else:
            return None, "Execution-loggen var gyldig JSON, men i et uventet format."
        if not rader:
            return None, "Execution-loggen var gyldig JSON, men inneholdt ingen tolkbare meldinger."
        return rader, None

    # JSONL-fallback: én JSON-melding per linje, hopp stille over uleselige linjer.
    rader = []
    for linje in stripped.splitlines():
        linje = linje.strip()
        if not linje:
            continue
        try:
            obj = json.loads(linje)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rader.append(obj)
    if not rader:
        return None, "Execution-loggen kunne ikke tolkes som JSON eller JSONL (ingen gyldige meldingslinjer)."
    return rader, None


def _tool_result_tekst(blokk):
    innhold = blokk.get("content")
    if isinstance(innhold, str):
        return innhold
    if isinstance(innhold, list):
        deler = []
        for del_ in innhold:
            if isinstance(del_, dict) and isinstance(del_.get("text"), str):
                deler.append(del_["text"])
            elif isinstance(del_, str):
                deler.append(del_)
        return " ".join(deler)
    return None


# Felt det er trygt å gjengi verdien av -- alle er identifiserende
# stier/URL-er, aldri fritekst-/innholds-felter som kan bære hemmeligheter
# (f.eks. Write/Edits `content`/`new_string`/`old_string`, eller en
# `prompt`/`body`/`query`).
_TRYGGE_INPUT_NOKLER = ("file_path", "path", "notebook_path", "pattern", "url")


def _render_input(tool_input):
    """Gjengir et konservativt, trygt SIGNATUR av et avvist kalls input --
    aldri kallets fritekst-verdier direkte (issue #348, Chief-review
    blokker 1). For `Bash` gjengis kommandolinjen selv (den avviste
    operasjonen), siden `_kort`/`_redigert` maskerer kjente
    hemmelighetsformer i den før den når sammendraget. For andre verktøy
    gjengis kun et kjent trygt felt (fil-/URL-sti); uten et slikt felt
    vises bare hvilke feltnavn input hadde -- aldri verdiene.
    """
    if not isinstance(tool_input, dict):
        return ""
    command = tool_input.get("command")
    if isinstance(command, str) and command.strip():
        return command
    for nokkel in _TRYGGE_INPUT_NOKLER:
        verdi = tool_input.get(nokkel)
        if isinstance(verdi, str) and verdi:
            return verdi
    if tool_input:
        return f"(input-felt: {', '.join(sorted(tool_input.keys()))})"
    return ""


def finn_tillatelses_avslag(rader):
    """Finner permission-avslag i allerede parsede meldingsrader.

    Returnerer en liste med `{"tool", "input_excerpt", "denial_excerpt"}`,
    i den rekkefølgen de ble funnet. Inkluderer ALDRI noe annet fra
    transkriptet -- kun det avviste kallets eget verktøynavn, en kort
    (maks 200 tegn), REDIGERT (`_render_input`/`_kort`/`_redigert`) og
    aldri fritekst-verdi-bærende gjengivelse av DET kallets input, og selve
    avslagsteksten (samme lengdebegrensning, samme redigering).
    """
    tool_use_by_id = {}
    funn = []
    for rad in rader or []:
        if not isinstance(rad, dict):
            continue
        melding = rad.get("message") if isinstance(rad.get("message"), dict) else None
        innhold = melding.get("content") if melding is not None else rad.get("content")
        if not isinstance(innhold, list):
            continue
        for blokk in innhold:
            if not isinstance(blokk, dict):
                continue
            btype = blokk.get("type")
            if btype == "tool_use":
                tuid = blokk.get("id")
                if tuid:
                    tool_use_by_id[tuid] = (blokk.get("name") or "ukjent verktøy", blokk.get("input"))
            elif btype == "tool_result":
                tekst = _tool_result_tekst(blokk)
                if tekst and _AVSLAG_MONSTER.search(tekst):
                    tuid = blokk.get("tool_use_id")
                    navn, tool_input = tool_use_by_id.get(tuid, ("ukjent verktøy", None))
                    funn.append({
                        "tool": navn,
                        "input_excerpt": _kort(_render_input(tool_input)),
                        "denial_excerpt": _kort(tekst),
                    })
    return funn


def formater_sammendrag(avslag, tilgjengelig, grunn):
    """Ett-linjes, kommentar-trygt sammendrag (ingen linjeskift)."""
    if not tilgjengelig:
        return _kort(
            f"Execution-logg utilgjengelig for denne kjøringen ({grunn}) -- "
            "kan ikke liste enkelt-avslag for denne forekomsten.",
            maks=_MAKS_SAMMENDRAG,
        )
    if not avslag:
        return "Ingen permission-avslag funnet i execution-loggen for denne kjøringen."
    deler = [f"{a['tool']}: {a['input_excerpt']} — {a['denial_excerpt']}" for a in avslag]
    return _kort(" | ".join(deler), maks=_MAKS_SAMMENDRAG)


def formater_markdown(avslag, tilgjengelig, grunn):
    linjer = ["", "### Claude Agent Bridge — permission-denial diagnostics (issue #348)", ""]
    if not tilgjengelig:
        linjer.append(f"Execution-logg utilgjengelig for denne kjøringen: {grunn}")
    elif not avslag:
        linjer.append("Ingen permission-avslag funnet i execution-loggen for denne kjøringen.")
    else:
        linjer.append(f"{len(avslag)} avvist(e) verktøykall funnet:")
        linjer.append("")
        for a in avslag:
            linjer.append(f"- **{a['tool']}**: `{a['input_excerpt']}` — {a['denial_excerpt']}")
    linjer.append("")
    return "\n".join(linjer)


def main():
    sti = os.environ.get("EXECUTION_FILE", "").strip()
    rader, feil = les_meldinger(sti)

    if rader is None:
        tilgjengelig = False
        grunn = feil or "Execution-logg utilgjengelig."
        avslag = []
    else:
        tilgjengelig = True
        grunn = None
        avslag = finn_tillatelses_avslag(rader)

    print(f"available={'true' if tilgjengelig else 'false'}")
    print(f"denial_count={len(avslag)}")
    print(f"denial_summary={formater_sammendrag(avslag, tilgjengelig, grunn)}")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(formater_markdown(avslag, tilgjengelig, grunn))
        except OSError:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
