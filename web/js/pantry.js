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
// gjaer.json sine objekt-nøkler) eller en custom-ingrediens-id for
// custom-varer. ALDRI fuzzy/normalisert navnematching. Recipe-sammenligning
// bygges i Runde 24B, ikke her.
//
// PRI 4C (issue #50) -- fram til nå mintet pantry en EGEN
// "egen_pantry_<type>_<unik>"-id per custom-vare, i et eget navnerom fra
// oppskriftenes "egen_malt_<timestamp>_<teller>"-ider (Runde 24 pkt. 6/8).
// Fra og med nå deler pantry, oppskriftenes malt/humle og custom-gjær ETT
// felles, opakt `kbh-custom-<uuidv4>`-navnerom (Core-kontraktens §3, se
// docs/development/CORE_CUSTOM_INGREDIENT_IDENTITY_V1.md) -- se
// nyCustomIngredientId() i custom_ingredient_id.js. Allerede lagrede
// `egen_pantry_*`-ider er permanent grandfatret (kontraktens §9) og røres
// ALDRI av denne filen.

const PANTRY_NOKKEL = "kvernhaug_web_pantry";
const PANTRY_VERSION = 1;
const PANTRY_TYPER = ["malt", "humle", "gjaer"];

// `korrupt: true` markerer at nøkkelen INNEHOLDT noe (i motsetning til å
// rett og slett mangle) som ikke kunne tolkes -- se lesPantryState() og
// PRI-oppgaven "localStorage safety" (issue #74). Skrivefunksjonene under
// sjekker ALLTID dette flagget før de lagrer, slik at en uleselig rådata
// aldri overskrives stille bare fordi leseren falt tilbake til en tom
// struktur.
function _tomPantryState(korrupt = false) {
  return { format: "kbh-pantry", version: PANTRY_VERSION, items: [], korrupt };
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

// Trygg lesing -- kaster aldri, skal ALDRI stoppe Pantry-siden. Manglende
// nøkkel er en EKTE tom state (korrupt: false). Ugyldig JSON, feil format/
// version eller et items-felt som ikke er en liste betyr derimot at
// RÅDATAEN finnes men ikke kan tolkes -- da settes korrupt: true i stedet
// for å late som lageret er tomt (issue #74: en tidligere leser falt
// tilbake til tom state ved BEGGE tilfellene, som lot en etterfølgende
// vanlig lagring stille overskrive den uleselige rådataen med en
// tilsynelatende gyldig, men i realiteten redusert/tom, state).
// Skrivefunksjonene under (leggTilPantryItem/oppdaterPantryItem/
// slettPantryItem) nekter å lagre når korrupt er true; erstattPantryItems
// er unntaket med hensikt -- den er allerede en eksplisitt,
// brukerbekreftet destruktiv gjenopprettingshandling (backup-import).
function lesPantryState() {
  let raw;
  try {
    raw = localStorage.getItem(PANTRY_NOKKEL);
  } catch {
    return _tomPantryState(true);
  }
  if (!raw) return _tomPantryState(false);

  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return _tomPantryState(true);
  }
  if (
    !parsed || typeof parsed !== "object" ||
    parsed.format !== "kbh-pantry" ||
    parsed.version !== PANTRY_VERSION ||
    !Array.isArray(parsed.items)
  ) {
    return _tomPantryState(true);
  }
  return {
    format: "kbh-pantry",
    version: PANTRY_VERSION,
    items: parsed.items.filter(_gyldigPantryItem).map(_normalisertPantryItem),
    korrupt: false,
  };
}

// Sant kun når nøkkelen INNEHOLDER noe som ikke kunne tolkes -- se
// lesPantryState(). UI-laget bruker dette til å vise et vedvarende varsel
// ved sidelasting, i stedet for å late som lageret bare er tomt.
function pantryStateErKorrupt() {
  return lesPantryState().korrupt === true;
}

