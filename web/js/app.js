// UI-logikk for Kvernhaug Brygghus sin web-oppskriftsbygger (Oppskriftsbygger-siden).
// Ingen backend: ingrediens-/stildata hentes fra statiske JSON-filer,
// oppskrifter lagres i localStorage. Selve beregningene ligger i calc.js
// (OG/FG/ABV/IBU/EBC), flavor.js (smaksprofil), radar.js (smakshjul),
// style.js (stilmatch) og veiledning.js (vennlig stilveiledning) -- orkestrert
// DOM-fritt av recipe_engine.js, som også brukes av utskrift_page.js. Denne
// filen er kun DOM-laget: leser skjemaet, kaller recipe_engine, skriver
// resultatet til høyre panel.
//
// Egendefinerte ingredienser og alfa-overstyring løses UTEN å røre calc.js/
// flavor.js/style.js: for hver beregning bygger recipe_engine.js et
// "effektivt" oppslagsobjekt ({...biblioteket, [egen_id]: egendefinertData})
// som sendes inn akkurat som det vanlige biblioteket.
//
// Aktiv-kladd-arkitektur: den ferdig sammensatte oppskriften ("kladden")
// autolagres til AKTIV_KLADD_NOKKEL ved hver eneste beregning -- ikke bare
// ved eksplisitt "Lagre oppskrift". Dette lar Utskrift-siden hente den
// AKTIVE, ulagrede oppskriften direkte, og lar denne siden gjenopprette seg
// selv ved neste besøk uten tap av data.

const LAGRINGSNOKKEL = "kvernhaug_web_oppskrifter";
const MODUS_NOKKEL = "kvernhaug_web_modus";
const IDENTITET_NOKKEL = "kvernhaug_web_identitet";
const AKTIV_KLADD_NOKKEL = "kvernhaug_web_aktiv_kladd";

// Malt-gruppering i søkefeltet -- speiler ui/malt_panel.py sin
// FORETRUKKET_GRUPPE_REKKEFØLGE/KATEGORI_TIL_GRUPPE nøyaktig, slik at web og
// desktop viser malt organisert på samme måte. Ingen ny taksonomi oppfunnet.
const MALT_GRUPPE_REKKEFOLGE = [
  "PALE / PILSNER",
  "MUNICH / VIENNA",
  "HVETE / RUG",
  "KARAMELL / CRYSTAL",
  "RØSTET / MØRK",
  "SPESIALMALT",
  "FLAKES / UMALTET",
  "NORSK MALT",
  "EKSTRAKT / SPRAYMALT",
];

const MALT_KATEGORI_TIL_GRUPPE = {
  "Basemalt": "PALE / PILSNER",
  "Hvete- / Rugmalt": "HVETE / RUG",
  "Karamell- / Krystallmalt": "KARAMELL / CRYSTAL",
  "Spesialmalt (Røstet / Andre)": "RØSTET / MØRK",
  "Flakes / Korn": "FLAKES / UMALTET",
  "Spraymalt": "EKSTRAKT / SPRAYMALT",
  "Norsk Malt": "NORSK MALT",
};

function _maltGruppe(info) {
  return info.display_group || MALT_KATEGORI_TIL_GRUPPE[info.kategori] || "SPESIALMALT";
}

let maltData = {};
let humleData = {};
let gjaerData = {};
let bjcpStyles = {};
let sisteBeregning = null;
let sisteStilAnalyse = null;
let _egendefinertTeller = 0;

const maltRaderEl = document.getElementById("malt-rader");
const humleRaderEl = document.getElementById("humle-rader");
const attenuationOverrideRad = document.getElementById("attenuation-override-rad");
const attenuationOverrideInput = document.getElementById("attenuation-override");
const gjaerEgendefinertFelt = document.getElementById("gjaer-egendefinert-felt");
const gjaerEgNavn = document.getElementById("gjaer-eg-navn");
const gjaerEgProdusent = document.getElementById("gjaer-eg-produsent");
const gjaerEgGjaertype = document.getElementById("gjaer-eg-gjaertype");

let gjaerCombobox = null;
let stilCombobox = null;
let oppdaterSmakshjul = null;

function nyEgendefinertId(prefiks) {
  _egendefinertTeller += 1;
  return `${prefiks}_${Date.now()}_${_egendefinertTeller}`;
}

// ─── Brukeridentitet (brygger/bryggeri) ──────────────────────────────────
// Oppskriften er brukerens, ikke Kvernhaug sin: brygger/bryggeri lagres på
// selve oppskriften (localStorage + JSON), OG som en egen, lett
// brukerpreferanse som kun brukes til å forhåndsutfylle NYE oppskrifter --
// den overstyrer aldri en allerede lastet eller importert oppskrift.

function lagreIdentitetsPreferanse() {
  const brygger = document.getElementById("brygger-navn").value.trim();
  const bryggeri = document.getElementById("bryggeri-navn").value.trim();
  if (!brygger && !bryggeri) {
    localStorage.removeItem(IDENTITET_NOKKEL);
    return;
  }
  localStorage.setItem(IDENTITET_NOKKEL, JSON.stringify({ brygger, bryggeri }));
}

