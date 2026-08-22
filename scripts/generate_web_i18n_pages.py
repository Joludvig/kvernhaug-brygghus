"""Genererer engelske, crawlbare speil-sider under web/en/ fra de norske
kilde-HTML-filene i web/*.html og web/hjelp/*.html + TEKSTER.en-ordboken i
web/js/i18n.js, samt web/sitemap.xml for alle 18 språk-URL-ene.

Kjøres manuelt, etter enhver endring i en registrert NO-side eller i
TEKSTER i i18n.js, og før commit av web/en/ + web/sitemap.xml:

    py -3 scripts/generate_web_i18n_pages.py

Ingen eksterne avhengigheter utover beautifulsoup4 (allerede krevd av
prosjektet, se requirements.txt). Deterministisk: uendret kildeinnhold gir
byte-identisk output ved re-kjøring (kan verifiseres med
`git diff --exit-code web/en/ web/sitemap.xml` etter en re-kjøring).

ARKITEKTUR (Runde 15A/15B.3/15B.4): de norske HTML-filene er ENESTE
strukturelle template/fasit; TEKSTER i i18n.js er ENESTE oversettelses-
innhold (inkl. meta-descriptions, Runde 15B.4). Denne filen eier ingen
tekst selv -- kun transformasjonen: sett <html lang="en">, anvend engelsk
tekst via data-i18n-* (inkl. data-i18n-content for <meta description>),
sett engelsk <title>, juster relative asset-stier for én ekstra katalog-
dybde, koble språkvelgeren til riktig søsterside, og overskriv
canonical/hreflang-lenkene (som allerede finnes i NO-kilden, satt for NO-
konteksten) med riktige EN-URL-er. web/en/** er 100% generert output og
skal ALDRI håndredigeres -- se web/README.md "Engelsk pre-render (web/en/)".

web/en/ inneholder KUN generert HTML -- css/js/assets/data er IKKE
kopiert inn, og lastes fra samme delte web-rot som norsk (se KBH_ROOT i
i18n.js, Runde 15B.1).

URL-kontrakt (Runde 15B.4, se web/README.md "URL-kontrakt (canonical/
hreflang)" for full begrunnelse): "pene" katalog-URL-er for index-sider
(https://kvernhaugbrygghus.no/ og /hjelp/, /en/ og /en/hjelp/), eksplisitt
.html for alle andre sider. Kun brukt for canonical/hreflang/sitemap --
selve navigasjonslenkene i HTML-en er URØRT dokument-relative .html-lenker
(uendret fra Runde 15B.3), ingen server-side rewrite/redirect er innført
eller forutsatt.
"""
import json
import posixpath
import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
WEB_EN = WEB / "en"
I18N_JS = WEB / "js" / "i18n.js"

# Eksplisitt, registrert sideliste -- se pkt. "NYE SIDER SKAL IKKE KUNNE
# GLEMMES" i Runde 15B.3-oppgaven. En norsk *.html i web/ eller web/hjelp/
# som ikke står her får generatoren til å avbryte (se valider_pages_mot_source).
PAGES = [
    "index.html",
    "mine-oppskrifter.html",
    "importer.html",
    "utskrift.html",
    "pantry.html",
    "bryggelogg.html",
    "personvern.html",
    "hjelp/index.html",
    "hjelp/bryggedag.html",
    "hjelp/bryggemetoder.html",
    "hjelp/trykkgjaering.html",
    "hjelp/sterke-ol.html",
    "hjelp/utstyr-brewzilla.html",
]

GENERATOR_MARKER = "GENERERT AV scripts/generate_web_i18n_pages.py"

# Sider som fortsatt genereres og valideres normalt via PAGES (EN-speiling
# skal fortsatt finnes og fungere), men som bevisst utelates fra
# sitemap.xml fordi de ikke har selvstendig søkeverdi for en crawler uten
# lokal brukerdata (SEO-audit: siden degraderer til en nesten tom
# tomtilstand for en crawler -- se <meta name="robots"> i NO-kilden, som
# generatoren kopierer uendret gjennom til EN-speilingen).
SITEMAP_EKSKLUDERT = {"utskrift.html"}

# Produksjonsdomene -- ENESTE stedet dette er hardkodet. Ingen etablert
# www.-konvensjon funnet noe sted i repoet ved innføring (Runde 15B.4) --
# verifisert på nytt før implementasjon.
PROD_BASE = "https://kvernhaugbrygghus.no"

