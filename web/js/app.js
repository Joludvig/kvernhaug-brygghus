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
    fetch(KBH_ROOT + "data/malt.json").then((r) => r.json()),
    fetch(KBH_ROOT + "data/humle.json").then((r) => r.json()),
    fetch(KBH_ROOT + "data/gjaer.json").then((r) => r.json()),
    fetch(KBH_ROOT + "data/bjcp_styles.json").then((r) => r.json()),
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
    .sort((a, b) => (rekkefolgeIndeks.get(a.group) - rekkefolgeIndeks.get(b.group)) || a.label.localeCompare(b.label, "no"))
    .map((item) => ({ ...item, group: maltGruppeVisning(item.group) }));
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
    .map((navn) => ({ id: navn, label: stilVisningsnavn(navn) }));
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
  if (statusEl) statusEl.textContent = t(modus === "mester" ? "modus.statusMester" : "modus.statusLaerling");
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
    placeholder: t("builder.malt.comboboxPlaceholder"),
    ariaLabel: t("builder.malt.comboboxAriaLabel"),
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
    _redigerteMaltProsentRader.delete(rad);
    rad.remove();
    oppdaterMaltProsent();
    beregnOgVisResultat();
  });
  rad.querySelector(".malt-mengde").addEventListener("input", () => {
    _redigerteMaltProsentRader.clear();
    oppdaterMaltProsent();
    beregnOgVisResultat();
  });
  rad.querySelector(".malt-pct").addEventListener("input", () => _registrerMaltProsentInput(rad));
  maltRaderEl.appendChild(rad);
  oppdaterMaltProsent();
  beregnOgVisResultat();
}

// ─── Malt kg ↔ % (kun Bryggmester) ────────────────────────────────────────
// Runde 12D -- to tydelige, motsatte redigeringsretninger:
//
// 1) Rediger KG (oppdaterMaltProsent, kalt fra .malt-mengde sin egen
//    "input"-lytter i leggTilMaltRad): kg er fasit, alle % beregnes fra
//    kg/total, live. Tømmer `_redigerteMaltProsentRader` -- gamle
//    %-redigeringer er ikke lenger relevante når kg endres direkte.
//
// 2) Rediger % (_registrerMaltProsentInput, kalt fra .malt-pct sin
//    "input"-lytter): MENS brukeren skriver endres KUN det feltet + sum-
//    indikatoren. Raden legges i settet `_redigerteMaltProsentRader` --
//    FLERE rader kan være manuelt redigert ("låst") samtidig, ikke bare
//    den sist skrevne. Verken kg eller andre %-felt røres her -- det
//    skjer kun i brukMaltProsentfordeling(), kalt av "Bruk
//    prosentfordeling"-knappen. Dette erstatter Runde 12C sin
//    enkelt-rad-låsing (`_sistRedigertMaltProsentRad`), som feilaktig
//    lot knappen overskrive tidligere manuelt satte %-verdier når
//    brukeren redigerte flere rader etter hverandre (f.eks. hovedmalt
//    60% + spesialmalt 20% -- 12C ville da kunne endre 60%-verdien).
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

// Leser DIREKTE fra de synlige .malt-pct-inputfeltene (aldri fra en
// tidligere/lagret verdi) -- dette er akkurat den verdien brukeren ser,
// også midlertidig mens summen f.eks. viser 135,0% før knappetrykk.
function oppdaterMaltProsentSum() {
  const el = document.getElementById("malt-prosent-sum");
  if (!el) return;
  const pcts = [...maltRaderEl.querySelectorAll(".malt-pct")].map((i) => parseFloat(i.value) || 0);
  const sum = pcts.reduce((a, b) => a + b, 0);
  el.textContent = t("builder.malt.prosentSum", { sum: sum.toFixed(1).replace(".", ",") });
  el.classList.toggle("malt-prosent-advarsel", pcts.length > 0 && Math.abs(sum - 100) > 0.5);
}

// Settet av maltrader brukeren har manuelt redigert %-feltet på siden
// forrige kg-redigering / vellykkede prosentfordeling. Kalt på hvert
// tastetrykk i et .malt-pct-felt -- gjør KUN to ting: legger raden i
// settet, og oppdaterer sum-indikatoren fra synlige felt.
let _redigerteMaltProsentRader = new Set();
function _registrerMaltProsentInput(rad) {
  _redigerteMaltProsentRader.add(rad);
  oppdaterMaltProsentSum();
  _visMaltProsentMelding("");
}

function _visMaltProsentMelding(tekst) {
  const el = document.getElementById("malt-prosent-melding");
  if (!el) return;
  el.textContent = tekst;
  el.hidden = !tekst;
}

