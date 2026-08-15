// Runde 24A -- Pantry V1, DOM-fri state-modul (samme prinsipp som
// equipment.js/recipe_engine.js), lastet FØR pantry_page.js. Bruker den
// globale t() fra i18n.js for brukervendte feilmeldinger -- samme
// ok/melding-kontrakt som equipment.js/kbhrecipe.js sin import-validering,
// ikke en ny oppfunnet.
//
// LOCAL-FIRST, BEVISST: Pantry-data lagres UTELUKKENDE i localStorage under
// PANTRY_NOKKEL. Ingen del av denne filen kaller fetch()/XHR eller sender
// noe til noen server -- lageret er brukerens private, enhetslokale data,
// aldri synkronisert. Se web/README.md "Deploy"/dataflyt-seksjonene for
// samme prinsipp anvendt på resten av web-appen.
//
// BUTIKKAGNOSTISK, BEVISST: ingen pris/butikk/leverandør/pakningsdata noe
// sted i denne modulen eller i pantry-item-modellen -- se Runde 24-notatet
// i web/README.md ("Aldri tatt med, uansett: butikk_match ... og all
// pantry-/lagerdata") og Runde 24A sitt eget "PRIS / BUTIKK"-tillegg.
// Handlelisten (Runde 24B) skal uttrykke HVA brukeren mangler, aldri HVOR
// det bør kjøpes.
//
// IDENTITY (Runde 24-arkitekturbeslutning, fryst for V1): et pantry-item
// peker på en ingrediens med EKSAKT samme id-skjema som en oppskrifts
// malt[]/humle[]-rader og gjaerId/gjaerCustom bruker -- enten en
// masterdata-nøkkel (samme streng som web/data/malt.json/humle.json/
// gjaer.json sine objekt-nøkler) eller en egen "egen_pantry_<type>_<unik>"-
// id for custom-varer. ALDRI fuzzy/normalisert navnematching. Custom
// pantry-ider er en EGEN navnerom fra oppskriftenes "egen_malt_<timestamp>_
// <teller>"-ider -- de skal ALDRI antas å matche hverandre (se Runde 24
// pkt. 6/8). Recipe-sammenligning bygges i Runde 24B, ikke her.

const PANTRY_NOKKEL = "kvernhaug_web_pantry";
const PANTRY_VERSION = 1;
const PANTRY_TYPER = ["malt", "humle", "gjaer"];

function _tomPantryState() {
  return { format: "kbh-pantry", version: PANTRY_VERSION, items: [] };
}

// Konservativ item-validering: en enkelt korrupt/ugyldig rad filtreres
// bort stille i stedet for å forkaste HELE pantryet (samme prinsipp som
// equipment.js sin profiles-filtrering). custom, hvis til stede, må minst
// ha et ikke-tomt navn -- ellers kan ikke raden vises forståelig.
function _gyldigPantryItem(item) {
  if (!item || typeof item !== "object") return false;
  if (typeof item.pantryItemId !== "string" || !item.pantryItemId) return false;
  if (!PANTRY_TYPER.includes(item.ingredientType)) return false;
  if (typeof item.id !== "string" || !item.id) return false;
  if (typeof item.mengde !== "number" || !isFinite(item.mengde) || item.mengde < 0) return false;
  if (item.ingredientType === "gjaer" && !Number.isInteger(item.mengde)) return false;
  if (item.custom !== undefined) {
    if (!item.custom || typeof item.custom !== "object") return false;
    if (typeof item.custom.navn !== "string" || !item.custom.navn.trim()) return false;
  }
  if (item.notat !== undefined && typeof item.notat !== "string") return false;
  return true;
}

function _normalisertPantryItem(item) {
  const ut = {
    pantryItemId: item.pantryItemId,
    ingredientType: item.ingredientType,
    id: item.id,
    mengde: item.mengde,
  };
  if (item.custom) {
    ut.custom = {
      navn: item.custom.navn.trim(),
      produsent: typeof item.custom.produsent === "string" && item.custom.produsent.trim() ? item.custom.produsent.trim() : undefined,
    };
  }
  if (typeof item.notat === "string" && item.notat.trim()) ut.notat = item.notat.trim();
  return ut;
}

// Trygg lesing -- manglende nøkkel, ugyldig JSON, feil format/version eller
// et items-felt som ikke er en liste faller ALLE tilbake til tom state.
// Kaster aldri -- skal ALDRI stoppe Pantry-siden.
function lesPantryState() {
  try {
    const raw = localStorage.getItem(PANTRY_NOKKEL);
    if (!raw) return _tomPantryState();
    const parsed = JSON.parse(raw);
    if (
      !parsed || typeof parsed !== "object" ||
      parsed.format !== "kbh-pantry" ||
      parsed.version !== PANTRY_VERSION ||
      !Array.isArray(parsed.items)
    ) {
      return _tomPantryState();
    }
    return {
      format: "kbh-pantry",
      version: PANTRY_VERSION,
      items: parsed.items.filter(_gyldigPantryItem).map(_normalisertPantryItem),
    };
  } catch {
    return _tomPantryState();
  }
}

function _lagrePantryState(state) {
  try {
    localStorage.setItem(PANTRY_NOKKEL, JSON.stringify(state));
  } catch {
    // F.eks. privat nettlesing / full lagringskvote -- trygg no-op, samme
    // prinsipp som resten av appens localStorage-skriving.
  }
}

