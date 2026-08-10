// UI-logikk for den forenklede web-oppskriftsbyggeren.
// Ingen backend: ingrediensdata hentes fra statiske JSON-filer, oppskrifter
// lagres i localStorage. Beregningene selv ligger i calc.js.

const LAGRINGSNOKKEL = "kvernhaug_web_oppskrifter";

let maltData = {};
let humleData = {};
let gjaerData = {};

const maltRaderEl = document.getElementById("malt-rader");
const humleRaderEl = document.getElementById("humle-rader");
const gjaerSelectEl = document.getElementById("gjaer-select");
const attenuationOverrideRad = document.getElementById("attenuation-override-rad");
const attenuationOverrideInput = document.getElementById("attenuation-override");

async function lastIngrediensdata() {
  const [malt, humle, gjaer] = await Promise.all([
    fetch("data/malt.json").then((r) => r.json()),
    fetch("data/humle.json").then((r) => r.json()),
    fetch("data/gjaer.json").then((r) => r.json()),
  ]);
  maltData = malt;
  humleData = humle;
  gjaerData = gjaer;
}

function fyllVelger(selectEl, data, forsteValgTekst) {
  selectEl.innerHTML = "";
  if (forsteValgTekst !== undefined) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = forsteValgTekst;
    selectEl.appendChild(opt);
  }
  for (const [id, entry] of Object.entries(data)) {
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = entry.navn;
    selectEl.appendChild(opt);
  }
}

function leggTilMaltRad(forhandsutfylt) {
  const mal = document.getElementById("malt-rad-mal");
  const rad = mal.content.firstElementChild.cloneNode(true);
  const velger = rad.querySelector(".malt-velger");
  fyllVelger(velger, maltData);
  if (forhandsutfylt) {
    velger.value = forhandsutfylt.id;
    rad.querySelector(".malt-mengde").value = forhandsutfylt.mengde;
  }
  rad.querySelector(".fjern-knapp").addEventListener("click", () => {
    rad.remove();
    beregnOgVisResultat();
  });
  rad.addEventListener("input", beregnOgVisResultat);
  maltRaderEl.appendChild(rad);
  beregnOgVisResultat();
}

function leggTilHumleRad(forhandsutfylt) {
  const mal = document.getElementById("humle-rad-mal");
  const rad = mal.content.firstElementChild.cloneNode(true);
  const velger = rad.querySelector(".humle-velger");
  fyllVelger(velger, humleData);
  if (forhandsutfylt) {
    velger.value = forhandsutfylt.id;
    rad.querySelector(".humle-gram").value = forhandsutfylt.gram;
    rad.querySelector(".humle-tid").value = forhandsutfylt.tid;
  }
  rad.querySelector(".fjern-knapp").addEventListener("click", () => {
    rad.remove();
    beregnOgVisResultat();
  });
  rad.addEventListener("input", beregnOgVisResultat);
  humleRaderEl.appendChild(rad);
  beregnOgVisResultat();
}

function lesMaltRader() {
  return [...maltRaderEl.querySelectorAll(".ingrediens-rad")]
    .map((rad) => ({
      id: rad.querySelector(".malt-velger").value,
      mengde: parseFloat(rad.querySelector(".malt-mengde").value) || 0,
    }))
    .filter((m) => m.id);
}

function lesHumleRader() {
  return [...humleRaderEl.querySelectorAll(".ingrediens-rad")]
    .map((rad) => ({
      id: rad.querySelector(".humle-velger").value,
      gram: parseFloat(rad.querySelector(".humle-gram").value) || 0,
      tid: parseFloat(rad.querySelector(".humle-tid").value) || 0,
    }))
    .filter((h) => h.id);
}

function hentUtgjaering() {
  const gjaerId = gjaerSelectEl.value;
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
}

function samleOppskrift() {
  return {
    navn: document.getElementById("oppskrift-navn").value.trim() || "Uten navn",
    volum: parseFloat(document.getElementById("batch-volum").value) || 0,
    effektivitet: parseFloat(document.getElementById("effektivitet").value) || 0,
    malt: lesMaltRader(),
    humle: lesHumleRader(),
    gjaerId: gjaerSelectEl.value || null,
    attenuationOverride: gjaerSelectEl.value ? null : parseFloat(attenuationOverrideInput.value) || null,
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

  gjaerSelectEl.value = oppskrift.gjaerId || "";
  attenuationOverrideRad.style.display = oppskrift.gjaerId ? "none" : "";
  if (oppskrift.attenuationOverride) {
    attenuationOverrideInput.value = oppskrift.attenuationOverride;
  }

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
  await lastIngrediensdata();

  fyllVelger(gjaerSelectEl, gjaerData, "— egendefinert utgjæring —");
  gjaerSelectEl.addEventListener("change", () => {
    attenuationOverrideRad.style.display = gjaerSelectEl.value ? "none" : "";
    beregnOgVisResultat();
  });

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