function forhandsutfyllIdentitetsPreferanse() {
  try {
    const lagret = JSON.parse(localStorage.getItem(IDENTITET_NOKKEL));
    if (!lagret) return;
    if (lagret.brygger) document.getElementById("brygger-navn").value = lagret.brygger;
    if (lagret.bryggeri) document.getElementById("bryggeri-navn").value = lagret.bryggeri;
  } catch {
    // Korrupt/manglende preferanse -- ufarlig å ignorere, feltene forblir tomme.
  }
}

async function lastData() {
  const [malt, humle, gjaer, stiler] = await Promise.all([
    fetch("data/malt.json").then((r) => r.json()),
    fetch("data/humle.json").then((r) => r.json()),
    fetch("data/gjaer.json").then((r) => r.json()),
    fetch("data/bjcp_styles.json").then((r) => r.json()),
  ]);
  maltData = malt;
  humleData = humle;
  gjaerData = gjaer;
  bjcpStyles = stiler;
}

// Søkefeltet ("search") lar brukeren finne en ingrediens på mer enn bare
// produktnavnet -- men bevisst begrenset til noen få, presise felt
// (produsent/opprinnelse/type/kategori) og IKKE frie smakstags, som ville
// gjort søket for bredt (f.eks. "sitrus" ville truffet dusinvis av humler).
// Malt er i tillegg gruppert (group-felt) -- søket selv går fortsatt på
// tvers av ALLE grupper, grupperingen er kun visuell organisering.
function maltItems() {
  const grupperTilStede = new Set(Object.values(maltData).map(_maltGruppe));
  const rekkefolge = [
    ...MALT_GRUPPE_REKKEFOLGE.filter((g) => grupperTilStede.has(g)),
    ...[...grupperTilStede]
      .filter((g) => !MALT_GRUPPE_REKKEFOLGE.includes(g))
      .sort((a, b) => a.localeCompare(b, "no")),
  ];
  const rekkefolgeIndeks = new Map(rekkefolge.map((g, i) => [g, i]));

  return Object.entries(maltData)
    .map(([id, v]) => ({
      id,
      label: v.navn,
      search: [v.navn, v.produsent, v.kategori].filter(Boolean).join(" ").toLowerCase(),
      group: _maltGruppe(v),
    }))
    .sort((a, b) => (rekkefolgeIndeks.get(a.group) - rekkefolgeIndeks.get(b.group)) || a.label.localeCompare(b.label, "no"));
}

function humleItems() {
  return Object.entries(humleData).map(([id, v]) => ({
    id,
    label: v.navn,
    search: [v.navn, v.opprinnelse, v.type].filter(Boolean).join(" ").toLowerCase(),
  }));
}

function gjaerItems() {
  return Object.entries(gjaerData).map(([id, v]) => ({
    id,
    label: v.navn,
    search: [v.navn, v.produsent, v.gjaertype].filter(Boolean).join(" ").toLowerCase(),
  }));
}

function stilItems() {
  return Object.keys(bjcpStyles)
    .sort((a, b) => a.localeCompare(b, "no"))
    .map((navn) => ({ id: navn, label: navn }));
}

// ─── Modus: Bryggelærling / Bryggmester ──────────────────────────────────
// Ren visningsbryter -- rører aldri oppskriftsdata, kun CSS-klasse på body.
// Runde 11: modusvalget er ikke lenger en stor, permanent kontroll i
// arbeidsflaten -- kun et førstegangsvalg (modal) + et lite bytte i
// hamburger-menyen. Alle modus-knapper (uansett hvor de bor i DOM-et)
// deler klassen .modus-knapp og data-modus, samme mønster som
// .meny-knapp/chrome.js bruker for flere hamburger-triggere.

function settModus(modus) {
  document.body.classList.toggle("modus-laerling", modus === "laerling");
  document.body.classList.toggle("modus-mester", modus === "mester");
  for (const knapp of document.querySelectorAll(".modus-knapp")) {
    knapp.setAttribute("aria-pressed", String(knapp.dataset.modus === modus));
  }
  const statusEl = document.getElementById("sidemeny-modus-status");
  if (statusEl) statusEl.textContent = modus === "mester" ? "Modus: Bryggmester" : "Modus: Bryggelærling";
  localStorage.setItem(MODUS_NOKKEL, modus);
}

function _lukkModusForstegang() {
  const dialog = document.getElementById("modus-forstegang");
  const bakteppe = document.getElementById("modus-forstegang-bakteppe");
  if (dialog) dialog.hidden = true;
  if (bakteppe) bakteppe.hidden = true;
}

