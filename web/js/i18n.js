// Runde 14 -- vanilla NO/EN i18n. Ingen npm, ingen build-steg, ingen
// tredjeparts i18n-bibliotek. Språk er REN presentasjon: recipe-state,
// localStorage-oppskrifter og .kbhrecipe-formatet vet ingenting om dette
// laget og skal aldri gjøre det (se web/README.md "Språk (NO/EN)").
//
// Runde 15B.2 -- dokumentets EGEN <html lang> (satt i HTML-kilden, og i en
// fremtidig /en/ av pre-render-generatoren) er AUTORITATIV språkkilde.
// localStorage er kun en husket preferanse for LIVE-bytte på samme side
// (se settSprak() under), aldri en side-autoritet, og browserens språk
// (navigator.language) brukes ikke lenger noe sted til å velge språk -- se
// gjeldendeSprak(). Nødvendig fordi en fremtidig pre-rendret /en/-side
// ellers kunne blitt vist på norsk (eller omvendt) avhengig av brukerens
// tidligere valg eller browserspråk, uavhengig av hva URL-en faktisk
// serverte -- SEO-kritisk galt.
//
// URL-strategi V1 (uendret denne runden): client-side språkbytte på SAMME
// url (ingen /en/, ingen query/hash-parameter) -- én statisk fil-struktur,
// ingen duplisert HTML å vedlikeholde, kompatibelt med dagens enkle statiske
// hosting. Kjent konsekvens: søkemotorer kan ikke indeksere en egen engelsk
// URL i V1 -- se web/README.md for anbefalt fremtidig løsning (statisk
// pre-render av /en/ ved deploy, IKKE en runtime-avhengighet).

const SPRAK_NOKKEL = "kvernhaug_web_sprak";
const SPRAK_LISTE = ["no", "en"];
const SPRAK_DEFAULT = "no";

// Runde 15B.1 -- delt web-root, uavhengig av hvilket katalognivå siden som
// laster dette scriptet ligger på (i dag: / eller /hjelp/; forarbeid for en
// fremtidig /en/ og /en/hjelp/ som deler samme js/ og data/ -- se
// web/README.md "Runtime data-paths"). Beregnes fra i18n.js sin egen
// <script src>-URL siden i18n.js alltid lastes som et vanlig, synkront,
// første <script> på alle sider (verifisert i alle 8 HTML-filer). js/
// ligger alltid rett under web-roten, uansett hvor mange undermapper siden
// selv ligger i, så "../" herfra er alltid roten. document.currentScript er
// kun pålitelig SYNKRONT under selve script-kjøringen -- caches derfor med
// det samme i en konstant, ikke lest på nytt senere (f.eks. inne i en
// event-listener, der den ville vært null).
const KBH_ROOT = (() => {
  const scriptUrl = document.currentScript && document.currentScript.src;
  if (!scriptUrl) {
    // Skal aldri skje ved korrekt <script src="...i18n.js">-lasting -- dette
    // er en utviklerfeil (f.eks. inline-script eller dynamisk injeksjon uten
    // src), ikke noe brukeren kan forårsake. Feiler høyt fremfor stille
    // fallback som kunne hentet data fra feil sted.
    throw new Error("KBH_ROOT: kan ikke bestemme web-root -- i18n.js ble ikke lastet via <script src>.");
  }
  return new URL("../", scriptUrl).href;
})();

// Dokumentets EGEN <html lang>, lest FØR noe annet i denne filen får sjanse
// til å endre den. Dette er kilden gjeldendeSprak() under prioriterer
// først. Caches med det samme -- document.documentElement.lang endres
// senere av settSprak() (live-bytte) og skal IKKE leses på nytt her, ellers
// ville live-bytte sluttet å virke (gjeldendeSprak() ville alltid falt
// tilbake til DOKUMENT_SPRAK i stedet for å beholde _gjeldendeSprak).
const DOKUMENT_SPRAK = SPRAK_LISTE.includes(document.documentElement.lang) ? document.documentElement.lang : null;

let _gjeldendeSprak = null;

function _lagretSprak() {
  try {
    const v = localStorage.getItem(SPRAK_NOKKEL);
    return SPRAK_LISTE.includes(v) ? v : null;
  } catch {
    return null;
  }
}

// Prioritet (Runde 15B.2): (1) dokumentets egen <html lang> -- satt i
// HTML-kilden, autoritativ, aldri overstyrt av en tidligere lagret
// preferanse; (2) lagret preferanse i localStorage, KUN som fallback for en
// side uten gyldig lang-attributt (skal i praksis aldri inntreffe -- alle
// dagens sider har korrekt lang="no" i kilden); (3) norsk default.
// navigator.language brukes ikke lenger noe sted til å velge språk --
// fjernet fordi det tidligere kunne få en pre-rendret engelsk side til å
// reverte til norsk (eller omvendt) etter at JS kjørte, uavhengig av hva
// URL-en faktisk serverte. Se web/README.md "Språk (NO/EN)".
function gjeldendeSprak() {
  if (_gjeldendeSprak) return _gjeldendeSprak;
  _gjeldendeSprak = DOKUMENT_SPRAK || _lagretSprak() || SPRAK_DEFAULT;
  return _gjeldendeSprak;
}

// Enkel parameter-substitusjon -- {navn}-plassholdere, ingen plural-regler,
// ingen betinget templating. Nok for denne appens behov (se pkt. 19).
function t(nokkel, params) {
  const spraak = gjeldendeSprak();
  let tekst = (TEKSTER[spraak] && TEKSTER[spraak][nokkel]) ?? (TEKSTER[SPRAK_DEFAULT] && TEKSTER[SPRAK_DEFAULT][nokkel]);
  if (tekst === undefined) return nokkel;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      tekst = tekst.replaceAll(`{${k}}`, v);
    }
  }
  return tekst;
}

function applyI18n(root) {
  const scope = root || document;
  scope.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.getAttribute("data-i18n"));
  });
  // data-i18n-html -- samme som data-i18n, men setter innerHTML i stedet for
  // textContent. Kun for brødtekst som trenger inline-markup (<strong>/<em>/
  // <a href="#anker">) -- typisk hjelp/bryggehåndbok-innhold (Runde 14B).
  // Trygt fordi TEKSTER er statisk, hardkodet innhold vi selv author -- aldri
  // brukerinput -- så det finnes ingen XSS-vektor her.
  scope.querySelectorAll("[data-i18n-html]").forEach((el) => {
    el.innerHTML = t(el.getAttribute("data-i18n-html"));
  });
  scope.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder")));
  });
  scope.querySelectorAll("[data-i18n-aria-label]").forEach((el) => {
    el.setAttribute("aria-label", t(el.getAttribute("data-i18n-aria-label")));
  });
  scope.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.setAttribute("title", t(el.getAttribute("data-i18n-title")));
  });
  scope.querySelectorAll("[data-i18n-alt]").forEach((el) => {
    el.setAttribute("alt", t(el.getAttribute("data-i18n-alt")));
  });
}

// aria-current (ikke aria-pressed) fordi .sprak-knapp er ekte <a href>-
// lenker siden Runde 15B.3, ikke toggle-knapper -- se _initSprakvelger().
function _oppdaterSprakvelgerUI() {
  document.querySelectorAll(".sprak-knapp").forEach((knapp) => {
    const aktiv = knapp.dataset.sprak === gjeldendeSprak();
    knapp.classList.toggle("aktiv", aktiv);
    if (aktiv) {
      knapp.setAttribute("aria-current", "page");
    } else {
      knapp.removeAttribute("aria-current");
    }
  });
}

// Bytter UI-tekst direkte i gjeldende DOM UTEN navigasjon -- beholdt som
// offentlig API (Runde 14) for evt. fremtidig/programmatisk bruk og fordi
// applyI18n()/gjeldendeSprak()/kvernhaug:sprakendret fortsatt er i aktiv
// bruk (dynamiske JS-strenger, re-render ved language-relevante hendelser).
// IKKE lenger koblet til språkvelgeren i UI-et -- se _initSprakvelger().
// Siden Runde 15B.3 er normal språkbytte-kontrakt URL-navigasjon til
// tilsvarende side under /en/ (ekte pre-rendret engelsk HTML, crawlbar uten
// JS) -- settSprak() ville uansett bli overskrevet av neste sideinnlasting.
function settSprak(kode) {
  if (!SPRAK_LISTE.includes(kode) || kode === gjeldendeSprak()) return;
  _gjeldendeSprak = kode;
  try {
    localStorage.setItem(SPRAK_NOKKEL, kode);
  } catch {
    // localStorage utilgjengelig -- språket gjelder likevel resten av økten
  }
  document.documentElement.lang = kode;
  document.title = t(document.body.dataset.i18nTittelNokkel || "meta.tittelFallback");
  applyI18n(document);
  _oppdaterSprakvelgerUI();
  window.dispatchEvent(new CustomEvent("kvernhaug:sprakendret", { detail: { sprak: kode } }));
}

// Runde 15B.3 -- .sprak-knapp er ekte <a href>-lenker til søsteren under
// /en/ (satt statisk i HTML-kilden/av generatoren, mekanisk speilet
// katalogstruktur -- se scripts/generate_web_i18n_pages.py). Ingen JS
// trengs for selve navigasjonen. Eneste nødvendige runtime-logikk: bevare
// en ev. nåværende location.hash (f.eks. #steg-7 på en hjelpeside) ved
// klikk, siden en statisk href aldri kan vite hvilket anker brukeren
// faktisk står på. Ingen query-parametre i dagens app, men bevares gratis
// av samme mekanisme dersom det skulle dukke opp.
function _initSprakvelger() {
  document.querySelectorAll(".sprak-knapp[href]").forEach((lenke) => {
    lenke.addEventListener("click", () => {
      if (location.hash || location.search) {
        const base = lenke.getAttribute("href").split("#")[0].split("?")[0];
        lenke.href = base + location.search + location.hash;
      }
    });
  });
  _oppdaterSprakvelgerUI();
}

// Normaliserer <html lang> til den løste språkverdien -- en no-op på alle
// dagens sider (som allerede har korrekt lang i kilden, altså
// DOKUMENT_SPRAK === gjeldendeSprak() her), men gir et definert resultat
// for en side uten gyldig lang-attributt (fallback-grenen i
// gjeldendeSprak() over).
document.documentElement.lang = gjeldendeSprak();

document.addEventListener("DOMContentLoaded", () => {
  applyI18n(document);
  _initSprakvelger();
  if (document.body.dataset.i18nTittelNokkel) {
    document.title = t(document.body.dataset.i18nTittelNokkel);
  }
});

