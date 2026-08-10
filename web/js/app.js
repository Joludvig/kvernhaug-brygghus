// UI-logikk for Kvernhaug Brygghus sin web-oppskriftsbygger.
// Ingen backend: ingrediens-/stildata hentes fra statiske JSON-filer,
// oppskrifter lagres i localStorage. Beregningene selv ligger i calc.js
// (OG/FG/ABV/IBU/EBC), flavor.js (smaksprofil), radar.js (smakshjul),
// style.js (stilmatch) og veiledning.js (vennlig stilveiledning).
//
// Egendefinerte ingredienser og alfa-overstyring løses UTEN å røre calc.js/
// flavor.js/style.js: for hver beregning bygges et "effektivt" oppslags-
// objekt ({...biblioteket, [egen_id]: egendefinertData}) som sendes inn
// akkurat som det vanlige biblioteket -- se _effektiveDatasett().

const LAGRINGSNOKKEL = "kvernhaug_web_oppskrifter";
const MODUS_NOKKEL = "kvernhaug_web_modus";

let maltData = {};
let humleData = {};
let gjaerData = {};
let bjcpStyles = {};
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
function maltItems() {
  return Object.entries(maltData).map(([id, v]) => ({
    id,
    label: v.navn,
    search: [v.navn, v.produsent, v.kategori].filter(Boolean).join(" ").toLowerCase(),
  }));
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

function settModus(modus) {
  document.body.classList.toggle("modus-laerling", modus === "laerling");
  document.body.classList.toggle("modus-mester", modus === "mester");
  document.getElementById("modus-laerling-knapp").setAttribute("aria-pressed", String(modus === "laerling"));
  document.getElementById("modus-mester-knapp").setAttribute("aria-pressed", String(modus === "mester"));
  localStorage.setItem(MODUS_NOKKEL, modus);
}

function initModus() {
  const lagret = localStorage.getItem(MODUS_NOKKEL);
  settModus(lagret === "mester" ? "mester" : "laerling");
  document.getElementById("modus-laerling-knapp").addEventListener("click", () => settModus("laerling"));
  document.getElementById("modus-mester-knapp").addEventListener("click", () => settModus("mester"));
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
    beregnOgVisResultat();
  });
  rad.querySelector(".malt-mengde").addEventListener("input", beregnOgVisResultat);
  maltRaderEl.appendChild(rad);
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
  rad.querySelector(".humle-tid").addEventListener("input", beregnOgVisResultat);
  alfaInput.addEventListener("input", beregnOgVisResultat);
  humleRaderEl.appendChild(rad);
  beregnOgVisResultat();
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

function hentUtgjaering() {
  const gjaerId = gjaerCombobox.getValue();
  if (gjaerId && gjaerData[gjaerId]) return gjaerData[gjaerId].attenuation;
  const manuell = parseFloat(attenuationOverrideInput.value);
  return isFinite(manuell) ? manuell / 100 : 0.75;
}

// Bygger "effektive" oppslagsobjekter (bibliotek + egendefinerte/overstyrte
// entries) slik at calc.js/flavor.js/style.js kan brukes helt uendret.
function _effektiveDatasett(maltRader, humleRader) {
  const effMalt = { ...maltData };
  for (const m of maltRader) if (m.custom) effMalt[m.id] = m.custom;

  const effHumle = { ...humleData };
  for (const h of humleRader) {
    if (h.custom) effHumle[h.id] = h.custom;
    else if (h.alfaOverride != null && humleData[h.id]) effHumle[h.id] = { ...humleData[h.id], alfa: h.alfaOverride };
  }

  const effGjaer = { ...gjaerData };
  let gjaerId = gjaerCombobox.getValue();
  const gjaerCustom = _lesGjaerEgendefinert();
  if (!gjaerId && gjaerCustom) {
    gjaerId = "egendefinert_gjaer";
    effGjaer[gjaerId] = gjaerCustom;
  }

  return { effMalt, effHumle, effGjaer, gjaerId };
}

function ebcTilFarge(ebc) {
  // Grov, kun-visuell EBC->RGB-tilnærming for fargeswatch (ikke en presis fargemodell).
  const clamped = Math.max(2, Math.min(ebc, 80));
  const lysstyrke = 92 - (clamped / 80) * 72;
  return `hsl(38, 75%, ${lysstyrke}%)`;
}

function beregnOgVisResultat() {
  const volum = parseFloat(document.getElementById("batch-volum").value) || 0;
  const effektivitet = (parseFloat(document.getElementById("effektivitet").value) || 0) / 100;

  const maltRader = lesMaltRader();
  const humleRader = lesHumleRader();
  const { effMalt, effHumle, effGjaer, gjaerId } = _effektiveDatasett(maltRader, humleRader);

  const og = beregnOG(maltRader, effMalt, volum, effektivitet);
  const ebc = beregnEBC(maltRader, effMalt, volum);
  const { fg, abv } = beregnFgOgAbv(og, hentUtgjaering());
  const ibu = beregnTotalIBU(humleRader, effHumle, volum, og);

  document.getElementById("res-og").textContent = og.toFixed(3);
  document.getElementById("res-fg").textContent = fg.toFixed(3);
  document.getElementById("res-abv").textContent = abv.toFixed(1).replace(".", ",") + " %";
  document.getElementById("res-ibu").textContent = Math.round(ibu);
  document.getElementById("res-ebc").textContent = Math.round(ebc);
  document.getElementById("ebc-swatch").style.backgroundColor = ebcTilFarge(ebc);

  const flavorProfile = beregnSmaksprofil(maltRader, effMalt, humleRader, effHumle, ibu, gjaerId, effGjaer);
  if (oppdaterSmakshjul) oppdaterSmakshjul(flavorProfile);
  const recipe = {
    malts: maltRader, hops: humleRader, yeast: gjaerId,
    stats: { og, fg, ibu, ebc, abv }, flavor_profile: flavorProfile,
  };
  sisteStilAnalyse = analyserStilOgBalanse(recipe, bjcpStyles);
  renderStilPanel();
}

