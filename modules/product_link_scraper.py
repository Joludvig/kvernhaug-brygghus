import requests
from bs4 import BeautifulSoup
import time
import json
import re
from html import unescape
from urllib.parse import urljoin, urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 KvernhaugBrygghusScraper/1.0"
}

CATEGORY_MARKERS = [
    "/råvarer/",
    "/raavarer/",
    "/ol/raavarer/",
    "/ol/ingredienser/",
]

URL_BLACKLIST = [
    "pizza", "caputo", "tomat", "strianese", "peel", "flour",
    "grill", "bbq", "sauce", "saus", "utstyr", "ovn",
    "pumpe", "pump", "apparater", "bryggemaskin", "fat", "keg",
    "search", "cart", "account", "blogg", "kundesenter", "checkout",
]

def _is_category_url(path: str) -> bool:
    """Stopper kategorier som /råvarer/humle/pellets fra å bli produkter."""
    if any(marker in path for marker in CATEGORY_MARKERS):
        return True
    return False

def _has_product_id(path: str, butikk: str) -> bool:
    """Produktlenker hos begge butikkene har vanligvis varenummer i URL-en."""
    if "vestbrygg" in butikk:
        return re.search(r"/\d{4,}/", path) is not None
    if "olbrygging" in butikk:
        return re.search(r"/\d{4,}/", path) is not None
    return True