function initModus() {
  const lagret = localStorage.getItem(MODUS_NOKKEL);
  settModus(lagret === "mester" ? "mester" : "laerling");

  // Førstegangsvalg: vis KUN når ingen preferanse er lagret ennå -- lagres
  // valget forsvinner dialogen for godt (samme localStorage-nøkkel som før).
  if (!lagret) {
    document.getElementById("modus-forstegang").hidden = false;
    document.getElementById("modus-forstegang-bakteppe").hidden = false;
  }

  for (const knapp of document.querySelectorAll(".modus-knapp")) {
    knapp.addEventListener("click", () => {
      settModus(knapp.dataset.modus);
      _lukkModusForstegang();
    });
  }
  document.getElementById("modus-forstegang-bakteppe").addEventListener("click", _lukkModusForstegang);
}

// ─── Egendefinert malt ────────────────────────────────────────────────────

function _settMaltEgendefinert(rad, pa, eksplisittId) {
  rad.dataset.egendefinert = pa ? "1" : "0";
  rad.querySelector(".egendefinert-felt").hidden = !pa;
  rad.querySelector(".combobox").style.display = pa ? "none" : "";
  rad.querySelector(".egendefinert-knapp").style.display = pa ? "none" : "";
  if (pa) {
    rad.dataset.egendefinertId = eksplisittId || rad.dataset.egendefinertId || nyEgendefinertId("egen_malt");
  } else {
    rad._combobox.clear();
  }
  beregnOgVisResultat();
}

function leggTilMaltRad(forhandsutfylt) {
  const mal = document.getElementById("malt-rad-mal");
  const rad = mal.content.firstElementChild.cloneNode(true);
  const mount = rad.querySelector(".malt-velger-mount");

  const cb = new Combobox({
    items: maltItems(),
    placeholder: "Søk etter malt …",
    ariaLabel: "Velg malt",
    onSelect: beregnOgVisResultat,
  });
  mount.replaceWith(cb.el);
  rad._combobox = cb;

  rad.querySelector(".egendefinert-knapp").addEventListener("click", () => _settMaltEgendefinert(rad, true));
  rad.querySelector(".egendefinert-tilbake-knapp").addEventListener("click", () => _settMaltEgendefinert(rad, false));
  for (const felt of rad.querySelectorAll(".egendefinert-felt input")) {
    felt.addEventListener("input", beregnOgVisResultat);
  }

  if (forhandsutfylt && forhandsutfylt.custom) {
    rad.querySelector(".malt-mengde").value = forhandsutfylt.mengde;
    _settMaltEgendefinert(rad, true, forhandsutfylt.id);
    rad.querySelector(".eg-navn").value = forhandsutfylt.custom.navn || "";
    rad.querySelector(".eg-produsent").value = forhandsutfylt.custom.produsent || "";
    rad.querySelector(".eg-ebc").value = forhandsutfylt.custom.ebc ?? "";
    rad.querySelector(".eg-potensiale").value = forhandsutfylt.custom.potensiale ?? "";
  } else if (forhandsutfylt) {
    cb.setValue(forhandsutfylt.id);
    rad.querySelector(".malt-mengde").value = forhandsutfylt.mengde;
  }

  rad.querySelector(".fjern-knapp").addEventListener("click", () => {
    rad.remove();
    oppdaterMaltProsent();
    beregnOgVisResultat();
  });
  rad.querySelector(".malt-mengde").addEventListener("input", () => {
    oppdaterMaltProsent();
    beregnOgVisResultat();
  });
  maltRaderEl.appendChild(rad);
  oppdaterMaltProsent();
  beregnOgVisResultat();
}

// ─── Malt kg ↔ % (kun Bryggmester) ────────────────────────────────────────
// Portert fra ui/malt_panel.py sin faktiske kontrakt: kg er ALLTID
// kilden, % er alltid DERIVERT av kg/total -- oppdateres live for alle
// rader hver gang en kg-verdi, tillegg eller fjerning endrer totalen
// (samme utløsere som desktop-appens "_malt_pct_pending_sync"). Det
// motsatte (redigere %) skjer IKKE live -- akkurat som på desktop krever
// det et eksplisitt klikk på "Bruk prosentfordeling", som leser ALLE
// rader sine %-felt samtidig og fordeler den NÅVÆRENDE totalvekten
// proporsjonalt. Ingen live-lytter på .malt-pct -- det er nettopp det
// som gjør at det ikke oppstår en kg<->%-feedback-loop.
function oppdaterMaltProsent() {
  const rader = [...maltRaderEl.querySelectorAll(".ingrediens-rad")];
  const kgVerdier = rader.map((r) => parseFloat(r.querySelector(".malt-mengde").value) || 0);
  const total = kgVerdier.reduce((a, b) => a + b, 0);
  rader.forEach((r, i) => {
    const pctInput = r.querySelector(".malt-pct");
    if (pctInput) pctInput.value = total > 0 ? (kgVerdier[i] / total * 100).toFixed(1) : "0.0";
  });
  oppdaterMaltProsentSum();
}

function oppdaterMaltProsentSum() {
  const el = document.getElementById("malt-prosent-sum");
  if (!el) return;
  const pcts = [...maltRaderEl.querySelectorAll(".malt-pct")].map((i) => parseFloat(i.value) || 0);
  const sum = pcts.reduce((a, b) => a + b, 0);
  el.textContent = `Prosent-sum: ${sum.toFixed(1).replace(".", ",")}%`;
  el.classList.toggle("malt-prosent-advarsel", pcts.length > 0 && Math.abs(sum - 100) > 0.5);
}

