// Importer oppskrift-siden: to metoder (fil / tekst), begge sender brukeren
// videre til byggeren via AKTIV_KLADD_NOKKEL -- samme hand-off-mekanisme
// som "Åpne i byggeren" på Mine oppskrifter-siden og byggerens egen
// autolagrede kladd (se app.js). Tekstimporten porter
// modules/recipe_importer.py sin kontrakt, se web/js/recipe_importer.js.

const AKTIV_KLADD_NOKKEL = "kvernhaug_web_aktiv_kladd";

let maltData = {}, humleData = {}, gjaerData = {};
let sisteTreff = null;

// Runde 13A -- samme beskyttelse som byggerens "Åpne oppskriftsfil"
// (app.js::apneOppskriftsfil): bekreft før en eksisterende, meningsfull
// aktiv kladd overskrives. Leser AKTIV_KLADD_NOKKEL direkte (denne siden
// har ingen egen live DOM-oppskrift) -- samme objektform som
// samleOppskrift() alltid skriver dit, se oppskriftHarInnhold() i
// kbhrecipe.js. Gjelder BÅDE fil- og tekstimport, som begge går via
// denne ene hand-off-funksjonen.
function _aktivKladdHarInnhold() {
  try {
    return oppskriftHarInnhold(JSON.parse(localStorage.getItem(AKTIV_KLADD_NOKKEL)));
  } catch {
    return false;
  }
}

function apneIByggeren(oppskrift) {
  if (_aktivKladdHarInnhold()) {
    const ok = confirm("Åpne denne oppskriften? Den aktive oppskriften blir erstattet.");
    if (!ok) return;
  }
  localStorage.setItem(AKTIV_KLADD_NOKKEL, JSON.stringify(oppskrift));
  window.location.href = "index.html";
}

// ─── Fil-import ─────────────────────────────────────────────────────────

function importerJsonFil(fil) {
  const status = document.getElementById("importer-fil-status");
  const reader = new FileReader();
  reader.onload = () => {
    const resultat = parseKbhRecipeInnhold(reader.result);
    if (!resultat.ok) {
      status.textContent = resultat.melding;
      return;
    }
    apneIByggeren(resultat.oppskrift);
  };
  reader.onerror = () => {
    status.textContent = "Kunne ikke lese filen.";
  };
  reader.readAsText(fil);
}

function initFilImport() {
  const knapp = document.getElementById("importer-fil-knapp");
  const filInput = document.getElementById("importer-fil");
  knapp.addEventListener("click", () => filInput.click());
  filInput.addEventListener("change", () => {
    if (filInput.files[0]) importerJsonFil(filInput.files[0]);
    filInput.value = "";
  });
}

// ─── Metode-faner (Åpne fil / Lim inn tekst) ───────────────────────────────

function settImportModus(modus) {
  document.getElementById("import-modus-fil").setAttribute("aria-pressed", String(modus === "fil"));
  document.getElementById("import-modus-tekst").setAttribute("aria-pressed", String(modus === "tekst"));
  document.getElementById("import-fane-fil").hidden = modus !== "fil";
  document.getElementById("import-fane-tekst").hidden = modus !== "tekst";
}

function initImportModus() {
  document.getElementById("import-modus-fil").addEventListener("click", () => settImportModus("fil"));
  document.getElementById("import-modus-tekst").addEventListener("click", () => settImportModus("tekst"));
}

// ─── Tekstimport ────────────────────────────────────────────────────────

function _treffLinjeHtml(tekst) {
  const li = document.createElement("li");
  li.className = "treff";
  li.innerHTML = tekst;
  return li;
}

function _uklartLinjeHtml(tekst) {
  const li = document.createElement("li");
  li.className = "uklart";
  li.textContent = tekst;
  return li;
}