const TEKSTER = {
  no: {
    "meta.tittelFallback": "Kvernhaug Brygghus",
    "meta.builder.tittel": "Kvernhaug Brygghus — Oppskriftsbygger",
    "meta.mineOppskrifter.tittel": "Kvernhaug Brygghus — Mine oppskrifter",
    "meta.importer.tittel": "Kvernhaug Brygghus — Importer oppskrift",
    "meta.utskrift.tittel": "Kvernhaug Brygghus — Utskrift",
    "meta.hjelp.tittel": "Kvernhaug Brygghus — Hjelp & bryggehåndbok",
    "meta.hjelpBryggedag.tittel": "En bryggedag — fra vann til gjæringskar — Kvernhaug Brygghus",
    "meta.hjelpBryggemetoder.tittel": "Bryggemetoder — Kvernhaug Brygghus",
    "meta.hjelpBrewzilla.tittel": "Utstyr: BrewZilla — Kvernhaug Brygghus",

    "brand.motto": "Brygg med ild. Del med ære.",
    "brand.stedTagline": "Ved Dalelva i Åsane",
    "brand.heroAlt": "Kvernhaug Brygghus — kråke ved kvernhuset i gyllen fjelldal",

    "sprak.no": "NO",
    "sprak.en": "EN",
    "sprak.ariaLabel": "Bytt språk",

    "chrome.apneMeny": "Åpne meny",
    "chrome.lukkMeny": "Lukk meny",
    "chrome.navKompaktAriaLabel": "Hovednavigasjon (kompakt)",
    "chrome.navAriaLabel": "Hovednavigasjon",

    "nav.bygger": "🍺 Oppskriftsbygger",
    "nav.mineOppskrifter": "📂 Mine oppskrifter",
    "nav.importer": "📥 Importer oppskrift",
    "nav.utskrift": "🖨️ Utskrift",
    "nav.hjelp": "📖 Hjelp / Bryggehåndbok",

    "modus.byttAriaLabel": "Bytt modus",
    "modus.knappLaerlingKort": "🎓 Lærling",
    "modus.knappMesterKort": "⚙️ Mester",
    "modus.statusMester": "Modus: Bryggmester",
    "modus.statusLaerling": "Modus: Bryggelærling",
    "modus.forstegangTittel": "Hvordan vil du brygge?",
    "modus.forstegangIntro": "Du kan bytte modus når som helst fra menyen (☰).",
    "modus.velgAriaLabel": "Velg modus",
    "modus.laerlingNavn": "🎓 Bryggelærling",
    "modus.laerlingUndertekst": "Veiledet modus – lær mens du brygger",
    "modus.mesterNavn": "⚙️ Bryggmester",
    "modus.mesterUndertekst": "Full kontroll – alle detaljer tilgjengelig",

    "footer.enkel": "Data lagres kun lokalt i denne nettleseren (localStorage) — ingenting sendes til noen server.",
    "footer.builder": "Data lagres kun lokalt i denne nettleseren (localStorage) — ingenting sendes til noen server. Full versjon med pantry, vannkjemi og full sensorisk analyse: se hovedappen.",

    "help.ogAriaLabel": "Hva er OG?",
    "help.fgAriaLabel": "Hva er FG?",
    "help.abvAriaLabel": "Hva er ABV?",
    "help.ibuAriaLabel": "Hva er IBU?",
    "help.ebcAriaLabel": "Hva er EBC?",
    "help.effektivitetAriaLabel": "Hva er brygghuseffektivitet?",
    "help.utgjaeringAriaLabel": "Hva er utgjæring?",
    "help.alfasyreAriaLabel": "Hva er alfasyre?",
    "help.smakshjulAriaLabel": "Hva er smakshjulet?",
    "help.stilmatchAriaLabel": "Hva er stilmatch?",
    "help.lesMer": "Les mer →",
    "help.lukk": "Lukk",

    "builder.grunndata.tittel": "Grunndata",
    "builder.grunndata.olnavn": "Ølnavn",
    "builder.grunndata.olnavnPlaceholder": "Navn på ølet",
    "builder.grunndata.brygger": "Brygger",
    "builder.grunndata.byggerPlaceholder": "Ditt navn",
    "builder.grunndata.bryggeri": "Bryggeri",
    "builder.grunndata.bryggeriPlaceholder": "Navn på bryggeriet",
    "builder.grunndata.batchvolum": "Batchvolum (liter)",
    "builder.grunndata.effektivitet": "Brygghuseffektivitet (%)",
    "builder.grunndata.notater": "Notater",
    "builder.grunndata.notaterPlaceholder": "F.eks. planlagte justeringer, tips til deg selv …",

    "builder.stilvalg.tittel": "Hva vil du brygge?",
    "builder.stilvalg.olstil": "Ølstil",
    "builder.stilvalg.hjelpetekst": "Valgfritt — du kan bygge helt fritt. Velger du en stil, vises stilmatchen til høyre mens du bygger.",
    "builder.stilvalg.comboboxPlaceholder": "Søk eller velg ølstil …",
    "builder.stilvalg.comboboxAriaLabel": "Velg ølstil",

    "builder.malt.tittel": "Malt",
    "builder.malt.leggTil": "+ Legg til malt",
    "builder.malt.prosentSum": "Prosent-sum: {sum}%",
    "builder.malt.brukProsentfordeling": "Bruk prosentfordeling",
    "builder.malt.comboboxPlaceholder": "Søk etter malt …",
    "builder.malt.comboboxAriaLabel": "Velg malt",
    "builder.malt.egendefinertTitle": "Legg til en malt som ikke finnes i biblioteket",
    "builder.malt.fjernTitle": "Fjern",
    "builder.malt.fjernAriaLabel": "Fjern malt",
    "builder.malt.ebcPlaceholder": "EBC *",
    "builder.malt.potensialePlaceholder": "Potensiale * (1.036)",

    "builder.egendefinert.navnPlaceholder": "Navn *",
    "builder.egendefinert.produsentPlaceholder": "Produsent (valgfritt)",
    "builder.egendefinert.tilbakeKnapp": "🔍 Søk i bibliotek i stedet",
    "builder.egendefinertKnapp": "+ Egendefinert",

    "builder.humle.tittel": "Humle",
    "builder.humle.leggTil": "+ Legg til humle",
    "builder.humle.comboboxPlaceholder": "Søk etter humle …",
    "builder.humle.comboboxAriaLabel": "Velg humle",
    "builder.humle.alfaPlaceholder": "alfa",
    "builder.humle.gramPlaceholder": "gram",
    "builder.humle.egendefinertTitle": "Legg til en humle som ikke finnes i biblioteket",
    "builder.humle.fjernTitle": "Fjern",
    "builder.humle.fjernAriaLabel": "Fjern humle",
    "builder.humle.opprinnelsePlaceholder": "Opprinnelse (valgfritt)",
    "builder.humle.typePlaceholder": "Type (valgfritt)",
    "builder.humle.maalIbuLabel": "Mål-IBU (denne tilsetningen)",
    "builder.humle.beregnGramKnapp": "Beregn gram",

    "builder.gjaer.tittel": "Gjær",
    "builder.gjaer.label": "Gjær",
    "builder.gjaer.egendefinertKnapp": "+ Egendefinert gjær",
    "builder.gjaer.utgjaering": "Forventet utgjæring (%)",
    "builder.gjaer.navnPlaceholder": "Navn (valgfritt)",
    "builder.gjaer.gjaertypePlaceholder": "Gjærtype (valgfritt)",
    "builder.gjaer.comboboxPlaceholder": "Søk etter gjær …",
    "builder.gjaer.comboboxAriaLabel": "Velg gjær",
    "builder.gjaer.egendefinertNavnDefault": "Egendefinert gjær",

    "builder.handling.tittel": "Lagre og eksporter",
    "builder.handling.nyOppskrift": "🆕 Ny oppskrift",
    "builder.handling.lagreOppskrift": "💾 Lagre oppskrift",
    "builder.handling.lagreFil": "📄 Lagre oppskriftsfil (.kbhrecipe)",
    "builder.handling.apneFil": "📂 Åpne oppskriftsfil",
    "builder.handling.hjelpetekst": "Lagrede oppskrifter ligger lokalt i denne nettleseren. Vil du ta backup eller flytte en oppskrift til en annen enhet, kan du lagre den som en .kbhrecipe-fil og åpne den igjen her eller under «📥 Importer oppskrift».",
    "builder.handling.avansertSummary": "Avansert: rå JSON",
    "builder.handling.eksporterKnapp": "⬇️ Eksporter rå JSON",
    "builder.handling.avansertHjelpetekst": "Kun til debugging/videre bearbeiding — bruk «Lagre oppskriftsfil» over til vanlig lagring og backup.",

    "builder.skaler.naavaerende": "Nåværende batch: {vol} L",
    "builder.skaler.maalLabel": "Skaler til (L)",
    "builder.skaler.knapp": "📐 Skaler oppskrift",
    "builder.skaler.hjelpetekst": "Malt (kg) og humle (gram) skaleres proporsjonalt til nytt volum. Ølnavn, brygger, bryggeri, notater, valgt stil, gjærvalg, humletid og alfasyre-overstyring endres ikke.",
    "builder.skaler.confirm": "Skaler oppskriften fra {fra} L til {til} L?\n\nAlle malt- (kg) og humlemengder (gram) endres proporsjonalt (faktor {faktor}). Navn, stil, notater og gjærvalg endres ikke.",
    "builder.skaler.statusUgyldig": "Ugyldig volum -- skalering avbrutt.",
    "builder.skaler.statusUendret": "Mål-volum er allerede lik gjeldende volum.",
    "builder.skaler.statusFerdig": "Skalert fra {fra} L til {til} L.",

    "identitet.utenNavn": "Uten navn",

    "builder.smaksprofil.tittel": "Smaksprofil",
    "builder.stilanalyse.tittel": "Stilanalyse",
    "builder.stilanalyse.tomTittel": "🍺 Ingen stilmatch ennå",
    "builder.stilanalyse.tomTekst": "Legg til malt og/eller humle for å se hvilke stiler oppskriften nærmer seg.",
    "builder.stilanalyse.headlineLabel": "Numerisk nærmeste stil",
    "builder.stilanalyse.nearbyTittel": "Nærliggende stiler",
    "builder.stilanalyse.valgtTittel": "Valgt stil",

    "stilanalyse.innenforAlle": "✅ Innenfor alle stilens numeriske grenser.",
    "stilanalyse.innenforOmrade": "✅ Oppskriften ligger innenfor det typiske området for {stil}.",
    "stilanalyse.ingenTreff": "Ingen stil i biblioteket treffer godt nok ennå — juster ingrediensene eller se nærliggende stiler under.",
    "stilanalyse.leggTilForMatch": "Legg til malt og/eller humle for å se hvordan oppskriften matcher {stil}.",
    "stilanalyse.buGu": "Bitterhetsindeks (BU:GU): {verdi}",

    "malt.prosent.tomFelt": "Skriv inn en prosentverdi i minst én maltrad før du bruker fordelingen.",
    "malt.prosent.ugyldigTall": "Prosentverdien må være et gyldig tall mellom 0 og 100 i alle redigerte rader.",
    "malt.prosent.justerTil100": "De valgte prosentene blir {sum} %. Juster summen til 100 %, eller la minst én malt stå urørt slik at resten kan beregnes automatisk.",
    "malt.prosent.overstiger100": "De valgte prosentene blir {sum} %, som er mer enn 100 %. Juster en av de redigerte radene.",

    "oppskrift.lagretStatus": "Lagret \"{navn}\" i nettleseren. Se \"📂 Mine oppskrifter\" for å åpne den igjen senere.",
    "oppskrift.lagreFilStatus": "Lastet ned \"{filnavn}.kbhrecipe\". Bruk denne filen som backup eller for å flytte oppskriften til en annen enhet.",
    "oppskrift.nyConfirm": "Vil du starte en ny oppskrift? Endringer i den aktive oppskriften som ikke er lagret eller eksportert vil forsvinne.",
    "oppskrift.nyStatus": "Ny, tom oppskrift.",
    "oppskrift.apneConfirm": "Åpne denne oppskriften? Den aktive oppskriften blir erstattet.",
    "oppskrift.apnetStatus": "Oppskriften er åpnet.",
    "oppskrift.lesefeil": "Kunne ikke lese filen.",

    "kbhrecipe.ugyldigJson": "Denne filen kunne ikke leses som en oppskriftsfil (ugyldig JSON).",
    "kbhrecipe.ikkeGyldigOppskrift": "Denne filen ser ikke ut som en gyldig Kvernhaug-oppskrift.",
    "kbhrecipe.manglerVersjon": "Denne oppskriftsfilen mangler versjonsinformasjon og kan ikke åpnes sikkert her.",
    "kbhrecipe.nyereVersjon": "Denne oppskriftsfilen er laget med en nyere versjon av Kvernhaug Brygghus og kan ikke åpnes sikkert her ennå.",
    "kbhrecipe.ustottetVersjon": "Denne oppskriftsfilen bruker en versjon av oppskriftsformatet som ikke støttes her.",
    "kbhrecipe.manglerOppskrift": "Denne oppskriftsfilen mangler selve oppskriften.",

    "meta.mineOppskrifter.sidetittel": "📂 Mine oppskrifter",
    "mineOppskrifter.tittel": "Mine lagrede oppskrifter",
    "mineOppskrifter.hjelpetekst": "Lagres kun i denne nettleseren (localStorage) — ingenting sendes til noen server.",
    "mineOppskrifter.ingenOppskrifter": "Ingen lagrede oppskrifter ennå. Bygg en oppskrift og trykk \"Lagre oppskrift\" i Oppskriftsbyggeren.",
    "mineOppskrifter.importerTittel": "Importere en oppskrift?",
    "mineOppskrifter.importerHjelpetekst": "Fil- og tekstimport har flyttet til en egen side i menyen:",
    "mineOppskrifter.apneKnapp": "Åpne i byggeren",
    "mineOppskrifter.slettTitle": "Slett",
    "mineOppskrifter.slettAriaLabel": "Slett {navn}",
    "mineOppskrifter.slettConfirm": "Slette \"{navn}\"? Dette kan ikke angres.",
    "mineOppskrifter.lagretDato": "Lagret {dato}",

    "meta.importer.sidetittel": "📥 Importer oppskrift",
    "importer.tittel": "Importer oppskrift",
    "importer.intro": "Bygg oppskriften fra en fil eller fra limt inn tekst — begge veier sender deg videre til Oppskriftsbyggeren med feltene forhåndsutfylt.",
    "importer.velgMetodeAriaLabel": "Velg importmetode",
    "importer.modusFil": "📄 Åpne fil",
    "importer.modusTekst": "✏️ Lim inn tekst",
    "importer.filTittel": "Åpne oppskriftsfil",
    "importer.filHjelpetekst": "Har du en .kbhrecipe-fil — fra denne siden, fra Oppskriftsbyggerens \"Lagre oppskriftsfil\", eller fra noen andre? Velg den her, så åpnes den direkte i byggeren. Eldre, rå oppskrifts-JSON støttes fortsatt.",
    "importer.filVelgKnapp": "⬆️ Velg en .kbhrecipe-fil",
    "importer.tekstTittel": "Lim inn oppskriftstekst",
    "importer.formatKgLabel": "Kg-format:",
    "importer.formatPctLabel": "Prosentformat (krever total maltmengde):",
    "importer.formatHumleLabel": "Humle (må ha koketid):",
    "importer.formatGjaerLabel": "Gjær:",
    "importer.tekstPlaceholder": "Lim inn oppskriften her …",
    "importer.analyserKnapp": "🔍 Analyser",
    "importer.matchetTittel": "Matchet",
    "importer.ikkeGjenkjentTittel": "Ikke gjenkjent",
    "importer.bekreftKnapp": "✅ Legg inn i oppskriftsbygger",

    "import.tellinger": "Tolket: {malt} malt · {humle} humle · {gjaer} gjær-linje(r)",
    "import.ingenGjenkjent": "Ingen ingredienser ble gjenkjent.",
    "import.treffMalt": "Malt: {navn} → <code>{display}</code> ({mengde} kg)",
    "import.treffHumle": "Humle: {navn} → <code>{display}</code> ({gram} g, {tid} min)",
    "import.treffGjaer": "Gjær: {navn} → <code>{display}</code>",
    "import.kategoriMalt": "Malt",
    "import.kategoriHumle": "Humle",
    "import.kategoriGjaer": "Gjær",
    "import.advarselProsentSum": "Maltprosentene summerer til {sum}% (forventet ~100%).",
    "import.advarselManglerTotal": "Mangler 'Total malt: X kg' — oppgi total maltmengde for å konvertere prosenter til kg.",
    "oppskrift.importertNavnDefault": "Importert oppskrift",

    "meta.utskrift.sidetittel": "🖨️ Utskrift",
    "utskrift.tomTittel": "Utskrift",
    "utskrift.tomTekst1": "Du har ingen oppskrift å skrive ut ennå.",
    "utskrift.tomTekst2": "Gå til <a href=\"index.html\">Oppskriftsbyggeren</a> og lag en, eller åpne en lagret oppskrift under <a href=\"mine-oppskrifter.html\">Mine oppskrifter</a>.",
    "utskrift.velgOppskriftTittel": "Velg oppskrift",
    "utskrift.oppskriftLabel": "Oppskrift",
    "utskrift.skrivUtTittel": "Skriv ut",
    "utskrift.skrivUtHjelpetekst": "Hvert ark er sin egen, utskriftsvennlige side — ikke bare et utskrift av denne skjermen.",
    "utskrift.knappOppskriftsark": "🖨️ Oppskriftsark",
    "utskrift.knappHandleliste": "🖨️ Handleliste",
    "utskrift.knappBryggedagsark": "🖨️ Bryggedagsark",
    "utskrift.knappBryggelogg": "🖨️ Bryggelogg",
    "utskrift.velgerAktivt": "{navn} (aktiv i byggeren, ikke lagret)",
    "utskrift.infoTall": "OG {og} · FG {fg} · ABV {abv} · IBU {ibu} · EBC {ebc}",

    "print.footer": "Laget med Kvernhaug Brygghus Oppskriftsbygger",
    "print.oppskriftsark.undertittel": "Oppskriftsark",
    "print.handleliste.undertittel": "Handleliste",
    "print.bryggedagsark.undertittel": "Bryggedagsark",
    "print.bryggelogg.undertittel": "Bryggelogg",
    "print.olstilLabel": "Ølstil:",
    "print.meta": "{vol} L · {eff}% brygghuseffektivitet",
    "print.maltTittel": "Malt",
    "print.humleTittel": "Humle",
    "print.gjaerTittel": "Gjær",
    "print.notaterTittel": "Notater",
    "print.navnKol": "Navn",
    "print.produsentKol": "Produsent",
    "print.mengdeKol": "Mengde",
    "print.alfasyreKol": "Alfasyre",
    "print.koketidKol": "Koketid",
    "print.oppskriftsark.ingenMalt": "Ingen malt lagt til.",
    "print.oppskriftsark.ingenHumle": "Ingen humle lagt til.",
    "print.ingenMalt": "Ingen malt.",
    "print.ingenHumle": "Ingen humle.",
    "print.ingenGjaerValgt": "Ingen gjær valgt.",
    "print.gjaerNavnFallback": "Gjær",
    "print.utgjaeringSuffix": " — forventet utgjæring {pct} %",
    "print.bryggedato": "Bryggedato:",
    "print.batch": "Batch: {vol} L",
    "print.ingrediensTittel": "Ingredienser",
    "print.humletilsetningKol": "Humletilsetning",
    "print.tidspunktKol": "Tidspunkt",
    "print.planlagteTallTittel": "Planlagte tall",
    "print.planlagtOg": "Planlagt OG",
    "print.faktiskOg": "Faktisk OG",
    "print.faktiskFg": "Faktisk FG",
    "print.planlagtVolum": "Planlagt volum",
    "print.faktiskVolum": "Faktisk volum",
    "print.sjekklisteTittel": "Sjekkliste",
    "print.sjekkliste.0": "Klargjør utstyr og ingredienser",
    "print.sjekkliste.1": "Varm opp meskevann",
    "print.sjekkliste.2": "Tilsett malt / mesk",
    "print.sjekkliste.3": "Mashout (hvis relevant)",
    "print.sjekkliste.4": "Skyll (hvis metoden bruker det)",
    "print.sjekkliste.5": "Kok",
    "print.sjekkliste.6": "Humletilsetninger som planlagt over",
    "print.sjekkliste.7": "Kjøl ned",
    "print.sjekkliste.8": "Mål OG",
    "print.sjekkliste.9": "Overfør til gjæringskar og tilsett gjær",
    "print.notaterFraBryggedagenTittel": "Notater fra bryggedagen",
    "print.bryggedato2": "Bryggedato",
    "print.batchKol": "Batch",
    "print.faktiskAbv": "Faktisk ABV",
    "print.gjaerLabel": "Gjær",
    "print.gjaeringstemp": "Gjæringstemp.",
    "print.karbonering": "Karbonering",
    "print.viktigeDatoerTittel": "Viktige datoer",
    "print.overfortTilGjaering": "Overført til gjæring",
    "print.ferdigGjaeret": "Ferdig gjæret",
    "print.flasketFatet": "Flasket / fatet",
    "print.klarTilSmaking": "Klar til smaking",
    "print.bryggedagsnotaterTittel": "Bryggedagsnotater",
    "print.gjaeringsnotaterTittel": "Gjæringsnotater",
    "print.smaksnotaterTittel": "Smaksnotater",
    "print.hvaFungerteBra": "Hva fungerte bra?",
    "print.hvaBorEndres": "Hva bør endres neste gang?",

    "hjelp.sidetittel": "📖 Hjelp & bryggehåndbok",
    "hjelp.sidenavFaq": "📖 Hjelp & FAQ",
    "hjelp.sidenavBryggedag": "🗓️ En bryggedag",
    "hjelp.sidenavBryggemetoder": "⚗️ Bryggemetoder",
    "hjelp.sidenavUtstyr": "🛠️ Utstyr: BrewZilla",
    "hjelp.innholdAriaLabel": "Innhold på denne siden",

    "hjelp.idx.toc.a": "A. Kom i gang",
    "hjelp.idx.toc.b": "B. Forstå oppskriften",
    "hjelp.idx.toc.c": "C. Ingredienser",
    "hjelp.idx.toc.d": "D. Bryggeprosess",
    "hjelp.idx.toc.e": "E. Spørsmål &amp; svar",
    "hjelp.idx.intro": "Et oppslagsverk for deg som bygger en oppskrift i Kvernhaug Brygghus. Alt her er skrevet for å svare på to spørsmål: hva betyr dette, og hvorfor bryr jeg meg? Bruk innholdsmenyen til å hoppe rundt, eller bla nedover som en vanlig håndbok.",

    "hjelp.idx.secA.tittel": "A. Kom i gang",
    "hjelp.idx.forsteOppskrift.tittel": "Lag din første øloppskrift",
    "hjelp.idx.forsteOppskrift.tekst": "Start i <strong>Grunndata</strong> med et ølnavn og batchvolum (hvor mange liter du skal brygge). Legg deretter til minst én malt under <strong>Malt</strong> — søkefeltet filtrerer mens du skriver. Gjør det samme under <strong>Humle</strong> og velg en <strong>Gjær</strong>. Tallene i <strong>Resultat</strong> (OG/FG/ABV/IBU/EBC) og smakshjulet oppdaterer seg automatisk for hvert valg — du trenger ikke trykke noen \"beregn\"-knapp.",
    "hjelp.idx.forsteOppskrift.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Det finnes ingen \"feil\" startpunkt. Prøv deg fram, se hvordan tallene endrer seg, og juster til de treffer stilen du har lyst på — eller bare det du synes høres godt ut.",

    "hjelp.idx.laerlingMester.tittel": "Bryggelærling og Bryggmester",
    "hjelp.idx.laerlingMester.tekst": "De to knappene øverst bytter mellom to visninger av <em>samme</em> oppskrift. <strong>Bryggelærling</strong> skjuler tekniske detaljer og viser mer veiledning — fin når du er ny. <strong>Bryggmester</strong> viser alt: BU:GU, nærliggende stiler, full stilanalyse. Ingen data forsvinner når du bytter — det er bare hvor mye som vises på skjermen som endrer seg.",
    "hjelp.idx.laerlingMester.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Du kan bytte fram og tilbake så mye du vil, når som helst i prosessen. Mange starter i Bryggelærling og går over til Bryggmester etter hvert som begrepene blir kjente.",

    "hjelp.idx.lagreOppskrift.tittel": "Lagre en oppskrift",
    "hjelp.idx.lagreOppskrift.tekst": "\"💾 Lagre oppskrift\" lagrer oppskriften <strong>i denne nettleseren</strong> (localStorage) under navnet du har gitt den. Den dukker opp i \"Mine lagrede oppskrifter\" lenger ned, og du kan laste den inn igjen når som helst — også etter at du har lukket fanen.",
    "hjelp.idx.lagreOppskrift.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Ingenting sendes til noen server. Lagrer du på én enhet, er oppskriften bare der — bruk \"⬇️ Eksporter (JSON)\" hvis du vil ta den med til en annen datamaskin eller telefon.",

    "hjelp.idx.aapneImportere.tittel": "Åpne eller importere en oppskrift",
    "hjelp.idx.aapneImportere.tekst": "Klikk \"Åpne i byggeren\" på en lagret oppskrift under \"Mine oppskrifter\" for å laste den inn. Har du en oppskrift som JSON-fil, eller bare limt inn som ren tekst (f.eks. \"5 kg Maris Otter\", \"20 g Magnum 60 min\"), bruk \"📥 Importer oppskrift\" i menyen — inkludert eventuelle egendefinerte ingredienser.",

    "hjelp.idx.skriveUt.tittel": "Skrive ut",
    "hjelp.idx.skriveUt.tekst": "Under \"Skriv ut\" finner du fire egne ark: <strong>Oppskriftsark</strong> (for å dele oppskriften med andre), <strong>Handleliste</strong> (bare ingrediensene), <strong>Bryggedagsark</strong> (arbeidsark for selve bryggedagen) og <strong>Bryggelogg</strong> (tomt skjema for faktiske resultater, til å fylle ut med penn). Hvert ark er sin egen, ryddige side — ikke bare et utskrift av skjermbildet.",

    "hjelp.idx.secB.tittel": "B. Forstå oppskriften",
    "hjelp.idx.og.tittel": "OG — Original Gravity",
    "hjelp.idx.og.tekst": "OG måler mengden sukker som er løst i vørteren <em>før</em> gjæring starter — vanligvis et tall som 1,050. Jo høyere OG, jo mer sukker har gjæren å jobbe med.",
    "hjelp.idx.og.hvorfor": "<strong>Hvorfor du bryr deg:</strong> OG er utgangspunktet for både alkoholstyrke og fylde. Øker du maltmengden (eller batcheffektiviteten), stiger OG. Reduserer du malt eller øker vannmengden, synker den. Et lyst, lett øl ligger typisk rundt 1,035–1,045; et sterkt øl kan ligge over 1,070.",

    "hjelp.idx.fg.tittel": "FG — Final Gravity",
    "hjelp.idx.fg.tekst": "FG måler sukkeret som er <em>igjen</em> etter at gjæringen er ferdig. Forskjellen mellom OG og FG forteller hvor mye sukker som faktisk ble omdannet til alkohol.",
    "hjelp.idx.fg.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Lav FG gir et tørrere øl, høy FG gir mer restsødme og fylde i munnen. FG styres i denne oppskriftsbyggeren av gjærens forventede <a href=\"#utgjaering\">utgjæring</a> — velger du en gjær med høyere utgjæring, synker FG. Den faktiske FG-en du måler etter brygging kan avvike noe fra det beregnede tallet, se <a href=\"#faq-faktisk-fg\">FAQ</a>.",

    "hjelp.idx.abv.tittel": "ABV — Alkoholstyrke",
    "hjelp.idx.abv.tekst": "ABV (Alcohol By Volume) er alkoholprosenten i det ferdige ølet, regnet ut fra forskjellen mellom OG og FG.",
    "hjelp.idx.abv.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Vil du ha et sterkere øl, må enten OG opp (mer malt) eller FG ned (gjær med høyere utgjæring) — eller begge deler. Et sessionøl ligger gjerne under 4,5 %, et vanlig pale ale rundt 5–6 %, et imperial stout kan passere 9–10 %.",

    "hjelp.idx.ibu.tittel": "IBU — Bitterhet",
    "hjelp.idx.ibu.tekst": "IBU (International Bitterness Units) er et mål på humlebitterhet. Høyere tall betyr mer bittert øl. De fleste ølstiler ligger et sted mellom 10 og 70 IBU.",
    "hjelp.idx.ibu.hvorfor": "<strong>Hvorfor du bryr deg:</strong> IBU styres av humlemengde, alfasyre og koketid — se <a href=\"#alfasyre\">alfasyre</a>. Humle tilsatt tidlig i koket (60 min) gir mest bitterhet; humle tilsatt sent (0–10 min) gir mer aroma og smak, men lite bitterhet. Dobler du mengden av en tidlig humletilsetning, øker IBU markant; flytter du samme humle til slutten av koket, synker IBU kraftig selv om mengden er lik.",

    "hjelp.idx.ebc.tittel": "EBC — Farge",
    "hjelp.idx.ebc.tekst": "EBC måler ølets farge, fra blekt gult (lave tall, under 10) via kobber og rav til nesten sort (over 80).",
    "hjelp.idx.ebc.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Fargen kommer nesten utelukkende fra malten — mørkere malt (som ristet malt eller karamellmalt) gir en langt større EBC-økning per kilo enn lys basemalt. Legger du til bare 200 g ristet malt i en ellers lys oppskrift, kan EBC hoppe merkbart selv om mengden er liten.",

    "hjelp.idx.buGu.tittel": "BU:GU — Bitterhet mot fylde",
    "hjelp.idx.buGu.tekst": "BU:GU (vist i Bryggmester) er forholdet mellom IBU og OG (skalert), og sier noe om balansen mellom bitterhet og maltfylde. Et lavt tall betyr et maltdominert øl, et høyt tall betyr et humledominert øl.",
    "hjelp.idx.buGu.hvorfor": "<strong>Hvorfor du bryr deg:</strong> To øl kan ha samme IBU, men oppleves helt forskjellig avhengig av hvor mye malt (OG) som står imot bitterheten. BU:GU er et raskt sjekkpunkt på om balansen stemmer med det du sikter mot.",

    "hjelp.idx.utgjaering.tittel": "Utgjæring (attenuation)",
    "hjelp.idx.utgjaering.tekst": "Utgjæring er hvor stor andel av sukkeret gjæren klarer å omdanne til alkohol, oppgitt i prosent. En gjær med 75 % utgjæring \"spiser\" 75 % av det tilgjengelige sukkeret.",
    "hjelp.idx.utgjaering.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Høyere utgjæring gir lavere <a href=\"#fg\">FG</a> og dermed et tørrere øl med litt høyere <a href=\"#abv\">ABV</a>, ved samme OG. Velger du en biblioteksgjær, fylles utgjæringen ut automatisk — du kan overstyre den manuelt hvis du bruker en egendefinert gjær eller vet noe annet om akkurat din gjærstamme.",

    "hjelp.idx.alfasyre.tittel": "Alfasyre",
    "hjelp.idx.alfasyre.tekst": "Alfasyre (α-syre) er prosentandelen bitterstoffer i humlen. Høyere alfasyre gir mer bitterhet per gram humle.",
    "hjelp.idx.alfasyre.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Alfasyre-innholdet i en gitt humlesort varierer normalt noe fra sesong til sesong og pose til pose — det som faktisk står trykt på <em>din</em> pose kan avvike fra bibliotekets typiske verdi. Juster gjerne alfa-feltet til det som faktisk står på posen din for et mer presist IBU-anslag; se <a href=\"#faq-produsentdata\">FAQ</a>.",

    "hjelp.idx.effektivitet.tittel": "Brygghuseffektivitet",
    "hjelp.idx.effektivitet.tekst": "Effektivitet er hvor stor andel av maltens sukkerpotensial du faktisk får ut i vørteren på ditt eget utstyr og med din egen teknikk — 75 % er et vanlig utgangspunkt, men det varierer fra bryggeri til bryggeri.",
    "hjelp.idx.effektivitet.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Effektiviteten går rett inn i <a href=\"#og\">OG</a>-beregningen. Bryggelærling skjuler feltet og bruker 75 % som estimat, slik at du kan komme i gang uten å måtte vite dette først. I Bryggmester kan du justere det etter egne, målte brygg — se også <a href=\"#faq-traff-ikke-og\">FAQ</a>.",

    "hjelp.idx.maltpotensial.tittel": "Maltpotensial",
    "hjelp.idx.maltpotensial.tekst": "Maltpotensial sier hvor mye sukker en gitt malt kan bidra med per kilo — grunnlaget for OG-beregningen. Ulike malttyper har ulikt potensial; en ren basemalt gir mer enn en spesialmalt med lavere gjærbart innhold.",
    "hjelp.idx.maltpotensial.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Legger du inn en egendefinert malt, må du oppgi et anslått potensial selv (produsentens datablad, hvis du har det, er beste kilde). Et for høyt tall overvurderer OG, et for lavt undervurderer den.",

    "hjelp.idx.smakshjulet.tittel": "Smakshjulet",
    "hjelp.idx.smakshjulet.tekst": "Smakshjulet er et radardiagram med 18 smaksakser, basert på malt-, humle- og gjærvalgene dine. Jo lenger ut mot kanten en akse strekker seg, jo mer fremtredende er den smaken forventet å bli.",
    "hjelp.idx.smakshjulet.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Det er en rask, visuell sjekk av om oppskriften faktisk peker i den retningen du hadde tenkt — for eksempel om en \"sitrus/tropisk\"-akse virkelig stikker ut når du har brukt mye Citra og Mosaic. Diagrammet er en forventning basert på ingrediensdataene, ikke en garanti for hvordan det faktiske ølet smaker.",

    "hjelp.idx.stilmatching.tittel": "Stilmatching",
    "hjelp.idx.stilmatching.tekst": "Stilmatchen sammenligner oppskriftens tall (OG/FG/ABV/IBU/EBC) og smaksprofil mot kjente ølstiler i Kvernhaug Brygghus sitt eget bibliotek, og viser hvilken stil oppskriften ligner mest på — pluss noen nærliggende alternativer.",
    "hjelp.idx.stilmatching.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Det er en rettesnor, ikke en dom. Se <a href=\"#stilgrenser\">stilgrenser</a> og <a href=\"#faq-feil-verdi\">FAQ</a> for hvordan du bør tolke den. Biblioteket dekker 26 stiler — det er <em>ikke</em> hele det offisielle BJCP 2021-stilheftet (som har rundt 100 understiler).",

    "hjelp.idx.stilgrenser.tittel": "Stilgrenser",
    "hjelp.idx.stilgrenser.tekst": "Hver stil i biblioteket har typiske tallområder for OG/FG/IBU/EBC/ABV, hentet fra kjente stilbeskrivelser. Når oppskriften din avviker fra en valgt stils typiske område, forklarer stilveiledningen dette i rolig språk — \"litt utenfor\" eller \"tydelig utenfor\" — aldri som en feilmelding.",
    "hjelp.idx.stilgrenser.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Stilgrenser er en beskrivelse av hva som er <em>typisk</em> for en stil, ikke en regel du må følge. Mange gode øl ligger bevisst utenfor en stils typiske område.",

    "hjelp.idx.secC.tittel": "C. Ingredienser",
    "hjelp.idx.omMalt.tittel": "Malt",
    "hjelp.idx.omMalt.tekst": "Malt er kornet som gir vørteren sukker (til alkohol), farge og mye av grunnsmaken. Det er kilden til det aller meste av OG og EBC i oppskriften.",

    "hjelp.idx.omHumle.tittel": "Humle",
    "hjelp.idx.omHumle.tekst": "Humle gir bitterhet (tidlig i koket), og aroma/smak (sent i koket eller etter koking). Samme humlesort kan altså bidra helt forskjellig avhengig av <em>når</em> den tilsettes.",

    "hjelp.idx.omGjaer.tittel": "Gjær",
    "hjelp.idx.omGjaer.tekst": "Gjæren omdanner sukker til alkohol og CO₂, men påvirker også smak og munnfølelse betydelig — se <a href=\"#gjaer-pavirkning\">hvordan gjær påvirker ølet</a> under.",

    "hjelp.idx.basemaltSpesialmalt.tittel": "Basemalt kontra spesialmalt",
    "hjelp.idx.basemaltSpesialmalt.tekst": "<strong>Basemalt</strong> (f.eks. Pilsner- eller Pale Ale-malt) utgjør normalt hoveddelen av kornregningen — lys farge, høyt potensial, nøytral-til-mild smak. <strong>Spesialmalt</strong> (karamellmalt, ristet malt, hvete, havre m.fl.) brukes i mindre mengder for å justere farge, kropp og smak.",
    "hjelp.idx.basemaltSpesialmalt.hvorfor": "<strong>Hvorfor du bryr deg:</strong> En oppskrift med 100 % basemalt blir ofte for tynn og ensformig i smaken; for mye spesialmalt kan derimot dominere og gjøre ølet klumpete i profilen. De fleste vellykkede oppskrifter har basemalt som bærebjelke og spesialmalt som krydder.",

    "hjelp.idx.bitterAroma.tittel": "Bitterhumle kontra aroma-/smakshumle",
    "hjelp.idx.bitterAroma.tekst": "Noen humlesorter har høy alfasyre og passer godt til tidlig, ren bittertilsetning. Andre er valgt for sin aroma og brukes sent i koket eller som \"dry hop\" etter gjæring, der bitterheten knapt rekker å utvikle seg.",
    "hjelp.idx.bitterAroma.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Samme totale grammantall humle kan gi helt ulikt resultat avhengig av om den er fordelt tidlig (bitterhet) eller sent (aroma). Se <a href=\"#ibu\">IBU</a> for sammenhengen med koketid.",

    "hjelp.idx.gjaerPavirkning.tittel": "Hvordan gjær påvirker ølet",
    "hjelp.idx.gjaerPavirkning.tekst": "Gjærvalget påvirker ikke bare <a href=\"#utgjaering\">utgjæring</a> (og dermed FG/ABV), men også smaksstoffer gjæren selv produserer — estere (fruktighet), fenoler (krydder/klove i enkelte hvete- og belgiske stiler) og gjæringstemperaturens innvirkning på begge deler.",
    "hjelp.idx.gjaerPavirkning.hvorfor": "<strong>Hvorfor du bryr deg:</strong> To identiske oppskrifter kan smake påfallende forskjellig med to ulike gjærstammer — selv om OG, FG og IBU er tilnærmet like.",

    "hjelp.idx.egendefinerte.tittel": "Egendefinerte ingredienser",
    "hjelp.idx.egendefinerte.tekst": "Finner du ikke malten, humlen eller gjæren din i biblioteket? Klikk \"+ Egendefinert\" på raden og skriv inn navn og de tekniske grunnverdiene selv (EBC/potensial for malt, alfasyre for humle, utgjæring for gjær). Egendefinerte ingredienser fungerer fullt ut i beregningene og følger oppskriften din i lagring, eksport og import.",
    "hjelp.idx.egendefinerte.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Egendefinerte ingredienser lagres kun på <em>din</em> oppskrift — de havner aldri i det delte biblioteket andre bruker.",

    "hjelp.idx.alfaVariasjon.tittel": "Hvorfor alfa-% kan variere fra pose til pose",
    "hjelp.idx.alfaVariasjon.tekst": "Alfasyreinnholdet i humle er en naturlig plante-egenskap som varierer med vekstsesong, klima og avling — ikke et fast tall. Biblioteket viser en typisk verdi, men produsentens faktiske pose kan avvike noe.",
    "hjelp.idx.alfaVariasjon.hvorfor": "<strong>Hvorfor du bryr deg:</strong> Har du posen for hånden, juster alfa-feltet på humleraden til det som faktisk står trykt der — det gir et mer presist IBU-anslag enn bibliotekets gjennomsnitt.",

    "hjelp.idx.produsentdata.tittel": "Hvorfor produsentdata kan variere",
    "hjelp.idx.produsentdata.tekst": "EBC, potensial, alfasyre og utgjæring er alle egenskaper som i praksis varierer noe fra batch til batch hos produsenten — biblioteket i Kvernhaug Brygghus viser typiske, kuraterte verdier, ikke en garanti for akkurat din pose eller pakke.",

    "hjelp.idx.secD.tittel": "D. Bryggeprosess — kort ordliste",
    "hjelp.idx.secD.intro": "Dette er en rask ordliste. For en fullstendig gjennomgang av selve bryggedagen, steg for steg, se <a href=\"bryggedag.html\">En bryggedag — fra vann til gjæringskar</a>.",

    "hjelp.idx.defMesking.tittel": "Mesking",
    "hjelp.idx.defMesking.tekst": "Å blande knust malt med varmt vann i en bestemt temperatur og tid, slik at maltens enzymer omdanner stivelse til gjærbart sukker.",
    "hjelp.idx.defMashout.tittel": "Mashout",
    "hjelp.idx.defMashout.tekst": "En kort oppvarming til rundt 75–78 °C etter mesking, som stanser enzymaktiviteten og gjør vørteren lettere å skylle ut.",
    "hjelp.idx.defSkylling.tittel": "Skylling",
    "hjelp.idx.defSkylling.tekst": "Å skylle gjenværende sukker ut av kornresten med varmt vann, slik at mest mulig av potensialet havner i kjelen — brukes ikke i alle metoder (se <a href=\"bryggemetoder.html\">bryggemetoder</a>).",
    "hjelp.idx.defKok.tittel": "Kok",
    "hjelp.idx.defKok.tekst": "Vørteren kokes, normalt 60 minutter, for å sterilisere, drive ut uønskede stoffer og gi humlen mulighet til å avgi bitterhet og aroma.",
    "hjelp.idx.defHumletilsetning.tittel": "Humletilsetninger",
    "hjelp.idx.defHumletilsetning.tekst": "Humle tilsatt på bestemte tidspunkt i koket — tidlig for bitterhet, sent for aroma. Se <a href=\"#ibu\">IBU</a>.",
    "hjelp.idx.defKjoling.tittel": "Kjøling",
    "hjelp.idx.defKjoling.tekst": "Rask nedkjøling av vørteren etter kok, ned mot gjærens starttemperatur — jo raskere, jo mindre risiko for uønsket bakterievekst og klarere øl.",
    "hjelp.idx.defOgMaling.tittel": "OG-måling",
    "hjelp.idx.defOgMaling.tekst": "Å måle vørterens tetthet rett før gjæring, med et flytespir eller refraktometer — sammenlignes mot beregnet <a href=\"#og\">OG</a>.",
    "hjelp.idx.defGjaering.tittel": "Gjæring",
    "hjelp.idx.defGjaering.tekst": "Perioden gjæren omdanner sukker til alkohol og CO₂ — varer normalt 1–3 uker avhengig av gjærtype, styrke og temperatur.",
    "hjelp.idx.defFgMaling.tittel": "FG-måling",
    "hjelp.idx.defFgMaling.tekst": "Å måle tettheten når gjæringen har roet seg, for å bekrefte at den er ferdig og regne ut faktisk <a href=\"#abv\">ABV</a>.",
    "hjelp.idx.defKarbonering.tittel": "Karbonering",
    "hjelp.idx.defKarbonering.tekst": "Å tilføre CO₂ til det ferdige ølet — enten naturlig (sukker + gjenværende gjær på flaske/fat) eller ved tvangskarbonering med CO₂-trykk på fat.",
    "hjelp.idx.defFlasking.tittel": "Flasking/fat, på generelt nivå",
    "hjelp.idx.defFlasking.tekst": "Ølet overføres til flasker eller fat for lagring, modning og servering. Valget påvirker først og fremst hvordan karboneringen gjøres.",

    "hjelp.idx.secE.tittel": "E. Ofte stilte spørsmål",
    "hjelp.idx.faqAlleVerdier.sporsmal": "Må alle verdier være innenfor ølstilen?",
    "hjelp.idx.faqAlleVerdier.svar": "Nei. Stilgrenser er typiske områder, ikke regler. Mange gode, bevisste øl ligger utenfor på ett eller flere punkter.",
    "hjelp.idx.faqFeilVerdi.sporsmal": "Er oppskriften feil hvis én verdi er utenfor?",
    "hjelp.idx.faqFeilVerdi.svar": "Nei — stilveiledningen sier fra om det (\"litt utenfor\" eller \"tydelig utenfor\"), men det er informasjon, ikke en feilmelding. Bruk den til å vurdere om avviket er med vilje.",
    "hjelp.idx.faqIbuEndring.sporsmal": "Hvorfor endrer IBU seg når jeg endrer alfasyren?",
    "hjelp.idx.faqIbuEndring.svar": "IBU beregnes direkte fra humlens alfasyreinnhold, mengde og koketid. Høyere alfasyre gir mer bitterstoff per gram humle, og dermed høyere IBU ved samme mengde og tid. Se <a href=\"#ibu\">IBU</a> og <a href=\"#alfasyre\">alfasyre</a>.",
    "hjelp.idx.faqMorkereFarge.sporsmal": "Hvorfor blir ølet mørkere når jeg legger til denne malten?",
    "hjelp.idx.faqMorkereFarge.svar": "Fargebidraget fra malt varierer enormt — en mørk, ristet malt kan ha 10–50 ganger høyere EBC enn en lys basemalt. Selv en liten mengde av en mørk malt kan derfor gi et stort utslag på ølets totale farge. Se <a href=\"#ebc\">EBC</a>.",
    "hjelp.idx.faqByttGjaer.sporsmal": "Hva skjer hvis jeg bytter gjær?",
    "hjelp.idx.faqByttGjaer.svar": "Utgjæringen (og dermed FG og ABV) endres til den nye gjærens verdi, og smaksprofilen kan endre seg — ulike gjærstammer bidrar med ulike estere og fenoler. Se <a href=\"#gjaer-pavirkning\">hvordan gjær påvirker ølet</a>.",
    "hjelp.idx.faqUtgjaering.sporsmal": "Hva betyr utgjæring?",
    "hjelp.idx.faqUtgjaering.svar": "Se <a href=\"#utgjaering\">utgjæring</a> over — kort sagt, hvor stor andel av sukkeret gjæren klarer å omdanne til alkohol.",
    "hjelp.idx.faqEgneIngredienser.sporsmal": "Kan jeg bruke ingredienser som ikke finnes i biblioteket?",
    "hjelp.idx.faqEgneIngredienser.svar": "Ja — bruk \"+ Egendefinert\" på malt-, humle- eller gjærraden. Se <a href=\"#egendefinerte-ingredienser\">egendefinerte ingredienser</a>.",
    "hjelp.idx.faqTraffIkkeOg.sporsmal": "Hvorfor traff jeg ikke forventet OG på bryggedagen?",
    "hjelp.idx.faqTraffIkkeOg.svar": "Beregnet OG forutsetter at brygghuseffektiviteten (feltet i Grunndata) faktisk stemmer med ditt utstyr og din teknikk denne dagen. Knusingsgrad, mesketemperatur, skyllemetode og selv værforhold kan gi avvik. Juster gjerne effektivitetstallet etter noen egne brygg, slik at fremtidige anslag blir mer presise for akkurat ditt oppsett.",
    "hjelp.idx.faqOgFgForskjell.sporsmal": "Hva er forskjellen på OG og FG?",
    "hjelp.idx.faqOgFgForskjell.svar": "OG måles før gjæring (sukker til stede), FG måles etter (sukker som er igjen). Se <a href=\"#og\">OG</a> og <a href=\"#fg\">FG</a>.",
    "hjelp.idx.faqFaktiskFg.sporsmal": "Hvorfor er faktisk FG forskjellig fra beregnet FG?",
    "hjelp.idx.faqFaktiskFg.svar": "Beregnet FG bruker gjærens <em>typiske</em> utgjæringsprosent. Faktisk utgjæring påvirkes av gjæringstemperatur, gjærmengde/-helse, mesketemperatur (som styrer hvor gjærbar vørteren faktisk er) og gjærstammens variasjon fra batch til batch. Et lite avvik er normalt og ingen grunn til bekymring.",

    "hjelp.idx.avslutning": "Fant du ikke svar på det du lurte på? Håndboken utvides fortløpende.",

    "hjelp.dag.toc.1": "1. Klargjør",
    "hjelp.dag.toc.2": "2. Meskevann",
    "hjelp.dag.toc.3": "3. Tilsett malt",
    "hjelp.dag.toc.4": "4. Mesk",
    "hjelp.dag.toc.5": "5. Mashout",
    "hjelp.dag.toc.6": "6. Skyll",
    "hjelp.dag.toc.7": "7. Kok",
    "hjelp.dag.toc.8": "8. Humle",
    "hjelp.dag.toc.9": "9. Kjøl ned",
    "hjelp.dag.toc.10": "10. Mål OG",
    "hjelp.dag.toc.11": "11. Gjæringskar",
    "hjelp.dag.toc.12": "12. Tilsett gjær",
    "hjelp.dag.toc.13": "13. Gjæring",
    "hjelp.dag.toc.14": "14. Mål FG",
    "hjelp.dag.toc.15": "15. Karboner/flask",
    "hjelp.dag.intro": "En generell gjennomgang av en vanlig all-grain-bryggedag, steg for steg. Nøyaktig rekkefølge og enkelte steg varierer med <a href=\"bryggemetoder.html\">bryggemetode</a> og utstyr — dette er den typiske rekkefølgen de fleste hjemmebryggere følger.",

    "hjelp.dag.dt.hva": "Hva gjør jeg?",
    "hjelp.dag.dt.hvorfor": "Hvorfor gjør jeg det?",
    "hjelp.dag.dt.folgMed": "Hva bør jeg følge med på?",
    "hjelp.dag.dt.feil": "Vanlige nybegynnerfeil",

    "hjelp.dag.steg1.tittel": "Klargjør utstyr og ingredienser",
    "hjelp.dag.steg1.hva": "Vei opp malt og humle etter oppskriften, rengjør og sett fram kjele, meskekar, kjøler, gjæringskar og alt du trenger underveis.",
    "hjelp.dag.steg1.hvorfor": "Å lete etter utstyr eller mangle en ingrediens midt i mesking eller kok koster deg dyrebar tid akkurat når temperatur og timing betyr mest.",
    "hjelp.dag.steg1.folgMed": "At alt som skal være rent faktisk er rent — spesielt alt som møter vørteren etter kok.",
    "hjelp.dag.steg1.feil": "Å oppdage etter at mesking er i gang at man mangler en ingrediens, eller at kjøleren ikke er koblet til vann.",

    "hjelp.dag.steg2.tittel": "Varm opp meskevann",
    "hjelp.dag.steg2.hva": "Varm opp vannmengden mesken trenger til noen grader over måltemperaturen (kaldt korn og kaldt utstyr trekker ned temperaturen når vannet møter malten).",
    "hjelp.dag.steg2.hvorfor": "Mesketemperaturen styrer hvilken type sukker enzymene produserer — og dermed hvor gjærbar vørteren blir. Se <a href=\"index.html#def-mesking\">mesking</a>.",
    "hjelp.dag.steg2.folgMed": "At du treffer riktig temperatur <em>etter</em> at malten er tilsatt, ikke bare i vannet alene.",
    "hjelp.dag.steg2.feil": "Å varme vannet til akkurat måltemperaturen, og så bomme fordi kaldt korn trekker temperaturen ned et par grader.",

    "hjelp.dag.steg3.tittel": "Tilsett malt",
    "hjelp.dag.steg3.hva": "Rør inn den knuste malten i vannet, jevnt og uten klumper (\"dough-in\").",
    "hjelp.dag.steg3.hvorfor": "Klumper av tørr malt (\"dough balls\") gjør at enzymene ikke når hele kornet, og du mister utbytte.",
    "hjelp.dag.steg3.folgMed": "Rør grundig med det samme, spesielt i bunn og langs kantene.",
    "hjelp.dag.steg3.feil": "Å helle all malten oppi på én gang uten å røre samtidig.",

    "hjelp.dag.steg4.tittel": "Mesk",
    "hjelp.dag.steg4.hva": "Hold blandingen på riktig temperatur i den tiden oppskriften sier (typisk 45–90 minutter), se <a href=\"index.html#def-mesking\">mesking</a>.",
    "hjelp.dag.steg4.hvorfor": "Dette er tiden enzymene faktisk omdanner stivelse til gjærbart sukker — grunnlaget for hele batchen.",
    "hjelp.dag.steg4.folgMed": "Temperaturdrift. Isolasjon (lokk, teppe) hjelper mye på enkle meskekar.",
    "hjelp.dag.steg4.feil": "Å la temperaturen synke gradvis uten å legge merke til det.",

    "hjelp.dag.steg5.tittel": "Mashout (hvis relevant)",
    "hjelp.dag.steg5.hva": "Varm mesken raskt opp til rundt 75–78 °C, se <a href=\"index.html#def-mashout\">mashout</a>.",
    "hjelp.dag.steg5.hvorfor": "Stanser enzymaktiviteten (låser sukkerprofilen) og gjør vørteren mindre seig, som gjør skylling lettere.",
    "hjelp.dag.steg5.folgMed": "Ikke la temperaturen gå for høyt eller stå for lenge — poenget er å stanse prosessen, ikke koke mesken.",
    "hjelp.dag.steg5.feil": "Å hoppe over mashout og lure på hvorfor skyllingen går tregt.",

    "hjelp.dag.steg6.tittel": "Skyll (hvis metoden bruker det)",
    "hjelp.dag.steg6.hva": "Skyll gjenværende sukker ut av kornresten med varmt vann, se <a href=\"index.html#def-skylling\">skylling</a> og <a href=\"bryggemetoder.html\">bryggemetoder</a> for hvilke metoder som bruker dette steget.",
    "hjelp.dag.steg6.hvorfor": "Uten skylling blir mye av maltpotensialet liggende igjen i kornresten — det påvirker <a href=\"index.html#og\">OG</a> direkte.",
    "hjelp.dag.steg6.folgMed": "Skyllevannets temperatur (for varmt kan trekke ut uønskede garvestoffer/tanniner).",
    "hjelp.dag.steg6.feil": "Å skylle med kokende vann, eller å presse kornresten hardt for å \"få ut mer\" — begge deler kan gi bitre biprodukter.",

    "hjelp.dag.steg7.tittel": "Kok",
    "hjelp.dag.steg7.hva": "Kok vørteren, normalt i 60 minutter, se <a href=\"index.html#def-kok\">kok</a>.",
    "hjelp.dag.steg7.hvorfor": "Sterilisering, konsentrasjon av vørteren, og grunnlaget for humletilsetningene under.",
    "hjelp.dag.steg7.folgMed": "Kraftig kok gir lettere oversvømming (\"boil-over\") de første minuttene — stå i nærheten til koket har roet seg.",
    "hjelp.dag.steg7.feil": "Å gå fra kjelen akkurat idet koket starter og få en oversvømt komfyr.",

    "hjelp.dag.steg8.tittel": "Humletilsetninger",
    "hjelp.dag.steg8.hva": "Tilsett humle på de tidspunktene oppskriften angir, se <a href=\"index.html#def-humletilsetning\">humletilsetninger</a>.",
    "hjelp.dag.steg8.hvorfor": "Timing avgjør om humlen bidrar mest til bitterhet (tidlig) eller aroma/smak (sent), se <a href=\"index.html#ibu\">IBU</a>.",
    "hjelp.dag.steg8.folgMed": "Å faktisk time tilsetningene mot gjenværende koketid, ikke mot forløpt tid.",
    "hjelp.dag.steg8.feil": "Å blande sammen \"minutter inn i koket\" og \"minutter igjen av koket\" — de er motsatte tellemåter.",

    "hjelp.dag.steg9.tittel": "Kjøl ned",
    "hjelp.dag.steg9.hva": "Kjøl vørteren raskt ned mot gjærens starttemperatur, se <a href=\"index.html#def-kjoling\">kjøling</a>.",
    "hjelp.dag.steg9.hvorfor": "Rask kjøling reduserer tiden vørteren står i et temperaturområde der uønskede bakterier trives, og gir ofte klarere øl.",
    "hjelp.dag.steg9.folgMed": "At kjøleutstyret faktisk er rent — det møter vørteren etter kok, altså i den mest sårbare fasen.",
    "hjelp.dag.steg9.feil": "Å la vørteren stå og kjøle sakte i romtemperatur i stedet for å bruke kjøler/isbad.",

    "hjelp.dag.steg10.tittel": "Mål OG",
    "hjelp.dag.steg10.hva": "Mål tettheten med flytespir eller refraktometer, se <a href=\"index.html#def-og-maling\">OG-måling</a>.",
    "hjelp.dag.steg10.hvorfor": "Bekrefter om du traff forventet <a href=\"index.html#og\">OG</a> — viktig utgangspunkt for å vurdere hele batchen.",
    "hjelp.dag.steg10.folgMed": "At prøven er avkjølt til riktig referansetemperatur for måleinstrumentet ditt.",
    "hjelp.dag.steg10.feil": "Å måle en varm prøve og få et misvisende tall, se <a href=\"index.html#faq-traff-ikke-og\">FAQ</a>.",

    "hjelp.dag.steg11.tittel": "Overfør til gjæringskar",
    "hjelp.dag.steg11.hva": "Overfør den nedkjølte vørteren til et rent, sanitert gjæringskar.",
    "hjelp.dag.steg11.hvorfor": "Fra dette punktet er det gjæren som skal dominere miljøet — ikke andre mikroorganismer.",
    "hjelp.dag.steg11.folgMed": "Litt luftig overføring (\"splashing\") her er faktisk ønskelig — vørteren trenger oksygen for at gjæren skal starte godt.",
    "hjelp.dag.steg11.feil": "Å overføre for forsiktig og gi gjæren for lite oksygen til en god start.",

    "hjelp.dag.steg12.tittel": "Tilsett gjær",
    "hjelp.dag.steg12.hva": "Tilsett gjæren (rehydrert eller direkte, etter produsentens anvisning).",
    "hjelp.dag.steg12.hvorfor": "Jo raskere gjæren kommer i gang, jo mindre tid har uønskede mikroorganismer til å etablere seg først.",
    "hjelp.dag.steg12.folgMed": "At vørteren er innenfor gjærens anbefalte temperaturområde før du tilsetter.",
    "hjelp.dag.steg12.feil": "Å tilsette gjær i for varm vørter, som kan skade eller drepe gjæren.",

    "hjelp.dag.steg13.tittel": "Gjæring",
    "hjelp.dag.steg13.hva": "La gjæren jobbe i fred, ved stabil temperatur, se <a href=\"index.html#def-gjaering\">gjæring</a>.",
    "hjelp.dag.steg13.hvorfor": "Stabil temperatur gir en renere, mer forutsigbar smaksprofil enn svingende temperatur.",
    "hjelp.dag.steg13.folgMed": "Aktivitet i gjæringslåsen de første dagene, og at temperaturen holder seg innenfor gjærens anbefalte område.",
    "hjelp.dag.steg13.feil": "Å åpne karet ofte \"for å sjekke\" — hver åpning er en ny mulighet for kontaminering.",

    "hjelp.dag.steg14.tittel": "Mål FG",
    "hjelp.dag.steg14.hva": "Mål tettheten når aktiviteten har roet seg, se <a href=\"index.html#def-fg-maling\">FG-måling</a>.",
    "hjelp.dag.steg14.hvorfor": "Bekrefter at gjæringen faktisk er ferdig, og lar deg regne ut faktisk <a href=\"index.html#abv\">ABV</a>.",
    "hjelp.dag.steg14.folgMed": "Mål gjerne to dager på rad — er tallet stabilt, er gjæringen ferdig.",
    "hjelp.dag.steg14.feil": "Å avslutte gjæringen for tidlig fordi gjæringslåsen har roet seg, uten å bekrefte med en faktisk måling.",

    "hjelp.dag.steg15.tittel": "Karboner / flask / sett på fat",
    "hjelp.dag.steg15.hva": "Overfør ølet til flasker eller fat og karboner det, se <a href=\"index.html#def-karbonering\">karbonering</a> og <a href=\"index.html#def-flasking\">flasking/fat</a>.",
    "hjelp.dag.steg15.hvorfor": "Dette er siste steg før ølet er klart til å drikkes — og det som gir det riktig munnfølelse.",
    "hjelp.dag.steg15.folgMed": "Riktig sukkermengde ved flaskekarbonering (for mye kan gi overtrykk/eksplosjonsfare), eller riktig trykk/tid ved tvangskarbonering på fat.",
    "hjelp.dag.steg15.feil": "Å drikke ølet for tidlig — de fleste øl blir tydelig bedre etter noen ukers modning.",

    "hjelp.dag.avslutning": "Lag et konkret bryggedagsark for din egen oppskrift fra oppskriftsbyggerens <a href=\"../index.html\">Skriv ut</a>-panel.",

    "hjelp.metoder.toc.biab": "BIAB",
    "hjelp.metoder.toc.allgrain": "Vanlig all-grain",
    "hjelp.metoder.toc.altiett": "Alt-i-ett-maskin",
    "hjelp.metoder.intro": "Alle metodene under følger i grove trekk den samme <a href=\"bryggedag.html\">bryggedagen</a> — forskjellen ligger i hvordan mesking og skylling gjøres praktisk. Denne runden dekker de tre vanligste for hjemmebryggere; flere kan legges til senere uten å endre strukturen på siden.",

    "hjelp.metoder.biab.tittel": "BIAB — Brew In A Bag",
    "hjelp.metoder.biab.tekst": "Hele kornregningen mesker direkte i en stor pose i kokekjelen — ingen separat meskekar. Etter mesking løftes posen opp og dryppes av, ofte <strong>uten</strong> separat skylling.",
    "hjelp.metoder.biab.hvorfor": "<strong>Hvordan påvirkes bryggedagen:</strong> Steg 3–6 i <a href=\"bryggedag.html\">bryggedagsguiden</a> (tilsett malt → mesk → mashout → skyll) forenkles til \"mesk i posen, løft opp, drypp av\" — <a href=\"index.html#def-skylling\">skylling</a> utgår ofte helt, eller gjøres som en enkel dypp-skyll. Krever mindre utstyr enn tradisjonell all-grain, men stiller litt høyere krav til god knusing for godt utbytte siden det ikke skylles like grundig.",

    "hjelp.metoder.allgrain.tittel": "Vanlig all-grain (separat meskekar)",
    "hjelp.metoder.allgrain.tekst": "Mesking skjer i et eget meskekar (ofte med falskbunn/filter), og vørteren dreneres over i kokekjelen — deretter skylles kornresten separat med varmt vann for å hente ut mer sukker.",
    "hjelp.metoder.allgrain.hvorfor": "<strong>Hvordan påvirkes bryggedagen:</strong> Alle 15 stegene i <a href=\"bryggedag.html\">bryggedagsguiden</a> gjennomføres som beskrevet, inkludert et eget, mer grundig <a href=\"index.html#def-skylling\">skylle</a>-steg. Krever mer utstyr (separat meskekar) enn BIAB, men gir ofte litt bedre kontroll på skylleprosessen og batchstørrelse.",

    "hjelp.metoder.altiett.tittel": "Alt-i-ett bryggemaskin",
    "hjelp.metoder.altiett.tekst": "Ett elektrisk kar gjør både mesking og koking, ofte med innebygd pumpe for resirkulering og/eller skylling. Se <a href=\"utstyr-brewzilla.html\">BrewZilla</a> for et konkret eksempel.",
    "hjelp.metoder.altiett.hvorfor": "<strong>Hvordan påvirkes bryggedagen:</strong> Samme steg som vanlig all-grain, men mesking og kok skjer i samme kar — du slipper å flytte vørter mellom to kar mellom steg 4 og 7 i <a href=\"bryggedag.html\">bryggedagsguiden</a>. Innebygd temperaturstyring gjør steg 2 og 4 (varm opp / hold temperatur) enklere å treffe presist enn med manuell gassbluss.",

    "hjelp.metoder.avslutning": "Flere metoder (f.eks. dekoksjon, parti-gyle, no-sparge) kan legges til som egne kort her senere, uten å endre resten av siden.",

    "hjelp.brewzilla.toc.tekniske": "Tekniske data",
    "hjelp.brewzilla.toc.altiett": "Alt-i-ett-prinsippet",
    "hjelp.brewzilla.toc.ikkeVerifisert": "Ikke verifisert ennå",
    "hjelp.brewzilla.intro": "Dette er en <strong>referanseguide</strong> for BrewZilla — først av flere planlagte utstyrsspesifikke guider — ikke en antakelse om at du selv eier én. Kvernhaug Brygghus har én intern utstyrsprofil kalibrert mot BrewZilla 35L Gen 4.1 (se <a href=\"../index.html\">Oppskriftsbyggeren</a>), og denne siden dokumenterer akkurat hvilke tall i den profilen som stammer fra produktet selv, og hvilke som er Kvernhaugs egne beregningsvalg. Bruker du annet utstyr, gjelder de generelle bryggeforutsetningene lenger ned uansett — de er ikke BrewZilla-spesifikke. Se også <a href=\"bryggemetoder.html#alt-i-ett\">alt-i-ett bryggemaskin</a> for den generelle metoden BrewZilla er ett eksempel på.",

    "hjelp.brewzilla.kjelekapasitet.tittel": "Kjelekapasitet",
    "hjelp.brewzilla.kjelekapasitet.tekst": "BrewZilla 35L Gen 4.1 har en nominell kjelekapasitet på <strong>35 liter</strong> — dette ligger i selve produktnavnet, og er den eneste av verdiene på denne siden som faktisk er en produktegenskap og ikke noe Kvernhaug Brygghus selv har valgt eller beregnet.",

    "hjelp.brewzilla.maksPreboil.tittel": "Kvernhaugs praktiske anbefaling: maks pre-boil-volum",
    "hjelp.brewzilla.maksPreboil.tekst": "Kvernhaug Brygghus-appen varsler når beregnet pre-boil-volum overstiger omtrent <strong>30 liter</strong> — en praktisk sikkerhetsmargin under kjelens 35-literskapasitet, for å unngå overkoking ved kraftig kok. Dette er <strong>Kvernhaugs egen praktiske grense</strong>, ikke et tall hentet fra en offisiell produsentspesifikasjon.",

    "hjelp.brewzilla.standardverdier.tittel": "Kvernhaugs standardverdier for beregning (utstyrsprofil)",
    "hjelp.brewzilla.standardverdier.tekst": "Disse to tallene er standardverdiene Kvernhaug Brygghus-appen bruker i sin egen BrewZilla-utstyrsprofil for å beregne vannmengder og volum. De er <strong>appens egne beregningsforutsetninger</strong>, ikke bekreftet mot en offisiell produsentspesifikasjon:",
    "hjelp.brewzilla.tabell.egenskap": "Egenskap",
    "hjelp.brewzilla.tabell.kvernhaugStandard": "Kvernhaug-standard for beregning",
    "hjelp.brewzilla.fordampning": "Fordampning under kok",
    "hjelp.brewzilla.fordampningVerdi": "4,0 L/time",
    "hjelp.brewzilla.deadspace": "Dead space (restvolum)",
    "hjelp.brewzilla.deadspaceVerdi": "2,0 L",
    "hjelp.brewzilla.standardverdier.tekst2": "Faktisk fordampning varierer med kokestyrke, lokk/uten lokk, effekt og omgivelser — juster gjerne tallet etter egne, målte brygg på ditt eget oppsett. Dead space er heller ikke kontrollert mot produsentens egen dokumentasjon.",

    "hjelp.brewzilla.generelle.tittel": "Generelle bryggeforutsetninger (ikke BrewZilla-spesifikke)",
    "hjelp.brewzilla.generelle.tekst": "Disse to tallene ligger i samme utstyrsprofil i koden, men er egentlig <strong>generelle bryggeforutsetninger</strong> som gjelder uansett hvilket utstyr du bruker — ikke egenskaper ved BrewZilla:",
    "hjelp.brewzilla.meskeforhold": "Meskeforhold",
    "hjelp.brewzilla.meskeforholdVerdi": "3,2 L/kg",
    "hjelp.brewzilla.kornabsorpsjon": "Kornabsorpsjon",
    "hjelp.brewzilla.kornabsorpsjonVerdi": "1,0 L/kg",
    "hjelp.brewzilla.generelle.tekst2": "Meskeforhold er et prosessvalg du kan justere selv, og kornabsorpsjon er en vanlig beregningsforutsetning i hjemmebrygging generelt — ingen av delene er en fast BrewZilla-spesifikasjon.",

    "hjelp.brewzilla.kildeliste": "Kilde for alle tallene over: Kvernhaug Brygghus-appens <code>modules/equipment.py</code> (standardverdier for utstyrsprofil) og bryggedagsberegningens 30 L-varsel i <code>modules/brewday_calc.py</code>/<code>ui/brewday_panel.py</code>. Ingen av tallene er kontrollert mot en offisiell BrewZilla-produktspesifikasjon.",

    "hjelp.brewzilla.altiett.tittel": "Alt-i-ett-prinsippet",
    "hjelp.brewzilla.altiett.tekst": "BrewZilla mesker og koker i samme kar, med elektrisk temperaturstyring og innebygd pumpe/filter for resirkulering — se <a href=\"bryggemetoder.html#alt-i-ett\">alt-i-ett bryggemaskin</a> for hvordan dette forenkler bryggedagen sammenlignet med separate kar.",

    "hjelp.brewzilla.ikkeVerifisert.tittel": "Ikke verifisert ennå",
    "hjelp.brewzilla.ikkeVerifisert.intro": "følgende er bevisst IKKE fylt ut med oppdiktet informasjon, og venter på faktisk verifisering mot et konkret BrewZilla-oppsett:",
    "hjelp.brewzilla.ikkeVerifisert.li1": "Konkrete kontrollpanel-/temperaturprogrammeringssteg",
    "hjelp.brewzilla.ikkeVerifisert.li2": "Anbefalt rengjørings- og vedlikeholdsrutine",
    "hjelp.brewzilla.ikkeVerifisert.li3": "Kjente quirks eller vanlige feilkilder spesifikt for BrewZilla",
    "hjelp.brewzilla.ikkeVerifisert.li4": "Pumpe-/resirkuleringsinnstillinger for optimal mesking",
    "hjelp.brewzilla.ikkeVerifisert.li5": "Modellspesifikke forskjeller (Gen 3 / Gen 4 / Gen 4.1 m.fl.)",
    "hjelp.brewzilla.ikkeVerifisert.avslutning": "Fyll inn denne seksjonen når informasjonen er verifisert — enten mot faktisk bruk, eller mot produsentens egen dokumentasjon.",

    "hjelp.brewzilla.roadmap": "Utstyrsvalg i selve oppskriftsbyggeren (kjelevolum, fordampning m.m.) er ikke koblet til denne guiden ennå — det er en egen, større funksjon planlagt lenger fram (se Equipment Profile i roadmapen).",

    "stilmatch.kreativtBrygg": "Kreativt Brygg",
    "stilmatch.seHvaSomMangler": "Se hva som mangler",
    "stilmatch.ikkeOffisiellBadge": "🏺 ikke offisiell BJCP",
    "stilmatch.ikkeOffisiellTitle": "Kvernhaug/historisk kategori, ikke offisiell BJCP-stil",
    "stilmatch.ikkeOffisiellHeadline": "🏺 Kvernhaug/historisk kategori — ikke en offisiell BJCP-stil",
    "stilmatch.ingenAlternativer": "Ingen stiler matcher oppskriften din ennå.",

    "stilmatch.ogUnder": "For lav styrke i vørteren: OG {og} — stilområde {lo}–{hi} — {diff} under",
    "stilmatch.ogOver": "For høy styrke i vørteren: OG {og} — stilområde {lo}–{hi} — {diff} over",
    "stilmatch.fgUnder": "For lav FG: {fg} — stilområde {lo}–{hi} — {diff} under",
    "stilmatch.fgOver": "For høy FG: {fg} — stilområde {lo}–{hi} — {diff} over",
    "stilmatch.ibuUnder": "For lav bitterhet: {ibu} IBU — stilområde {lo}–{hi} IBU — {diff} IBU under",
    "stilmatch.ibuOver": "For høy bitterhet: {ibu} IBU — stilområde {lo}–{hi} IBU — {diff} IBU over",
    "stilmatch.ebcUnder": "For lys farge: {ebc} EBC — stilområde {lo}–{hi} EBC — {diff} EBC under",
    "stilmatch.ebcOver": "For mørk farge: {ebc} EBC — stilområde {lo}–{hi} EBC — {diff} EBC over",
    "stilmatch.abvUnder": "For lav alkohol: {abv} % — stilområde {lo}–{hi} % — {diff} prosentpoeng under",
    "stilmatch.abvOver": "For høy alkohol: {abv} % — stilområde {lo}–{hi} % — {diff} prosentpoeng over",
    "stilmatch.sensoriskOnsket": "Ønsket sensorisk preg av *{smak}* (har {reell}, stilen ber om {krav}+)",

    "builder.smaksprofil.ariaLabel": "Smakshjul — sensorisk profil basert på valgte ingredienser",
    "veiledning.linje": "{label} er {niva} {retning} enn typisk for {stil}. Vanlig område: {omrade}.",
    "veiledning.tips": " Tips: {tips} vil trekke oppskriften nærmere stilen.",
    "veiledning.samlet": "Oppskriften din er {adjektiver} enn typisk for {stil}. Se «Nærliggende stiler» under for et konkret alternativ som kan passe bedre.",
    "veiledning.nivaTydelig": "tydelig",
    "veiledning.nivaLitt": "litt",
    "veiledning.retningLavere": "lavere",
    "veiledning.retningHoyere": "høyere",
    "veiledning.listeOg": "og",

    "stilmatch.balanse.humledominert": "🔥 Humledominert: Bitterheten vil dominere kraftig over maltprofilen din.",
    "stilmatch.balanse.maltdominert": "🌾 Maltdominert: Lav bitterhet gjør at restsødmen fra kornene vil merkes godt.",
    "stilmatch.balanse.harmonisk": "⚖️ Harmonisk balansert: Forholdet mellom sødme og bitterhet oppleves veldig balansert.",
    "stilmatch.balanse.ekstremtTort": "🍃 Ekstremt tørt brygg: Gjæren har spist opp nesten alt sukkeret.",
    "stilmatch.problem.tungSodme": "⚠️ Fare for tung sødme: Høy FG betyr uforgjærbart sukker. Ølet kan bli klissete.",
    "stilmatch.problem.askeaktig": "☕ Askeaktig finish: Kombinasjonen av mørkt brentmalt og høy bitterhet kan skape en skarp ettersmak.",
    "stilmatch.problem.juiceSirup": "🧃 Juice/sirup-fare: Tropisk humle, høy restsødme og lav bitterhet kan gi et søtt, sirupaktig resultat.",
    "stilmatch.problem.sensoriskKonflikt": "🔥 Sensorisk konflikt: Røykmalt og sitrus-/tropisk humle slåss mot hverandre — disse smaknuansene forsterker ikke hverandre.",
    "stilmatch.problem.stilkollisjon": "🇧🇪 Stilkollisjon: Belgisk gjær og aggressive amerikanske humler kan overvelde gjærens esterprofil — vurder nøytral gjær for humledrevne stiler.",
    "stilmatch.sig.britisk": "🇬🇧 Britisk ale-signatur: Maris Otter / EKG / britisk gjær gir klassisk pub ale-karakter.",
    "stilmatch.sig.hazy": "🌀 Hazy-signatur: Tropiske humler kombinert med myk malt (havre/hvete) peker mot NEIPA / Hazy IPA.",
    "stilmatch.sig.belgisk": "🇧🇪 Belgisk signatur: Gjæren vil dominere med krydrede fenol- og esternoter — typisk pepper, nellik og frukt.",
    "stilmatch.sig.stout": "☕ Stout-signatur: Røstet bygg / sort malt gir brent espresso-karakter og sort farge.",
    "stilmatch.sig.westCoast": "🏄 West Coast-signatur: Ren, tørr gjær og bittre aromatiske humler gir klassisk West Coast IPA-profil.",
    "stilmatch.sig.lager": "🍺 Lager-signatur: Lagergjær peker mot pilsner og lagerstiler.",
  },
  en: {
    "meta.tittelFallback": "Kvernhaug Brygghus",
    "meta.builder.tittel": "Kvernhaug Brygghus — Recipe Builder",
    "meta.mineOppskrifter.tittel": "Kvernhaug Brygghus — My Recipes",
    "meta.importer.tittel": "Kvernhaug Brygghus — Import Recipe",
    "meta.utskrift.tittel": "Kvernhaug Brygghus — Print",
    "meta.hjelp.tittel": "Kvernhaug Brygghus — Help & Brewing Handbook",
    "meta.hjelpBryggedag.tittel": "A Brew Day — From Water to Fermenter — Kvernhaug Brygghus",
    "meta.hjelpBryggemetoder.tittel": "Brewing Methods — Kvernhaug Brygghus",
    "meta.hjelpBrewzilla.tittel": "Equipment: BrewZilla — Kvernhaug Brygghus",

    "brand.motto": "Brew with fire. Share with honor.",
    "brand.stedTagline": "By the Dalelva, Åsane",
    "brand.heroAlt": "Kvernhaug Brygghus — a crow by the mill house in a golden mountain valley",

    "sprak.no": "NO",
    "sprak.en": "EN",
    "sprak.ariaLabel": "Switch language",

    "chrome.apneMeny": "Open menu",
    "chrome.lukkMeny": "Close menu",
    "chrome.navKompaktAriaLabel": "Main navigation (compact)",
    "chrome.navAriaLabel": "Main navigation",

    "nav.bygger": "🍺 Recipe Builder",
    "nav.mineOppskrifter": "📂 My Recipes",
    "nav.importer": "📥 Import Recipe",
    "nav.utskrift": "🖨️ Print",
    "nav.hjelp": "📖 Help / Brewing Handbook",

    "modus.byttAriaLabel": "Switch mode",
    "modus.knappLaerlingKort": "🎓 Apprentice",
    "modus.knappMesterKort": "⚙️ Master",
    "modus.statusMester": "Mode: Brewing Master",
    "modus.statusLaerling": "Mode: Brewing Apprentice",
    "modus.forstegangTittel": "How do you want to brew?",
    "modus.forstegangIntro": "You can switch mode any time from the menu (☰).",
    "modus.velgAriaLabel": "Choose mode",
    "modus.laerlingNavn": "🎓 Brewing Apprentice",
    "modus.laerlingUndertekst": "Guided mode – learn as you brew",
    "modus.mesterNavn": "⚙️ Brewing Master",
    "modus.mesterUndertekst": "Full control – every detail available",

    "footer.enkel": "Data is stored only locally in this browser (localStorage) — nothing is sent to any server.",
    "footer.builder": "Data is stored only locally in this browser (localStorage) — nothing is sent to any server. Full version with pantry, water chemistry, and full sensory analysis: see the main app.",

    "help.ogAriaLabel": "What is OG?",
    "help.fgAriaLabel": "What is FG?",
    "help.abvAriaLabel": "What is ABV?",
    "help.ibuAriaLabel": "What is IBU?",
    "help.ebcAriaLabel": "What is EBC?",
    "help.effektivitetAriaLabel": "What is brewhouse efficiency?",
    "help.utgjaeringAriaLabel": "What is attenuation?",
    "help.alfasyreAriaLabel": "What is alpha acid?",
    "help.smakshjulAriaLabel": "What is the flavor wheel?",
    "help.stilmatchAriaLabel": "What is style matching?",
    "help.lesMer": "Read more →",
    "help.lukk": "Close",

    "builder.grunndata.tittel": "Basics",
    "builder.grunndata.olnavn": "Beer name",
    "builder.grunndata.olnavnPlaceholder": "Name of the beer",
    "builder.grunndata.brygger": "Brewer",
    "builder.grunndata.byggerPlaceholder": "Your name",
    "builder.grunndata.bryggeri": "Brewery",
    "builder.grunndata.bryggeriPlaceholder": "Name of the brewery",
    "builder.grunndata.batchvolum": "Batch volume (liters)",
    "builder.grunndata.effektivitet": "Brewhouse efficiency (%)",
    "builder.grunndata.notater": "Notes",
    "builder.grunndata.notaterPlaceholder": "E.g. planned adjustments, notes to yourself …",

    "builder.stilvalg.tittel": "What are you brewing?",
    "builder.stilvalg.olstil": "Beer style",
    "builder.stilvalg.hjelpetekst": "Optional — you can build completely freely. If you pick a style, the style match shows on the right as you build.",
    "builder.stilvalg.comboboxPlaceholder": "Search or choose a style …",
    "builder.stilvalg.comboboxAriaLabel": "Choose beer style",

    "builder.malt.tittel": "Malt",
    "builder.malt.leggTil": "+ Add malt",
    "builder.malt.prosentSum": "Percent total: {sum}%",
    "builder.malt.brukProsentfordeling": "Apply percentage split",
    "builder.malt.comboboxPlaceholder": "Search for malt …",
    "builder.malt.comboboxAriaLabel": "Choose malt",
    "builder.malt.egendefinertTitle": "Add a malt not found in the library",
    "builder.malt.fjernTitle": "Remove",
    "builder.malt.fjernAriaLabel": "Remove malt",
    "builder.malt.ebcPlaceholder": "EBC *",
    "builder.malt.potensialePlaceholder": "Potential * (1.036)",

    "builder.egendefinert.navnPlaceholder": "Name *",
    "builder.egendefinert.produsentPlaceholder": "Producer (optional)",
    "builder.egendefinert.tilbakeKnapp": "🔍 Search the library instead",
    "builder.egendefinertKnapp": "+ Custom",

    "builder.humle.tittel": "Hops",
    "builder.humle.leggTil": "+ Add hops",
    "builder.humle.comboboxPlaceholder": "Search for hops …",
    "builder.humle.comboboxAriaLabel": "Choose hops",
    "builder.humle.alfaPlaceholder": "alpha",
    "builder.humle.gramPlaceholder": "grams",
    "builder.humle.egendefinertTitle": "Add a hop not found in the library",
    "builder.humle.fjernTitle": "Remove",
    "builder.humle.fjernAriaLabel": "Remove hops",
    "builder.humle.opprinnelsePlaceholder": "Origin (optional)",
    "builder.humle.typePlaceholder": "Type (optional)",
    "builder.humle.maalIbuLabel": "Target IBU (this addition)",
    "builder.humle.beregnGramKnapp": "Calculate grams",

    "builder.gjaer.tittel": "Yeast",
    "builder.gjaer.label": "Yeast",
    "builder.gjaer.egendefinertKnapp": "+ Custom yeast",
    "builder.gjaer.utgjaering": "Expected attenuation (%)",
    "builder.gjaer.navnPlaceholder": "Name (optional)",
    "builder.gjaer.gjaertypePlaceholder": "Yeast type (optional)",
    "builder.gjaer.comboboxPlaceholder": "Search for yeast …",
    "builder.gjaer.comboboxAriaLabel": "Choose yeast",
    "builder.gjaer.egendefinertNavnDefault": "Custom yeast",

    "builder.handling.tittel": "Save & export",
    "builder.handling.nyOppskrift": "🆕 New recipe",
    "builder.handling.lagreOppskrift": "💾 Save recipe",
    "builder.handling.lagreFil": "📄 Save recipe file (.kbhrecipe)",
    "builder.handling.apneFil": "📂 Open recipe file",
    "builder.handling.hjelpetekst": "Saved recipes live locally in this browser. To back up or move a recipe to another device, save it as a .kbhrecipe file and open it again here or under «📥 Import Recipe».",
    "builder.handling.avansertSummary": "Advanced: raw JSON",
    "builder.handling.eksporterKnapp": "⬇️ Export raw JSON",
    "builder.handling.avansertHjelpetekst": "For debugging/further processing only — use «Save recipe file» above for regular saving and backup.",

    "builder.skaler.naavaerende": "Current batch: {vol} L",
    "builder.skaler.maalLabel": "Scale to (L)",
    "builder.skaler.knapp": "📐 Scale recipe",
    "builder.skaler.hjelpetekst": "Malt (kg) and hops (grams) scale proportionally to the new volume. Beer name, brewer, brewery, notes, chosen style, yeast choice, hop time, and alpha acid overrides are not changed.",
    "builder.skaler.confirm": "Scale the recipe from {fra} L to {til} L?\n\nAll malt (kg) and hop amounts (grams) change proportionally (factor {faktor}). Name, style, notes, and yeast choice are not changed.",
    "builder.skaler.statusUgyldig": "Invalid volume -- scaling cancelled.",
    "builder.skaler.statusUendret": "Target volume is already equal to the current volume.",
    "builder.skaler.statusFerdig": "Scaled from {fra} L to {til} L.",

    "identitet.utenNavn": "Untitled",

    "builder.smaksprofil.tittel": "Flavor Profile",
    "builder.stilanalyse.tittel": "Style Analysis",
    "builder.stilanalyse.tomTittel": "🍺 No style match yet",
    "builder.stilanalyse.tomTekst": "Add malt and/or hops to see which styles the recipe is approaching.",
    "builder.stilanalyse.headlineLabel": "Numerically closest style",
    "builder.stilanalyse.nearbyTittel": "Nearby styles",
    "builder.stilanalyse.valgtTittel": "Selected style",

    "stilanalyse.innenforAlle": "✅ Within all of the style's numeric ranges.",
    "stilanalyse.innenforOmrade": "✅ The recipe is within the typical range for {stil}.",
    "stilanalyse.ingenTreff": "No style in the library matches closely enough yet — adjust the ingredients or see nearby styles below.",
    "stilanalyse.leggTilForMatch": "Add malt and/or hops to see how the recipe matches {stil}.",
    "stilanalyse.buGu": "Bitterness index (BU:GU): {verdi}",

    "malt.prosent.tomFelt": "Enter a percentage in at least one malt row before applying the split.",
    "malt.prosent.ugyldigTall": "The percentage must be a valid number between 0 and 100 in every edited row.",
    "malt.prosent.justerTil100": "The selected percentages total {sum}%. Adjust the total to 100%, or leave at least one malt untouched so the rest can be calculated automatically.",
    "malt.prosent.overstiger100": "The selected percentages total {sum}%, which is more than 100%. Adjust one of the edited rows.",

    "oppskrift.lagretStatus": "Saved \"{navn}\" in the browser. See \"📂 My Recipes\" to open it again later.",
    "oppskrift.lagreFilStatus": "Downloaded \"{filnavn}.kbhrecipe\". Use this file as a backup or to move the recipe to another device.",
    "oppskrift.nyConfirm": "Start a new recipe? Changes to the active recipe that haven't been saved or exported will be lost.",
    "oppskrift.nyStatus": "New, empty recipe.",
    "oppskrift.apneConfirm": "Open this recipe? The active recipe will be replaced.",
    "oppskrift.apnetStatus": "The recipe has been opened.",
    "oppskrift.lesefeil": "Could not read the file.",

    "kbhrecipe.ugyldigJson": "This file could not be read as a recipe file (invalid JSON).",
    "kbhrecipe.ikkeGyldigOppskrift": "This file doesn't look like a valid Kvernhaug recipe.",
    "kbhrecipe.manglerVersjon": "This recipe file is missing version information and can't be safely opened here.",
    "kbhrecipe.nyereVersjon": "This recipe file was made with a newer version of Kvernhaug Brygghus and can't be safely opened here yet.",
    "kbhrecipe.ustottetVersjon": "This recipe file uses a version of the recipe format that isn't supported here.",
    "kbhrecipe.manglerOppskrift": "This recipe file is missing the actual recipe.",

    "meta.mineOppskrifter.sidetittel": "📂 My Recipes",
    "mineOppskrifter.tittel": "My saved recipes",
    "mineOppskrifter.hjelpetekst": "Stored only in this browser (localStorage) — nothing is sent to any server.",
    "mineOppskrifter.ingenOppskrifter": "No saved recipes yet. Build a recipe and press \"Save recipe\" in the Recipe Builder.",
    "mineOppskrifter.importerTittel": "Importing a recipe?",
    "mineOppskrifter.importerHjelpetekst": "File and text import have moved to their own page in the menu:",
    "mineOppskrifter.apneKnapp": "Open in builder",
    "mineOppskrifter.slettTitle": "Delete",
    "mineOppskrifter.slettAriaLabel": "Delete {navn}",
    "mineOppskrifter.slettConfirm": "Delete \"{navn}\"? This can't be undone.",
    "mineOppskrifter.lagretDato": "Saved {dato}",

    "meta.importer.sidetittel": "📥 Import Recipe",
    "importer.tittel": "Import Recipe",
    "importer.intro": "Build the recipe from a file or from pasted text — either way sends you on to the Recipe Builder with the fields pre-filled.",
    "importer.velgMetodeAriaLabel": "Choose import method",
    "importer.modusFil": "📄 Open file",
    "importer.modusTekst": "✏️ Paste text",
    "importer.filTittel": "Open recipe file",
    "importer.filHjelpetekst": "Have a .kbhrecipe file — from this page, from the Recipe Builder's \"Save recipe file\", or from somewhere else? Choose it here and it opens directly in the builder. Older, raw recipe JSON is still supported.",
    "importer.filVelgKnapp": "⬆️ Choose a .kbhrecipe file",
    "importer.tekstTittel": "Paste recipe text",
    "importer.formatKgLabel": "Kg format:",
    "importer.formatPctLabel": "Percentage format (requires total malt amount):",
    "importer.formatHumleLabel": "Hops (must have a boil time):",
    "importer.formatGjaerLabel": "Yeast:",
    "importer.tekstPlaceholder": "Paste the recipe here …",
    "importer.analyserKnapp": "🔍 Analyze",
    "importer.matchetTittel": "Matched",
    "importer.ikkeGjenkjentTittel": "Not recognized",
    "importer.bekreftKnapp": "✅ Add to recipe builder",

    "import.tellinger": "Parsed: {malt} malt · {humle} hops · {gjaer} yeast line(s)",
    "import.ingenGjenkjent": "No ingredients were recognized.",
    "import.treffMalt": "Malt: {navn} → <code>{display}</code> ({mengde} kg)",
    "import.treffHumle": "Hops: {navn} → <code>{display}</code> ({gram} g, {tid} min)",
    "import.treffGjaer": "Yeast: {navn} → <code>{display}</code>",
    "import.kategoriMalt": "Malt",
    "import.kategoriHumle": "Hops",
    "import.kategoriGjaer": "Yeast",
    "import.advarselProsentSum": "The malt percentages total {sum}% (expected ~100%).",
    "import.advarselManglerTotal": "Missing 'Total malt: X kg' — provide the total malt amount to convert percentages to kg.",
    "oppskrift.importertNavnDefault": "Imported recipe",

    "meta.utskrift.sidetittel": "🖨️ Print",
    "utskrift.tomTittel": "Print",
    "utskrift.tomTekst1": "You don't have a recipe to print yet.",
    "utskrift.tomTekst2": "Go to the <a href=\"index.html\">Recipe Builder</a> and make one, or open a saved recipe under <a href=\"mine-oppskrifter.html\">My Recipes</a>.",
    "utskrift.velgOppskriftTittel": "Choose recipe",
    "utskrift.oppskriftLabel": "Recipe",
    "utskrift.skrivUtTittel": "Print",
    "utskrift.skrivUtHjelpetekst": "Each sheet is its own print-friendly page — not just a printout of this screen.",
    "utskrift.knappOppskriftsark": "🖨️ Recipe Sheet",
    "utskrift.knappHandleliste": "🖨️ Shopping List",
    "utskrift.knappBryggedagsark": "🖨️ Brew Day Sheet",
    "utskrift.knappBryggelogg": "🖨️ Brew Log",
    "utskrift.velgerAktivt": "{navn} (active in builder, not saved)",
    "utskrift.infoTall": "OG {og} · FG {fg} · ABV {abv} · IBU {ibu} · EBC {ebc}",

    "print.footer": "Made with Kvernhaug Brygghus Recipe Builder",
    "print.oppskriftsark.undertittel": "Recipe Sheet",
    "print.handleliste.undertittel": "Shopping List",
    "print.bryggedagsark.undertittel": "Brew Day Sheet",
    "print.bryggelogg.undertittel": "Brew Log",
    "print.olstilLabel": "Beer style:",
    "print.meta": "{vol} L · {eff}% brewhouse efficiency",
    "print.maltTittel": "Malt",
    "print.humleTittel": "Hops",
    "print.gjaerTittel": "Yeast",
    "print.notaterTittel": "Notes",
    "print.navnKol": "Name",
    "print.produsentKol": "Producer",
    "print.mengdeKol": "Amount",
    "print.alfasyreKol": "Alpha acid",
    "print.koketidKol": "Boil time",
    "print.oppskriftsark.ingenMalt": "No malt added.",
    "print.oppskriftsark.ingenHumle": "No hops added.",
    "print.ingenMalt": "No malt.",
    "print.ingenHumle": "No hops.",
    "print.ingenGjaerValgt": "No yeast selected.",
    "print.gjaerNavnFallback": "Yeast",
    "print.utgjaeringSuffix": " — expected attenuation {pct}%",
    "print.bryggedato": "Brew date:",
    "print.batch": "Batch: {vol} L",
    "print.ingrediensTittel": "Ingredients",
    "print.humletilsetningKol": "Hop addition",
    "print.tidspunktKol": "Timing",
    "print.planlagteTallTittel": "Planned numbers",
    "print.planlagtOg": "Planned OG",
    "print.faktiskOg": "Actual OG",
    "print.faktiskFg": "Actual FG",
    "print.planlagtVolum": "Planned volume",
    "print.faktiskVolum": "Actual volume",
    "print.sjekklisteTittel": "Checklist",
    "print.sjekkliste.0": "Prepare equipment and ingredients",
    "print.sjekkliste.1": "Heat mash water",
    "print.sjekkliste.2": "Add malt / mash in",
    "print.sjekkliste.3": "Mash out (if relevant)",
    "print.sjekkliste.4": "Sparge (if the method uses it)",
    "print.sjekkliste.5": "Boil",
    "print.sjekkliste.6": "Hop additions as planned above",
    "print.sjekkliste.7": "Chill",
    "print.sjekkliste.8": "Measure OG",
    "print.sjekkliste.9": "Transfer to fermenter and pitch yeast",
    "print.notaterFraBryggedagenTittel": "Notes from brew day",
    "print.bryggedato2": "Brew date",
    "print.batchKol": "Batch",
    "print.faktiskAbv": "Actual ABV",
    "print.gjaerLabel": "Yeast",
    "print.gjaeringstemp": "Fermentation temp.",
    "print.karbonering": "Carbonation",
    "print.viktigeDatoerTittel": "Important dates",
    "print.overfortTilGjaering": "Transferred to fermenter",
    "print.ferdigGjaeret": "Fermentation complete",
    "print.flasketFatet": "Bottled / kegged",
    "print.klarTilSmaking": "Ready to taste",
    "print.bryggedagsnotaterTittel": "Brew day notes",
    "print.gjaeringsnotaterTittel": "Fermentation notes",
    "print.smaksnotaterTittel": "Tasting notes",
    "print.hvaFungerteBra": "What worked well?",
    "print.hvaBorEndres": "What should change next time?",

    "hjelp.sidetittel": "📖 Help & Brewing Handbook",
    "hjelp.sidenavFaq": "📖 Help & FAQ",
    "hjelp.sidenavBryggedag": "🗓️ A Brew Day",
    "hjelp.sidenavBryggemetoder": "⚗️ Brewing Methods",
    "hjelp.sidenavUtstyr": "🛠️ Equipment: BrewZilla",
    "hjelp.innholdAriaLabel": "Contents of this page",

    "hjelp.idx.toc.a": "A. Getting Started",
    "hjelp.idx.toc.b": "B. Understanding the Recipe",
    "hjelp.idx.toc.c": "C. Ingredients",
    "hjelp.idx.toc.d": "D. Brewing Process",
    "hjelp.idx.toc.e": "E. Questions &amp; Answers",
    "hjelp.idx.intro": "A reference for anyone building a recipe in Kvernhaug Brygghus. Everything here is written to answer two questions: what does this mean, and why should I care? Use the contents menu to jump around, or scroll down like an ordinary handbook.",

    "hjelp.idx.secA.tittel": "A. Getting Started",
    "hjelp.idx.forsteOppskrift.tittel": "Build Your First Beer Recipe",
    "hjelp.idx.forsteOppskrift.tekst": "Start in <strong>Basics</strong> with a beer name and batch volume (how many litres you're brewing). Then add at least one malt under <strong>Malt</strong> — the search field filters as you type. Do the same under <strong>Hops</strong> and pick a <strong>Yeast</strong>. The numbers in <strong>Results</strong> (OG/FG/ABV/IBU/EBC) and the flavor wheel update automatically with every choice — there's no \"calculate\" button to press.",
    "hjelp.idx.forsteOppskrift.hvorfor": "<strong>Why this matters:</strong> There's no \"wrong\" starting point. Experiment, watch how the numbers change, and adjust until they match the style you're going for — or just whatever sounds good to you.",

    "hjelp.idx.laerlingMester.tittel": "Brewing Apprentice and Brewing Master",
    "hjelp.idx.laerlingMester.tekst": "The two buttons at the top switch between two views of the <em>same</em> recipe. <strong>Brewing Apprentice</strong> hides technical detail and shows more guidance — good when you're new. <strong>Brewing Master</strong> shows everything: BU:GU, nearby styles, full style analysis. No data disappears when you switch — only how much shows on screen changes.",
    "hjelp.idx.laerlingMester.hvorfor": "<strong>Why this matters:</strong> You can switch back and forth as often as you like, at any point in the process. Many people start in Brewing Apprentice and move to Brewing Master as the terms become familiar.",

    "hjelp.idx.lagreOppskrift.tittel": "Save a Recipe",
    "hjelp.idx.lagreOppskrift.tekst": "\"💾 Save recipe\" saves the recipe <strong>in this browser</strong> (localStorage) under the name you gave it. It shows up under \"My saved recipes\" further down, and you can reload it any time — even after closing the tab.",
    "hjelp.idx.lagreOppskrift.hvorfor": "<strong>Why this matters:</strong> Nothing is sent to any server, so a recipe saved this way only exists on this device. To back it up or move it to another computer or phone, use \"📄 Save recipe file (.kbhrecipe)\" instead — that's the normal, portable way to back up and share a recipe. Raw JSON export is still available under \"Advanced\" for legacy files or further processing, but .kbhrecipe is the recommended format for everyday use.",

    "hjelp.idx.aapneImportere.tittel": "Open or Import a Recipe",
    "hjelp.idx.aapneImportere.tekst": "Click \"Open in builder\" on a saved recipe under \"My recipes\" to load it instantly. Have a .kbhrecipe file (or an older, raw recipe JSON)? Use \"📂 Open recipe file\" in the builder, or the \"Open file\" option on the \"📥 Import Recipe\" page — both open it directly, no re-typing needed. Have a recipe as plain pasted text instead (e.g. \"5 kg Maris Otter\", \"20 g Magnum 60 min\")? Use \"📥 Import Recipe\" and its \"Paste text\" mode — custom ingredients included.",

    "hjelp.idx.skriveUt.tittel": "Printing",
    "hjelp.idx.skriveUt.tekst": "Under \"Print\" you'll find four separate sheets: <strong>Recipe sheet</strong> (for sharing the recipe with others), <strong>Shopping list</strong> (ingredients only), <strong>Brew day sheet</strong> (a worksheet for the brew day itself), and <strong>Brew log</strong> (a blank form for actual results, to fill in by hand). Each sheet is its own clean page — not just a screenshot printout.",

    "hjelp.idx.secB.tittel": "B. Understanding the Recipe",
    "hjelp.idx.og.tittel": "OG — Original Gravity",
    "hjelp.idx.og.tekst": "OG measures the amount of sugar dissolved in the wort <em>before</em> fermentation starts — typically a number like 1.050. The higher the OG, the more sugar the yeast has to work with.",
    "hjelp.idx.og.hvorfor": "<strong>Why this matters:</strong> OG is the starting point for both alcohol strength and body. Increase the malt amount (or your brewhouse efficiency) and OG rises. Reduce malt or add more water and it drops. A light, easy-drinking beer typically sits around 1.035–1.045; a strong beer can go above 1.070.",

    "hjelp.idx.fg.tittel": "FG — Final Gravity",
    "hjelp.idx.fg.tekst": "FG measures the sugar <em>left over</em> once fermentation is finished. The difference between OG and FG tells you how much sugar was actually converted to alcohol.",
    "hjelp.idx.fg.hvorfor": "<strong>Why this matters:</strong> A low FG gives a drier beer, a high FG gives more residual sweetness and mouthfeel. In this recipe builder, FG is driven by the yeast's expected <a href=\"#utgjaering\">attenuation</a> — pick a yeast with higher attenuation and FG drops. The actual FG you measure after brewing can differ slightly from the calculated number — see the <a href=\"#faq-faktisk-fg\">FAQ</a>.",

    "hjelp.idx.abv.tittel": "ABV — Alcohol Strength",
    "hjelp.idx.abv.tekst": "ABV (Alcohol By Volume) is the alcohol percentage in the finished beer, calculated from the difference between OG and FG.",
    "hjelp.idx.abv.hvorfor": "<strong>Why this matters:</strong> To get a stronger beer, either OG needs to go up (more malt) or FG needs to come down (a higher-attenuation yeast) — or both. A session beer usually sits under 4.5%, a typical pale ale around 5–6%, an imperial stout can pass 9–10%.",

    "hjelp.idx.ibu.tittel": "IBU — Bitterness",
    "hjelp.idx.ibu.tekst": "IBU (International Bitterness Units) measures hop bitterness. Higher numbers mean a more bitter beer. Most beer styles fall somewhere between 10 and 70 IBU.",
    "hjelp.idx.ibu.hvorfor": "<strong>Why this matters:</strong> IBU is driven by hop amount, alpha acid, and boil time — see <a href=\"#alfasyre\">alpha acid</a>. Hops added early in the boil (60 min) give the most bitterness; hops added late (0–10 min) give more aroma and flavor but little bitterness. Double the amount of an early hop addition and IBU rises sharply; move that same hop to the end of the boil and IBU drops sharply even though the amount is the same.",

    "hjelp.idx.ebc.tittel": "EBC — Color",
    "hjelp.idx.ebc.tekst": "EBC measures the beer's color, from pale gold (low numbers, under 10) through copper and amber to almost black (over 80).",
    "hjelp.idx.ebc.hvorfor": "<strong>Why this matters:</strong> Color comes almost entirely from the malt — darker malt (like roasted malt or crystal malt) gives a far bigger EBC increase per kilo than pale base malt. Add just 200 g of roasted malt to an otherwise pale recipe and EBC can jump noticeably even though the amount is small.",

    "hjelp.idx.buGu.tittel": "BU:GU — Bitterness vs. Body",
    "hjelp.idx.buGu.tekst": "BU:GU (shown in Brewing Master) is the ratio of IBU to OG (scaled), and says something about the balance between bitterness and malt body. A low number means a malt-forward beer, a high number means a hop-forward beer.",
    "hjelp.idx.buGu.hvorfor": "<strong>Why this matters:</strong> Two beers can have the same IBU but taste completely different depending on how much malt (OG) stands up to the bitterness. BU:GU is a quick check on whether the balance matches what you're aiming for.",

    "hjelp.idx.utgjaering.tittel": "Attenuation",
    "hjelp.idx.utgjaering.tekst": "Attenuation is how much of the available sugar the yeast manages to convert to alcohol, given as a percentage. A yeast with 75% attenuation \"eats\" 75% of the available sugar.",
    "hjelp.idx.utgjaering.hvorfor": "<strong>Why this matters:</strong> Higher attenuation gives a lower <a href=\"#fg\">FG</a> and therefore a drier beer with slightly higher <a href=\"#abv\">ABV</a>, at the same OG. Pick a library yeast and attenuation fills in automatically — you can override it manually if you're using a custom yeast or know something specific about your particular strain.",

    "hjelp.idx.alfasyre.tittel": "Alpha Acid",
    "hjelp.idx.alfasyre.tekst": "Alpha acid (α-acid) is the percentage of bittering compounds in the hop. Higher alpha acid means more bitterness per gram of hops.",
    "hjelp.idx.alfasyre.hvorfor": "<strong>Why this matters:</strong> The alpha acid content of a given hop variety normally varies somewhat from season to season and pack to pack — what's actually printed on <em>your</em> pack can differ from the library's typical value. Feel free to adjust the alpha field to match what's actually printed on your pack for a more precise IBU estimate; see the <a href=\"#faq-produsentdata\">FAQ</a>.",

    "hjelp.idx.effektivitet.tittel": "Brewhouse Efficiency",
    "hjelp.idx.effektivitet.tekst": "Efficiency is how much of the malt's sugar potential you actually get into the wort with your own equipment and technique — 75% is a common starting point, but it varies from brewery to brewery.",
    "hjelp.idx.effektivitet.hvorfor": "<strong>Why this matters:</strong> Efficiency feeds directly into the <a href=\"#og\">OG</a> calculation. Brewing Apprentice hides the field and uses 75% as an estimate, so you can get started without needing to know this first. In Brewing Master you can adjust it based on your own measured brews — see also the <a href=\"#faq-traff-ikke-og\">FAQ</a>.",

    "hjelp.idx.maltpotensial.tittel": "Malt Potential",
    "hjelp.idx.maltpotensial.tekst": "Malt potential is how much sugar a given malt can contribute per kilo — the basis for the OG calculation. Different malt types have different potential; a pure base malt gives more than a specialty malt with lower fermentable content.",
    "hjelp.idx.maltpotensial.hvorfor": "<strong>Why this matters:</strong> If you enter a custom malt, you need to supply an estimated potential yourself (the manufacturer's data sheet, if you have it, is the best source). Too high a number overestimates OG, too low underestimates it.",

    "hjelp.idx.smakshjulet.tittel": "The Flavor Wheel",
    "hjelp.idx.smakshjulet.tekst": "The flavor wheel is a radar chart with 18 flavor axes, based on your malt, hop, and yeast choices. The further an axis stretches toward the edge, the more prominent that flavor is expected to be.",
    "hjelp.idx.smakshjulet.hvorfor": "<strong>Why this matters:</strong> It's a quick, visual check on whether the recipe is actually pointing in the direction you intended — for example, whether a \"citrus/tropical\" axis really stands out when you've used plenty of Citra and Mosaic. The chart is an expectation based on the ingredient data, not a guarantee of how the actual beer will taste.",

    "hjelp.idx.stilmatching.tittel": "Style Matching",
    "hjelp.idx.stilmatching.tekst": "Style matching compares the recipe's numbers (OG/FG/ABV/IBU/EBC) and flavor profile against known beer styles in Kvernhaug Brygghus's own library, and shows which style the recipe resembles most — plus a few nearby alternatives.",
    "hjelp.idx.stilmatching.hvorfor": "<strong>Why this matters:</strong> It's a guideline, not a verdict. See <a href=\"#stilgrenser\">style ranges</a> and the <a href=\"#faq-feil-verdi\">FAQ</a> for how to interpret it. The library covers 26 styles — this is <em>not</em> the entire official BJCP 2021 style guide (which has around 100 sub-styles).",

    "hjelp.idx.stilgrenser.tittel": "Style Ranges",
    "hjelp.idx.stilgrenser.tekst": "Each style in the library has typical ranges for OG/FG/IBU/EBC/ABV, drawn from well-known style descriptions. When your recipe deviates from a selected style's typical range, the style guidance explains this in calm language — \"slightly outside\" or \"clearly outside\" — never as an error message.",
    "hjelp.idx.stilgrenser.hvorfor": "<strong>Why this matters:</strong> Style ranges describe what's <em>typical</em> for a style, not a rule you must follow. Many good beers sit deliberately outside a style's typical range.",

    "hjelp.idx.secC.tittel": "C. Ingredients",
    "hjelp.idx.omMalt.tittel": "Malt",
    "hjelp.idx.omMalt.tekst": "Malt is the grain that gives the wort sugar (for alcohol), color, and much of the base flavor. It's the source of nearly all the OG and EBC in the recipe.",

    "hjelp.idx.omHumle.tittel": "Hops",
    "hjelp.idx.omHumle.tekst": "Hops provide bitterness (early in the boil) and aroma/flavor (late in the boil or after boiling). The same hop variety can therefore contribute completely differently depending on <em>when</em> it's added.",

    "hjelp.idx.omGjaer.tittel": "Yeast",
    "hjelp.idx.omGjaer.tekst": "Yeast converts sugar into alcohol and CO₂, but also significantly affects flavor and mouthfeel — see <a href=\"#gjaer-pavirkning\">how yeast affects the beer</a> below.",

    "hjelp.idx.basemaltSpesialmalt.tittel": "Base Malt vs. Specialty Malt",
    "hjelp.idx.basemaltSpesialmalt.tekst": "<strong>Base malt</strong> (e.g. Pilsner or Pale Ale malt) normally makes up the bulk of the grain bill — pale color, high potential, neutral-to-mild flavor. <strong>Specialty malt</strong> (crystal malt, roasted malt, wheat, oats, and others) is used in smaller amounts to adjust color, body, and flavor.",
    "hjelp.idx.basemaltSpesialmalt.hvorfor": "<strong>Why this matters:</strong> A recipe with 100% base malt often ends up thin and one-dimensional in flavor; too much specialty malt, on the other hand, can dominate and make the beer's profile muddled. Most successful recipes have base malt as the backbone and specialty malt as seasoning.",

    "hjelp.idx.bitterAroma.tittel": "Bittering Hops vs. Aroma/Flavor Hops",
    "hjelp.idx.bitterAroma.tekst": "Some hop varieties have high alpha acid and suit a clean, early bittering addition. Others are chosen for their aroma and are used late in the boil or as a \"dry hop\" after fermentation, where bitterness barely has time to develop.",
    "hjelp.idx.bitterAroma.hvorfor": "<strong>Why this matters:</strong> The same total gram count of hops can give a completely different result depending on whether it's split early (bitterness) or late (aroma). See <a href=\"#ibu\">IBU</a> for the connection to boil time.",

    "hjelp.idx.gjaerPavirkning.tittel": "How Yeast Affects the Beer",
    "hjelp.idx.gjaerPavirkning.tekst": "Your yeast choice affects not just <a href=\"#utgjaering\">attenuation</a> (and therefore FG/ABV), but also flavor compounds the yeast itself produces — esters (fruitiness), phenols (spice/clove in certain wheat and Belgian styles), and how fermentation temperature influences both.",
    "hjelp.idx.gjaerPavirkning.hvorfor": "<strong>Why this matters:</strong> Two identical recipes can taste strikingly different with two different yeast strains — even when OG, FG, and IBU are nearly the same.",

    "hjelp.idx.egendefinerte.tittel": "Custom Ingredients",
    "hjelp.idx.egendefinerte.tekst": "Can't find your malt, hop, or yeast in the library? Click \"+ Custom\" on the row and enter the name and basic technical values yourself (EBC/potential for malt, alpha acid for hops, attenuation for yeast). Custom ingredients work fully in the calculations and travel with your recipe through saving, export, and import.",
    "hjelp.idx.egendefinerte.hvorfor": "<strong>Why this matters:</strong> Custom ingredients are saved only on <em>your</em> recipe — they never end up in the shared library other users see.",

    "hjelp.idx.alfaVariasjon.tittel": "Why Alpha % Can Vary from Pack to Pack",
    "hjelp.idx.alfaVariasjon.tekst": "The alpha acid content of hops is a natural plant trait that varies with growing season, climate, and harvest — not a fixed number. The library shows a typical value, but the actual pack from the manufacturer can differ somewhat.",
    "hjelp.idx.alfaVariasjon.hvorfor": "<strong>Why this matters:</strong> If you have the pack in hand, adjust the alpha field on the hop row to match what's actually printed on it — it gives a more precise IBU estimate than the library average.",

    "hjelp.idx.produsentdata.tittel": "Why Manufacturer Data Can Vary",
    "hjelp.idx.produsentdata.tekst": "EBC, potential, alpha acid, and attenuation are all properties that in practice vary somewhat from batch to batch at the manufacturer — the Kvernhaug Brygghus library shows typical, curated values, not a guarantee for your specific pack or package.",

    "hjelp.idx.secD.tittel": "D. Brewing Process — Quick Glossary",
    "hjelp.idx.secD.intro": "This is a quick glossary. For a full step-by-step walkthrough of the brew day itself, see <a href=\"bryggedag.html\">A Brew Day — From Water to Fermenter</a>.",

    "hjelp.idx.defMesking.tittel": "Mashing",
    "hjelp.idx.defMesking.tekst": "Mixing crushed malt with hot water at a specific temperature and time, so the malt's enzymes convert starch into fermentable sugar.",
    "hjelp.idx.defMashout.tittel": "Mash-out",
    "hjelp.idx.defMashout.tekst": "A brief heat-up to around 75–78°C after mashing, which stops enzyme activity and makes the wort easier to sparge.",
    "hjelp.idx.defSkylling.tittel": "Sparging",
    "hjelp.idx.defSkylling.tekst": "Rinsing remaining sugar out of the grain bed with hot water, so as much of the potential as possible ends up in the kettle — not used in every method (see <a href=\"bryggemetoder.html\">brewing methods</a>).",
    "hjelp.idx.defKok.tittel": "Boil",
    "hjelp.idx.defKok.tekst": "The wort is boiled, normally for 60 minutes, to sterilize, drive off unwanted compounds, and let the hops release bitterness and aroma.",
    "hjelp.idx.defHumletilsetning.tittel": "Hop Additions",
    "hjelp.idx.defHumletilsetning.tekst": "Hops added at specific points in the boil — early for bitterness, late for aroma. See <a href=\"#ibu\">IBU</a>.",
    "hjelp.idx.defKjoling.tittel": "Chilling",
    "hjelp.idx.defKjoling.tekst": "Rapidly cooling the wort after the boil, down toward the yeast's starting temperature — the faster, the lower the risk of unwanted bacterial growth and the clearer the beer.",
    "hjelp.idx.defOgMaling.tittel": "OG Reading",
    "hjelp.idx.defOgMaling.tekst": "Measuring the wort's gravity right before fermentation, with a hydrometer or refractometer — compared against the calculated <a href=\"#og\">OG</a>.",
    "hjelp.idx.defGjaering.tittel": "Fermentation",
    "hjelp.idx.defGjaering.tekst": "The period during which yeast converts sugar into alcohol and CO₂ — normally lasts 1–3 weeks depending on yeast type, strength, and temperature.",
    "hjelp.idx.defFgMaling.tittel": "FG Reading",
    "hjelp.idx.defFgMaling.tekst": "Measuring the gravity once fermentation has settled down, to confirm it's finished and calculate the actual <a href=\"#abv\">ABV</a>.",
    "hjelp.idx.defKarbonering.tittel": "Carbonation",
    "hjelp.idx.defKarbonering.tekst": "Adding CO₂ to the finished beer — either naturally (sugar + residual yeast in bottle/keg) or by force-carbonating with CO₂ pressure in a keg.",
    "hjelp.idx.defFlasking.tittel": "Bottling/Kegging, in General",
    "hjelp.idx.defFlasking.tekst": "The beer is transferred to bottles or a keg for storage, conditioning, and serving. The choice mainly affects how carbonation is handled.",

    "hjelp.idx.secE.tittel": "E. Frequently Asked Questions",
    "hjelp.idx.faqAlleVerdier.sporsmal": "Do all values need to fall within the beer style?",
    "hjelp.idx.faqAlleVerdier.svar": "No. Style ranges are typical ranges, not rules. Many good, deliberate beers fall outside on one or more points.",
    "hjelp.idx.faqFeilVerdi.sporsmal": "Is the recipe wrong if one value is outside range?",
    "hjelp.idx.faqFeilVerdi.svar": "No — the style guidance flags it (\"slightly outside\" or \"clearly outside\"), but that's information, not an error message. Use it to judge whether the deviation is intentional.",
    "hjelp.idx.faqIbuEndring.sporsmal": "Why does IBU change when I change the alpha acid?",
    "hjelp.idx.faqIbuEndring.svar": "IBU is calculated directly from the hop's alpha acid content, amount, and boil time. Higher alpha acid means more bittering compound per gram of hops, and therefore higher IBU at the same amount and time. See <a href=\"#ibu\">IBU</a> and <a href=\"#alfasyre\">alpha acid</a>.",
    "hjelp.idx.faqMorkereFarge.sporsmal": "Why does the beer get darker when I add this malt?",
    "hjelp.idx.faqMorkereFarge.svar": "Malt's color contribution varies enormously — a dark, roasted malt can have 10–50 times higher EBC than a pale base malt. Even a small amount of a dark malt can therefore have a large effect on the beer's overall color. See <a href=\"#ebc\">EBC</a>.",
    "hjelp.idx.faqByttGjaer.sporsmal": "What happens if I switch yeast?",
    "hjelp.idx.faqByttGjaer.svar": "Attenuation (and therefore FG and ABV) changes to the new yeast's value, and the flavor profile can change — different yeast strains contribute different esters and phenols. See <a href=\"#gjaer-pavirkning\">how yeast affects the beer</a>.",
    "hjelp.idx.faqUtgjaering.sporsmal": "What does attenuation mean?",
    "hjelp.idx.faqUtgjaering.svar": "See <a href=\"#utgjaering\">attenuation</a> above — in short, how much of the sugar the yeast manages to convert to alcohol.",
    "hjelp.idx.faqEgneIngredienser.sporsmal": "Can I use ingredients that aren't in the library?",
    "hjelp.idx.faqEgneIngredienser.svar": "Yes — use \"+ Custom\" on the malt, hop, or yeast row. See <a href=\"#egendefinerte-ingredienser\">custom ingredients</a>.",
    "hjelp.idx.faqTraffIkkeOg.sporsmal": "Why didn't I hit my expected OG on brew day?",
    "hjelp.idx.faqTraffIkkeOg.svar": "The calculated OG assumes your brewhouse efficiency (the field in Basics) actually matches your equipment and technique that day. Crush quality, mash temperature, sparging method, and even weather conditions can cause deviation. Feel free to adjust the efficiency number after a few of your own brews, so future estimates become more precise for your specific setup.",
    "hjelp.idx.faqOgFgForskjell.sporsmal": "What's the difference between OG and FG?",
    "hjelp.idx.faqOgFgForskjell.svar": "OG is measured before fermentation (sugar present), FG is measured after (sugar remaining). See <a href=\"#og\">OG</a> and <a href=\"#fg\">FG</a>.",
    "hjelp.idx.faqFaktiskFg.sporsmal": "Why is the actual FG different from the calculated FG?",
    "hjelp.idx.faqFaktiskFg.svar": "Calculated FG uses the yeast's <em>typical</em> attenuation percentage. Actual attenuation is affected by fermentation temperature, yeast amount/health, mash temperature (which governs how fermentable the wort actually is), and the yeast strain's variation from batch to batch. A small deviation is normal and no cause for concern.",

    "hjelp.idx.avslutning": "Didn't find what you were looking for? The handbook keeps growing.",

    "hjelp.dag.toc.1": "1. Prep",
    "hjelp.dag.toc.2": "2. Mash Water",
    "hjelp.dag.toc.3": "3. Add Malt",
    "hjelp.dag.toc.4": "4. Mash",
    "hjelp.dag.toc.5": "5. Mash-out",
    "hjelp.dag.toc.6": "6. Sparge",
    "hjelp.dag.toc.7": "7. Boil",
    "hjelp.dag.toc.8": "8. Hops",
    "hjelp.dag.toc.9": "9. Chill",
    "hjelp.dag.toc.10": "10. OG Reading",
    "hjelp.dag.toc.11": "11. Fermenter",
    "hjelp.dag.toc.12": "12. Pitch Yeast",
    "hjelp.dag.toc.13": "13. Fermentation",
    "hjelp.dag.toc.14": "14. FG Reading",
    "hjelp.dag.toc.15": "15. Carbonate/Bottle",
    "hjelp.dag.intro": "A general walkthrough of a typical all-grain brew day, step by step. The exact order and some steps vary with <a href=\"bryggemetoder.html\">brewing method</a> and equipment — this is the typical sequence most homebrewers follow.",

    "hjelp.dag.dt.hva": "What do I do?",
    "hjelp.dag.dt.hvorfor": "Why do I do it?",
    "hjelp.dag.dt.folgMed": "What should I watch for?",
    "hjelp.dag.dt.feil": "Common beginner mistakes",

    "hjelp.dag.steg1.tittel": "Prep Equipment and Ingredients",
    "hjelp.dag.steg1.hva": "Weigh out malt and hops according to the recipe, clean and set out the kettle, mash tun, chiller, fermenter, and everything else you'll need along the way.",
    "hjelp.dag.steg1.hvorfor": "Hunting for equipment or missing an ingredient mid-mash or mid-boil costs you precious time exactly when temperature and timing matter most.",
    "hjelp.dag.steg1.folgMed": "That everything that needs to be clean actually is clean — especially anything that touches the wort after the boil.",
    "hjelp.dag.steg1.feil": "Discovering after mashing has started that you're missing an ingredient, or that the chiller isn't hooked up to water.",

    "hjelp.dag.steg2.tittel": "Heat the Mash Water",
    "hjelp.dag.steg2.hva": "Heat the amount of water the mash needs to a few degrees above your target temperature (cold grain and cold equipment pull the temperature down when the water meets the malt).",
    "hjelp.dag.steg2.hvorfor": "Mash temperature determines which type of sugar the enzymes produce — and therefore how fermentable the wort becomes. See <a href=\"index.html#def-mesking\">mashing</a>.",
    "hjelp.dag.steg2.folgMed": "That you hit the right temperature <em>after</em> the malt has been added, not just in the water alone.",
    "hjelp.dag.steg2.feil": "Heating the water to exactly the target temperature, then missing because cold grain pulls the temperature down a couple of degrees.",

    "hjelp.dag.steg3.tittel": "Add the Malt",
    "hjelp.dag.steg3.hva": "Stir the crushed malt into the water, evenly and without clumps (\"dough-in\").",
    "hjelp.dag.steg3.hvorfor": "Clumps of dry malt (\"dough balls\") stop the enzymes from reaching the whole grain, and you lose yield.",
    "hjelp.dag.steg3.folgMed": "Stir thoroughly right away, especially at the bottom and along the edges.",
    "hjelp.dag.steg3.feil": "Pouring in all the malt at once without stirring at the same time.",

    "hjelp.dag.steg4.tittel": "Mash",
    "hjelp.dag.steg4.hva": "Hold the mixture at the correct temperature for the time the recipe specifies (typically 45–90 minutes), see <a href=\"index.html#def-mesking\">mashing</a>.",
    "hjelp.dag.steg4.hvorfor": "This is when the enzymes actually convert starch into fermentable sugar — the foundation of the whole batch.",
    "hjelp.dag.steg4.folgMed": "Temperature drift. Insulation (lid, blanket) helps a lot on simple mash tuns.",
    "hjelp.dag.steg4.feil": "Letting the temperature drop gradually without noticing.",

    "hjelp.dag.steg5.tittel": "Mash-out (If Relevant)",
    "hjelp.dag.steg5.hva": "Quickly heat the mash to around 75–78°C, see <a href=\"index.html#def-mashout\">mash-out</a>.",
    "hjelp.dag.steg5.hvorfor": "Stops enzyme activity (locking in the sugar profile) and makes the wort less viscous, which makes sparging easier.",
    "hjelp.dag.steg5.folgMed": "Don't let the temperature go too high or hold too long — the point is to stop the process, not boil the mash.",
    "hjelp.dag.steg5.feil": "Skipping mash-out and then wondering why sparging is slow.",

    "hjelp.dag.steg6.tittel": "Sparge (If the Method Uses It)",
    "hjelp.dag.steg6.hva": "Rinse remaining sugar out of the grain bed with hot water, see <a href=\"index.html#def-skylling\">sparging</a> and <a href=\"bryggemetoder.html\">brewing methods</a> for which methods use this step.",
    "hjelp.dag.steg6.hvorfor": "Without sparging, a lot of the malt potential is left behind in the grain bed — it directly affects <a href=\"index.html#og\">OG</a>.",
    "hjelp.dag.steg6.folgMed": "The sparge water temperature (too hot can extract unwanted tannins).",
    "hjelp.dag.steg6.feil": "Sparging with boiling water, or squeezing the grain bed hard to \"get more out\" — both can produce bitter byproducts.",

    "hjelp.dag.steg7.tittel": "Boil",
    "hjelp.dag.steg7.hva": "Boil the wort, normally for 60 minutes, see <a href=\"index.html#def-kok\">boil</a>.",
    "hjelp.dag.steg7.hvorfor": "Sterilization, concentrating the wort, and the foundation for the hop additions below.",
    "hjelp.dag.steg7.folgMed": "A vigorous boil is prone to boiling over in the first few minutes — stay nearby until the boil has settled.",
    "hjelp.dag.steg7.feil": "Walking away from the kettle right as the boil starts and coming back to a boiled-over stovetop.",

    "hjelp.dag.steg8.tittel": "Hop Additions",
    "hjelp.dag.steg8.hva": "Add hops at the times the recipe specifies, see <a href=\"index.html#def-humletilsetning\">hop additions</a>.",
    "hjelp.dag.steg8.hvorfor": "Timing determines whether the hops contribute mostly bitterness (early) or aroma/flavor (late), see <a href=\"index.html#ibu\">IBU</a>.",
    "hjelp.dag.steg8.folgMed": "Actually timing the additions against remaining boil time, not elapsed time.",
    "hjelp.dag.steg8.feil": "Mixing up \"minutes into the boil\" and \"minutes left in the boil\" — they count in opposite directions.",

    "hjelp.dag.steg9.tittel": "Chill",
    "hjelp.dag.steg9.hva": "Rapidly chill the wort down toward the yeast's starting temperature, see <a href=\"index.html#def-kjoling\">chilling</a>.",
    "hjelp.dag.steg9.hvorfor": "Rapid chilling reduces the time the wort spends in a temperature range where unwanted bacteria thrive, and often gives clearer beer.",
    "hjelp.dag.steg9.folgMed": "That your chilling equipment is actually clean — it meets the wort after the boil, the most vulnerable phase.",
    "hjelp.dag.steg9.feil": "Letting the wort sit and cool slowly at room temperature instead of using a chiller/ice bath.",

    "hjelp.dag.steg10.tittel": "Take an OG Reading",
    "hjelp.dag.steg10.hva": "Measure the gravity with a hydrometer or refractometer, see <a href=\"index.html#def-og-maling\">OG reading</a>.",
    "hjelp.dag.steg10.hvorfor": "Confirms whether you hit your expected <a href=\"index.html#og\">OG</a> — an important starting point for assessing the whole batch.",
    "hjelp.dag.steg10.folgMed": "That the sample has cooled to the correct reference temperature for your instrument.",
    "hjelp.dag.steg10.feil": "Measuring a warm sample and getting a misleading number, see the <a href=\"index.html#faq-traff-ikke-og\">FAQ</a>.",

    "hjelp.dag.steg11.tittel": "Transfer to the Fermenter",
    "hjelp.dag.steg11.hva": "Transfer the chilled wort to a clean, sanitized fermenter.",
    "hjelp.dag.steg11.hvorfor": "From this point on, it's the yeast that should dominate the environment — not other microorganisms.",
    "hjelp.dag.steg11.folgMed": "A bit of splashing during transfer is actually desirable here — the wort needs oxygen for the yeast to get off to a good start.",
    "hjelp.dag.steg11.feil": "Transferring too gently and giving the yeast too little oxygen for a good start.",

    "hjelp.dag.steg12.tittel": "Pitch Yeast",
    "hjelp.dag.steg12.hva": "Add the yeast (rehydrated or pitched directly, per the manufacturer's instructions).",
    "hjelp.dag.steg12.hvorfor": "The faster the yeast gets going, the less time unwanted microorganisms have to establish themselves first.",
    "hjelp.dag.steg12.folgMed": "That the wort is within the yeast's recommended temperature range before you pitch.",
    "hjelp.dag.steg12.feil": "Pitching yeast into wort that's too warm, which can damage or kill the yeast.",

    "hjelp.dag.steg13.tittel": "Fermentation",
    "hjelp.dag.steg13.hva": "Let the yeast work undisturbed, at a stable temperature, see <a href=\"index.html#def-gjaering\">fermentation</a>.",
    "hjelp.dag.steg13.hvorfor": "A stable temperature gives a cleaner, more predictable flavor profile than a fluctuating one.",
    "hjelp.dag.steg13.folgMed": "Activity in the airlock over the first few days, and that the temperature stays within the yeast's recommended range.",
    "hjelp.dag.steg13.feil": "Opening the fermenter often \"to check\" — every opening is a new chance for contamination.",

    "hjelp.dag.steg14.tittel": "Take an FG Reading",
    "hjelp.dag.steg14.hva": "Measure the gravity once activity has settled down, see <a href=\"index.html#def-fg-maling\">FG reading</a>.",
    "hjelp.dag.steg14.hvorfor": "Confirms that fermentation is actually finished, and lets you calculate the actual <a href=\"index.html#abv\">ABV</a>.",
    "hjelp.dag.steg14.folgMed": "Take readings on two consecutive days — if the number is stable, fermentation is done.",
    "hjelp.dag.steg14.feil": "Ending fermentation too early because the airlock has gone quiet, without confirming with an actual reading.",

    "hjelp.dag.steg15.tittel": "Carbonate / Bottle / Keg",
    "hjelp.dag.steg15.hva": "Transfer the beer to bottles or a keg and carbonate it, see <a href=\"index.html#def-karbonering\">carbonation</a> and <a href=\"index.html#def-flasking\">bottling/kegging</a>.",
    "hjelp.dag.steg15.hvorfor": "This is the last step before the beer is ready to drink — and what gives it the right mouthfeel.",
    "hjelp.dag.steg15.folgMed": "The correct sugar amount for bottle carbonation (too much can cause overpressure/explosion risk), or the correct pressure/time for force-carbonating in a keg.",
    "hjelp.dag.steg15.feil": "Drinking the beer too soon — most beers improve noticeably after a few weeks of conditioning.",

    "hjelp.dag.avslutning": "Build a concrete brew day sheet for your own recipe from the recipe builder's <a href=\"../index.html\">Print</a> panel.",

    "hjelp.metoder.toc.biab": "BIAB",
    "hjelp.metoder.toc.allgrain": "Traditional All-Grain",
    "hjelp.metoder.toc.altiett": "All-in-One System",
    "hjelp.metoder.intro": "All the methods below broadly follow the same <a href=\"bryggedag.html\">brew day</a> — the difference lies in how mashing and sparging are done in practice. This round covers the three most common for homebrewers; more can be added later without changing the page's structure.",

    "hjelp.metoder.biab.tittel": "BIAB — Brew In A Bag",
    "hjelp.metoder.biab.tekst": "The entire grain bill mashes directly in a large bag in the boil kettle — no separate mash tun. After mashing, the bag is lifted out and drained, often <strong>without</strong> a separate sparge.",
    "hjelp.metoder.biab.hvorfor": "<strong>How it affects the brew day:</strong> Steps 3–6 in the <a href=\"bryggedag.html\">brew day guide</a> (add malt → mash → mash-out → sparge) simplify to \"mash in the bag, lift out, drain\" — <a href=\"index.html#def-skylling\">sparging</a> is often skipped entirely, or done as a simple dunk sparge. Requires less equipment than traditional all-grain, but places slightly higher demands on a good crush for good yield since it isn't sparged as thoroughly.",

    "hjelp.metoder.allgrain.tittel": "Traditional All-Grain (Separate Mash Tun)",
    "hjelp.metoder.allgrain.tekst": "Mashing takes place in a dedicated mash tun (often with a false bottom/filter), and the wort is drained into the boil kettle — the grain bed is then sparged separately with hot water to extract more sugar.",
    "hjelp.metoder.allgrain.hvorfor": "<strong>How it affects the brew day:</strong> All 15 steps in the <a href=\"bryggedag.html\">brew day guide</a> are carried out as described, including a dedicated, more thorough <a href=\"index.html#def-skylling\">sparge</a> step. Requires more equipment (a separate mash tun) than BIAB, but often gives somewhat better control over the sparging process and batch size.",

    "hjelp.metoder.altiett.tittel": "All-in-One Brewing System",
    "hjelp.metoder.altiett.tekst": "A single electric vessel handles both mashing and boiling, often with a built-in pump for recirculation and/or sparging. See <a href=\"utstyr-brewzilla.html\">BrewZilla</a> for a concrete example.",
    "hjelp.metoder.altiett.hvorfor": "<strong>How it affects the brew day:</strong> Same steps as traditional all-grain, but mashing and boiling happen in the same vessel — you skip moving wort between two vessels between steps 4 and 7 in the <a href=\"bryggedag.html\">brew day guide</a>. Built-in temperature control makes steps 2 and 4 (heating / holding temperature) easier to hit precisely than with a manual gas burner.",

    "hjelp.metoder.avslutning": "More methods (e.g. decoction, parti-gyle, no-sparge) can be added as their own cards here later, without changing the rest of the page.",

    "hjelp.brewzilla.toc.tekniske": "Technical Specs",
    "hjelp.brewzilla.toc.altiett": "All-in-One Principle",
    "hjelp.brewzilla.toc.ikkeVerifisert": "Not Yet Verified",
    "hjelp.brewzilla.intro": "This is a <strong>reference guide</strong> for the BrewZilla — the first of several planned equipment-specific guides — not an assumption that you own one yourself. Kvernhaug Brygghus has one internal equipment profile calibrated against the BrewZilla 35L Gen 4.1 (see the <a href=\"../index.html\">Recipe Builder</a>), and this page documents exactly which numbers in that profile come from the product itself, and which are Kvernhaug's own calculation choices. If you use other equipment, the general brewing assumptions further down still apply — they aren't BrewZilla-specific. See also <a href=\"bryggemetoder.html#alt-i-ett\">all-in-one brewing system</a> for the general method the BrewZilla is one example of.",

    "hjelp.brewzilla.kjelekapasitet.tittel": "Kettle Capacity",
    "hjelp.brewzilla.kjelekapasitet.tekst": "The BrewZilla 35L Gen 4.1 has a nominal kettle capacity of <strong>35 litres</strong> — this is right there in the product name, and is the only value on this page that is actually a product property and not something Kvernhaug Brygghus itself chose or calculated.",

    "hjelp.brewzilla.maksPreboil.tittel": "Kvernhaug's Practical Recommendation: Max Pre-Boil Volume",
    "hjelp.brewzilla.maksPreboil.tekst": "The Kvernhaug Brygghus app warns when the calculated pre-boil volume exceeds roughly <strong>30 litres</strong> — a practical safety margin under the kettle's 35-litre capacity, to avoid boil-over during a vigorous boil. This is <strong>Kvernhaug's own practical limit</strong>, not a number taken from an official manufacturer specification.",

    "hjelp.brewzilla.standardverdier.tittel": "Kvernhaug's Calculation Defaults (Equipment Profile)",
    "hjelp.brewzilla.standardverdier.tekst": "These two numbers are the default values the Kvernhaug Brygghus app uses in its own BrewZilla equipment profile to calculate water amounts and volume. They are <strong>the app's own calculation assumptions</strong>, not confirmed against an official manufacturer specification:",
    "hjelp.brewzilla.tabell.egenskap": "Property",
    "hjelp.brewzilla.tabell.kvernhaugStandard": "Kvernhaug Calculation Default",
    "hjelp.brewzilla.fordampning": "Boil-off Rate",
    "hjelp.brewzilla.fordampningVerdi": "4.0 L/hour",
    "hjelp.brewzilla.deadspace": "Dead Space (Residual Volume)",
    "hjelp.brewzilla.deadspaceVerdi": "2.0 L",
    "hjelp.brewzilla.standardverdier.tekst2": "Actual boil-off varies with boil intensity, lid on/off, power, and ambient conditions — feel free to adjust the number based on your own measured brews on your specific setup. Dead space is likewise not checked against the manufacturer's own documentation.",

    "hjelp.brewzilla.generelle.tittel": "General Brewing Assumptions (Not BrewZilla-Specific)",
    "hjelp.brewzilla.generelle.tekst": "These two numbers live in the same equipment profile in the code, but are really <strong>general brewing assumptions</strong> that apply regardless of which equipment you use — not properties of the BrewZilla:",
    "hjelp.brewzilla.meskeforhold": "Mash Ratio",
    "hjelp.brewzilla.meskeforholdVerdi": "3.2 L/kg",
    "hjelp.brewzilla.kornabsorpsjon": "Grain Absorption",
    "hjelp.brewzilla.kornabsorpsjonVerdi": "1.0 L/kg",
    "hjelp.brewzilla.generelle.tekst2": "Mash ratio is a process choice you can adjust yourself, and grain absorption is a common calculation assumption in homebrewing generally — neither is a fixed BrewZilla specification.",

    "hjelp.brewzilla.kildeliste": "Source for all the numbers above: the Kvernhaug Brygghus app's <code>modules/equipment.py</code> (equipment profile default values) and the brew day calculation's 30 L warning in <code>modules/brewday_calc.py</code>/<code>ui/brewday_panel.py</code>. None of the numbers have been checked against an official BrewZilla product specification.",

    "hjelp.brewzilla.altiett.tittel": "The All-in-One Principle",
    "hjelp.brewzilla.altiett.tekst": "The BrewZilla mashes and boils in the same vessel, with electric temperature control and a built-in pump/filter for recirculation — see <a href=\"bryggemetoder.html#alt-i-ett\">all-in-one brewing system</a> for how this simplifies the brew day compared to separate vessels.",

    "hjelp.brewzilla.ikkeVerifisert.tittel": "Not Yet Verified",
    "hjelp.brewzilla.ikkeVerifisert.intro": "the following has deliberately NOT been filled in with made-up information, and is waiting for actual verification against a concrete BrewZilla setup:",
    "hjelp.brewzilla.ikkeVerifisert.li1": "Concrete control panel / temperature programming steps",
    "hjelp.brewzilla.ikkeVerifisert.li2": "Recommended cleaning and maintenance routine",
    "hjelp.brewzilla.ikkeVerifisert.li3": "Known quirks or common sources of error specific to the BrewZilla",
    "hjelp.brewzilla.ikkeVerifisert.li4": "Pump/recirculation settings for optimal mashing",
    "hjelp.brewzilla.ikkeVerifisert.li5": "Model-specific differences (Gen 3 / Gen 4 / Gen 4.1, etc.)",
    "hjelp.brewzilla.ikkeVerifisert.avslutning": "This section will be filled in once the information is verified — either through actual use, or against the manufacturer's own documentation.",

    "hjelp.brewzilla.roadmap": "Equipment choices in the recipe builder itself (kettle volume, boil-off, etc.) aren't connected to this guide yet — that's a separate, larger feature planned further out (see Equipment Profile in the roadmap).",

    "stilmatch.kreativtBrygg": "Creative Brew",
    "stilmatch.seHvaSomMangler": "See what's missing",
    "stilmatch.ikkeOffisiellBadge": "🏺 not official BJCP",
    "stilmatch.ikkeOffisiellTitle": "Kvernhaug/historical category, not an official BJCP style",
    "stilmatch.ikkeOffisiellHeadline": "🏺 Kvernhaug/historical category — not an official BJCP style",
    "stilmatch.ingenAlternativer": "No styles match your recipe yet.",

    "stilmatch.ogUnder": "Gravity too low: OG {og} — style range {lo}–{hi} — {diff} under",
    "stilmatch.ogOver": "Gravity too high: OG {og} — style range {lo}–{hi} — {diff} over",
    "stilmatch.fgUnder": "FG too low: {fg} — style range {lo}–{hi} — {diff} under",
    "stilmatch.fgOver": "FG too high: {fg} — style range {lo}–{hi} — {diff} over",
    "stilmatch.ibuUnder": "Bitterness too low: {ibu} IBU — style range {lo}–{hi} IBU — {diff} IBU under",
    "stilmatch.ibuOver": "Bitterness too high: {ibu} IBU — style range {lo}–{hi} IBU — {diff} IBU over",
    "stilmatch.ebcUnder": "Color too light: {ebc} EBC — style range {lo}–{hi} EBC — {diff} EBC under",
    "stilmatch.ebcOver": "Color too dark: {ebc} EBC — style range {lo}–{hi} EBC — {diff} EBC over",
    "stilmatch.abvUnder": "Alcohol too low: {abv}% — style range {lo}–{hi}% — {diff} percentage points under",
    "stilmatch.abvOver": "Alcohol too high: {abv}% — style range {lo}–{hi}% — {diff} percentage points over",
    "stilmatch.sensoriskOnsket": "Desired sensory character of *{smak}* (has {reell}, style calls for {krav}+)",

    "builder.smaksprofil.ariaLabel": "Flavor wheel — sensory profile based on the chosen ingredients",
    "veiledning.linje": "{label} is {niva} {retning} than typical for {stil}. Typical range: {omrade}.",
    "veiledning.tips": " Tip: {tips} will bring the recipe closer to the style.",
    "veiledning.samlet": "Your recipe is {adjektiver} than typical for {stil}. See «Nearby styles» below for a concrete alternative that might fit better.",
    "veiledning.nivaTydelig": "clearly",
    "veiledning.nivaLitt": "slightly",
    "veiledning.retningLavere": "lower",
    "veiledning.retningHoyere": "higher",
    "veiledning.listeOg": "and",

    "stilmatch.balanse.humledominert": "🔥 Hop-dominant: bitterness will strongly dominate over the malt profile.",
    "stilmatch.balanse.maltdominert": "🌾 Malt-dominant: low bitterness means the residual sweetness from the grain will really show.",
    "stilmatch.balanse.harmonisk": "⚖️ Harmoniously balanced: the balance between sweetness and bitterness feels very even.",
    "stilmatch.balanse.ekstremtTort": "🍃 Extremely dry brew: the yeast has eaten up nearly all the sugar.",
    "stilmatch.problem.tungSodme": "⚠️ Risk of cloying sweetness: high FG means unfermentable sugar. The beer could turn out sticky-sweet.",
    "stilmatch.problem.askeaktig": "☕ Ashy finish: the combination of dark roasted malt and high bitterness can create a sharp aftertaste.",
    "stilmatch.problem.juiceSirup": "🧃 Juice/syrup risk: tropical hops, high residual sweetness, and low bitterness can give a sweet, syrupy result.",
    "stilmatch.problem.sensoriskKonflikt": "🔥 Sensory conflict: smoked malt and citrus/tropical hops fight each other — these flavor notes don't reinforce one another.",
    "stilmatch.problem.stilkollisjon": "🇧🇪 Style clash: Belgian yeast and aggressive American hops can overwhelm the yeast's ester profile — consider a neutral yeast for hop-forward styles.",
    "stilmatch.sig.britisk": "🇬🇧 British ale signature: Maris Otter / EKG / British yeast gives classic pub-ale character.",
    "stilmatch.sig.hazy": "🌀 Hazy signature: tropical hops combined with soft malt (oats/wheat) point toward NEIPA / Hazy IPA.",
    "stilmatch.sig.belgisk": "🇧🇪 Belgian signature: the yeast will dominate with spicy phenol and ester notes — typically pepper, clove, and fruit.",
    "stilmatch.sig.stout": "☕ Stout signature: roasted barley / black malt gives a burnt-espresso character and black color.",
    "stilmatch.sig.westCoast": "🏄 West Coast signature: clean, dry yeast and bitter, aromatic hops give a classic West Coast IPA profile.",
    "stilmatch.sig.lager": "🍺 Lager signature: lager yeast points toward pilsner and lager styles.",
  },
};