// Kalt av "Bruk prosentfordeling"-knappen. ALLE manuelt redigerte rader
// (`_redigerteMaltProsentRader`) er brukerens eksplisitte, låste valg og
// endres ALDRI av denne funksjonen. De ØVRIGE (urørte) radene fordeles
// proporsjonalt mellom seg (ut fra sine SYNLIGE %-forhold på
// knappetrykk-tidspunktet) slik at summen blir eksakt 100,0%, og total
// maltvekt (fasit = summen av kg FØR knappetrykk) fordeles på nytt til
// alle rader ut fra den ferdige %-fordelingen.
function brukMaltProsentfordeling() {
  const alleRader = [...maltRaderEl.querySelectorAll(".ingrediens-rad")];
  if (alleRader.length === 0) return;

  const totalKg = alleRader.reduce((sum, r) => sum + (parseFloat(r.querySelector(".malt-mengde").value) || 0), 0);

  // Spesialtilfelle: kun én maltrad -- den er alltid 100%.
  if (alleRader.length === 1) {
    alleRader[0].querySelector(".malt-pct").value = "100.0";
    alleRader[0].querySelector(".malt-mengde").value = Math.round(totalKg * 1000) / 1000;
    _redigerteMaltProsentRader.clear();
    _visMaltProsentMelding("");
    oppdaterMaltProsentSum();
    beregnOgVisResultat();
    return;
  }

  // Kun rader som fortsatt finnes i DOM-et regnes som gyldig låst --
  // beskytter mot stale referanser (f.eks. etter at oppskriften er
  // bygget på nytt fra lagret state/import).
  const laste = alleRader.filter((r) => _redigerteMaltProsentRader.has(r));
  const urorte = alleRader.filter((r) => !_redigerteMaltProsentRader.has(r));

  if (laste.length === 0) {
    _visMaltProsentMelding(t("malt.prosent.tomFelt"));
    return;
  }

  const lastePct = [];
  for (const r of laste) {
    let v = parseFloat(r.querySelector(".malt-pct").value);
    if (!isFinite(v)) {
      _visMaltProsentMelding(t("malt.prosent.ugyldigTall"));
      return;
    }
    if (v > 100) v = 100;
    else if (v < 0) v = 0;
    lastePct.push(v);
  }
  const lastSum = lastePct.reduce((a, b) => a + b, 0);
  const rest = 100 - lastSum;

  // Ingen urørt rad kan absorbere resten -- da må de låste verdiene
  // allerede summere til (tilnærmet) 100% for å kunne aksepteres.
  if (urorte.length === 0) {
    if (Math.abs(rest) >= 0.05) {
      _visMaltProsentMelding(t("malt.prosent.justerTil100", { sum: lastSum.toFixed(1).replace(".", ",") }));
      return;
    }
    laste.forEach((r, i) => { r.querySelector(".malt-pct").value = lastePct[i].toFixed(1); });
    const nyeKg = laste.map((_, i) => Math.round(totalKg * lastePct[i] / 100 * 1000) / 1000);
    laste.forEach((r, i) => { r.querySelector(".malt-mengde").value = nyeKg[i]; });
    _redigerteMaltProsentRader.clear();
    _visMaltProsentMelding("");
    oppdaterMaltProsentSum();
    beregnOgVisResultat();
    return;
  }

  // Låste verdier som til sammen overstiger 100% kan ikke fordeles til
  // urørte rader uten å produsere negative prosenter -- avvis vennlig
  // i stedet for å korrumpere data.
  if (rest < -0.05) {
    _visMaltProsentMelding(t("malt.prosent.overstiger100", { sum: lastSum.toFixed(1).replace(".", ",") }));
    return;
  }
  const restKlemt = Math.max(0, rest);

  // Skriv låste verdier uendret tilbake (etter klemming til [0,100]).
  laste.forEach((r, i) => { r.querySelector(".malt-pct").value = lastePct[i].toFixed(1); });

  // Proporsjonal fordeling av `restKlemt` mellom de urørte radene, ut fra
  // deres synlige %-forhold på knappetrykk-tidspunktet. Siste urørte rad
  // får avrundingsresten i stedet for sin egen avrundede andel, slik at
  // vist sum alltid blir eksakt 100,0%. Ved 0-sum blant de urørte: fordel
  // resten likt (unngår udefinert 0/0-divisjon).
  const gjeldendeUrortePct = urorte.map((r) => parseFloat(r.querySelector(".malt-pct").value) || 0);
  const gjeldendeUrorteSum = gjeldendeUrortePct.reduce((a, b) => a + b, 0);
  const nyeUrortePct = urorte.map((_, i) => {
    if (i === urorte.length - 1) return null; // fylles inn under
    return gjeldendeUrorteSum > 0
      ? gjeldendeUrortePct[i] / gjeldendeUrorteSum * restKlemt
      : restKlemt / urorte.length;
  });
  let sumUtenSiste = 0;
  for (let i = 0; i < urorte.length - 1; i++) {
    nyeUrortePct[i] = Math.round(nyeUrortePct[i] * 10) / 10;
    sumUtenSiste += nyeUrortePct[i];
  }
  nyeUrortePct[urorte.length - 1] = Math.round((restKlemt - sumUtenSiste) * 10) / 10;

  urorte.forEach((r, i) => {
    r.querySelector(".malt-pct").value = nyeUrortePct[i].toFixed(1);
  });

  // Kg beregnes for ALLE rader direkte fra den ferdige %-fordelingen
  // (3 desimaler). En eventuell avrundingsrest korrigeres på en URØRT
  // rad (siste urørte) slik at total maltvekt bevares eksakt -- de
  // manuelt låste radene røres aldri for avrunding.
  const nyeKg = alleRader.map((r) => {
    const lasteIdx = laste.indexOf(r);
    if (lasteIdx !== -1) return Math.round(totalKg * lastePct[lasteIdx] / 100 * 1000) / 1000;
    const urortIdx = urorte.indexOf(r);
    return Math.round(totalKg * nyeUrortePct[urortIdx] / 100 * 1000) / 1000;
  });
  const kgSum = nyeKg.reduce((a, b) => a + b, 0);
  const kgRest = Math.round((totalKg - kgSum) * 1000) / 1000;
  if (kgRest !== 0) {
    const sisteUrortIdx = alleRader.indexOf(urorte[urorte.length - 1]);
    nyeKg[sisteUrortIdx] = Math.round((nyeKg[sisteUrortIdx] + kgRest) * 1000) / 1000;
  }
  alleRader.forEach((r, i) => { r.querySelector(".malt-mengde").value = nyeKg[i]; });

  _redigerteMaltProsentRader.clear();
  _visMaltProsentMelding("");
  oppdaterMaltProsentSum();
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
    placeholder: t("builder.humle.comboboxPlaceholder"),
    ariaLabel: t("builder.humle.comboboxAriaLabel"),
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

// ─── Oppskriftsskalering (kun Bryggmester) ────────────────────────────────
// Portert fra ui/recipe_card.py sin "Skaler oppskrift"-kontrakt: faktor =
// mål-volum / nåværende volum, malt-kg skaleres til 3 desimaler, humle-gram
// til 1 desimal (samme avrunding som desktop). Alt annet -- humletid,
// alfasyre-overstyring, egendefinerte ingredienser, gjærvalg, navn, brygger,
// bryggeri, notater, valgt stil -- er UENDRET, akkurat som desktop (som kun
// itererer malt sitt "mengde"-felt og humle sitt "gram"-felt, aldri gjær
// eller metadata -- se ui/recipe_card.py sin skaler_btn-handler). Ett
// bevisst avvik fra desktop: desktop foreslår automatisk et nytt navn
// ("<navn> - <mål>L batch") som en lagre-sikkerhet mot å overskrive
// originalen ved et uhell -- her beholdes navnet helt uendret, siden
// oppskriftsnavnet eksplisitt skal bevares ved skalering i web. Eksplisitt
// knapp, ingen live-kobling til batch-volum-feltet -- samme prinsipp som
// hindrer en feedback-loop i malt kg/%- og mål-IBU-arbeidet over.
function _fmtVolum(v) {
  return formatVolumeNumber(v);
}

function skalerOppskrift() {
  const volumInput = document.getElementById("batch-volum");
  const naavaerende = parseFloat(volumInput.value) || 0;
  const maalInput = document.getElementById("skaler-maal-volum");
  const maal = parseFloat(maalInput.value) || 0;
  const statusEl = document.getElementById("skaler-status");

  if (naavaerende <= 0 || maal <= 0) {
    statusEl.textContent = t("builder.skaler.statusUgyldig");
    return;
  }
  if (Math.abs(maal - naavaerende) < 0.01) {
    statusEl.textContent = t("builder.skaler.statusUendret");
    return;
  }

  const faktor = maal / naavaerende;
  const bekreftet = confirm(
    t("builder.skaler.confirm", { fra: _fmtVolum(naavaerende), til: _fmtVolum(maal), faktor: faktor.toFixed(3) })
  );
  if (!bekreftet) return;

  for (const rad of maltRaderEl.querySelectorAll(".ingrediens-rad")) {
    const felt = rad.querySelector(".malt-mengde");
    felt.value = Math.round((parseFloat(felt.value) || 0) * faktor * 1000) / 1000;
  }
  for (const rad of humleRaderEl.querySelectorAll(".ingrediens-rad")) {
    const felt = rad.querySelector(".humle-gram");
    felt.value = Math.round((parseFloat(felt.value) || 0) * faktor * 10) / 10;
  }

  volumInput.value = maal;
  maalInput.value = maal;

  _redigerteMaltProsentRader.clear();
  oppdaterMaltProsent();
  beregnOgVisResultat();

  statusEl.textContent = t("builder.skaler.statusFerdig", { fra: _fmtVolum(naavaerende), til: _fmtVolum(maal) });
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
  document.getElementById("identitet-navn").textContent = oppskrift.navn === "Uten navn" ? t("identitet.utenNavn") : oppskrift.navn;
  const bryggerLinje = [oppskrift.brygger, oppskrift.bryggeri].filter(Boolean).join(" · ");
  document.getElementById("identitet-brygger").textContent = bryggerLinje;
  document.getElementById("identitet-brygger").hidden = !bryggerLinje;

  // Kortets identitetsområde skal vise brukerens VALGTE ølstil (samme
  // felt som lagres/eksporteres, oppskrift.valgtStil) -- IKKE den
  // automatiske stilmatchen (sisteStilAnalyse.stil), som fortsatt vises
  // separat i Stilanalyse-seksjonen. Vises uansett om resten av
  // oppskriften er tom, skjules kun når ingen stil er valgt.
  document.getElementById("identitet-stil").textContent = stilVisningsnavn(oppskrift.valgtStil) || "";
  document.getElementById("identitet-stil").hidden = !oppskrift.valgtStil;

  if (oppdaterSmakshjul) oppdaterSmakshjul(sisteBeregning.flavorProfile);
  renderStilPanel();

  // Kun en visningsetikett (ikke et felt brukeren skriver i) -- trygt å
  // oppdatere på hver beregning, i motsetning til #skaler-maal-volum selv.
  document.getElementById("skaler-naavaerende").textContent = t("builder.skaler.naavaerende", { vol: _fmtVolum(oppskrift.volum) });

  // Runde 21B -- leser aktiv utstyrsprofil på hver beregning (samme
  // rimelige kostnad som t()/localStorage ellers i denne funksjonen).
  // Dekker batch-volum-input OG skalering gratis, siden begge ender her.
  _oppdaterUtstyrBatchAdvarsel(oppskrift.volum);

  localStorage.setItem(AKTIV_KLADD_NOKKEL, JSON.stringify(oppskrift));
}

// ─── Utstyrsprofiler (Runde 21B) ────────────────────────────────────────
// UI-laget for web/js/equipment.js sin DOM-frie state. Ingen kobling til
// recipe-beregninger her -- kettleCapacityL/maxRecommendedBatchL er ren
// metadata/veiledning i V1, se equipment.js for full begrunnelse.

let _utstyrRedigererId = null; // null = "nytt utstyr", ellers id på profilen som redigeres

function _utstyrRadDetalj(profil) {
  const deler = [];
  const merke = [profil.manufacturer, profil.model].filter(Boolean).join(" ");
  if (merke) deler.push(merke);
  deler.push(t("utstyr.detaljKapasitet", { kap: formatVolume(profil.kettleCapacityL) }));
  if (profil.maxRecommendedBatchL) {
    deler.push(t("utstyr.detaljMaks", { maks: formatVolume(profil.maxRecommendedBatchL) }));
  }
  return deler.join(" · ");
}

function _byggUtstyrRad(profil, aktivId) {
  const mal = document.getElementById("utstyr-rad-mal");
  const rad = mal.content.cloneNode(true).querySelector(".utstyr-rad");
  const knapp = rad.querySelector(".utstyr-rad-velg");
  const navnEl = rad.querySelector(".utstyr-rad-navn");
  const detaljEl = rad.querySelector(".utstyr-rad-detalj");
  const handlinger = rad.querySelector(".utstyr-rad-handlinger");

  const id = profil ? profil.id : null;
  if (!profil) {
    navnEl.textContent = t("utstyr.ingenProfilValgt");
    detaljEl.textContent = "";
  } else {
    navnEl.textContent = profil.name;
    detaljEl.textContent = _utstyrRadDetalj(profil);
  }

  const erAktiv = id === aktivId;
  rad.classList.toggle("aktiv", erAktiv);
  knapp.setAttribute("aria-pressed", String(erAktiv));
  // Velge en profil aktiverer og lukker modalen med det samme (samme
  // "velg og ferdig"-mønster som #modus-forstegang) -- rediger/slett
  // under skal derimot IKKE lukke, siden brukeren ofte vil fortsette å
  // se på listen etterpå.
  knapp.addEventListener("click", () => {
    aktiverUtstyrsprofil(id);
    _oppdaterUtstyrUI();
    _lukkUtstyrModal();
  });

  if (profil && profil.type === "custom") {
    handlinger.hidden = false;
    rad.querySelector(".utstyr-rad-rediger").addEventListener("click", (e) => {
      e.stopPropagation();
      _apneUtstyrSkjema(profil);
    });
    rad.querySelector(".utstyr-rad-slett").addEventListener("click", (e) => {
      e.stopPropagation();
      _slettUtstyrMedBekreftelse(profil);
    });
  }

  return rad;
}

function _renderUtstyrListe() {
  const liste = document.getElementById("utstyr-liste");
  liste.innerHTML = "";
  const aktivId = lesUtstyrState().activeProfileId;
  liste.appendChild(_byggUtstyrRad(null, aktivId));
  for (const profil of alleUtstyrsprofiler()) {
    liste.appendChild(_byggUtstyrRad(profil, aktivId));
  }
}

function _oppdaterUtstyrChip() {
  const profil = hentAktivUtstyrsprofil();
  document.getElementById("utstyr-velger-navn").textContent = profil ? profil.name : t("utstyr.ingenProfilValgt");
}

// batchVolum sendes inn av beregnOgVisResultat() (allerede kjent der) --
// unngår å lese/parse #batch-volum.value på nytt her.
function _oppdaterUtstyrBatchAdvarsel(batchVolum) {
  const el = document.getElementById("utstyr-batch-advarsel");
  if (!el) return;
  const profil = hentAktivUtstyrsprofil();
  if (!profil || !profil.maxRecommendedBatchL || batchVolum <= profil.maxRecommendedBatchL) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.textContent = t("utstyr.batchAdvarsel", { navn: profil.name, maks: formatVolume(profil.maxRecommendedBatchL) });
  el.hidden = false;
}

function _oppdaterUtstyrUI() {
  _oppdaterUtstyrChip();
  _oppdaterUtstyrBatchAdvarsel(parseFloat(document.getElementById("batch-volum").value) || 0);
}

function _utstyrEscapeHandler(e) {
  if (e.key === "Escape") _lukkUtstyrModal();
}

function _apneUtstyrModal() {
  _renderUtstyrListe();
  _lukkUtstyrSkjema();
  document.getElementById("utstyr-modal-bakteppe").hidden = false;
  document.getElementById("utstyr-modal").hidden = false;
  document.addEventListener("keydown", _utstyrEscapeHandler);
}

function _lukkUtstyrModal() {
  document.getElementById("utstyr-modal-bakteppe").hidden = true;
  document.getElementById("utstyr-modal").hidden = true;
  document.removeEventListener("keydown", _utstyrEscapeHandler);
}

function _apneUtstyrSkjema(profil) {
  _utstyrRedigererId = profil ? profil.id : null;
  document.getElementById("utstyr-skjema-tittel").textContent = profil
    ? t("utstyr.skjemaTittelRediger")
    : t("utstyr.skjemaTittelNytt");
  document.getElementById("utstyr-felt-navn").value = profil ? profil.name : "";
  document.getElementById("utstyr-felt-produsent").value = (profil && profil.manufacturer) || "";
  document.getElementById("utstyr-felt-modell").value = (profil && profil.model) || "";
  document.getElementById("utstyr-felt-kapasitet").value = profil ? profil.kettleCapacityL : "";
  document.getElementById("utstyr-felt-maks").value = (profil && profil.maxRecommendedBatchL) || "";
  document.getElementById("utstyr-felt-notater").value = (profil && profil.notes) || "";
  _visUtstyrSkjemaMelding("");
  document.getElementById("utstyr-skjema").hidden = false;
  document.getElementById("utstyr-felt-navn").focus();
}

function _lukkUtstyrSkjema() {
  const skjema = document.getElementById("utstyr-skjema");
  skjema.hidden = true;
  skjema.reset();
  _utstyrRedigererId = null;
  _visUtstyrSkjemaMelding("");
}

function _visUtstyrSkjemaMelding(tekst) {
  const el = document.getElementById("utstyr-skjema-melding");
  el.textContent = tekst;
  el.hidden = !tekst;
}

function _handleUtstyrSkjemaSubmit(e) {
  e.preventDefault();
  const felter = {
    name: document.getElementById("utstyr-felt-navn").value,
    manufacturer: document.getElementById("utstyr-felt-produsent").value,
    model: document.getElementById("utstyr-felt-modell").value,
    kettleCapacityL: document.getElementById("utstyr-felt-kapasitet").value,
    maxRecommendedBatchL: document.getElementById("utstyr-felt-maks").value,
    notes: document.getElementById("utstyr-felt-notater").value,
  };
  const resultat = _utstyrRedigererId
    ? oppdaterCustomUtstyrsprofil(_utstyrRedigererId, felter)
    : opprettCustomUtstyrsprofil(felter);
  if (!resultat.ok) {
    _visUtstyrSkjemaMelding(resultat.melding);
    return;
  }
  _lukkUtstyrSkjema();
  _renderUtstyrListe();
  _oppdaterUtstyrUI();
}

function _slettUtstyrMedBekreftelse(profil) {
  const bekreftet = confirm(t("utstyr.slettBekreft", { navn: profil.name }));
  if (!bekreftet) return;
  slettCustomUtstyrsprofil(profil.id);
  _renderUtstyrListe();
  _oppdaterUtstyrUI();
}

function initUtstyr() {
  document.getElementById("utstyr-velger-knapp").addEventListener("click", _apneUtstyrModal);
  document.getElementById("utstyr-modal-bakteppe").addEventListener("click", _lukkUtstyrModal);
  document.getElementById("utstyr-modal-lukk").addEventListener("click", _lukkUtstyrModal);
  document.getElementById("utstyr-nytt-knapp").addEventListener("click", () => _apneUtstyrSkjema(null));
  document.getElementById("utstyr-skjema-avbryt").addEventListener("click", _lukkUtstyrSkjema);
  document.getElementById("utstyr-skjema").addEventListener("submit", _handleUtstyrSkjemaSubmit);
  _oppdaterUtstyrChip();
}

// ─── Stilmatch-visning (read-only, høyre panel) ──────────────────────────

function _stilEntryFor(navn) {
  return sisteStilAnalyse.stil_liste.find((s) => s.stil === navn);
}

function _stilKortHtml(s, { visBeskrivelse = false } = {}) {
  const merke = s.bjcp_offisiell === false
    ? `<span class="stil-merke" title="${escHtml(t("stilmatch.ikkeOffisiellTitle"))}">${escHtml(t("stilmatch.ikkeOffisiellBadge"))}</span>`
    : "";
  const detaljer = [];
  for (const m of s.mangler) detaljer.push(`<li class="mangel">❌ ${escHtml(m)}</li>`);
  for (const o of s.onsket_sensorisk) detaljer.push(`<li class="onsket">💭 ${escHtml(o)}</li>`);
  const detaljerHtml = detaljer.length
    ? `<details class="stil-detaljer"><summary>${escHtml(t("stilmatch.seHvaSomMangler"))}</summary><ul>${detaljer.join("")}</ul></details>`
    : `<p class="stil-full-match">${escHtml(t("stilanalyse.innenforAlle"))}</p>`;

  return `
    <div class="stil-kort">
      <div class="stil-kort-topp">
        <span class="stil-kort-navn">${escHtml(stilVisningsnavn(s.stil))}</span>
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
    container.innerHTML = `<p class="stil-veiledning-innenfor">${escHtml(t("stilanalyse.innenforOmrade", { stil: stilVisningsnavn(stilNavn) }))}</p>`;
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
    headlineNavn.textContent = stilVisningsnavn(a.stil);

    const autoContainer = document.getElementById("stil-veiledning-auto");
    if (a.stil === "Kreativt Brygg") {
      headlineInfo.textContent = t("stilanalyse.ingenTreff");
      autoContainer.innerHTML = "";
    } else {
      const entry = _stilEntryFor(a.stil);
      headlineInfo.innerHTML = entry && entry.bjcp_offisiell === false
        ? `<span class="stil-merke">${escHtml(t("stilmatch.ikkeOffisiellHeadline"))}</span>`
        : "";
      _renderVeiledning(autoContainer, entry, a.stil);
    }

    document.getElementById("bu-gu-tekst").textContent = t("stilanalyse.buGu", { verdi: a.bu_gu.toFixed(2) });

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
      : `<p class="hjelpetekst">${escHtml(t("stilmatch.ingenAlternativer"))}</p>`;
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
    veiledningEl.innerHTML = `<p class="hjelpetekst">${escHtml(t("stilanalyse.leggTilForMatch", { stil: stilVisningsnavn(valgtNavn) }))}</p>`;
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
  status.textContent = t("oppskrift.lagretStatus", { navn: visningsnavn(oppskrift.navn) });
}

// Gjenoppretter en oppskrift (fra aktiv kladd, en lagret oppskrift, eller en
// importert JSON-fil) inn i skjemaet.
function _gjenopprettOppskrift(oppskrift) {
  // Runde 18A -- den interne sentinelen "Uten navn" (satt av samleOppskrift()
  // når feltet står tomt) skal ALDRI settes som selve input-verdien -- det
  // ville vist den norske sentinelteksten ordrett også i EN. Feltet skal i
  // stedet stå tomt, akkurat som en fersk/blank oppskrift, slik at den
  // allerede lokaliserte placeholder-teksten (builder.grunndata.
  // olnavnPlaceholder) vises naturlig. Et faktisk brukerskrevet navn --
  // inkl. om det tilfeldigvis er nøyaktig "Uten navn" -- settes uendret.
  document.getElementById("oppskrift-navn").value = (oppskrift.navn && oppskrift.navn !== "Uten navn") ? oppskrift.navn : "";
  document.getElementById("brygger-navn").value = oppskrift.brygger || "";
  document.getElementById("bryggeri-navn").value = oppskrift.bryggeri || "";
  document.getElementById("oppskrift-notater").value = oppskrift.notater || "";
  document.getElementById("batch-volum").value = oppskrift.volum;
  document.getElementById("effektivitet").value = oppskrift.effektivitet || 75;

  _redigerteMaltProsentRader.clear();
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

// ─── Portabel .kbhrecipe-fil (Runde 13) ──────────────────────────────────
// Primær lagrings-/delingsflyt for vanlige brukere -- se js/kbhrecipe.js
// for selve filformatet/parsingen. Rå JSON (eksporterJson over) er kun
// beholdt som et nedgradert "Avansert"-alternativ i markup-et.

function lagreOppskriftsfil() {
  const oppskrift = samleOppskrift();
  lastNedKbhRecipeFil(oppskrift);
  document.getElementById("lagre-status").textContent =
    t("oppskrift.lagreFilStatus", { filnavn: tryggFilnavn(oppskrift.navn) });
}

// Blank oppskrift -- SAMME autoritative default-form som init() sin
// "ingen aktiv kladd"-oppstart (leggTilMaltRad()/leggTilHumleRad() med
// tomme rader, batch-volum 20 L, effektivitet 75 %, ingen gjær/stil).
// Ingen parallell "tom oppskrift"-modell -- kun et eksplisitt kall til
// den eksisterende _gjenopprettOppskrift()-kontrakten.
function _blankOppskrift() {
  return {
    navn: "", brygger: "", bryggeri: "", notater: "",
    volum: 20, effektivitet: 75,
    malt: [], humle: [],
    gjaerId: null, gjaerCustom: null, attenuationOverride: 75,
    valgtStil: null,
  };
}

// Runde 13A -- eksplisitt "start på nytt"-handling. Brygger/bryggeri er
// brukerpreferanser (se forhandsutfyllIdentitetsPreferanse()), ikke
// oppskriftsdata -- de nullstilles derfor av _gjenopprettOppskrift()
// (som _blankOppskrift() ber om) og fylles umiddelbart inn igjen fra
// IDENTITET_NOKKEL, akkurat som ved en helt fersk sideinnlasting uten
// aktiv kladd. Bekrefter kun dersom aktiv oppskrift faktisk har
// meningsfullt innhold (oppskriftHarInnhold(), se kbhrecipe.js).
function nyOppskrift() {
  if (oppskriftHarInnhold(samleOppskrift())) {
    const ok = confirm(t("oppskrift.nyConfirm"));
    if (!ok) return;
  }
  _gjenopprettOppskrift(_blankOppskrift());
  forhandsutfyllIdentitetsPreferanse();
  beregnOgVisResultat();
  document.getElementById("skaler-maal-volum").value = document.getElementById("batch-volum").value;
  document.getElementById("lagre-status").textContent = t("oppskrift.nyStatus");
}

function apneOppskriftsfil(fil) {
  const status = document.getElementById("lagre-status");
  const reader = new FileReader();
  reader.onload = () => {
    const resultat = parseKbhRecipeInnhold(reader.result);
    if (!resultat.ok) {
      status.textContent = resultat.melding;
      return;
    }
    if (oppskriftHarInnhold(samleOppskrift())) {
      const ok = confirm(t("oppskrift.apneConfirm"));
      if (!ok) return;
    }
    _gjenopprettOppskrift(resultat.oppskrift);
    status.textContent = t("oppskrift.apnetStatus");
  };
  reader.onerror = () => {
    status.textContent = t("oppskrift.lesefeil");
  };
  reader.readAsText(fil);
}

async function init() {
  await lastData();
  initModus();
  initHjelp();
  initUtstyr();

  oppdaterSmakshjul = initSmakshjul(document.getElementById("smakshjul-container"), SMAKS_KATEGORIER);

  const gjaerMount = document.getElementById("gjaer-velger-mount");
  gjaerCombobox = new Combobox({
    items: gjaerItems(),
    placeholder: t("builder.gjaer.comboboxPlaceholder"),
    ariaLabel: t("builder.gjaer.comboboxAriaLabel"),
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
    placeholder: t("builder.stilvalg.comboboxPlaceholder"),
    ariaLabel: t("builder.stilvalg.comboboxAriaLabel"),
    onSelect: () => { renderStilManuell(); beregnOgVisResultat(); },
  });
  stilMount.replaceWith(stilCombobox.el);

  document.getElementById("legg-til-malt").addEventListener("click", () => leggTilMaltRad());
  document.getElementById("legg-til-humle").addEventListener("click", () => leggTilHumleRad());
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

  document.getElementById("ny-oppskrift-knapp").addEventListener("click", nyOppskrift);
  document.getElementById("lagre-knapp").addEventListener("click", lagreOppskrift);
  document.getElementById("eksporter-knapp").addEventListener("click", eksporterJson);
  document.getElementById("lagre-fil-knapp").addEventListener("click", lagreOppskriftsfil);
  const apneFilInput = document.getElementById("apne-fil-input");
  document.getElementById("apne-fil-knapp").addEventListener("click", () => apneFilInput.click());
  apneFilInput.addEventListener("change", () => {
    if (apneFilInput.files[0]) apneOppskriftsfil(apneFilInput.files[0]);
    apneFilInput.value = "";
  });
  document.getElementById("skaler-knapp").addEventListener("click", skalerOppskrift);
  document.getElementById("malt-bruk-prosent-knapp").addEventListener("click", brukMaltProsentfordeling);

  const kladd = hentAktivKladd();
  if (kladd) {
    _gjenopprettOppskrift(kladd);
  } else {
    leggTilMaltRad();
    leggTilHumleRad();
    beregnOgVisResultat();
  }
  // Skaler-til-feltet foreslår gjeldende volum som startpunkt (som desktop-
  // appens number_input(value=ctx["volum"])) -- oppdateres kun her og etter
  // vellykket skalering, ALDRI på hvert tastetrykk i beregnOgVisResultat(),
  // slik at vi ikke overskriver brukerens pågående inntasting i feltet.
  document.getElementById("skaler-maal-volum").value = document.getElementById("batch-volum").value;
}

// Runde 14 -- språkbytte skal aldri miste arbeid eller reloade siden (se
// i18n.js). data-i18n-attributtene i HTML-en oppdateres allerede av
// i18n.js sin egen applyI18n(); denne lytteren tar seg KUN av det
// data-i18n ikke når: allerede-konstruerte combobox-widgeter (placeholder/
// aria-label lever inne i widgetens egne DOM-noder, og malt/stil sine
// item-lister/valgt visningstekst må bygges på nytt fra maltData/
// bjcpStyles), smakshjulets statiske akse-etiketter (tegnes kun én gang av
// initSmakshjul), og selve resultatberegningen (stilmatch-/veilednings-
// tekstene genereres på nytt av style.js/veiledning.js sine t()-kall).
// Ingen oppskriftsdata røres -- kun visning.
window.addEventListener("kvernhaug:sprakendret", () => {
  // Runde 15B.0 -- #sidemeny-modus-status fikk et data-i18n (for pre-
  // render-crawlbarhet av Bryggelærling-standardteksten), men den er
  // modus-avhengig -- applyI18n() alene ville alltid tvunget den tilbake
  // til laerling-teksten. settModus() med GJELDENDE modus (lest fra
  // body-klassen settModus selv setter) gjenoppretter riktig tekst uten
  // å røre modus-state.
  settModus(document.body.classList.contains("modus-mester") ? "mester" : "laerling");
  for (const rad of maltRaderEl.querySelectorAll(".ingrediens-rad")) {
    const cb = rad._combobox;
    if (!cb) continue;
    cb.items = maltItems();
    cb.inputEl.placeholder = t("builder.malt.comboboxPlaceholder");
    cb.inputEl.setAttribute("aria-label", t("builder.malt.comboboxAriaLabel"));
  }
  for (const rad of humleRaderEl.querySelectorAll(".ingrediens-rad")) {
    const cb = rad._combobox;
    if (!cb) continue;
    cb.inputEl.placeholder = t("builder.humle.comboboxPlaceholder");
    cb.inputEl.setAttribute("aria-label", t("builder.humle.comboboxAriaLabel"));
  }
  if (gjaerCombobox) {
    gjaerCombobox.inputEl.placeholder = t("builder.gjaer.comboboxPlaceholder");
    gjaerCombobox.inputEl.setAttribute("aria-label", t("builder.gjaer.comboboxAriaLabel"));
  }
  if (stilCombobox) {
    stilCombobox.items = stilItems();
    stilCombobox.inputEl.placeholder = t("builder.stilvalg.comboboxPlaceholder");
    stilCombobox.inputEl.setAttribute("aria-label", t("builder.stilvalg.comboboxAriaLabel"));
    if (stilCombobox.getValue()) stilCombobox.setValue(stilCombobox.getValue());
  }
  oppdaterSmakshjul = initSmakshjul(document.getElementById("smakshjul-container"), SMAKS_KATEGORIER);
  oppdaterMaltProsentSum();
  beregnOgVisResultat();
});

init();
