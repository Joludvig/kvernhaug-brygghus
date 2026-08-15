// Runde 24A -- Pantry-siden: DOM-laget over pantry.js (samme oppdeling som
// app.js over recipe_engine.js). Ren CRUD + visning -- ingen recipe-
// sammenligning/mangelliste her, det kommer i Runde 24B (se filhode-
// kommentaren i pantry.js).
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
  if (items.length === 0) return;

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

  visPantryListe();
}

document.addEventListener("kvernhaug:enhetendret", _pantryEnhetRerender);
window.addEventListener("kvernhaug:sprakendret", visPantryListe);

init();
