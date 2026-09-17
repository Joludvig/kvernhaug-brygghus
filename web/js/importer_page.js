// Importer oppskrift-siden: to metoder (fil / tekst), begge sender brukeren
// videre til byggeren via AKTIV_KLADD_NOKKEL -- samme hand-off-mekanisme
// som "Åpne i byggeren" på Mine oppskrifter-siden og byggerens egen
// autolagrede kladd (se app.js). Tekstimporten porter
// modules/recipe_importer.py sin kontrakt, se web/js/recipe_importer.js.

const AKTIV_KLADD_NOKKEL = "kvernhaug_web_aktiv_kladd";

let maltData = {}, humleData = {}, gjaerData = {};
let sisteTreff = null;
let sistParsed = null; // Runde 23A -- husket for å kunne rerendre preview live ved enhetsbytte

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

// `hint` (issue #300) -- kbhRecipeHandoffHint()-resultat fra fil-import,
// eller undefined fra tekstimport (bekreftImportTekst() under, som ikke
// har noen .kbhrecipe-konvolutt å hente hint fra) -- se kbhrecipe.js.
function apneIByggeren(oppskrift, hint) {
  if (_aktivKladdHarInnhold()) {
    const ok = confirm(kbhRecipeApneConfirmMelding(hint));
    if (!ok) return;
  }
  // Chief review (PR #305) -- denne funksjonen navigerer ALLTID bort fra
  // siden rett under, også når ingen aktiv kladd fantes å bekrefte
  // overskriving av (ingen confirm() over i det hele tatt) -- uten dette
  // ble hinten aldri vist på det vanlige, "rene" import-sporet. Skrives
  // UBETINGET (ikke bare i overskrivings-grenen over) for å speile
  // app.js sin egen apneOppskriftsfil(): der vises hinten BÅDE i
  // confirm()-dialogen OG i status-teksten etterpå, uansett om en aktiv
  // kladd fantes. No-op når hint er undefined/null (tekstimport, eller
  // ukjent/manglende metadata) -- se lagreHandoffHintFlash() i
  // kbhrecipe.js.
  lagreHandoffHintFlash(hint);
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
    // CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md §3.4/§3.6 -- speiler app.js sin
    // apneOppskriftsfil(): eksakt-streng duplikatsjekk FØR hand-off til
    // byggeren, ingen stille sammenslåing/overskriving. Krever
    // recipe_storage.js lastet på denne siden (se importer.html).
    if (finnesOppskriftMedOrigin(resultat.oppskrift.originRecipeId)) {
      status.textContent = t("oppskrift.importDuplikat");
      return;
    }
    apneIByggeren(resultat.oppskrift, kbhRecipeHandoffHint(resultat));
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
  // Runde 23A -- mengde/gram formateres via units.js (samme unit-helper
  // som byggeren) FØR de settes inn i i18n-malen, slik at malen selv
  // aldri trenger å inneholde en hardkodet "kg"/"g" -- se
  // import.treffMalt/import.treffHumle i i18n.js.
  const enhet = hentUnitSystem();
  for (const m of matched.malt) {
    treffListe.appendChild(_treffLinjeHtml(t("import.treffMalt", { navn: escHtml(m.navn), display: escHtml(m.display_name), mengde: formatMaltMass(m.mengde, enhet) })));
    noeMatchet = true;
  }
  for (const h of matched.humle) {
    treffListe.appendChild(_treffLinjeHtml(t("import.treffHumle", { navn: escHtml(h.navn), display: escHtml(h.display_name), gram: formatHopMass(h.gram, enhet), tid: h.tid })));
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
  sistParsed = parsed;
  visImportForhandsvisning(parsed, resultat);
}

// Runde 23A -- treff-listen viser malt/humle-mengder i valgt unitSystem
// (se visImportForhandsvisning). Uten dette ville et enhetsbytte mens
// forhåndsvisningen står synlig latt den vise feil enhet til neste
// "Analyser"-klikk -- rerendrer samme data på nytt, ingen ny analyse.
document.addEventListener("kvernhaug:enhetendret", () => {
  if (sistParsed) visImportForhandsvisning(sistParsed, sisteTreff);
});

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
    fetch(KBH_ROOT + "data/malt.json").then((r) => r.json()),
    fetch(KBH_ROOT + "data/humle.json").then((r) => r.json()),
    fetch(KBH_ROOT + "data/gjaer.json").then((r) => r.json()),
  ]);
  maltData = malt;
  humleData = humle;
  gjaerData = gjaer;

  initFilImport();
  initImportModus();
  initTekstImport();
}

init();
