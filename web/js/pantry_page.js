// Runde 24A/24B -- Pantry-siden: DOM-laget over pantry.js (samme oppdeling
// som app.js over recipe_engine.js) og pantry_compare.js (samme oppdeling
// som utskrift_page.js over recipe_engine.js). CRUD + visning + oppskrift
// ↔ lager-sammenligning ("Hva mangler du?").
//
// Enhetsbevisst mengde-felt: samme dataset.canonical-mønster som app.js
// (_settEnhetsfelt/_lesEnhetsfelt/_syncKanonisk), duplisert lokalt i liten
// skala fordi app.js ikke lastes på denne siden (den drar med seg hele
// byggeren -- stilanalyse, skalering, osv. -- som ikke er relevant her).
// Gjær har INGEN enhetskonvertering (rent antall pakker) og hopper derfor
// helt over canonical-dansen.

let maltData = {}, humleData = {}, gjaerData = {};
let _valgtType = "malt";
let _redigererId = null;

// ─── Runde 24B -- Oppskrift ↔ lager-sammenligning ─────────────────────────
// Gjenbruker EKSAKT samme mønster som utskrift_page.js (aktiv kladd +
// lagrede oppskrifter, samme lagringsnøkler/select-verdikonvensjon
// "__aktiv__" / "lagret:<navn>") -- ingen ny oppskrifts-storage-kontrakt.
// Skriver ALDRI til AKTIV_KLADD_NOKKEL eller LAGRINGSNOKKEL, samme
// prinsipp som utskrift-siden: å se på en oppskrift her endrer den aldri.

const LAGRINGSNOKKEL = "kvernhaug_web_oppskrifter";
const AKTIV_KLADD_NOKKEL = "kvernhaug_web_aktiv_kladd";
let valgtOppskrift = null;
let sisteSammenligning = null;

const PANTRY_ENHET_FORKORTELSE = {
  metric: { malt: "kg", humle: "g" },
  us: { malt: "lb", humle: "oz" },
};

const PANTRY_COMBOBOX_TEKST = {
  malt: { placeholder: "builder.malt.comboboxPlaceholder", ariaLabel: "builder.malt.comboboxAriaLabel" },
  humle: { placeholder: "builder.humle.comboboxPlaceholder", ariaLabel: "builder.humle.comboboxAriaLabel" },
  gjaer: { placeholder: "builder.gjaer.comboboxPlaceholder", ariaLabel: "builder.gjaer.comboboxAriaLabel" },
};

let pantryVelger = null;

function _dataForType(type) {
  return type === "malt" ? maltData : type === "humle" ? humleData : gjaerData;
}

