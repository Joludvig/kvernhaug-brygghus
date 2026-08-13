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
    const ok = confirm(t("oppskrift.apneConfirm"));
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
    status.textContent = t("oppskrift.lesefeil");
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

const _IMPORT_KATEGORI_NOKKEL = { malt: "import.kategoriMalt", humle: "import.kategoriHumle", gjaer: "import.kategoriGjaer" };

function visImportForhandsvisning(parsed, resultat) {
  sisteTreff = resultat;
  const nMalt = parsed.malt.length, nHumle = parsed.humle.length, nGjaer = parsed.gjaer.length;
  document.getElementById("import-tellinger").textContent = t("import.tellinger", { malt: nMalt, humle: nHumle, gjaer: nGjaer });

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
    treffListe.appendChild(_treffLinjeHtml(t("import.treffMalt", { navn: escHtml(m.navn), display: escHtml(m.display_name), mengde: m.mengde })));
    noeMatchet = true;
  }
  for (const h of matched.humle) {
    treffListe.appendChild(_treffLinjeHtml(t("import.treffHumle", { navn: escHtml(h.navn), display: escHtml(h.display_name), gram: h.gram, tid: h.tid })));
    noeMatchet = true;
  }
  if (matched.gjaer) {
    treffListe.appendChild(_treffLinjeHtml(t("import.treffGjaer", { navn: escHtml(matched.gjaer.navn), display: escHtml(matched.gjaer.display_name) })));
    noeMatchet = true;
  }
  if (!noeMatchet) {
    treffListe.appendChild((() => {
      const li = document.createElement("li");
      li.textContent = t("import.ingenGjenkjent");
      return li;
    })());
  }

  const uklartSeksjon = document.getElementById("import-uklart-seksjon");
  const uklartListe = document.getElementById("import-uklart-liste");
  uklartListe.innerHTML = "";
  uklartSeksjon.hidden = unmatched.length === 0;
  for (const u of unmatched) {
    const kategoriNavn = t(_IMPORT_KATEGORI_NOKKEL[u.kategori] || "import.kategoriMalt");
    uklartListe.appendChild(_uklartLinjeHtml(`${kategoriNavn}: ${u.navn}`));
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
    navn: (metadata && metadata.navn) || t("oppskrift.importertNavnDefault"),
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