def _extract_price(text: str) -> float:
    """
    Henter én pris uten å slå sammen flere tall.
    Hindrer feil som 99.0035.
    """
    if not text:
        return 0.0

    text = text.replace("\xa0", " ")

    patterns = [
        r"(?:fra\s*)?(\d{1,4})(?:[,.](\d{1,2}))?\s*,-",
        r"(?:fra\s*)?(\d{1,4})(?:[,.](\d{1,2}))?\s*kr",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            kroner = match.group(1).replace(" ", "")
            ore = match.group(2)
            if ore:
                return float(f"{kroner}.{ore}")
            return float(kroner)

    return 0.0

_BODY_CLASS_RE = re.compile(r'<body[^>]*\bclass="([^"]*)"', re.IGNORECASE)


def _lagerstatus_fra_html(raw_html):
    """
    Leser lagerstatus fra <body class="... in-stock|not-in-stock ...">.

    Verifisert mot ekte, nedlastet rå-HTML (Steg F2) for BÅDE Weyermann- og
    Thomas Fawcett-produkter hos Vestbrygg, med og uten lager: klassetokenet
    er identisk og entydig i begge tilfeller, og finnes ikke i noe JSON-LD
    eller dataLayer-datafelt (kun dette CSS-klassetokenet er et verifisert
    signal). Returnerer "ukjent" når signalet mangler helt (f.eks. andre
    sider/butikker der konvensjonen ikke er bekreftet) -- IKKE "utsolgt",
    slik at et manglende signal aldri feiltolkes som en kjent status.

    Returnerer én av: "pa_lager", "utsolgt", "ukjent".
    """
    match = _BODY_CLASS_RE.search(raw_html)
    if not match:
        return "ukjent"
    klasser = match.group(1).split()
    if "not-in-stock" in klasser:
        return "utsolgt"
    if "in-stock" in klasser:
        return "pa_lager"
    return "ukjent"


def finn_gjær_fra_sitemap(base_url):
    """
    Henter alle gjær-produkt-URLer fra sitemap.
    Brukes fordi brandsider/kategorisider bare viser kryssalg.
    """
    GJAER_PATHS = [
        "/fermentis/", "/lallemand/", "/mangrove-jack-s/",
        "/white-labs/", "/whitelabs/", "/cellarscience/",
        "/t%c3%b8rrgj%c3%a6r/", "/fersk-gj%c3%a6r/", "/lalvin/",
    ]
    try:
        res = requests.get(f"{base_url}/sitemap.xml", headers=HEADERS, timeout=10)
        if res.status_code != 200:
            print(f"[SITEMAP] Feil HTTP {res.status_code}")
            return []
        res.encoding = res.apparent_encoding
        alle = re.findall(r"<loc>([^<]+)</loc>", unescape(res.text))
        produkt_urls = []
        for u in alle:
            ul = u.lower()
            if re.search(r"/\d{4,}/", ul) and any(p in ul for p in GJAER_PATHS):
                produkt_urls.append(u.replace("www.vestbrygg.no", "vestbrygg.no"))
        print(f"[SITEMAP] Fant {len(produkt_urls)} gjær-produkt-URLer")
        return produkt_urls
    except Exception as e:
        print(f"[SITEMAP] Feil: {e}")
        return []


def finn_humle_fra_sitemap(base_url):
    """
    Henter alle humle-produkt-URLer fra vestbrygg sitemap.
    Brukes fordi vestbrygg (ASP.NET) ikke støtter ?page=N-paginering.
    """
    HUMLE_PATHS = ["/pellets/", "/humle/"]
    try:
        res = requests.get(f"{base_url}/sitemap.xml", headers=HEADERS, timeout=10)
        if res.status_code != 200:
            print(f"[SITEMAP] Feil HTTP {res.status_code}")
            return []
        res.encoding = res.apparent_encoding
        alle = re.findall(r"<loc>([^<]+)</loc>", unescape(res.text))
        produkt_urls = []
        for u in alle:
            ul = u.lower()
            if re.search(r"/\d{4,}/", ul) and any(p in ul for p in HUMLE_PATHS):
                produkt_urls.append(u.replace("www.vestbrygg.no", "vestbrygg.no"))
        print(f"[SITEMAP] Fant {len(produkt_urls)} humle-produkt-URLer")
        return produkt_urls
    except Exception as e:
        print(f"[SITEMAP] Feil: {e}")
        return []


def finn_produktsider(base_url, kategori_path, kategori):
    produkt_lenker = set()
    side = 1
    domene = urlparse(base_url).netloc

    while True:
        url = f"{base_url}/{kategori_path}?page={side}"
        print(f"[SCAN] {url}")

        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                break

            res.encoding = res.apparent_encoding
            soup = BeautifulSoup(unescape(res.text), "html.parser")
            nye_lenker = 0

            for tag in soup.find_all("a", href=True):
                full_url = urljoin(base_url, tag["href"])
                parsed = urlparse(full_url)
                path = parsed.path.lower()

                if parsed.netloc != domene:
                    continue

                if any(bad in path for bad in URL_BLACKLIST):
                    print(f"[BLOCKED] {full_url}")
                    continue

                if _is_category_url(path):
                    continue

                if not _has_product_id(path, domene):
                    continue

                if full_url not in produkt_lenker:
                    produkt_lenker.add(full_url)
                    nye_lenker += 1
                    print(f"[FUNNET LINK] {full_url}")

            if nye_lenker == 0:
                break

            side += 1
            time.sleep(0.7)

        except Exception as e:
            print(f"[ERROR] Kunne ikke skanne {url}: {e}")
            break

    print(f"[OK] Fant {len(produkt_lenker)} produktlenker for {kategori}")
    return list(produkt_lenker)


def _variant_barnelenker_fra_html(mor_url, raw_html):
    """
    Finner Vestbryggs faktiske barn-/variantlenker (f.eks. "1 kg hel",
    "1 kg knust", "100g knust", "25 kg Sekk hel/knust") fra en mor-
    produktsides variantvelger-widget.

    Widgeten (verifisert i rå-HTML mot Weyermann- OG Thomas Fawcett-sider,
    se Steg F1-rapporten) har konsekvent formen:

        <div id="..._VariantVelgerVisuell_..."> ... </div>
            <div class="VariantChildVisual">          <!-- ev. "...  no-stock" -->
                <div id="..."><a href="/relativ/sti/...">...</a></div>
                <span class="VariantChildAttribName">1 kg heil malt</span>
            </div>
            ... (opptil fem slike blokker, ALDRI konstruert av oss)

    Bruker BeautifulSoups klasse-selector (matcher ETT klassetoken blant
    flere), så en "no-stock"-markert variant (bekreftet observert for
    CaraRed Malt sin manglende 25 kg-sekk) fanges opp på samme måte som en
    ordinær variant — denne funksjonen tar IKKE stilling til lagerstatus,
    den finner bare de faktiske lenkene som er der.

    Returnerer en TOM liste dersom siden ikke har denne variantvelgeren
    (mor-siden er da et vanlig, ikke-variantstrukturert produkt, f.eks.
    spraymalt — kalleren beholder da mor-URL-en uendret).

    Bruker ALDRI ID-aritmetikk (mor_id-6000=1kg hel osv.) — det mønsteret
    ble observert under Steg E, men er kun verifisert på 3 av ~24 malter og
    skal IKKE brukes som produksjonslogikk.
    """
    soup = BeautifulSoup(unescape(raw_html), "html.parser")
    barn = []
    sett = set()
    for div in soup.select("div.VariantChildVisual"):
        a = div.find("a", href=True)
        if not a:
            continue
        full_url = urljoin(mor_url, a["href"])
        if full_url in sett:
            continue
        sett.add(full_url)
        barn.append(full_url)
    return barn


def finn_vestbrygg_malt_med_varianter(mor_urls):
    """
    Utvider en liste med Vestbrygg-malt-URL-er (typisk output fra
    finn_produktsider()) slik at enhver mor-side med en faktisk
    variantvelger erstattes av sine ekte barn-/variant-URL-er.

    Mor-sider UTEN variantvelger (f.eks. spraymalt/ekstrakt, som ikke er
    strukturert som mor+barn) beholdes helt uendret — eksisterende
    oppførsel er 100 % bevart for dem.

    Rekkefølgen er deterministisk: mor-URL-enes opprinnelige rekkefølge
    bevares, og for hver mor-URL listes barna i den rekkefølgen
    variantvelgeren faktisk viser dem i. Duplikate URL-er (uansett om de
    kommer fra flere mor-sider eller er identiske barn) fjernes.

    INGEN rekursjon: kun de opprinnelige mor_urls hentes og undersøkes for
    varianter her — de returnerte barne-URL-ene blir aldri selv sendt inn
    i denne funksjonen igjen (de går videre til den ordinære
    parse_produktside()-flyten, som ikke driver lenke-oppdagelse).
    """
    resultat = []
    sett = set()

    def _legg_til(url):
        if url not in sett:
            sett.add(url)
            resultat.append(url)

    for mor_url in mor_urls:
        try:
            res = requests.get(mor_url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                _legg_til(mor_url)
                continue
            res.encoding = res.apparent_encoding
            barn = _variant_barnelenker_fra_html(mor_url, res.text)
        except Exception as e:
            print(f"[VARIANT-FEIL] Kunne ikke hente varianter for {mor_url}: {e}")
            barn = []

        if not barn:
            _legg_til(mor_url)
            continue

        print(f"[VARIANTER] {mor_url}: fant {len(barn)} barn-produkter")
        for url in barn:
            _legg_til(url)

    return resultat


BREADCRUMB_DENY_SEGMENTER = [
    "ølsett", "olsett", "ekstraktsett", "utstyr", "tilbehør", "tilbehor",
    "gavekort", "bøker", "boker", "rengjøring", "rengjoring",
]

BREADCRUMB_RAAVARE_KRAV = {
    "malt": "råvarer/malt",
    "humle": "råvarer/humle",
    "gjaer": "råvarer/gjær",
}

_BREADCRUMB_DATALAYER_RE = re.compile(r"'BreadCrumb'\s*:\s*'([^']*)'")


def _hent_breadcrumb_fra_datalayer(raw_html):
    """Primærsignal: GTM dataLayer.push({...'BreadCrumb': 'A/B/C'...}) på produktsiden.

    Identisk feltnavn/format hos både vestbrygg og olbrygging (verifisert mot
    rå-HTML), til stede uavhengig av om siden har JSON-LD eller ikke.
    """
    match = _BREADCRUMB_DATALAYER_RE.search(raw_html)
    if not match:
        return None
    segmenter = [s.strip() for s in match.group(1).split("/") if s.strip()]
    return segmenter or None


def _hent_breadcrumb_fra_dom(soup):
    """Fallback når dataLayer mangler: synlig brødsmulesti via `.BreadCrumbLink`.

    Samme CSS-klasse hos begge butikker, selv om ID-strukturen rundt
    (ASP.NET-repeatere) er forskjellig mellom dem.
    """
    lenker = soup.select(".BreadCrumbLink")
    segmenter = [a.get_text(strip=True) for a in lenker if a.get_text(strip=True)]
    return segmenter or None


def _brodsmule_status(raw_html, soup, kategori):
    """
    Avgjør om produktsiden hører hjemme i råvarekategorien `kategori`, basert
    på butikkens egen kategori-taksonomi i stedet for nøkkelord i produktnavnet.

    Returnerer (er_raavare, kilde):
    - (True/False, "datalayer"|"dom") når en brødsmulesti ble funnet og kunne avgjøre saken
    - (None, None) når ingen brødsmule kunne leses — kalleren faller da tilbake
      til eksisterende nøkkelordlogikk, uendret.
    """
    segmenter = _hent_breadcrumb_fra_datalayer(raw_html)
    kilde = "datalayer"
    if segmenter is None:
        segmenter = _hent_breadcrumb_fra_dom(soup)
        kilde = "dom"
    if segmenter is None:
        return None, None

    full_sti = "/".join(s.lower() for s in segmenter)

    if any(deny in full_sti for deny in BREADCRUMB_DENY_SEGMENTER):
        return False, kilde

    krav = BREADCRUMB_RAAVARE_KRAV.get(kategori)
    if krav and krav not in full_sti:
        return False, kilde

    return True, kilde


def parse_produktside(url, kategori, butikk_navn):
    if any(bad in url.lower() for bad in URL_BLACKLIST):
        return None

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return None

        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(unescape(res.text), "html.parser")
        full_text = soup.get_text("\n")

        schema_data = {}
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        schema_data = item
                        break
            except Exception:
                pass

        navn = unescape(schema_data.get("name") or "")
        if not navn:
            meta_title = soup.find("meta", property="og:title")
            h1 = soup.find("h1")
            navn = meta_title["content"] if meta_title else (h1.text if h1 else "Ukjjent")

        navn = (
            navn.replace("- Ølbrygging AS", "")
            .replace("- Vestbrygg AS", "")
            .replace("hos litebrygg,no - Litebrygg.no", "")
            .replace("hos litebrygg.no - Litebrygg.no", "")
            .replace("Kjøp ", "")
            .strip()
        )

        l_navn = navn.lower()

        er_raavare, brodsmule_kilde = _brodsmule_status(res.text, soup, kategori)
        if er_raavare is False:
            print(f"[FORKASTET] Brødsmule ({brodsmule_kilde}) er ikke råvare: {navn}")
            return None
        if brodsmule_kilde is None:
            print(f"[BRØDSMULE MANGLER] {url} -> faller tilbake til nøkkelordlogikk")

        # Nøkkelordlogikken under er siste sikkerhetsnett — brukes kun når
        # verken dataLayer eller synlig brødsmule kunne avgjøre kategorien.
        if brodsmule_kilde is None:
            # Globale ord som blokkeres for ALLE kategorier
            hard_block = [
                "kolbe", "spade", "rensemiddel", "varmematte", "ølsett",
                "allgrain", "pizzaovn", "tappetårn", "bryggeapparat",
                "fatkobling", "co2", "regulator", "ølkit", "ølsett",
                "brewtools", "kamado", "ooni", "gozney", "pizzaovn",
                "hydrometer", "termometer", "pumpe", "slange", "kran",
                "fatflak", "tappehane", "skål", "keramisk", "grill",
                "wok", "chemsan", "omberg", "topping station"
            ]
            if any(x in l_navn for x in hard_block):
                print(f"[FORKASTET] Utstyr/pakke/annet: {navn}")
                return None

            if kategori == "malt":
                malt_produsenter = [
                    "weyermann", "viking", "crisp", "castle", "château",
                    "chateau", "fawcett", "bestmalz", "bonsak", "ireks",
                    "muntons", "briess", "bairds", "brewferm"
                ]

                # Ekskluder liquid malt extract og beer enhancer
                if any(x in l_navn for x in ["liquid malt", "liquid extract", "beer enhancer", "young's"]):
                    print(f"[FORKASTET] Ekstrakt/hjelpmiddel: {navn}")
                    return None

                # Tillat spraymalt, ren malt, eller kjente produsenter
                har_malt = re.search(r"\bmalt\b|\bspraymalt\b", l_navn)
                har_ebc = re.search(r"\d+[\.,]?\d*\s*ebc", l_navn)
                har_produsent = any(p in l_navn for p in malt_produsenter)

                if not (har_malt or har_ebc or har_produsent):
                    print(f"[FORKASTET] Ikke bryggemalt: {navn}")
                    return None

                if any(x in l_navn for x in ["pizzamel", "hvetemel", "surdeig", "tomater", "mel"]):
                    print(f"[FORKASTET] Mat/pizza: {navn}")
                    return None

        pris = 0.0

        meta_price = soup.find("meta", property="product:price:amount")
        if meta_price:
            pris = _extract_price(meta_price.get("content", ""))

        if pris == 0.0 and "offers" in schema_data:
            offers = schema_data["offers"]
            if isinstance(offers, dict):
                pris = _extract_price(str(offers.get("price", "")))

        if pris == 0.0:
            price_elem = soup.select_one(".price, .product-price, .current-price")
            if price_elem:
                pris = _extract_price(price_elem.get_text(" "))

        if pris == 0.0:
            pris = _extract_price(full_text)

        if pris == 0.0:
            pris = 45.0 if kategori == "malt" else 69.0

        beskrivelse = schema_data.get("description", "")
        if not beskrivelse:
            meta_desc = soup.find("meta", property="og:description")
            beskrivelse = meta_desc["content"] if meta_desc else "Kvalitetsråvare."

        beskrivelse = re.sub(r"\s+", " ", str(beskrivelse)).strip()

        sone = f"{navn} {beskrivelse}".lower()
        produsent = "Ukjent"
        produsenter = {
            "weyermann": "Weyermann",
            "viking": "Viking Malt",
            "castle": "Castle Malting",
            "château": "Castle Malting",
            "fawcett": "Thomas Fawcett",
            "fermentis": "Fermentis",
            "safale": "Fermentis",
            "saflager": "Fermentis",
            "lallemand": "Lallemand",
            "lalbrew": "Lallemand",
            "wyeast": "Wyeast",
            "mangrove": "Mangrove Jack's",
            "white labs": "White Labs",
            "wlp": "White Labs",
            "crisp": "Crisp Malting",
            "ireks": "Ireks",
            "muntons": "Muntons",
            "briess": "Briess",
            "bestmalz": "BestMalz",
            "bonsak": "Bonsak",
        }

        for key, value in produsenter.items():
            if key in sone:
                produsent = value
                break

        ebc_match = re.search(r"(\d+[\.,]?\d*)\s*EBC", f"{navn} {beskrivelse}", re.IGNORECASE)
        if not ebc_match:
            ebc_match = re.search(r"-(\d+[\.,]?\d*)-ebc", url.lower())
        ebc = float(ebc_match.group(1).replace(",", ".")) if ebc_match else 4.0

        # Gjær-spesifikk filtrering: ekskluder gjærnæring, nutrient, ølsett, utstyr
        # (siste sikkerhetsnett — kun når brødsmule ikke kunne avgjøre saken, se over)
        if kategori == "gjaer" and brodsmule_kilde is None:
            gjaer_block = [
                "gjaernaring", "gjærnæring", "nutrient", "fermaid", "go-ferm", "yeast nutrient",
                "ispose", "shipping", "oelsett", "ølsett", "allgrain", "kit", "extract",
                "gelling agent", "wine yeast", "cider nutrient", "cider m", "cider yeast",
                "english cider", "cider", "champagne", "mead", "beer enhancer", "distiller",
                "classic turbo", "turbo", "chemsan", "brewtools", "hydrometer", "termometer", "wok",
                "kamado", "ooni", "gozney", "pizzaovn", "pizza oven", "grill",
                "omberg", "topping", "spade", "kran", "slange", "pumpe", "kolbe",
                "hop spider", "flaskebørste", "børste", "flaske",
                "500 g", "500g",
            ]
            # Normalisér til ASCII-like versjon for matching
            l_navn_normalized = l_navn.replace("æ", "ae").replace("ø", "o").replace("å", "aa")
            if any(x in l_navn or x in l_navn_normalized for x in gjaer_block):
                print(f"[FORKASTET] Gjærtilskudd/utstyr: {navn}")
                return None

            # Positiv validering: kun kjente gjær-merker/typer — sjekkes mot produktnavn (ikke beskrivelse)
            # "ale"/"ipa"/"lager" er fjernet — for generiske, treffer ølkits og utstyrsbeskrivelser
            # "m 0"-"m 9" fanger Mangrove Jack's format: "M 76", "M 41" osv.
            gjaer_valid = [
                "wyeast", "white labs", "wlp", "mangrove", "lallemand", "lalbrew",
                "fermentis", "safale", "saflager", "kveik", "k.", "cellarscience", "cs velo", "cs ne", "cs west", "cs hefe", "cs maison", "cs jungle", "cs røkkar", "cs big ben",
                "m0", "m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8", "m9",
                "m 0", "m 1", "m 2", "m 3", "m 4", "m 5", "m 6", "m 7", "m 8", "m 9",
                "saison", "yeast",
            ]
            if not any(x in l_navn for x in gjaer_valid):
                print(f"[FORKASTET] Ikke gjær: {navn}")
                return None

        alfa = 0.0
        if kategori == "humle":
            alfa_match = re.search(r"(\d+[\.,]?\d*)\s*(?:%|pcnt|prosent|aa)", f"{navn} {beskrivelse}", re.IGNORECASE)
            alfa = float(alfa_match.group(1).replace(",", ".")) if alfa_match else 5.0

        navn_clean = re.sub(r"([a-zA-ZæøåÆØÅ])(\d)", r"\1 \2", navn)
        navn_clean = re.sub(r"(\d)([a-zA-ZæøåÆØÅ])", r"\1 \2", navn_clean)
        navn_clean = re.sub(r"\s+", " ", navn_clean).strip()

        # Detekter pakningsstørrelse og regn om til pris per kg
        size_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|g|gr|gram)\b", navn_clean.lower())
        pakke_gram = None
        if size_match:
            amount = float(size_match.group(1).replace(",", "."))
            unit = size_match.group(2).lower()
            pakke_gram = amount * 1000 if unit == "kg" else amount

        er_knust = bool(re.search(r"\bknust\b|\bcrushed\b", navn_clean.lower()))

        # Detekter spraymalt som egen kategori
        er_spraymalt = bool(re.search(r"spraymalt|spray malt|liquid malt", l_navn))
        kategori_final = "spraymalt" if (kategori == "malt" and er_spraymalt) else kategori

        lagerstatus = _lagerstatus_fra_html(res.text)

        print(f"[GODKJENT] {navn_clean} ({pris} kr) -> {produsent}")

        return {
            "navn": navn_clean,
            "pris": pris,
            "pakke_gram": pakke_gram,
            "er_knust": er_knust,
            "url": url,
            "lagerstatus": lagerstatus,
            "beskrivelse": beskrivelse[:150] + "...",
            "butikk": butikk_navn,
            "kategori": kategori_final,
            "produsent": produsent,
            "ebc": ebc,
            "alfa": alfa,
            "attenuation": 0.75,
        }

    except Exception as e:
        print(f"[ERROR] Kunne ikke parse {url}: {e}")
        return None