// "Bruk prosentfordeling" -- portert fra malt_panel.py sin apply_pct_btn:
// leser hva brukeren har skrevet i %-feltene NÅ, og fordeler dagens
// totale kg-vekt proporsjonalt mellom radene (round til 3 desimaler,
// samme som desktop). Rører ingenting hvis prosentsummen eller totalen er 0.
function brukMaltProsentfordeling() {
  const rader = [...maltRaderEl.querySelectorAll(".ingrediens-rad")];
  const pcts = rader.map((r) => parseFloat(r.querySelector(".malt-pct").value) || 0);
  const sumPct = pcts.reduce((a, b) => a + b, 0);
  const currentTotal = rader.reduce((sum, r) => sum + (parseFloat(r.querySelector(".malt-mengde").value) || 0), 0);
  if (sumPct > 0 && currentTotal > 0) {
    rader.forEach((r, i) => {
      const nyKg = Math.round((pcts[i] / sumPct) * currentTotal * 1000) / 1000;
      r.querySelector(".malt-mengde").value = nyKg;
    });
  }
  oppdaterMaltProsent();
  beregnOgVisResultat();
}

// ─── Egendefinert humle (+ alfa-overstyring på biblioteks-humle) ─────────

function _settHumleEgendefinert(rad, pa, eksplisittId) {
  rad.dataset.egendefinert = pa ? "1" : "0";
  rad.querySelector(".egendefinert-felt").hidden = !pa;
  rad.querySelector(".combobox").style.display = pa ? "none" : "";
  rad.querySelector(".egendefinert-knapp").style.display = pa ? "none" : "";
  if (pa) {
    rad.dataset.egendefinertId = eksplisittId || rad.dataset.egendefinertId || nyEgendefinertId("egen_humle");
  } else {
    rad._combobox.clear();
  }
  beregnOgVisResultat();
}

function leggTilHumleRad(forhandsutfylt) {
  const mal = document.getElementById("humle-rad-mal");
  const rad = mal.content.firstElementChild.cloneNode(true);
  const mount = rad.querySelector(".humle-velger-mount");
  const alfaInput = rad.querySelector(".humle-alfa");

  const cb = new Combobox({
    items: humleItems(),
    placeholder: "Søk etter humle …",
    ariaLabel: "Velg humle",
    onSelect: (id) => {
      const info = humleData[id];
      if (info && alfaInput.value === "") alfaInput.value = info.alfa;
      beregnOgVisResultat();
    },
  });
  mount.replaceWith(cb.el);
  rad._combobox = cb;

  rad.querySelector(".egendefinert-knapp").addEventListener("click", () => _settHumleEgendefinert(rad, true));
  rad.querySelector(".egendefinert-tilbake-knapp").addEventListener("click", () => _settHumleEgendefinert(rad, false));
  for (const felt of rad.querySelectorAll(".egendefinert-felt input")) {
    felt.addEventListener("input", beregnOgVisResultat);
  }

  if (forhandsutfylt && forhandsutfylt.custom) {
    rad.querySelector(".humle-gram").value = forhandsutfylt.gram;
    rad.querySelector(".humle-tid").value = forhandsutfylt.tid;
    alfaInput.value = forhandsutfylt.custom.alfa ?? "";
    _settHumleEgendefinert(rad, true, forhandsutfylt.id);
    rad.querySelector(".eg-navn").value = forhandsutfylt.custom.navn || "";
    rad.querySelector(".eg-opprinnelse").value = forhandsutfylt.custom.opprinnelse || "";
    rad.querySelector(".eg-type").value = forhandsutfylt.custom.type || "";
  } else if (forhandsutfylt) {
    cb.setValue(forhandsutfylt.id);
    rad.querySelector(".humle-gram").value = forhandsutfylt.gram;
    rad.querySelector(".humle-tid").value = forhandsutfylt.tid;
    if (forhandsutfylt.alfaOverride != null) alfaInput.value = forhandsutfylt.alfaOverride;
    else if (humleData[forhandsutfylt.id]) alfaInput.value = humleData[forhandsutfylt.id].alfa;
  }

  rad.querySelector(".fjern-knapp").addEventListener("click", () => {
    rad.remove();
    beregnOgVisResultat();
  });
  rad.querySelector(".humle-gram").addEventListener("input", beregnOgVisResultat);
  rad.querySelector(".humle-tid").addEventListener("input", () => {
    oppdaterHumleMaalIbuSynlighet(rad);
    beregnOgVisResultat();
  });
  alfaInput.addEventListener("input", beregnOgVisResultat);
  rad.querySelector(".humle-beregn-knapp").addEventListener("click", () => beregnHumleGramFraMaalIbu(rad));
  oppdaterHumleMaalIbuSynlighet(rad);
  humleRaderEl.appendChild(rad);
  beregnOgVisResultat();
}