// Skriver og VERIFISERER ved tilbakelesing -- samme kontrakt som
// recipe_storage.js/brew_storage.js (Runde 25A/25B pkt. 13, utvidet hit i
// issue #74): lagring skal aldri feile stille og aldri late som den
// lyktes. Returnerer boolean. `state` kommer typisk fra lesPantryState()
// og bærer derfor et internt korrupt-flagg (se over) -- KUN de tre ekte
// skjemafeltene skrives faktisk til nøkkelen, slik at det interne flagget
// aldri lekker inn i den lagrede JSON-en.
function _lagrePantryState(state) {
  const persistert = { format: "kbh-pantry", version: PANTRY_VERSION, items: state.items };
  let serialisert;
  try {
    serialisert = JSON.stringify(persistert);
  } catch {
    return false;
  }
  try {
    localStorage.setItem(PANTRY_NOKKEL, serialisert);
    return localStorage.getItem(PANTRY_NOKKEL) === serialisert;
  } catch {
    // F.eks. privat nettlesing / full lagringskvote.
    return false;
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
  if (state.korrupt) return { ok: false, melding: t("pantry.feilKorrupt") };
  const item = {
    pantryItemId: _genererPantryItemId(),
    ingredientType,
    id: custom ? nyCustomIngredientId() : id,
    mengde,
  };
  if (custom) item.custom = { navn: custom.navn.trim(), produsent: (custom.produsent || "").toString().trim() || undefined };
  if (notat && String(notat).trim()) item.notat = String(notat).trim();

  state.items.push(item);
  if (!_lagrePantryState(state)) return { ok: false, melding: t("pantry.feilLagring") };
  return { ok: true, item };
}

// Kan endre mengde/notat, og for custom-varer navn/produsent. Bytter
// ALDRI ingredientType eller id -- se Runde 24A pkt. 13 (slett + legg til
// ny er akseptabel V1-vei for å "bytte vare").
function oppdaterPantryItem(pantryItemId, endringer) {
  const state = lesPantryState();
  if (state.korrupt) return { ok: false, melding: t("pantry.feilKorrupt") };
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
  if (!_lagrePantryState(state)) return { ok: false, melding: t("pantry.feilLagring") };
  return { ok: true, item: oppdatert };
}

// Returnerer boolean -- samme kontrakt som før (issue #74 gjorde den kun
// STRENGERE: aldri true med mindre raden faktisk ble borte OG lagringen
// faktisk lyktes).
function slettPantryItem(pantryItemId) {
  const state = lesPantryState();
  if (state.korrupt) return false;
  const forrigeLengde = state.items.length;
  state.items = state.items.filter((i) => i.pantryItemId !== pantryItemId);
  if (state.items.length === forrigeLengde) return false;
  return _lagrePantryState(state);
}

// ─── Runde 24C -- Backup/eksport/import ────────────────────────────────────
// Eget, portabelt format -- ALDRI .kbhrecipe (se kbhrecipe.js). Inneholder
// KUN pantry-items, alltid canonical (kg/gram/antall) -- aldri valgt
// display-enhet (unitSystem hentes fra en helt separat nøkkel,
// preferences.js, og skal aldri blandes inn i en pantry-backup). Samme
// versjonerte wrapper-idé som .kbhrecipe, men eget format-navn slik at de
// to filtypene aldri kan forveksles eller åpnes i feil flyt.

const PANTRY_BACKUP_FORMAT = "kbhpantry";
const PANTRY_BACKUP_VERSION = 1;

function byggPantryBackupInnhold() {
  return {
    format: PANTRY_BACKUP_FORMAT,
    version: PANTRY_BACKUP_VERSION,
    exportedAt: new Date().toISOString(),
    generator: "Kvernhaug Brygghus",
    pantry: { items: allePantryItems() },
  };
}

function _pantryBackupFilnavn() {
  return `Kvernhaug-Pantry-Backup-${new Date().toISOString().slice(0, 10)}`;
}

function lastNedPantryBackup() {
  const blob = new Blob([JSON.stringify(byggPantryBackupInnhold(), null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${_pantryBackupFilnavn()}.kbhpantry`;
  a.click();
  URL.revokeObjectURL(url);
}

// Parser en importert backup-fils tekstinnhold. Returnerer { ok: true,
// items } eller { ok: false, melding }. Kontrakt (Runde 24C pkt. 17):
// WRAPPER-feil (ugyldig JSON, feil format/version, pantry.items ikke en
// array) avviser HELE importen -- ingen delvis gjetting på en fil som ikke
// engang har riktig struktur. Enkelt-ITEM-feil (korrupt rad, negativ
// mengde, desimal gjær-antall, custom uten navn, osv.) filtreres derimot
// bort stille -- samme _gyldigPantryItem-validering som lesPantryState()
// allerede bruker -- SÅ LENGE wrapperen selv er gyldig, slik at resten av
// en ellers god backup ikke går tapt pga. én dårlig rad.
function parsePantryBackupInnhold(tekst) {
  let parsed;
  try {
    parsed = JSON.parse(tekst);
  } catch {
    return { ok: false, melding: t("pantry.backup.feilUgyldigJson") };
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ok: false, melding: t("pantry.backup.feilUgyldigFil") };
  }
  if (parsed.format !== PANTRY_BACKUP_FORMAT) {
    return { ok: false, melding: t("pantry.backup.feilUgyldigFil") };
  }
  if (parsed.version !== PANTRY_BACKUP_VERSION) {
    return { ok: false, melding: t("pantry.backup.feilVersjon") };
  }
  if (!parsed.pantry || typeof parsed.pantry !== "object" || !Array.isArray(parsed.pantry.items)) {
    return { ok: false, melding: t("pantry.backup.feilUgyldigFil") };
  }
  return { ok: true, items: parsed.pantry.items.filter(_gyldigPantryItem).map(_normalisertPantryItem) };
}

// Erstatter HELE pantryet med en allerede validert item-liste (typisk fra
// parsePantryBackupInnhold()). Kjører items gjennom samme validering en
// gang til -- defense in depth, samme prinsipp som lesPantryState() --
// slik at denne funksjonen aldri kan lagre noe ugyldig uansett hvem som
// kaller den. RESTORE/REPLACE, ikke merge (Runde 24C pkt. 5) -- UI-laget
// (pantry_page.js) er ansvarlig for å bekrefte med brukeren FØR dette
// kalles. Dette er bevisst den ENE skrivefunksjonen som IKKE nekter på et
// korrupt lager -- det ER den eksplisitte, brukerbekreftede
// destruktive gjenopprettingshandlingen issue #74 sin Scope C forbeholder
// unntak for. Returnerer { ok, items } -- issue #74 utvidet den tidligere
// rene item-listen med en ok-flagg slik at et mislykket skriveforsøk
// (privat nettlesing/full kvote) kan skilles fra et vellykket, samme
// kontrakt som resten av modulen.
function erstattPantryItems(items) {
  const gyldige = (Array.isArray(items) ? items : []).filter(_gyldigPantryItem).map(_normalisertPantryItem);
  const lagret = _lagrePantryState({ format: "kbh-pantry", version: PANTRY_VERSION, items: gyldige });
  return { ok: lagret, items: gyldige };
}