// Runde 14, pkt. 9 -- stilbiblioteket (data/bjcp_styles.json) bruker det
// norske displaynavnet SOM stabil identitet (dict-nøkkel, valgtStil,
// combobox-verdi -- ingen egen id-kolonne finnes). En bred migrering til en
// separat stabil id ville risikert bakoverkompatibilitet med allerede
// lagrede oppskrifter og .kbhrecipe-filer (rapportert i sluttrapporten i
// stedet for gjennomført). Løsningen her er derfor et rent VISNINGSLAG:
// `valgtStil`/dict-nøklene forblir norske og uendret overalt i logikk,
// lagring og eksport -- kun stilVisningsnavn() oversetter for skjerm.
// Stiler uten oppføring her (bør ikke forekomme, men failer trygt) vises
// med sitt norske navn uansett språk fremfor en tom streng.
const STIL_NAVN_EN = {
  "Tysk Pilsner": "German Pilsner",
  "Tsjekkisk Pilsner": "Czech Pilsner",
  "Münchener Dunkel": "Munich Dunkel",
  "Vienna Lager": "Vienna Lager",
  "Märzen": "Märzen",
  "Historisk Wiesn-Märzen": "Historical Wiesn Märzen",
  "Festbier": "Festbier",
  "Heller Bock (Mai-Bock)": "Helles Bock (Maibock)",
  "Dunkles Bock": "Dunkles Bock",
  "Tysk Weissbier / Hefeweizen": "German Weissbier / Hefeweizen",
  "Robust Porter": "Robust Porter",
  "Imperial Porter / Baltic Porter": "Imperial Porter / Baltic Porter",
  "Irsk Tørr Stout": "Irish Dry Stout",
  "Oatmeal Stout": "Oatmeal Stout",
  "Klassisk Røykøl (Rauchbier)": "Classic Smoked Beer (Rauchbier)",
  "Tradisjonelt Norsk Gårdsøl / Kveik": "Traditional Norwegian Farmhouse Ale / Kveik",
  "Tradisjonelt Norsk Juleøl": "Traditional Norwegian Christmas Ale",
  "Belgisk Witbier": "Belgian Witbier",
  "Belgisk Dubbel": "Belgian Dubbel",
  "Belgisk Tripel": "Belgian Tripel",
  "Hazy IPA / NEIPA": "Hazy IPA / NEIPA",
  "Amerikansk IPA": "American IPA",
  "English Bitter": "English Bitter",
  "Best Bitter": "Best Bitter",
  "ESB / Strong Bitter": "ESB / Strong Bitter",
  "English Dark Mild": "English Dark Mild",
};