// ─── Humle gram ↔ mål-IBU (kun Bryggmester) ───────────────────────────────
// Portert fra ui/hop_panel.py: mål-IBU er ALDRI en live-kobling -- den
// vanlige gram->IBU-beregningen kjører som før på hvert tastetrykk, og
// mål-IBU->gram skjer KUN ved eksplisitt klikk på "Beregn gram" (samme
// knapp-mønster som desktop-appen). Dette er nettopp det som unngår en
// feedback-loop mellom de to feltene. Dryhumle (tid=0) har ingen
// kokeutnyttelse og skjuler derfor kontrollen helt, som på desktop.
function oppdaterHumleMaalIbuSynlighet(rad) {
  const tid = parseFloat(rad.querySelector(".humle-tid").value) || 0;
  const ibuRad = rad.querySelector(".humle-maal-ibu-rad");
  if (ibuRad) ibuRad.hidden = tid <= 0;
}

function beregnHumleGramFraMaalIbu(rad) {
  const maalIbu = parseFloat(rad.querySelector(".humle-maal-ibu").value) || 0;
  if (maalIbu <= 0) return;
  const alfa = parseFloat(rad.querySelector(".humle-alfa").value) || 0;
  const tid = parseFloat(rad.querySelector(".humle-tid").value) || 0;
  const volum = parseFloat(document.getElementById("batch-volum").value) || 0;
  const og = sisteBeregning ? sisteBeregning.og : 1.05;
  const gram = beregnGramFraIBU(maalIbu, alfa, tid, volum, og);
  if (gram > 0) {
    rad.querySelector(".humle-gram").value = gram;
    beregnOgVisResultat();
  }
}

// ─── Lesing av radene ─────────────────────────────────────────────────────

function lesMaltRader() {
  return [...maltRaderEl.querySelectorAll(".ingrediens-rad")]
    .map((rad) => {
      const mengde = parseFloat(rad.querySelector(".malt-mengde").value) || 0;
      if (rad.dataset.egendefinert === "1") {
        const navn = rad.querySelector(".eg-navn").value.trim();
        if (!navn) return null;
        const ebc = parseFloat(rad.querySelector(".eg-ebc").value);
        const potensiale = parseFloat(rad.querySelector(".eg-potensiale").value);
        return {
          id: rad.dataset.egendefinertId, mengde,
          custom: {
            navn,
            produsent: rad.querySelector(".eg-produsent").value.trim() || undefined,
            ebc: isFinite(ebc) ? ebc : 10,
            potensiale: isFinite(potensiale) ? potensiale : 1.036,
          },
        };
      }
      return { id: rad._combobox.getValue(), mengde };
    })
    .filter((m) => m && m.id);
}

function lesHumleRader() {
  return [...humleRaderEl.querySelectorAll(".ingrediens-rad")]
    .map((rad) => {
      const gram = parseFloat(rad.querySelector(".humle-gram").value) || 0;
      const tid = parseFloat(rad.querySelector(".humle-tid").value) || 0;
      const alfaTekst = rad.querySelector(".humle-alfa").value;
      const alfa = alfaTekst !== "" ? parseFloat(alfaTekst) : null;

      if (rad.dataset.egendefinert === "1") {
        const navn = rad.querySelector(".eg-navn").value.trim();
        if (!navn) return null;
        return {
          id: rad.dataset.egendefinertId, gram, tid,
          custom: {
            navn,
            opprinnelse: rad.querySelector(".eg-opprinnelse").value.trim() || undefined,
            type: rad.querySelector(".eg-type").value.trim() || undefined,
            alfa: isFinite(alfa) ? alfa : 5.0,
          },
        };
      }
      const id = rad._combobox.getValue();
      return { id, gram, tid, alfaOverride: isFinite(alfa) ? alfa : null };
    })
    .filter((h) => h && h.id);
}

function _lesGjaerEgendefinert() {
  if (gjaerCombobox.getValue() || gjaerEgendefinertFelt.hidden) return null;
  return {
    navn: gjaerEgNavn.value.trim() || "Egendefinert gjær",
    produsent: gjaerEgProdusent.value.trim() || undefined,
    gjaertype: gjaerEgGjaertype.value.trim() || undefined,
    attenuation: (parseFloat(attenuationOverrideInput.value) || 75) / 100,
  };
}

function ebcTilFarge(ebc) {
  // Grov, kun-visuell EBC->RGB-tilnærming for fargeswatch (ikke en presis fargemodell).
  const clamped = Math.max(2, Math.min(ebc, 80));
  const lysstyrke = 92 - (clamped / 80) * 72;
  return `hsl(38, 75%, ${lysstyrke}%)`;
}