_ASSET_PREFIX_RE = re.compile(r"^(?:\.\./)*(?:css|js|assets)/")


class GeneratorError(RuntimeError):
    """Hard feil -- generatoren skal ALDRI skrive delvis eller feil output
    stille. Alle kall-steder i main() lar denne boble opp og stoppe kjøringen
    med ikke-null exit-kode."""


# ---------------------------------------------------------------------------
# TEKSTER-parsing (web/js/i18n.js -> {"no": {...}, "en": {...}})
# ---------------------------------------------------------------------------

def _finn_balansert_klamme(tekst: str, start: int) -> int:
    """Returnerer index til '}' som matcher '{' ved `start`, uten å telle
    klammer inni JS-strengliteraler (enkelt-/dobbeltfnutt, backslash-escape).
    Nødvendig fordi oversettelsestekstene inneholder {param}-plassholdere
    (f.eks. "Modus: {status}") som ellers ville ødelagt balanseringen."""
    depth = 0
    i = start
    n = len(tekst)
    in_streng = None
    escaped = False
    while i < n:
        ch = tekst[i]
        if in_streng:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_streng:
                in_streng = None
        else:
            if ch in ("'", '"'):
                in_streng = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    raise GeneratorError("TEKSTER: ubalanserte klammer -- fant ingen matchende '}'.")


def parse_tekster() -> dict:
    """Leser `const TEKSTER = { no: {...}, en: {...} };` fra i18n.js som
    JSON, uten å evaluere JS. Selve strengverdiene er allerede gyldig
    JSON-syntaks i kildefilen (dobbeltfnutter, \\" og \\n er korrekt
    escaped) -- kun de to bare (uquotede) toppnivå-nøklene no/en og
    trailing commas må normaliseres før json.loads()."""
    if not I18N_JS.exists():
        raise GeneratorError(f"Fant ikke {I18N_JS}")
    src = I18N_JS.read_text(encoding="utf-8")
    marker = "const TEKSTER = "
    try:
        marker_idx = src.index(marker)
    except ValueError:
        raise GeneratorError(f"Fant ikke '{marker}' i {I18N_JS}")
    open_idx = src.index("{", marker_idx)
    close_idx = _finn_balansert_klamme(src, open_idx)
    raw = src[open_idx : close_idx + 1]

    normalisert = re.sub(r"(?<=[{,])(\s*)(no|en)(\s*):", r'\1"\2"\3:', raw)
    normalisert = re.sub(r",(\s*[}\]])", r"\1", normalisert)

    try:
        data = json.loads(normalisert)
    except json.JSONDecodeError as e:
        raise GeneratorError(
            f"TEKSTER kunne ikke parses som JSON etter normalisering: {e}"
        ) from e

    if set(data.keys()) != {"no", "en"}:
        raise GeneratorError(
            f"TEKSTER: forventet nøklene 'no'/'en', fant {sorted(data.keys())}"
        )

    no_nokler = set(data["no"].keys())
    en_nokler = set(data["en"].keys())
    if no_nokler != en_nokler:
        mangler_en = sorted(no_nokler - en_nokler)
        mangler_no = sorted(en_nokler - no_nokler)
        raise GeneratorError(
            "TEKSTER: NO/EN-nøkkelasymmetri. "
            f"Mangler i EN ({len(mangler_en)}): {mangler_en[:10]}. "
            f"Mangler i NO ({len(mangler_no)}): {mangler_no[:10]}."
        )
    return data


# ---------------------------------------------------------------------------
# Guard: nye/uregistrerte source-sider skal aldri kunne glemmes
# ---------------------------------------------------------------------------

def _oppdag_source_sider() -> set[str]:
    sider = {p.name for p in WEB.glob("*.html")}
    hjelp_dir = WEB / "hjelp"
    if hjelp_dir.is_dir():
        sider |= {f"hjelp/{p.name}" for p in hjelp_dir.glob("*.html")}
    return sider


def valider_pages_mot_source() -> None:
    faktiske = _oppdag_source_sider()
    forventede = set(PAGES)
    uregistrerte = faktiske - forventede
    manglende = forventede - faktiske
    if uregistrerte:
        raise GeneratorError(
            f"Fant NO source-side(r) som ikke er registrert i PAGES: {sorted(uregistrerte)}. "
            "Registrer den nye siden i PAGES (og gi den data-i18n-dekning + "
            "data-i18n-tittel-nokkel) før generering."
        )
    if manglende:
        raise GeneratorError(
            f"PAGES nevner side(r) som ikke finnes på disk: {sorted(manglende)}"
        )