function visImportForhandsvisning(parsed, resultat) {
  sisteTreff = resultat;
  const nMalt = parsed.malt.length, nHumle = parsed.humle.length, nGjaer = parsed.gjaer.length;
  document.getElementById("import-tellinger").textContent = `Tolket: ${nMalt} malt · ${nHumle} humle · ${nGjaer} gjær-linje(r)`;

  const advarselEl = document.getElementById("import-advarsler");
  advarselEl.innerHTML = "";
  for (const w of parsed.warnings) {
    const div = document.createElement("div");
    div.className = "hjelp-advarsel";
    div.textContent = w;
    div.style.marginBottom = "0.5rem";
    advarselEl.appendChild(div);
  }

  const treffListe = document.getElementById("import-treff-liste");
  treffListe.innerHTML = "";
  const { matched, unmatched } = resultat;
  let noeMatchet = false;
  for (const m of matched.malt) {
    treffListe.appendChild(_treffLinjeHtml(`Malt: ${escHtml(m.navn)} → <code>${escHtml(m.display_name)}</code> (${m.mengde} kg)`));
    noeMatchet = true;
  }
  for (const h of matched.humle) {
    treffListe.appendChild(_treffLinjeHtml(`Humle: ${escHtml(h.navn)} → <code>${escHtml(h.display_name)}</code> (${h.gram} g, ${h.tid} min)`));
    noeMatchet = true;
  }
  if (matched.gjaer) {
    treffListe.appendChild(_treffLinjeHtml(`Gjær: ${escHtml(matched.gjaer.navn)} → <code>${escHtml(matched.gjaer.display_name)}</code>`));
    noeMatchet = true;
  }
  if (!noeMatchet) {
    treffListe.appendChild((() => {
      const li = document.createElement("li");
      li.textContent = "Ingen ingredienser ble gjenkjent.";
      return li;
    })());
  }

  const uklartSeksjon = document.getElementById("import-uklart-seksjon");
  const uklartListe = document.getElementById("import-uklart-liste");
  uklartListe.innerHTML = "";
  uklartSeksjon.hidden = unmatched.length === 0;
  for (const u of unmatched) {
    uklartListe.appendChild(_uklartLinjeHtml(`${u.kategori.charAt(0).toUpperCase()}${u.kategori.slice(1)}: ${u.navn}`));
  }

  document.getElementById("import-bekreft-knapp").disabled = !noeMatchet;
  document.getElementById("import-forhandsvisning").hidden = false;
}

function analyserImportTekst() {
  const tekst = document.getElementById("import-tekst-input").value;
  if (!tekst.trim()) {
    document.getElementById("import-forhandsvisning").hidden = true;
    return;
  }
  const parsed = parseRecipeText(tekst);
  const resultat = matchImportedIngredients(parsed, maltData, humleData, gjaerData);
  resultat.metadata = { navn: parsed.navn, batch_liter: parsed.batch_liter };
  visImportForhandsvisning(parsed, resultat);
}

function bekreftImportTekst() {
  if (!sisteTreff) return;
  const { matched, metadata } = sisteTreff;
  const oppskrift = {
    navn: (metadata && metadata.navn) || "Importert oppskrift",
    volum: (metadata && metadata.batch_liter) || 20,
    malt: matched.malt.map((m) => ({ id: m.id, mengde: m.mengde })),
    humle: matched.humle.map((h) => ({ id: h.id, gram: h.gram, tid: h.tid })),
    gjaerId: matched.gjaer ? matched.gjaer.id : null,
  };
  apneIByggeren(oppskrift);
}

function initTekstImport() {
  document.getElementById("import-analyser-knapp").addEventListener("click", analyserImportTekst);
  document.getElementById("import-bekreft-knapp").addEventListener("click", bekreftImportTekst);
}

async function init() {
  const [malt, humle, gjaer] = await Promise.all([
    fetch("data/malt.json").then((r) => r.json()),
    fetch("data/humle.json").then((r) => r.json()),
    fetch("data/gjaer.json").then((r) => r.json()),
  ]);
  maltData = malt;
  humleData = humle;
  gjaerData = gjaer;

  initFilImport();
  initImportModus();
  initTekstImport();
}

init();