function beregnOgVisResultat() {
  const oppskrift = samleOppskrift();
  sisteBeregning = beregnOppskrift(oppskrift, maltData, humleData, gjaerData, bjcpStyles);
  sisteStilAnalyse = sisteBeregning.stilAnalyse;

  document.getElementById("res-og").textContent = sisteBeregning.og.toFixed(3);
  document.getElementById("res-fg").textContent = sisteBeregning.fg.toFixed(3);
  document.getElementById("res-abv").textContent = sisteBeregning.abv.toFixed(1).replace(".", ",") + " %";
  document.getElementById("res-ibu").textContent = Math.round(sisteBeregning.ibu);
  document.getElementById("res-ebc").textContent = Math.round(sisteBeregning.ebc);
  document.getElementById("ebc-swatch").style.backgroundColor = ebcTilFarge(sisteBeregning.ebc);
  document.getElementById("identitet-navn").textContent = oppskrift.navn;
  const bryggerLinje = [oppskrift.brygger, oppskrift.bryggeri].filter(Boolean).join(" · ");
  document.getElementById("identitet-brygger").textContent = bryggerLinje;
  document.getElementById("identitet-brygger").hidden = !bryggerLinje;

  // Kortets identitetsområde skal vise brukerens VALGTE ølstil (samme
  // felt som lagres/eksporteres, oppskrift.valgtStil) -- IKKE den
  // automatiske stilmatchen (sisteStilAnalyse.stil), som fortsatt vises
  // separat i Stilanalyse-seksjonen. Vises uansett om resten av
  // oppskriften er tom, skjules kun når ingen stil er valgt.
  document.getElementById("identitet-stil").textContent = oppskrift.valgtStil || "";
  document.getElementById("identitet-stil").hidden = !oppskrift.valgtStil;

  if (oppdaterSmakshjul) oppdaterSmakshjul(sisteBeregning.flavorProfile);
  renderStilPanel();

  localStorage.setItem(AKTIV_KLADD_NOKKEL, JSON.stringify(oppskrift));
}

// ─── Stilmatch-visning (read-only, høyre panel) ──────────────────────────

function _stilEntryFor(navn) {
  return sisteStilAnalyse.stil_liste.find((s) => s.stil === navn);
}

function _stilKortHtml(s, { visBeskrivelse = false } = {}) {
  const merke = s.bjcp_offisiell === false
    ? '<span class="stil-merke" title="Kvernhaug/historisk kategori, ikke offisiell BJCP-stil">🏺 ikke offisiell BJCP</span>'
    : "";
  const detaljer = [];
  for (const m of s.mangler) detaljer.push(`<li class="mangel">❌ ${escHtml(m)}</li>`);
  for (const o of s.onsket_sensorisk) detaljer.push(`<li class="onsket">💭 ${escHtml(o)}</li>`);
  const detaljerHtml = detaljer.length
    ? `<details class="stil-detaljer"><summary>Se hva som mangler</summary><ul>${detaljer.join("")}</ul></details>`
    : `<p class="stil-full-match">✅ Innenfor alle stilens numeriske grenser.</p>`;

  return `
    <div class="stil-kort">
      <div class="stil-kort-topp">
        <span class="stil-kort-navn">${escHtml(s.stil)}</span>
        <span class="stil-kort-score">${s.score}%</span>
      </div>
      ${merke}
      ${visBeskrivelse && s.beskrivelse ? `<p class="stil-beskrivelse">${escHtml(s.beskrivelse)}</p>` : ""}
      ${detaljerHtml}
    </div>`;
}

// ─── Stilveiledning-visning (begge moduser: vennlig, rolig språk) ────────

function _renderVeiledning(container, stilEntry, stilNavn) {
  if (!stilEntry) {
    container.innerHTML = "";
    return;
  }
  const v = byggStilVeiledning(stilEntry, stilNavn);
  if (v.alleInnenfor) {
    container.innerHTML = `<p class="stil-veiledning-innenfor">✅ Oppskriften ligger innenfor det typiske området for ${escHtml(stilNavn)}.</p>`;
    return;
  }
  const linjer = v.linjer
    .map((l) => `<p class="stil-veiledning-linje niva-${l.niva}">${escHtml(l.tekst)}</p>`)
    .join("");
  const samlet = v.samlet ? `<p class="stil-veiledning-samlet">${escHtml(v.samlet)}</p>` : "";
  container.innerHTML = linjer + samlet;
}

