// Runde 14 -- vanilla NO/EN i18n. Ingen npm, ingen build-steg, ingen
// tredjeparts i18n-bibliotek. Språk er REN presentasjon: recipe-state,
// localStorage-oppskrifter og .kbhrecipe-formatet vet ingenting om dette
// laget og skal aldri gjøre det (se web/README.md "Språk (NO/EN)").
//
// URL-strategi V1: client-side språkbytte på SAMME url (ingen /en/, ingen
// query/hash-parameter) -- én statisk fil-struktur, ingen duplisert HTML å
// vedlikeholde, kompatibelt med dagens enkle statiske hosting. Kjent
// konsekvens: søkemotorer kan ikke indeksere en egen engelsk URL i V1 --
// se web/README.md for anbefalt fremtidig løsning (statisk pre-render av
// /en/ ved deploy, IKKE en runtime-avhengighet).

const SPRAK_NOKKEL = "kvernhaug_web_sprak";
const SPRAK_LISTE = ["no", "en"];
const SPRAK_DEFAULT = "no";

let _gjeldendeSprak = null;

function _lagretSprak() {
  try {
    const v = localStorage.getItem(SPRAK_NOKKEL);
    return SPRAK_LISTE.includes(v) ? v : null;
  } catch {
    return null;
  }
}

// Ingen IP/geolocation, ingen serverlogikk -- kun navigator.language, og
// KUN som et engangs-utgangspunkt når brukeren ikke har valgt noe selv.
// Norsk er fortsatt fallback for alt annet (inkl. "nb"/"nn" og alt vi ikke
// gjenkjenner). Brukeren kan alltid bytte manuelt via språkvelgeren.
function _nettleserSprakGjetning() {
  try {
    const spraak = (navigator.language || navigator.userLanguage || "").toLowerCase();
    if (spraak.startsWith("en")) return "en";
  } catch {
    // ignorer -- fall gjennom til norsk default
  }
  return SPRAK_DEFAULT;
}

function gjeldendeSprak() {
  if (_gjeldendeSprak) return _gjeldendeSprak;
  _gjeldendeSprak = _lagretSprak() || _nettleserSprakGjetning();
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

function _oppdaterSprakvelgerUI() {
  document.querySelectorAll(".sprak-knapp").forEach((knapp) => {
    const aktiv = knapp.dataset.sprak === gjeldendeSprak();
    knapp.classList.toggle("aktiv", aktiv);
    knapp.setAttribute("aria-pressed", String(aktiv));
  });
}

// Bytter UI-tekst direkte i gjeldende DOM -- ingen reload, ingen tap av
// arbeid (pkt. 25). Sider med egne dynamiske visninger (byggerens
// resultater, Mine oppskrifter sin liste, stilanalyse osv.) lytter selv på
// "kvernhaug:sprakendret" og gjør sin egen re-render -- i18n.js vet
// bevisst ingenting om sidespesifikk state.
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

function _initSprakvelger() {
  document.querySelectorAll(".sprak-knapp").forEach((knapp) => {
    knapp.addEventListener("click", () => settSprak(knapp.dataset.sprak));
  });
  _oppdaterSprakvelgerUI();
}

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
    "hjelp.rundeSprakMerknad": "Denne siden er foreløpig kun tilgjengelig på norsk. Full engelsk oversettelse er planlagt i en senere runde.",

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
    "hjelp.rundeSprakMerknad": "This page is currently only available in Norwegian. A full English translation is planned for a later round.",

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