function allePantryItems() {
  return lesPantryState().items;
}

function finnPantryItem(pantryItemId) {
  return allePantryItems().find((i) => i.pantryItemId === pantryItemId) || null;
}

// Kun meningsfullt for biblioteksvarer (custom-ider er alltid unike og kan
// derfor aldri kollidere) -- brukes av UI-laget til duplikat-spørsmålet i
// pkt. 12 ("Du har allerede denne varen i lageret..."). ekskluderPantryItemId
// (valgfri) lar redigering av en eksisterende rad ikke telle seg selv som
// duplikat av seg selv.
function finnPantryItemVedIngrediens(ingredientType, id, ekskluderPantryItemId = null) {
  return (
    allePantryItems().find(
      (i) => i.ingredientType === ingredientType && i.id === id && !i.custom && i.pantryItemId !== ekskluderPantryItemId
    ) || null
  );
}

function _genererId(prefiks) {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return `${prefiks}-${crypto.randomUUID()}`;
  return `${prefiks}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function _genererPantryItemId() {
  return _genererId("pantryitem");
}

// Egen navnerom fra oppskriftenes "egen_malt_<timestamp>_<teller>" -- se
// filhode-kommentaren. IKKE samme prefiks/form som app.js sin
// nyEgendefinertId(), bevisst, slik at det aldri er mulig å forveksle de to.
function nyPantryCustomId(ingredientType) {
  return _genererId(`egen_pantry_${ingredientType}`);
}

function _erGyldigMengde(ingredientType, mengde) {
  if (typeof mengde !== "number" || !isFinite(mengde) || mengde < 0) return false;
  if (ingredientType === "gjaer" && !Number.isInteger(mengde)) return false;
  return true;
}

function _validerCustomNavn(custom) {
  return !!(custom && typeof custom.navn === "string" && custom.navn.trim());
}

// Returnerer { ok: true, item } eller { ok: false, melding } -- samme
// kontrakt som equipment.js/kbhrecipe.js. Oppretter ALLTID en ny rad --
// duplikat-spørsmålet (slå sammen med eksisterende) er et UI-anliggende
// (pantry_page.js), ikke noe denne funksjonen gjetter på selv.
function leggTilPantryItem({ ingredientType, id, custom, mengde, notat }) {
  if (!PANTRY_TYPER.includes(ingredientType)) return { ok: false, melding: t("pantry.feilUgyldigType") };
  if (custom) {
    if (!_validerCustomNavn(custom)) return { ok: false, melding: t("pantry.feilManglerNavn") };
  } else if (typeof id !== "string" || !id) {
    return { ok: false, melding: t("pantry.feilManglerVare") };
  }
  if (!_erGyldigMengde(ingredientType, mengde)) {
    return {
      ok: false,
      melding: ingredientType === "gjaer" ? t("pantry.feilMengdeHeltall") : t("pantry.feilMengdeUgyldig"),
    };
  }

  const state = lesPantryState();
  const item = {
    pantryItemId: _genererPantryItemId(),
    ingredientType,
    id: custom ? nyPantryCustomId(ingredientType) : id,
    mengde,
  };
  if (custom) item.custom = { navn: custom.navn.trim(), produsent: (custom.produsent || "").toString().trim() || undefined };
  if (notat && String(notat).trim()) item.notat = String(notat).trim();

  state.items.push(item);
  _lagrePantryState(state);
  return { ok: true, item };
}

// Kan endre mengde/notat, og for custom-varer navn/produsent. Bytter
// ALDRI ingredientType eller id -- se Runde 24A pkt. 13 (slett + legg til
// ny er akseptabel V1-vei for å "bytte vare").
function oppdaterPantryItem(pantryItemId, endringer) {
  const state = lesPantryState();
  const idx = state.items.findIndex((i) => i.pantryItemId === pantryItemId);
  if (idx === -1) return { ok: false, melding: t("pantry.feilFinnesIkke") };
  const eksisterende = state.items[idx];

  const mengde = endringer.mengde !== undefined ? endringer.mengde : eksisterende.mengde;
  if (!_erGyldigMengde(eksisterende.ingredientType, mengde)) {
    return {
      ok: false,
      melding: eksisterende.ingredientType === "gjaer" ? t("pantry.feilMengdeHeltall") : t("pantry.feilMengdeUgyldig"),
    };
  }

  const oppdatert = { ...eksisterende, mengde };
  if (endringer.notat !== undefined) {
    const notat = String(endringer.notat).trim();
    if (notat) oppdatert.notat = notat;
    else delete oppdatert.notat;
  }
  if (eksisterende.custom && endringer.custom) {
    if (!_validerCustomNavn(endringer.custom)) return { ok: false, melding: t("pantry.feilManglerNavn") };
    oppdatert.custom = {
      navn: endringer.custom.navn.trim(),
      produsent: (endringer.custom.produsent || "").toString().trim() || undefined,
    };
  }

  state.items[idx] = oppdatert;
  _lagrePantryState(state);
  return { ok: true, item: oppdatert };
}

function slettPantryItem(pantryItemId) {
  const state = lesPantryState();
  const forrigeLengde = state.items.length;
  state.items = state.items.filter((i) => i.pantryItemId !== pantryItemId);
  const slettet = state.items.length !== forrigeLengde;
  if (slettet) _lagrePantryState(state);
  return slettet;
}