function renderStilPanel() {
  const a = sisteStilAnalyse;
  if (!a || !sisteBeregning) return;

  const harData = harNokDataForStilmatch(sisteBeregning.maltRader, sisteBeregning.humleRader);
  const tomTilstandEl = document.getElementById("stil-tom-tilstand");
  const autoInnholdEl = document.getElementById("stil-auto-innhold");
  tomTilstandEl.hidden = harData;
  autoInnholdEl.hidden = !harData;

  if (harData) {
    const headlineNavn = document.getElementById("stil-headline-navn");
    const headlineInfo = document.getElementById("stil-headline-info");
    headlineNavn.textContent = a.stil;

    const autoContainer = document.getElementById("stil-veiledning-auto");
    if (a.stil === "Kreativt Brygg") {
      headlineInfo.textContent = "Ingen stil i biblioteket treffer godt nok ennå — juster ingrediensene eller se nærliggende stiler under.";
      autoContainer.innerHTML = "";
    } else {
      const entry = _stilEntryFor(a.stil);
      headlineInfo.innerHTML = entry && entry.bjcp_offisiell === false
        ? '<span class="stil-merke">🏺 Kvernhaug/historisk kategori — ikke en offisiell BJCP-stil</span>'
        : "";
      _renderVeiledning(autoContainer, entry, a.stil);
    }

    document.getElementById("bu-gu-tekst").textContent = `Bitterhetsindeks (BU:GU): ${a.bu_gu.toFixed(2)}`;

    const notatEl = document.getElementById("stil-notater");
    notatEl.innerHTML = "";
    for (const note of [...a.balanse, ...a.problemer]) {
      const li = document.createElement("li");
      li.textContent = note;
      if (a.problemer.includes(note)) li.classList.add("stil-notat-advarsel");
      notatEl.appendChild(li);
    }

    const alternativer = [...a.stil_liste]
      .filter((s) => s.score >= 5)
      .sort((x, y) => y.score - x.score || x.prio - y.prio)
      .slice(0, 5);
    const altEl = document.getElementById("stil-alternativ-liste");
    altEl.innerHTML = alternativer.length
      ? alternativer.map((s) => _stilKortHtml(s)).join("")
      : '<p class="hjelpetekst">Ingen stiler matcher oppskriften din ennå.</p>';
  }

  renderStilManuell();
}

function renderStilManuell() {
  const resultatEl = document.getElementById("stil-manuell-resultat");
  const veiledningEl = document.getElementById("stil-veiledning-manuell");
  const valgtNavn = stilCombobox ? stilCombobox.getValue() : null;
  if (!valgtNavn || !sisteStilAnalyse) {
    resultatEl.innerHTML = "";
    veiledningEl.innerHTML = "";
    return;
  }
  const harData = sisteBeregning && harNokDataForStilmatch(sisteBeregning.maltRader, sisteBeregning.humleRader);
  if (!harData) {
    resultatEl.innerHTML = "";
    veiledningEl.innerHTML = `<p class="hjelpetekst">Legg til malt og/eller humle for å se hvordan oppskriften matcher ${escHtml(valgtNavn)}.</p>`;
    return;
  }
  const entry = _stilEntryFor(valgtNavn);
  resultatEl.innerHTML = entry ? _stilKortHtml(entry, { visBeskrivelse: true }) : "";
  _renderVeiledning(veiledningEl, entry, valgtNavn);
}

// ─── Lagring / lasting / eksport / import ────────────────────────────────

function samleOppskrift() {
  return {
    navn: document.getElementById("oppskrift-navn").value.trim() || "Uten navn",
    brygger: document.getElementById("brygger-navn").value.trim(),
    bryggeri: document.getElementById("bryggeri-navn").value.trim(),
    notater: document.getElementById("oppskrift-notater").value.trim(),
    volum: parseFloat(document.getElementById("batch-volum").value) || 0,
    effektivitet: parseFloat(document.getElementById("effektivitet").value) || 0,
    malt: lesMaltRader(),
    humle: lesHumleRader(),
    gjaerId: gjaerCombobox.getValue() || null,
    gjaerCustom: _lesGjaerEgendefinert(),
    attenuationOverride: gjaerCombobox.getValue() ? null : parseFloat(attenuationOverrideInput.value) || null,
    valgtStil: stilCombobox ? stilCombobox.getValue() : null,
    lagretDato: new Date().toISOString(),
  };
}

function hentLagredeOppskrifter() {
  try {
    return JSON.parse(localStorage.getItem(LAGRINGSNOKKEL)) || {};
  } catch {
    return {};
  }
}

function lagreOppskrift() {
  const oppskrift = samleOppskrift();
  const alle = hentLagredeOppskrifter();
  alle[oppskrift.navn] = oppskrift;
  localStorage.setItem(LAGRINGSNOKKEL, JSON.stringify(alle));
  const status = document.getElementById("lagre-status");
  status.textContent = `Lagret "${oppskrift.navn}" i nettleseren. Se "📂 Mine oppskrifter" for å åpne den igjen senere.`;
}