function _comboboxItemsForType(type) {
  const data = _dataForType(type);
  return Object.entries(data)
    .map(([id, info]) => ({
      id,
      label: info.navn || id,
      search: `${info.navn || ""} ${info.produsent || info.opprinnelse || ""}`.toLowerCase(),
    }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

function _hentVisningsnavn(item) {
  if (item.custom) return item.custom.navn;
  const info = _dataForType(item.ingredientType)[item.id];
  return info ? info.navn : item.id;
}

// ─── Enhetsbevisst mengde-felt (kun malt/humle -- se filhode) ─────────────

function _settPantryMengdeFelt(canonicalVerdi, type) {
  const el = document.getElementById("pantry-mengde");
  if (type === "gjaer") {
    el.value = isFinite(canonicalVerdi) ? String(canonicalVerdi) : "";
    delete el.dataset.canonical;
    return;
  }
  const formatterNumber = type === "malt" ? formatMaltMassNumber : formatHopMassNumber;
  el.dataset.canonical = String(canonicalVerdi);
  el.value = formatterNumber(canonicalVerdi, hentUnitSystem());
}

function _lesPantryMengdeFelt(type) {
  const el = document.getElementById("pantry-mengde");
  if (type === "gjaer") return Number(el.value);
  if (el.dataset.canonical !== undefined && el.dataset.canonical !== "") {
    const lagret = parseFloat(el.dataset.canonical);
    if (isFinite(lagret)) return lagret;
  }
  const parser = type === "malt" ? parseMaltMass : parseHopMass;
  const tolket = parser(el.value, hentUnitSystem());
  return isFinite(tolket) ? tolket : NaN;
}

function _syncPantryMengdeKanonisk() {
  if (_valgtType === "gjaer") return;
  const el = document.getElementById("pantry-mengde");
  const parser = _valgtType === "malt" ? parseMaltMass : parseHopMass;
  const tolket = parser(el.value, hentUnitSystem());
  el.dataset.canonical = isFinite(tolket) ? String(tolket) : "";
}

function _oppdaterMengdeLabelOgAttrs() {
  const label = document.getElementById("pantry-mengde-label");
  const el = document.getElementById("pantry-mengde");
  const enhet = _valgtType === "gjaer" ? t("pantry.gjaerEnhet") : PANTRY_ENHET_FORKORTELSE[hentUnitSystem()][_valgtType];
  label.textContent = t("pantry.mengdeLabel", { enhet });
  el.step = _valgtType === "gjaer" ? "1" : "0.01";
  el.min = "0";
}

// ─── Listevisning ──────────────────────────────────────────────────────

function _radDetalj(item) {
  const enhet = hentUnitSystem();
  let mengdeTekst;
  if (item.ingredientType === "malt") mengdeTekst = formatMaltMass(item.mengde, enhet);
  else if (item.ingredientType === "humle") mengdeTekst = formatHopMass(item.mengde, enhet);
  else mengdeTekst = `${item.mengde} ${t("pantry.gjaerEnhet")}`;

  const nokkel = item.ingredientType === "malt" ? "pantry.radDetaljMalt" : item.ingredientType === "humle" ? "pantry.radDetaljHumle" : "pantry.radDetaljGjaer";
  let tekst = t(nokkel, { mengde: mengdeTekst });
  if (item.notat) tekst += ` · ${t("pantry.radNotat", { notat: item.notat })}`;
  return tekst;
}

function visPantryListe() {
  const items = allePantryItems();
  const listeEl = document.getElementById("pantry-liste");
  const tomEl = document.getElementById("pantry-tom-melding");
  listeEl.innerHTML = "";
  tomEl.hidden = items.length !== 0;
  if (items.length === 0) {
    _oppdaterSammenligning();
    return;
  }

  const mal = document.getElementById("pantry-rad-mal");
  for (const item of items) {
    const rad = mal.content.firstElementChild.cloneNode(true);
    rad.querySelector(".utstyr-rad-navn").textContent = _hentVisningsnavn(item);
    rad.querySelector(".utstyr-rad-detalj").textContent = _radDetalj(item);
    rad.querySelector(".utstyr-rad-rediger").addEventListener("click", () => _apnePantrySkjemaRediger(item));
    rad.querySelector(".utstyr-rad-slett").addEventListener("click", () => {
      if (confirm(t("pantry.slettConfirm", { navn: _hentVisningsnavn(item) }))) {
        slettPantryItem(item.pantryItemId);
        visPantryListe();
      }
    });
    listeEl.appendChild(rad);
  }

  _oppdaterSammenligning();
}

// ─── Runde 24B -- Oppskriftsvelger ─────────────────────────────────────────
// Identisk mønster med utskrift_page.js sin hentAktivKladd/
// hentLagredeOppskrifter/byggValgliste/velgOppskrift.

function hentAktivKladd() {
  try {
    return JSON.parse(localStorage.getItem(AKTIV_KLADD_NOKKEL));
  } catch {
    return null;
  }
}

function hentLagredeOppskrifter() {
  try {
    return JSON.parse(localStorage.getItem(LAGRINGSNOKKEL)) || {};
  } catch {
    return {};
  }
}

function velgOppskrift(valgtVerdi) {
  const kladd = hentAktivKladd();
  const lagrede = hentLagredeOppskrifter();
  if (valgtVerdi === "__aktiv__") valgtOppskrift = kladd;
  else if (valgtVerdi && valgtVerdi.startsWith("lagret:")) valgtOppskrift = lagrede[valgtVerdi.slice(7)];
  else valgtOppskrift = kladd || Object.values(lagrede)[0] || null;
  _oppdaterSammenligning();
}

function byggOppskriftValgliste() {
  const kladd = hentAktivKladd();
  const lagrede = hentLagredeOppskrifter();
  const tomEl = document.getElementById("pantry-oppskrift-tom-melding");
  const velgerRad = document.getElementById("pantry-oppskrift-velger-rad");

  if (!kladd && Object.keys(lagrede).length === 0) {
    tomEl.hidden = false;
    velgerRad.hidden = true;
    valgtOppskrift = null;
    _oppdaterSammenligning();
    return;
  }
  tomEl.hidden = true;
  velgerRad.hidden = false;

  const select = document.getElementById("pantry-oppskrift-velger");
  const forrigeValg = select.value;
  select.innerHTML = "";
  if (kladd) {
    const opt = document.createElement("option");
    opt.value = "__aktiv__";
    opt.textContent = t("utskrift.velgerAktivt", { navn: visningsnavn(kladd.navn) || t("identitet.utenNavn") });
    select.appendChild(opt);
  }
  for (const navn of Object.keys(lagrede)) {
    const opt = document.createElement("option");
    opt.value = `lagret:${navn}`;
    opt.textContent = visningsnavn(navn);
    select.appendChild(opt);
  }
  if (forrigeValg && [...select.options].some((o) => o.value === forrigeValg)) select.value = forrigeValg;
  velgOppskrift(select.value);
}

// ─── Runde 24B -- Sammenligningsresultat (Hva mangler du?) ─────────────────

function _formatMengdeForType(type, mengde) {
  if (type === "malt") return formatMaltMass(mengde, hentUnitSystem());
  if (type === "humle") return formatHopMass(mengde, hentUnitSystem());
  return `${mengde} ${t("pantry.gjaerEnhet")}`;
}

function _statusTekst(status) {
  if (status === "nok") return t("pantry.compare.statusNok");
  if (status === "knapp") return t("pantry.compare.statusKnapp");
  return t("pantry.compare.statusMangler");
}

function _visMangelRad(listeEl, type, rad) {
  const mal = document.getElementById("pantry-mangel-rad-mal");
  const li = mal.content.firstElementChild.cloneNode(true);
  li.querySelector(".utstyr-rad-navn").textContent = rad.navn || t("pantry.compare.ukjentVare");
  let detalj = t("pantry.compare.radDetalj", {
    trengs: _formatMengdeForType(type, rad.required),
    paaLager: _formatMengdeForType(type, rad.available),
  });
  if (rad.shortage > 0) {
    detalj += ` · ${t("pantry.compare.radMangler", { mangler: _formatMengdeForType(type, rad.shortage) })}`;
  }
  li.querySelector(".utstyr-rad-detalj").textContent = detalj;
  const status = li.querySelector(".pantry-status");
  status.textContent = _statusTekst(rad.status);
  status.classList.add(`pantry-status-${rad.status}`);

  const quickAddKnapp = li.querySelector(".pantry-quick-add-knapp");
  if (rad.shortage > 0) {
    quickAddKnapp.hidden = false;
    quickAddKnapp.addEventListener("click", () => _handleQuickAdd(type, rad.id, rad.shortage));
  }
  listeEl.appendChild(li);
}

// ─── Runde 24C -- "Legg til i lager" fra shortage-rad ──────────────────────
// Bruker ALLTID rad.shortage -- den kanoniske verdien fra pantry_compare.js
// -- ALDRI et parset/avrundet display-tall (Runde 24C pkt. 11), for å
// unngå drift. Kun tracked (bibliotek-id-baserte) rader har denne knappen
// i det hele tatt -- egendefinerte oppskrift-rader vises kun i "Ikke
// sporet i lager" og får ALDRI en auto-link-knapp (pkt. 10).
function _handleQuickAdd(type, id, shortage) {
  const eksisterende = finnPantryItemVedIngrediens(type, id);
  const res = eksisterende
    ? oppdaterPantryItem(eksisterende.pantryItemId, { mengde: eksisterende.mengde + shortage })
    : leggTilPantryItem({ ingredientType: type, id, mengde: shortage });
  if (res.ok) visPantryListe();
}

function _visIkkeSporetRad(listeEl, rad) {
  const mal = document.getElementById("pantry-ikke-sporet-rad-mal");
  const li = mal.content.firstElementChild.cloneNode(true);
  li.querySelector(".utstyr-rad-navn").textContent = rad.navn;
  li.querySelector(".utstyr-rad-detalj").textContent = t("pantry.compare.ikkeSporetTrengs", {
    trengs: _formatMengdeForType(rad.ingredientType, rad.required),
  });
  listeEl.appendChild(li);
}

function _oppdaterSammenligning() {
  const panel = document.getElementById("pantry-mangel-panel");
  if (!valgtOppskrift) {
    panel.hidden = true;
    sisteSammenligning = null;
    return;
  }

  const resultat = beregnPantryStatus(valgtOppskrift, allePantryItems(), maltData, humleData, gjaerData);
  sisteSammenligning = resultat;
  panel.hidden = false;

  const oppsummeringEl = document.getElementById("pantry-mangel-oppsummering");
  oppsummeringEl.textContent = resultat.antallMangler === 0
    ? t("pantry.compare.altPaaLager")
    : (resultat.antallMangler === 1 ? t("pantry.compare.mangler1") : t("pantry.compare.manglerN", { antall: resultat.antallMangler }));
  if (resultat.antallIkkeSporet > 0) {
    oppsummeringEl.textContent += " · " + (resultat.antallIkkeSporet === 1
      ? t("pantry.compare.ikkeSporet1")
      : t("pantry.compare.ikkeSporetN", { antall: resultat.antallIkkeSporet }));
  }

  const listeEl = document.getElementById("pantry-mangel-liste");
  listeEl.innerHTML = "";
  for (const rad of resultat.malt) _visMangelRad(listeEl, "malt", rad);
  for (const rad of resultat.humle) _visMangelRad(listeEl, "humle", rad);
  if (resultat.gjaer) _visMangelRad(listeEl, "gjaer", resultat.gjaer);

  const ikkeSporetBlokk = document.getElementById("pantry-ikke-sporet-blokk");
  const ikkeSporetListe = document.getElementById("pantry-ikke-sporet-liste");
  ikkeSporetListe.innerHTML = "";
  ikkeSporetBlokk.hidden = resultat.ikkeSporet.length === 0;
  for (const rad of resultat.ikkeSporet) _visIkkeSporetRad(ikkeSporetListe, rad);

  document.getElementById("pantry-kopier-handleliste-knapp").hidden =
    resultat.antallMangler === 0 && resultat.antallIkkeSporet === 0;
  document.getElementById("pantry-kopier-status").hidden = true;
}

// ─── Runde 24B -- Kopier handleliste (SHOULD, pkt. 17) ─────────────────────
// Kopierer KUN shortage-varer + "ikke sporet"-seksjonen -- aldri varer som
// allerede er nok/knapt nok på lager. Ren tekst, ingen pris/butikk/valuta
// (Runde 24B pkt. 16).

function _byggHandlelisteTekst(resultat) {
  const linjer = [t("pantry.compare.handlelisteTittel"), ""];
  const grupper = [["malt", resultat.malt], ["humle", resultat.humle], ["gjaer", resultat.gjaer ? [resultat.gjaer] : []]];
  for (const [type, rader] of grupper) {
    for (const rad of rader) {
      if (rad.shortage > 0) linjer.push(`${rad.navn || t("pantry.compare.ukjentVare")} — ${_formatMengdeForType(type, rad.shortage)}`);
    }
  }
  if (resultat.ikkeSporet.length > 0) {
    linjer.push("");
    linjer.push(t("pantry.compare.handlelisteIkkeSporetTittel"));
    for (const rad of resultat.ikkeSporet) {
      linjer.push(`${rad.navn} — ${_formatMengdeForType(rad.ingredientType, rad.required)}`);
    }
  }
  return linjer.join("\n");
}

function _handleKopierHandleliste() {
  if (!sisteSammenligning) return;
  const tekst = _byggHandlelisteTekst(sisteSammenligning);
  const statusEl = document.getElementById("pantry-kopier-status");
  const visStatus = (nokkel) => {
    statusEl.textContent = t(nokkel);
    statusEl.hidden = false;
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(tekst).then(
      () => visStatus("pantry.compare.kopiertBekreftelse"),
      () => visStatus("pantry.compare.kopieringFeilet")
    );
  } else {
    visStatus("pantry.compare.kopieringFeilet");
  }
}

// ─── Runde 24C -- Backup/eksport/import ─────────────────────────────────────
// Samme fil-mønster som app.js sin lagreOppskriftsfil()/apneOppskriftsfil()
// (Blob-nedlasting / FileReader + skjult <input type="file">), men et
// helt eget .kbhpantry-format (se pantry.js) -- aldri .kbhrecipe, aldri
// recipe-data. Import er RESTORE/REPLACE (Runde 24C pkt. 5), ikke merge --
// brukeren bekreftes eksplisitt FØR eksisterende lager erstattes.

function _visBackupStatus(tekst) {
  const el = document.getElementById("pantry-backup-status");
  el.textContent = tekst;
  el.hidden = false;
}

function _handleEksporterPantry() {
  lastNedPantryBackup();
  _visBackupStatus(t("pantry.backup.eksportertStatus"));
}

function _handleImporterPantryFil(fil) {
  const reader = new FileReader();
  reader.onload = () => {
    const resultat = parsePantryBackupInnhold(reader.result);
    if (!resultat.ok) {
      _visBackupStatus(resultat.melding);
      return;
    }
    if (!confirm(t("pantry.backup.erstattConfirm"))) return;
    const importerte = erstattPantryItems(resultat.items);
    visPantryListe();
    _visBackupStatus(t("pantry.backup.importertStatus", { antall: importerte.length }));
  };
  reader.onerror = () => _visBackupStatus(t("pantry.backup.lesefeil"));
  reader.readAsText(fil);
}

// ─── Skjema: type-bryter / combobox / egendefinert ────────────────────────

function _byggPantryVelger() {
  const mount = document.getElementById("pantry-velger-mount");
  mount.innerHTML = "";
  const tekst = PANTRY_COMBOBOX_TEKST[_valgtType];
  pantryVelger = new Combobox({
    items: _comboboxItemsForType(_valgtType),
    placeholder: t(tekst.placeholder),
    ariaLabel: t(tekst.ariaLabel),
  });
  mount.appendChild(pantryVelger.el);
}

function _settType(type) {
  _valgtType = type;
  document.querySelectorAll(".pantry-type-knapp").forEach((knapp) => {
    knapp.setAttribute("aria-pressed", String(knapp.dataset.type === type));
  });
  _byggPantryVelger();
  _visEgendefinert(false);
  _settPantryMengdeFelt(NaN, type);
  document.getElementById("pantry-mengde").value = "";
  _oppdaterMengdeLabelOgAttrs();
}

function _visEgendefinert(vis) {
  document.getElementById("pantry-velger-rad").hidden = vis;
  document.getElementById("pantry-egendefinert-knapp").hidden = vis;
  document.getElementById("pantry-egendefinert-felt").hidden = !vis;
  if (vis) {
    document.getElementById("pantry-eg-navn").value = "";
    document.getElementById("pantry-eg-produsent").value = "";
  }
}

// ─── Åpne/lukke skjema (samme ett-skjema-for-nytt-og-rediger-mønster som
// app.js sin _apneUtstyrSkjema()) ───────────────────────────────────────

function _apnePantrySkjemaNy() {
  _redigererId = null;
  document.getElementById("pantry-skjema-tittel").textContent = t("pantry.skjemaTittelNytt");
  document.getElementById("pantry-type-bryter").hidden = false;
  document.getElementById("pantry-redigerer-navn").hidden = true;
  document.getElementById("pantry-skjema-melding").hidden = true;
  document.getElementById("pantry-notat").value = "";
  _settType("malt");
  document.querySelectorAll(".pantry-type-knapp").forEach((k) => k.disabled = false);
  document.getElementById("pantry-skjema").hidden = false;
}

function _apnePantrySkjemaRediger(item) {
  _redigererId = item.pantryItemId;
  _valgtType = item.ingredientType;
  document.getElementById("pantry-skjema-tittel").textContent = t("pantry.skjemaTittelRediger");
  document.getElementById("pantry-skjema-melding").hidden = true;
  document.getElementById("pantry-type-bryter").hidden = true;
  document.getElementById("pantry-velger-rad").hidden = true;
  document.getElementById("pantry-egendefinert-knapp").hidden = true;

  const redigererNavnEl = document.getElementById("pantry-redigerer-navn");
  const egFeltEl = document.getElementById("pantry-egendefinert-felt");
  if (item.custom) {
    redigererNavnEl.hidden = true;
    egFeltEl.hidden = false;
    document.getElementById("pantry-eg-navn").value = item.custom.navn;
    document.getElementById("pantry-eg-produsent").value = item.custom.produsent || "";
  } else {
    egFeltEl.hidden = true;
    redigererNavnEl.hidden = false;
    redigererNavnEl.textContent = t("pantry.redigererVare", { navn: _hentVisningsnavn(item) });
  }

  _settPantryMengdeFelt(item.mengde, item.ingredientType);
  _oppdaterMengdeLabelOgAttrs();
  document.getElementById("pantry-notat").value = item.notat || "";
  document.getElementById("pantry-skjema").hidden = false;
  document.getElementById("pantry-skjema").scrollIntoView({ block: "nearest" });
}

function _lukkPantrySkjema() {
  document.getElementById("pantry-skjema").hidden = true;
  document.getElementById("pantry-skjema-melding").hidden = true;
  _redigererId = null;
}

function _visMelding(tekst) {
  const el = document.getElementById("pantry-skjema-melding");
  el.textContent = tekst;
  el.hidden = false;
}

// ─── Submit ────────────────────────────────────────────────────────────

function _handlePantrySkjemaSubmit(e) {
  e.preventDefault();
  const customAktiv = !document.getElementById("pantry-egendefinert-felt").hidden;
  const notat = document.getElementById("pantry-notat").value;
  const mengde = _lesPantryMengdeFelt(_valgtType);

  let custom = null;
  let id = null;
  if (customAktiv) {
    const navn = document.getElementById("pantry-eg-navn").value.trim();
    if (!navn) return _visMelding(t("pantry.feilManglerNavn"));
    custom = { navn, produsent: document.getElementById("pantry-eg-produsent").value };
  } else if (_redigererId === null) {
    id = pantryVelger.getValue();
    if (!id) return _visMelding(t("pantry.feilManglerVare"));
  }

  if (_redigererId !== null) {
    const res = oppdaterPantryItem(_redigererId, { mengde, notat, custom: custom || undefined });
    if (!res.ok) return _visMelding(res.melding);
    _lukkPantrySkjema();
    visPantryListe();
    return;
  }

  if (!customAktiv) {
    const dupe = finnPantryItemVedIngrediens(_valgtType, id);
    if (dupe) {
      if (!confirm(t("pantry.duplikatSporsmal"))) return;
      const res = oppdaterPantryItem(dupe.pantryItemId, { mengde: dupe.mengde + mengde });
      if (!res.ok) return _visMelding(res.melding);
      _lukkPantrySkjema();
      visPantryListe();
      return;
    }
  }

  const res = leggTilPantryItem({ ingredientType: _valgtType, id, custom, mengde, notat });
  if (!res.ok) return _visMelding(res.melding);
  _lukkPantrySkjema();
  visPantryListe();
}

// ─── Live enhetsbytte (Runde 24A pkt. 17) ─────────────────────────────────

function _pantryEnhetRerender() {
  visPantryListe();
  const skjemaApent = !document.getElementById("pantry-skjema").hidden;
  if (skjemaApent && _valgtType !== "gjaer") {
    const el = document.getElementById("pantry-mengde");
    const canonical = parseFloat(el.dataset.canonical);
    if (isFinite(canonical)) {
      const formatterNumber = _valgtType === "malt" ? formatMaltMassNumber : formatHopMassNumber;
      el.value = formatterNumber(canonical, hentUnitSystem());
    }
    _oppdaterMengdeLabelOgAttrs();
  }
}

// ─── Init ──────────────────────────────────────────────────────────────

async function init() {
  const [malt, humle, gjaer] = await Promise.all([
    fetch(KBH_ROOT + "data/malt.json").then((r) => r.json()),
    fetch(KBH_ROOT + "data/humle.json").then((r) => r.json()),
    fetch(KBH_ROOT + "data/gjaer.json").then((r) => r.json()),
  ]);
  maltData = malt;
  humleData = humle;
  gjaerData = gjaer;

  document.getElementById("pantry-legg-til-knapp").addEventListener("click", _apnePantrySkjemaNy);
  document.getElementById("pantry-skjema-avbryt").addEventListener("click", _lukkPantrySkjema);
  document.getElementById("pantry-skjema").addEventListener("submit", _handlePantrySkjemaSubmit);
  document.getElementById("pantry-egendefinert-knapp").addEventListener("click", () => _visEgendefinert(true));
  document.getElementById("pantry-egendefinert-tilbake-knapp").addEventListener("click", () => _visEgendefinert(false));
  document.getElementById("pantry-mengde").addEventListener("input", _syncPantryMengdeKanonisk);
  document.querySelectorAll(".pantry-type-knapp").forEach((knapp) => {
    knapp.addEventListener("click", () => _settType(knapp.dataset.type));
  });
  document.getElementById("pantry-oppskrift-velger").addEventListener("change", (e) => velgOppskrift(e.target.value));
  document.getElementById("pantry-kopier-handleliste-knapp").addEventListener("click", _handleKopierHandleliste);

  document.getElementById("pantry-eksporter-knapp").addEventListener("click", _handleEksporterPantry);
  const importerInput = document.getElementById("pantry-importer-input");
  document.getElementById("pantry-importer-knapp").addEventListener("click", () => importerInput.click());
  importerInput.addEventListener("change", () => {
    if (importerInput.files[0]) _handleImporterPantryFil(importerInput.files[0]);
    importerInput.value = "";
  });

  byggOppskriftValgliste();
  visPantryListe();
}

function _sprakRerender() {
  byggOppskriftValgliste();
  visPantryListe();
}

document.addEventListener("kvernhaug:enhetendret", _pantryEnhetRerender);
window.addEventListener("kvernhaug:sprakendret", _sprakRerender);

init();