// ─── Stilmatch-visning (Bryggmester: tekniske detaljer) ──────────────────

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

function escHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
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
  if (!a) return;

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
  const entry = _stilEntryFor(valgtNavn);
  resultatEl.innerHTML = entry ? _stilKortHtml(entry, { visBeskrivelse: true }) : "";
  _renderVeiledning(veiledningEl, entry, valgtNavn);
}

// ─── Lagring / lasting / eksport / import ────────────────────────────────

function samleOppskrift() {
  return {
    navn: document.getElementById("oppskrift-navn").value.trim() || "Uten navn",
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
  status.textContent = `Lagret "${oppskrift.navn}" i nettleseren.`;
  visLagredeOppskrifter();
}

function slettOppskrift(navn) {
  const alle = hentLagredeOppskrifter();
  delete alle[navn];
  localStorage.setItem(LAGRINGSNOKKEL, JSON.stringify(alle));
  visLagredeOppskrifter();
}

// Gjenoppretter en oppskrift (fra localStorage ELLER en importert JSON-fil)
// inn i skjemaet -- delt av lastInnOppskrift() og importerJson().
function _gjenopprettOppskrift(oppskrift) {
  document.getElementById("oppskrift-navn").value = oppskrift.navn || "";
  document.getElementById("batch-volum").value = oppskrift.volum;
  document.getElementById("effektivitet").value = oppskrift.effektivitet;

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

function lastInnOppskrift(navn) {
  const alle = hentLagredeOppskrifter();
  const oppskrift = alle[navn];
  if (!oppskrift) return;
  _gjenopprettOppskrift(oppskrift);
}

function visLagredeOppskrifter() {
  const alle = hentLagredeOppskrifter();
  const navn = Object.keys(alle);
  const listeEl = document.getElementById("oppskrift-liste");
  const meldingEl = document.getElementById("ingen-oppskrifter-melding");
  listeEl.innerHTML = "";

  meldingEl.style.display = navn.length === 0 ? "" : "none";

  for (const n of navn) {
    const li = document.createElement("li");

    const lastKnapp = document.createElement("button");
    lastKnapp.type = "button";
    lastKnapp.textContent = n;
    lastKnapp.className = "oppskrift-last-knapp";
    lastKnapp.addEventListener("click", () => lastInnOppskrift(n));

    const slettKnapp = document.createElement("button");
    slettKnapp.type = "button";
    slettKnapp.textContent = "✕";
    slettKnapp.className = "fjern-knapp";
    slettKnapp.title = "Slett";
    slettKnapp.addEventListener("click", () => slettOppskrift(n));

    li.appendChild(lastKnapp);
    li.appendChild(slettKnapp);
    listeEl.appendChild(li);
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

function importerJsonFil(fil) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const oppskrift = JSON.parse(reader.result);
      _gjenopprettOppskrift(oppskrift);
      document.getElementById("lagre-status").textContent = `Importerte "${oppskrift.navn || "oppskrift"}" fra fil.`;
    } catch (e) {
      document.getElementById("lagre-status").textContent = "Kunne ikke lese filen — er det en gyldig, eksportert oppskrift-JSON?";
    }
  };
  reader.readAsText(fil);
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
    placeholder: "Søk etter ølstil …",
    ariaLabel: "Velg ølstil å sjekke mot",
    onSelect: renderStilManuell,
  });
  stilMount.replaceWith(stilCombobox.el);

  document.getElementById("legg-til-malt").addEventListener("click", () => leggTilMaltRad());
  document.getElementById("legg-til-humle").addEventListener("click", () => leggTilHumleRad());
  document.getElementById("batch-volum").addEventListener("input", beregnOgVisResultat);
  document.getElementById("effektivitet").addEventListener("input", beregnOgVisResultat);
  attenuationOverrideInput.addEventListener("input", beregnOgVisResultat);

  document.getElementById("lagre-knapp").addEventListener("click", lagreOppskrift);
  document.getElementById("skriv-ut-knapp").addEventListener("click", () => window.print());
  document.getElementById("eksporter-knapp").addEventListener("click", eksporterJson);

  const importerFil = document.getElementById("importer-fil");
  document.getElementById("importer-knapp").addEventListener("click", () => importerFil.click());
  importerFil.addEventListener("change", () => {
    if (importerFil.files[0]) importerJsonFil(importerFil.files[0]);
    importerFil.value = "";
  });

  leggTilMaltRad();
  leggTilHumleRad();
  visLagredeOppskrifter();
  beregnOgVisResultat();
}

init();