# ---------------------------------------------------------------------------
# Speilet URL-struktur -- språkvelgerens href-mapping
# ---------------------------------------------------------------------------

def _en_katalog(page: str) -> str:
    d = posixpath.dirname(page)
    return f"en/{d}" if d else "en"


def _no_href_fra_en(page: str) -> str:
    """Href fra EN-speilets katalog tilbake til NO-søsteren."""
    return posixpath.relpath(page, _en_katalog(page))


def _en_href_selv(page: str) -> str:
    """Href fra EN-speilets katalog til seg selv (samme fil)."""
    return posixpath.relpath(f"en/{page}", _en_katalog(page))


# ---------------------------------------------------------------------------
# Absolutt URL-kontrakt (canonical/hreflang/sitemap) -- Runde 15B.4
# ---------------------------------------------------------------------------

def _url_sti_no(page: str) -> str:
    """"Pen" katalog-URL for index-sider (/, /hjelp/), ellers eksplisitt
    .html. Se modulens toppkommentar "URL-kontrakt" for begrunnelse."""
    if posixpath.basename(page) == "index.html":
        d = posixpath.dirname(page)
        return f"/{d}/" if d else "/"
    return f"/{page}"


def canonical_url(page: str, spraak: str) -> str:
    sti = _url_sti_no(page)
    if spraak == "en":
        sti = "/en" + sti
    elif spraak != "no":
        raise GeneratorError(f"canonical_url: ugyldig språk {spraak!r}")
    return PROD_BASE + sti


# ---------------------------------------------------------------------------
# HTML-transformasjon
# ---------------------------------------------------------------------------

def _dypere_asset_sti(verdi: str) -> str:
    """En norsk side og sin engelske speiling ligger på samme relative
    dybde til hverandre (web/hjelp/x.html <-> web/en/hjelp/x.html), så
    vanlige side-til-side-navigasjonslenker (index.html, ../index.html,
    bryggedag.html#anker) er UENDRET riktige og skal ikke røres. Men delte
    css/js/assets-mapper ligger KUN under web/ (ikke duplisert under
    web/en/), så en referanse til dem må bli én katalognivå dypere. Denne
    funksjonen er et rent no-op for alt annet enn nettopp de tre mappene."""
    if _ASSET_PREFIX_RE.match(verdi):
        return "../" + verdi
    return verdi


def _rewrite_asset_paths(soup: BeautifulSoup) -> None:
    for el in soup.find_all(src=True):
        el["src"] = _dypere_asset_sti(el["src"])
    for el in soup.find_all(href=True):
        klasser = el.get("class") or []
        if el.name == "a" and "sprak-knapp" in klasser:
            continue  # håndteres eksplisitt i _rewrite_sprakvelger
        el["href"] = _dypere_asset_sti(el["href"])


def _rewrite_sprakvelger(soup: BeautifulSoup, page: str) -> None:
    no_href = _no_href_fra_en(page)
    en_href = _en_href_selv(page)
    knapper = soup.select(".sprak-knapp")
    if len(knapper) != 6:
        raise GeneratorError(
            f"{page}: forventet 6 .sprak-knapp-lenker (2 språk x 3 plasseringer), fant {len(knapper)}"
        )
    for a in knapper:
        spraak = a.get("data-sprak")
        if spraak not in ("no", "en"):
            raise GeneratorError(f"{page}: .sprak-knapp uten gyldig data-sprak ({spraak!r})")
        aktiv = spraak == "en"
        a["href"] = en_href if aktiv else no_href
        klasser = [c for c in a.get("class", []) if c != "aktiv"]
        if aktiv:
            klasser.append("aktiv")
        a["class"] = klasser
        if aktiv:
            a["aria-current"] = "page"
        elif a.has_attr("aria-current"):
            del a["aria-current"]


def _hent_tekst(en: dict, nokkel: str, page: str, attributt: str) -> str:
    if nokkel not in en:
        raise GeneratorError(
            f"{page}: mangler i18n-nøkkel '{nokkel}' (referert via {attributt}) i TEKSTER.en"
        )
    return en[nokkel]