function stilVisningsnavn(navn) {
  if (!navn) return navn;
  if (navn === "Kreativt Brygg") return t("stilmatch.kreativtBrygg");
  if (gjeldendeSprak() === "en") return STIL_NAVN_EN[navn] || navn;
  return navn;
}

// Samme prinsipp som stilnavn: Flavor Engine-kategoriene (SMAKS_KATEGORIER
// i flavor.js) er dict-nøkler delt med ingrediensdataens `kategorier`-felt
// og selve smaksprofil-beregningen -- disse må IKKE endres. Kun smakshjulets
// akse-etiketter og stilmatch-tekstens kategorinavn oversettes for skjerm.
const SMAKS_KATEGORI_EN = {
  "Maltfylde": "Malt body",
  "Brød": "Bread",
  "Toast": "Toast",
  "Karamell": "Caramel",
  "Honning": "Honey",
  "Nøtter": "Nuts",
  "Sjokolade": "Chocolate",
  "Kaffe": "Coffee",
  "Røyk": "Smoke",
  "Bitterhet": "Bitterness",
  "Furunål": "Pine",
  "Jordlig": "Earthy",
  "Krydder": "Spice",
  "Sitrus": "Citrus",
  "Tropisk": "Tropical",
  "Fruktighet": "Fruitiness",
  "Steinfrukt": "Stone fruit",
  "Vinøs": "Vinous",
};