// Gjenoppretter en oppskrift (fra aktiv kladd, en lagret oppskrift, eller en
// importert JSON-fil) inn i skjemaet.
function _gjenopprettOppskrift(oppskrift) {
  document.getElementById("oppskrift-navn").value = oppskrift.navn || "";
  document.getElementById("brygger-navn").value = oppskrift.brygger || "";
  document.getElementById("bryggeri-navn").value = oppskrift.bryggeri || "";
  document.getElementById("oppskrift-notater").value = oppskrift.notater || "";
  document.getElementById("batch-volum").value = oppskrift.volum;
  document.getElementById("effektivitet").value = oppskrift.effektivitet || 75;

  maltRaderEl.innerHTML = "";
  (oppskrift.malt || []).forEach((m) => leggTilMaltRad(m));
  if (!oppskrift.malt || oppskrift.malt.length === 0) leggTilMaltRad();

  humleRaderEl.innerHTML = "";
  (oppskrift.humle || []).forEach((h) => leggTilHumleRad(h));
  if (!oppskrift.humle || oppskrift.humle.length === 0) leggTilHumleRad();

  if (oppskrift.gjaerId) {
    gjaerCombobox.setValue(oppskrift.gjaerId);
    gjaerEgendefinertFelt.hidden = true;
  } else {
    gjaerCombobox.clear();
    const custom = oppskrift.gjaerCustom;
    if (custom) {
      gjaerEgendefinertFelt.hidden = false;
      gjaerEgNavn.value = custom.navn && custom.navn !== "Egendefinert gjær" ? custom.navn : "";
      gjaerEgProdusent.value = custom.produsent || "";
      gjaerEgGjaertype.value = custom.gjaertype || "";
      attenuationOverrideInput.value = Math.round(custom.attenuation * 100);
    } else {
      gjaerEgendefinertFelt.hidden = true;
      // Bakoverkompatibilitet: eldre lagrede oppskrifter (før gjaerCustom
      // fantes) hadde kun et bart attenuationOverride-tall.
      if (oppskrift.attenuationOverride) attenuationOverrideInput.value = oppskrift.attenuationOverride;
    }
  }
  attenuationOverrideRad.style.display = oppskrift.gjaerId ? "none" : "";

  if (oppskrift.valgtStil) stilCombobox.setValue(oppskrift.valgtStil);
  else stilCombobox.clear();

  beregnOgVisResultat();
}

function hentAktivKladd() {
  try {
    return JSON.parse(localStorage.getItem(AKTIV_KLADD_NOKKEL));
  } catch {
    return null;
  }
}

function eksporterJson() {
  const oppskrift = samleOppskrift();
  const blob = new Blob([JSON.stringify(oppskrift, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${oppskrift.navn.replace(/\s+/g, "_")}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

async function init() {
  await lastData();
  initModus();
  initHjelp();

  oppdaterSmakshjul = initSmakshjul(document.getElementById("smakshjul-container"), SMAKS_KATEGORIER);

  const gjaerMount = document.getElementById("gjaer-velger-mount");
  gjaerCombobox = new Combobox({
    items: gjaerItems(),
    placeholder: "Søk etter gjær …",
    ariaLabel: "Velg gjær",
    onSelect: () => {
      attenuationOverrideRad.style.display = gjaerCombobox.getValue() ? "none" : "";
      if (gjaerCombobox.getValue()) gjaerEgendefinertFelt.hidden = true;
      beregnOgVisResultat();
    },
  });
  gjaerMount.replaceWith(gjaerCombobox.el);

  document.getElementById("gjaer-egendefinert-knapp").addEventListener("click", () => {
    gjaerEgendefinertFelt.hidden = !gjaerEgendefinertFelt.hidden;
    attenuationOverrideRad.style.display = gjaerCombobox.getValue() ? "none" : "";
    beregnOgVisResultat();
  });
  for (const felt of [gjaerEgNavn, gjaerEgProdusent, gjaerEgGjaertype]) {
    felt.addEventListener("input", beregnOgVisResultat);
  }

  const stilMount = document.getElementById("stil-velger-mount");
  stilCombobox = new Combobox({
    items: stilItems(),
    placeholder: "Søk eller velg ølstil …",
    ariaLabel: "Velg ølstil",
    onSelect: () => { renderStilManuell(); beregnOgVisResultat(); },
  });
  stilMount.replaceWith(stilCombobox.el);

  document.getElementById("legg-til-malt").addEventListener("click", () => leggTilMaltRad());
  document.getElementById("legg-til-humle").addEventListener("click", () => leggTilHumleRad());
  document.getElementById("malt-bruk-prosent-knapp").addEventListener("click", brukMaltProsentfordeling);
  document.getElementById("oppskrift-navn").addEventListener("input", beregnOgVisResultat);
  document.getElementById("batch-volum").addEventListener("input", beregnOgVisResultat);
  document.getElementById("effektivitet").addEventListener("input", beregnOgVisResultat);
  attenuationOverrideInput.addEventListener("input", beregnOgVisResultat);
  document.getElementById("oppskrift-notater").addEventListener("input", beregnOgVisResultat);

  document.getElementById("brygger-navn").addEventListener("input", () => {
    lagreIdentitetsPreferanse();
    beregnOgVisResultat();
  });
  document.getElementById("bryggeri-navn").addEventListener("input", () => {
    lagreIdentitetsPreferanse();
    beregnOgVisResultat();
  });
  forhandsutfyllIdentitetsPreferanse();

  document.getElementById("lagre-knapp").addEventListener("click", lagreOppskrift);
  document.getElementById("eksporter-knapp").addEventListener("click", eksporterJson);

  const kladd = hentAktivKladd();
  if (kladd) {
    _gjenopprettOppskrift(kladd);
  } else {
    leggTilMaltRad();
    leggTilHumleRad();
    beregnOgVisResultat();
  }
}

init();
