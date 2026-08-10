// UI-logikk for den forenklede web-oppskriftsbyggeren.
// Ingen backend: ingrediens-/stildata hentes fra statiske JSON-filer,
// oppskrifter lagres i localStorage. Beregningene selv ligger i calc.js
// (OG/FG/ABV/IBU/EBC), flavor.js (smaksprofil) og style.js (BJCP-matching).

const LAGRINGSNOKKEL = "kvernhaug_web_oppskrifter";

let maltData = {};
let humleData = {};
let gjaerData = {};
let bjcpStyles = {};
let sisteStilAnalyse = null;

const maltRaderEl = document.getElementById("malt-rader");
const humleRaderEl = document.getElementById("humle-rader");
const attenuationOverrideRad = document.getElementById("attenuation-override-rad");
const attenuationOverrideInput = document.getElementById("attenuation-override");

let gjaerCombobox = null;
let stilCombobox = null;

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

function itemsFra(data) {
  return Object.entries(data).map(([id, v]) => ({ id, label: v.navn }));
}

function stilItems() {
  return Object.keys(bjcpStyles)
    .sort((a, b) => a.localeCompare(b, "no"))
    .map((navn) => ({ id: navn, label: navn }));
}

function leggTilMaltRad(forhandsutfylt) {
  const mal = document.getElementById("malt-rad-mal");
  const rad = mal.content.firstElementChild.cloneNode(true);
  const mount = rad.querySelector(".malt-velger-mount");

  const cb = new Combobox({
    items: itemsFra(maltData),
    placeholder: "Søk etter malt …",
    ariaLabel: "Velg malt",
    onSelect: beregnOgVisResultat,
  });
  mount.replaceWith(cb.el);
  rad._combobox = cb;

  if (forhandsutfylt) {
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

function leggTilHumleRad(forhandsutfylt) {
  const mal = document.getElementById("humle-rad-mal");
  const rad = mal.content.firstElementChild.cloneNode(true);
  const mount = rad.querySelector(".humle-velger-mount");

  const cb = new Combobox({
    items: itemsFra(humleData),
    placeholder: "Søk etter humle …",
    ariaLabel: "Velg humle",
    onSelect: beregnOgVisResultat,
  });
  mount.replaceWith(cb.el);
  rad._combobox = cb;

  if (forhandsutfylt) {
    cb.setValue(forhandsutfylt.id);
    rad.querySelector(".humle-gram").value = forhandsutfylt.gram;
    rad.querySelector(".humle-tid").value = forhandsutfylt.tid;
  }

  rad.querySelector(".fjern-knapp").addEventListener("click", () => {
    rad.remove();
    beregnOgVisResultat();
  });
  rad.querySelector(".humle-gram").addEventListener("input", beregnOgVisResultat);
  rad.querySelector(".humle-tid").addEventListener("input", beregnOgVisResultat);
  humleRaderEl.appendChild(rad);
  beregnOgVisResultat();
}

function lesMaltRader() {
  return [...maltRaderEl.querySelectorAll(".ingrediens-rad")]
    .map((rad) => ({
      id: rad._combobox.getValue(),
      mengde: parseFloat(rad.querySelector(".malt-mengde").value) || 0,
    }))
    .filter((m) => m.id);
}

function lesHumleRader() {
  return [...humleRaderEl.querySelectorAll(".ingrediens-rad")]
    .map((rad) => ({
      id: rad._combobox.getValue(),
      gram: parseFloat(rad.querySelector(".humle-gram").value) || 0,
      tid: parseFloat(rad.querySelector(".humle-tid").value) || 0,
    }))
    .filter((h) => h.id);
}

function hentUtgjaering() {
  const gjaerId = gjaerCombobox.getValue();
  if (gjaerId && gjaerData[gjaerId]) {
    return gjaerData[gjaerId].attenuation;
  }
  const manuell = parseFloat(attenuationOverrideInput.value);
  return isFinite(manuell) ? manuell / 100 : 0.75;
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
  const gjaerId = gjaerCombobox ? gjaerCombobox.getValue() : null;

  const og = beregnOG(maltRader, maltData, volum, effektivitet);
  const ebc = beregnEBC(maltRader, maltData, volum);
  const { fg, abv } = beregnFgOgAbv(og, hentUtgjaering());
  const ibu = beregnTotalIBU(humleRader, humleData, volum, og);

  document.getElementById("res-og").textContent = og.toFixed(3);
  document.getElementById("res-fg").textContent = fg.toFixed(3);
  document.getElementById("res-abv").textContent = abv.toFixed(1).replace(".", ",") + " %";
  document.getElementById("res-ibu").textContent = Math.round(ibu);
  document.getElementById("res-ebc").textContent = Math.round(ebc);
  document.getElementById("ebc-swatch").style.backgroundColor = ebcTilFarge(ebc);

  const flavorProfile = beregnSmaksprofil(maltRader, maltData, humleRader, humleData, ibu, gjaerId, gjaerData);
  const recipe = {
    malts: maltRader, hops: humleRader, yeast: gjaerId,
    stats: { og, fg, ibu, ebc, abv }, flavor_profile: flavorProfile,
  };
  sisteStilAnalyse = analyserStilOgBalanse(recipe, bjcpStyles);
  renderStilPanel();
}

// ─── Stilmatch-visning ──────────────────────────────────────────────────

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

function renderStilPanel() {
  const a = sisteStilAnalyse;
  if (!a) return;

  const headlineNavn = document.getElementById("stil-headline-navn");
  const headlineInfo = document.getElementById("stil-headline-info");
  headlineNavn.textContent = a.stil;

  if (a.stil === "Kreativt Brygg") {
    headlineInfo.textContent = "Ingen stil i biblioteket treffer godt nok ennå — juster ingrediensene eller se nærliggende stiler under.";
  } else {
    const entry = _stilEntryFor(a.stil);
    headlineInfo.innerHTML = entry && entry.bjcp_offisiell === false
      ? '<span class="stil-merke">🏺 Kvernhaug/historisk kategori — ikke en offisiell BJCP-stil</span>'
      : "";
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
  const valgtNavn = stilCombobox ? stilCombobox.getValue() : null;
  if (!valgtNavn || !sisteStilAnalyse) {
    resultatEl.innerHTML = "";
    return;
  }
  const entry = _stilEntryFor(valgtNavn);
  resultatEl.innerHTML = entry ? _stilKortHtml(entry, { visBeskrivelse: true }) : "";
}

// ─── Lagring / lasting ──────────────────────────────────────────────────

function samleOppskrift() {
  return {
    navn: document.getElementById("oppskrift-navn").value.trim() || "Uten navn",
    volum: parseFloat(document.getElementById("batch-volum").value) || 0,
    effektivitet: parseFloat(document.getElementById("effektivitet").value) || 0,
    malt: lesMaltRader(),
    humle: lesHumleRader(),
    gjaerId: gjaerCombobox.getValue() || null,
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

function lastInnOppskrift(navn) {
  const alle = hentLagredeOppskrifter();
  const oppskrift = alle[navn];
  if (!oppskrift) return;

  document.getElementById("oppskrift-navn").value = oppskrift.navn;
  document.getElementById("batch-volum").value = oppskrift.volum;
  document.getElementById("effektivitet").value = oppskrift.effektivitet;

  maltRaderEl.innerHTML = "";
  oppskrift.malt.forEach((m) => leggTilMaltRad(m));
  if (oppskrift.malt.length === 0) leggTilMaltRad();

  humleRaderEl.innerHTML = "";
  oppskrift.humle.forEach((h) => leggTilHumleRad(h));
  if (oppskrift.humle.length === 0) leggTilHumleRad();

  if (oppskrift.gjaerId) gjaerCombobox.setValue(oppskrift.gjaerId);
  else gjaerCombobox.clear();
  attenuationOverrideRad.style.display = oppskrift.gjaerId ? "none" : "";
  if (oppskrift.attenuationOverride) {
    attenuationOverrideInput.value = oppskrift.attenuationOverride;
  }

  if (oppskrift.valgtStil) stilCombobox.setValue(oppskrift.valgtStil);
  else stilCombobox.clear();

  beregnOgVisResultat();
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

async function init() {
  await lastData();

  const gjaerMount = document.getElementById("gjaer-velger-mount");
  gjaerCombobox = new Combobox({
    items: itemsFra(gjaerData),
    placeholder: "Søk etter gjær …",
    ariaLabel: "Velg gjær",
    onSelect: () => {
      attenuationOverrideRad.style.display = gjaerCombobox.getValue() ? "none" : "";
      beregnOgVisResultat();
    },
  });
  gjaerMount.replaceWith(gjaerCombobox.el);

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

  leggTilMaltRad();
  leggTilHumleRad();
  visLagredeOppskrifter();
  beregnOgVisResultat();
}

init();