def _sett_tekst(el, verdi: str) -> None:
    el.clear()
    el.append(NavigableString(verdi))


def _sett_innhold_html(el, verdi: str) -> None:
    """data-i18n-html-kontrakten (Runde 14B): setter markup, ikke bare
    tekst -- speiler i18n.js sin applyI18n() (innerHTML i stedet for
    textContent) slik at f.eks. <strong>/<a href="#anker">-innhold blir
    ekte DOM-noder i den pre-rendrede HTML-en, ikke escaped tekst."""
    el.clear()
    fragment = BeautifulSoup(verdi, "html.parser")
    for node in list(fragment.contents):
        el.append(node.extract())


def _anvend_i18n(soup: BeautifulSoup, en: dict, page: str) -> None:
    for el in soup.select("[data-i18n]"):
        nokkel = el["data-i18n"]
        _sett_tekst(el, _hent_tekst(en, nokkel, page, "data-i18n"))
    for el in soup.select("[data-i18n-html]"):
        nokkel = el["data-i18n-html"]
        _sett_innhold_html(el, _hent_tekst(en, nokkel, page, "data-i18n-html"))
    for el in soup.select("[data-i18n-placeholder]"):
        nokkel = el["data-i18n-placeholder"]
        el["placeholder"] = _hent_tekst(en, nokkel, page, "data-i18n-placeholder")
    for el in soup.select("[data-i18n-aria-label]"):
        nokkel = el["data-i18n-aria-label"]
        el["aria-label"] = _hent_tekst(en, nokkel, page, "data-i18n-aria-label")
    for el in soup.select("[data-i18n-title]"):
        nokkel = el["data-i18n-title"]
        el["title"] = _hent_tekst(en, nokkel, page, "data-i18n-title")
    for el in soup.select("[data-i18n-alt]"):
        nokkel = el["data-i18n-alt"]
        el["alt"] = _hent_tekst(en, nokkel, page, "data-i18n-alt")
    for el in soup.select("[data-i18n-content]"):
        nokkel = el["data-i18n-content"]
        el["content"] = _hent_tekst(en, nokkel, page, "data-i18n-content")


def _rewrite_seo_links(soup: BeautifulSoup, page: str) -> None:
    """Overskriver canonical + hreflang-lenkene som allerede finnes i
    NO-kilden (satt for NO-konteksten av Runde 15B.4-migreringen) med
    riktige, absolutte EN-URL-er. Krever at NO-kilden faktisk har disse
    fire elementene -- en registrert side som mangler dem er en SEO-guard-
    feil (pkt. "META-/SEO-GUARD"), ikke noe generatoren stille kompenserer for."""
    no_url = canonical_url(page, "no")
    en_url = canonical_url(page, "en")

    canonical = soup.find("link", rel="canonical")
    if canonical is None:
        raise GeneratorError(f'{page}: mangler <link rel="canonical"> i NO-kilden')
    canonical["href"] = en_url

    alternates = soup.find_all("link", rel="alternate")
    per_kode = {a.get("hreflang"): a for a in alternates}
    for kode in ("no", "en", "x-default"):
        if kode not in per_kode:
            raise GeneratorError(
                f'{page}: mangler <link rel="alternate" hreflang="{kode}"> i NO-kilden'
            )
    per_kode["no"]["href"] = no_url
    per_kode["en"]["href"] = en_url
    per_kode["x-default"]["href"] = no_url


def _sett_tittel(soup: BeautifulSoup, en: dict, page: str) -> None:
    body = soup.find("body")
    nokkel = body.get("data-i18n-tittel-nokkel") if body else None
    if not nokkel:
        raise GeneratorError(f"{page}: <body> mangler data-i18n-tittel-nokkel")
    tittel_verdi = _hent_tekst(en, nokkel, page, "data-i18n-tittel-nokkel")
    title_tag = soup.find("title")
    if title_tag is None:
        raise GeneratorError(f"{page}: mangler <title>")
    title_tag.string = tittel_verdi