function smaksKategoriVisning(kat) {
  if (gjeldendeSprak() === "en") return SMAKS_KATEGORI_EN[kat] || kat;
  return kat;
}

// Samme prinsipp for malt-gruppeoverskriftene i søkefeltet (app.js sin
// MALT_GRUPPE_REKKEFOLGE/_maltGruppe) -- sorteringsrekkefølgen er nøkkelt
// på det norske navnet, kun visningsteksten oversettes.
const MALT_GRUPPE_LABEL_EN = {
  "PALE / PILSNER": "PALE / PILSNER",
  "MUNICH / VIENNA": "MUNICH / VIENNA",
  "HVETE / RUG": "WHEAT / RYE",
  "KARAMELL / CRYSTAL": "CARAMEL / CRYSTAL",
  "RØSTET / MØRK": "ROASTED / DARK",
  "SPESIALMALT": "SPECIALTY MALT",
  "FLAKES / UMALTET": "FLAKES / UNMALTED",
  "NORSK MALT": "NORWEGIAN MALT",
  "EKSTRAKT / SPRAYMALT": "EXTRACT / DME",
};

function maltGruppeVisning(gruppe) {
  if (gjeldendeSprak() === "en") return MALT_GRUPPE_LABEL_EN[gruppe] || gruppe;
  return gruppe;
}