def generer_side_html(page: str, en: dict) -> str:
    src_html = (WEB / page).read_text(encoding="utf-8")
    soup = BeautifulSoup(src_html, "html.parser")

    html_tag = soup.find("html")
    if html_tag is None:
        raise GeneratorError(f"{page}: fant ikke <html>")
    html_tag["lang"] = "en"

    _anvend_i18n(soup, en, page)
    _sett_tittel(soup, en, page)
    _rewrite_asset_paths(soup)
    _rewrite_sprakvelger(soup, page)
    _rewrite_seo_links(soup, page)

    header = (
        "<!--\n"
        f"  {GENERATOR_MARKER} — IKKE REDIGER MANUELT.\n"
        f"  Kilde: web/{page} (struktur/mal) + web/js/i18n.js sin TEKSTER.en (innhold).\n"
        "  Kjør generatoren på nytt for å oppdatere denne filen — håndredigering blir\n"
        "  overskrevet ved neste kjøring. Se web/README.md \"Engelsk pre-render (web/en/)\".\n"
        "-->\n"
    )
    return header + str(soup)


# ---------------------------------------------------------------------------
# Output-hygiene: rydd kun generator-eide filer, aldri fremmed innhold
# ---------------------------------------------------------------------------

def _rens_gammel_output() -> None:
    if not WEB_EN.exists():
        return
    for p in sorted(WEB_EN.rglob("*")):
        if p.is_dir():
            continue
        if p.suffix != ".html":
            raise GeneratorError(
                f"Uventet ikke-HTML-fil funnet under web/en/: {p.relative_to(WEB)}. "
                "web/en/ skal KUN inneholde generert HTML (css/js/assets/data deles fra "
                "web/, ikke kopieres inn) -- avbryter uten å slette noe."
            )
        innhold = p.read_text(encoding="utf-8", errors="replace")
        if GENERATOR_MARKER not in innhold[:400]:
            raise GeneratorError(
                f"Fil under web/en/ mangler generator-signaturen og kan være håndredigert "
                f"eller fremmed innhold: {p.relative_to(WEB)}. Avbryter uten å slette noe."
            )
        p.unlink()
    # Fjern nå tomme undermapper (f.eks. web/en/hjelp) slik at strukturen
    # bygges helt på nytt hver kjøring -- ingen stale filer kan bli liggende.
    for p in sorted(WEB_EN.rglob("*"), reverse=True):
        if p.is_dir() and not any(p.iterdir()):
            p.rmdir()


# ---------------------------------------------------------------------------
# sitemap.xml -- PAGES for HTML/canonical/hreflang, med SITEMAP_EKSKLUDERT
# som eneste unntak for selve sitemap-outputen (se SEO-audit-begrunnelse
# ved SITEMAP_EKSKLUDERT over).
# ---------------------------------------------------------------------------

def build_sitemap_xml() -> str:
    """<url>-entries for PAGES minus SITEMAP_EKSKLUDERT, x2 (NO/EN), hver
    med gjensidige hreflang-alternates (xhtml-namespace). Ingen lastmod --
    ville gjort output ikke-deterministisk uten å representere ekte
    innholdsdata (pkt. 9 i Runde 15B.4-oppgaven). Ingen priority/changefreq."""
    linjer = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f"<!-- {GENERATOR_MARKER} — IKKE REDIGER MANUELT. -->",
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for page in PAGES:
        if page in SITEMAP_EKSKLUDERT:
            continue
        no_url = canonical_url(page, "no")
        en_url = canonical_url(page, "en")
        for loc in (no_url, en_url):
            linjer.append("  <url>")
            linjer.append(f"    <loc>{loc}</loc>")
            linjer.append(f'    <xhtml:link rel="alternate" hreflang="no" href="{no_url}"/>')
            linjer.append(f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url}"/>')
            linjer.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{no_url}"/>')
            linjer.append("  </url>")
    linjer.append("</urlset>")
    return "\n".join(linjer) + "\n"


def main() -> None:
    valider_pages_mot_source()
    tekster = parse_tekster()
    en = tekster["en"]

    _rens_gammel_output()

    for page in PAGES:
        output = generer_side_html(page, en)
        out_path = WEB_EN / page
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")

    sitemap = build_sitemap_xml()
    (WEB / "sitemap.xml").write_text(sitemap, encoding="utf-8")

    print(f"i18n-nøkler: no={len(tekster['no'])}, en={len(tekster['en'])} (symmetrisk)")
    print(f"Genererte {len(PAGES)} side(r) under {WEB_EN}")
    sitemap_url_antall = (len(PAGES) - len(SITEMAP_EKSKLUDERT)) * 2
    print(f"Genererte sitemap.xml med {sitemap_url_antall} URL-er under {WEB}")


if __name__ == "__main__":
    main()
