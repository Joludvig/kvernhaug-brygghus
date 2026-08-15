// Runde 25A -- versjonert lagring av oppskrifter med STABILE ID-er.
// DOM-fri, samme prinsipp/kontraktform som equipment.js/preferences.js/
// pantry.js. Lastet FØR sidenes egne page-script.
//
// BAKGRUNN: fram til denne runden var kvernhaug_web_oppskrifter en flat
// ordbok nøklet på OPPSKRIFTSNAVN -- den eneste lagringskontrakten i
// systemet uten format/version-wrapper. Navnet var altså også identiteten,
// med to konsekvenser: (1) å endre navn og lagre opprettet en NY rad og lot
// den gamle bli liggende (utilsiktet duplikat), og (2) ingen annen del av
// systemet kunne holde en referanse til en oppskrift som overlevde et
// navnebytte. Det siste blokkerte fremtidig .kbhbrew, som må kunne peke
// svakt på en oppskrift OG bære et frosset snapshot av den.
//
// KONTRAKTEN FRA OG MED NÅ:
//   recipeId  = stabil, lokal identitet. Genereres én gang, endres aldri,
//               overlever navnebytte. Aldri utledet fra navnet.
//   navn      = ren visningsmetadata. Kan endres fritt.
//
// LAGRINGSFORM (kvernhaug_web_oppskrifter):
//   { format: "kbh-recipes", version: 1, items: [ { recipeId, recipe } ] }
//
// Hvorfor recipe ligger NESTET og ikke flatt sammen med recipeId: `recipe`
// er da nøyaktig den samme selvstendige payloaden som .kbhrecipe sitt
// `recipe`-felt og som samleOppskrift() produserer -- ett objekt som kan
// løftes ut og fryses i sin helhet. Et fremtidig .kbhbrew-snapshot er
// dermed bokstavelig talt item.recipe, uten at lagringsmetadata (recipeId,
// og hva som ellers måtte komme) blør inn i den frosne historikken eller ut
// i eksporterte filer.
//
// SCHEMA-VERSJON: recipeSchemaVersion ligger INNE i selve payloaden, ikke
// som søsken til den. Det er bevisst: versjonen må reise SAMMEN med
// oppskriften inn i .kbhrecipe-filer og (senere) inn i .kbhbrew-snapshots
// som skal kunne tolkes om mange år. En versjon som ligger utenfor
// payloaden går tapt i det øyeblikket payloaden løftes ut.

const OPPSKRIFT_NOKKEL = "kvernhaug_web_oppskrifter";
const OPPSKRIFT_LEGACY_BACKUP_NOKKEL = "kvernhaug_web_oppskrifter_legacy_backup";
const OPPSKRIFT_STORE_FORMAT = "kbh-recipes";
const OPPSKRIFT_STORE_VERSION = 1;

// Semantisk versjon på selve oppskrifts-payloaden (malt/humle/gjaerId/...).
// Økes KUN når payloadens betydning endres på en måte en gammel leser ikke
// kan tolke riktig -- ikke ved rene tillegg av valgfrie felt.
const RECIPE_SCHEMA_VERSION = 1;

function _tomOppskriftState() {
  return { format: OPPSKRIFT_STORE_FORMAT, version: OPPSKRIFT_STORE_VERSION, items: [] };
}

// Samme id-mønster som pantry.js/equipment.js -- crypto.randomUUID der den
// finnes, ellers tid+tilfeldighet. Ingen eksterne bibliotek, ingen backend.
function _genererRecipeId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return `recipe-${crypto.randomUUID()}`;
  return `recipe-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

// Lett "ser dette ut som en oppskrift?"-sjekk, bevisst tolerant: en
// oppskrift kan være nesten tom (fersk kladd) og skal likevel ikke kastes.
// Speiler _erGyldigOppskriftForm() i kbhrecipe.js, men duplisert lokalt
// fordi denne filen også lastes på sider som ikke laster kbhrecipe.js.
function _erOppskriftForm(o) {
  if (!o || typeof o !== "object" || Array.isArray(o)) return false;
  return ["navn", "malt", "humle", "gjaerId", "gjaerCustom", "volum", "brygger", "bryggeri"].some((f) => f in o);
}

// Defensiv normalisering av payloaden. malt/humle MÅ være arrays -- både
// beregnOppskrift() og _gjenopprettOppskrift() itererer over dem.
// recipeId strippes bevisst HER også: lokal lagringsidentitet skal aldri
// ligge inne i payloaden (se _importertRecipeUtenLokalId under).
function _normalisertRecipe(recipe) {
  const ut = { ...recipe };
  delete ut.recipeId;
  ut.recipeSchemaVersion = RECIPE_SCHEMA_VERSION;
  if (!Array.isArray(ut.malt)) ut.malt = [];
  if (!Array.isArray(ut.humle)) ut.humle = [];
  return ut;
}

function _gyldigItem(item) {
  if (!item || typeof item !== "object") return false;
  if (typeof item.recipeId !== "string" || !item.recipeId) return false;
  return _erOppskriftForm(item.recipe);
}

function _normalisertItem(item) {
  return { recipeId: item.recipeId, recipe: _normalisertRecipe(item.recipe) };
}

// ─── Migrering fra flat, navne-nøklet ordbok ──────────────────────────────

function _erLegacyFlatOrdbok(parsed) {
  return !!parsed && typeof parsed === "object" && !Array.isArray(parsed) && parsed.format === undefined;
}

function _migrerLegacy(parsed) {
  const items = [];
  // Object.keys bevarer innsettingsrekkefølgen for strengnøkler, slik at
  // brukerens liste ser lik ut før og etter migreringen.
  for (const navn of Object.keys(parsed)) {
    const recipe = parsed[navn];
    if (!_erOppskriftForm(recipe)) continue; // hopp over korrupt rad, behold resten
    const normalisert = _normalisertRecipe(recipe);
    // Navnet var identiteten før -- behold det som visningsnavn, også om
    // selve payloaden manglet/hadde et avvikende navnefelt.
    if (typeof normalisert.navn !== "string" || !normalisert.navn) normalisert.navn = navn;
    items.push({ recipeId: _genererRecipeId(), recipe: normalisert });
  }
  return { format: OPPSKRIFT_STORE_FORMAT, version: OPPSKRIFT_STORE_VERSION, items };
}

// Rå backup av den gamle strengen FØR hovednøkkelen overskrives, med
// verifiserende tilbakelesing. Returnerer false hvis backupen ikke kunne
// skrives ELLER ikke kunne leses tilbake identisk -- da skal migreringen
// ikke persisteres i det hele tatt (se _persisterMigrering).
function _sikreLegacyBackup(raa) {
  try {
    const eksisterende = localStorage.getItem(OPPSKRIFT_LEGACY_BACKUP_NOKKEL);
    // Migrering kjøres kun én gang, men hvis en backup allerede finnes
    // (f.eks. fra et avbrutt forsøk) skal den ALDRI overskrives -- den
    // eldste kopien er den mest verdifulle.
    if (eksisterende !== null) return true;
    localStorage.setItem(OPPSKRIFT_LEGACY_BACKUP_NOKKEL, raa);
    return localStorage.getItem(OPPSKRIFT_LEGACY_BACKUP_NOKKEL) === raa;
  } catch {
    return false;
  }
}

// Skriver state og VERIFISERER ved tilbakelesing. Returnerer boolean i
// stedet for å svelge feilen stille -- kallende UI-lag kan da si fra til
// brukeren (Runde 25A pkt. 13). Full lagringskvote og privat nettlesing er
// de reelle tilfellene.
function _skrivOppskriftState(state) {
  let serialisert;
  try {
    serialisert = JSON.stringify(state);
  } catch {
    return false;
  }
  try {
    localStorage.setItem(OPPSKRIFT_NOKKEL, serialisert);
    return localStorage.getItem(OPPSKRIFT_NOKKEL) === serialisert;
  } catch {
    return false;
  }
}

// Persisterer en migrert state, men ALDRI før den gamle rådataen er trygt
// sikkerhetskopiert. Feiler noe som helst underveis, lar vi den gamle
// nøkkelen stå urørt -- appen kjører videre på den migrerte staten i minnet,
// og et nytt forsøk skjer ved neste lesing. Ingenting går tapt.
function _persisterMigrering(state, raa) {
  if (!_sikreLegacyBackup(raa)) return false;
  return _skrivOppskriftState(state);
}

// ─── Lesing ───────────────────────────────────────────────────────────────

// Kaster aldri. Håndterer: tom nøkkel, ugyldig JSON, gammel flat ordbok,
// ny wrapper, feil format/version, items som ikke er array, og enkeltrader
// som er korrupte (filtreres bort, resten beholdes).
function lesOppskriftState() {
  let raa;
  try {
    raa = localStorage.getItem(OPPSKRIFT_NOKKEL);
  } catch {
    return _tomOppskriftState();
  }
  if (!raa) return _tomOppskriftState();

  let parsed;
  try {
    parsed = JSON.parse(raa);
  } catch {
    return _tomOppskriftState();
  }

  if (_erLegacyFlatOrdbok(parsed)) {
    const migrert = _migrerLegacy(parsed);
    _persisterMigrering(migrert, raa);
    return migrert;
  }

  if (
    !parsed || typeof parsed !== "object" ||
    parsed.format !== OPPSKRIFT_STORE_FORMAT ||
    parsed.version !== OPPSKRIFT_STORE_VERSION ||
    !Array.isArray(parsed.items)
  ) {
    return _tomOppskriftState();
  }

  return {
    format: OPPSKRIFT_STORE_FORMAT,
    version: OPPSKRIFT_STORE_VERSION,
    items: parsed.items.filter(_gyldigItem).map(_normalisertItem),
  };
}

function alleOppskrifter() {
  return lesOppskriftState().items;
}

function finnOppskrift(recipeId) {
  if (!recipeId) return null;
  return alleOppskrifter().find((i) => i.recipeId === recipeId) || null;
}

function finnOppskriftVedNavn(navn) {
  return alleOppskrifter().find((i) => i.recipe.navn === navn) || null;
}

// ─── Skriving ─────────────────────────────────────────────────────────────

// Lagrer en oppskrift og returnerer { ok: true, recipeId } eller
// { ok: false, melding }.
//
// Identitet: oppgitt recipeId brukes hvis den finnes (oppdatering i
// stedet for duplikat -- dette er selve navnebytte-fiksen). Ellers
// genereres en ny.
//
// Navneunikhet: BEVART fra den gamle kontrakten. Den flate ordboken gjorde
// duplikatnavn teknisk umulig -- `alle[navn] = oppskrift` erstattet stille
// en eksisterende oppskrift med samme navn. Den nye modellen tillater
// duplikatnavn teknisk, men Runde 25A skal ikke åpne nytt UX-scope, så
// regelen håndheves eksplisitt her: en annen rad med samme navn fjernes,
// nøyaktig som før.
function lagreOppskriftIStore(recipe, recipeId) {
  if (!_erOppskriftForm(recipe)) return { ok: false, melding: t("oppskrift.lagreFeil") };

  const state = lesOppskriftState();
  const normalisert = _normalisertRecipe(recipe);
  const id = recipeId || _genererRecipeId();

  state.items = state.items.filter((i) => i.recipeId !== id && i.recipe.navn !== normalisert.navn);
  state.items.push({ recipeId: id, recipe: normalisert });

  if (!_skrivOppskriftState(state)) return { ok: false, melding: t("oppskrift.lagreFeil") };
  return { ok: true, recipeId: id };
}

function slettOppskriftFraStore(recipeId) {
  const state = lesOppskriftState();
  const forrige = state.items.length;
  state.items = state.items.filter((i) => i.recipeId !== recipeId);
  if (state.items.length === forrige) return false;
  return _skrivOppskriftState(state);
}

// ─── .kbhrecipe-identitet (Runde 25A pkt. 10) ─────────────────────────────
// En recipeId er LOKAL identitet, aldri global. Den skrives derfor aldri
// til en .kbhrecipe-fil og leses aldri fra en.
//
//   A) egen backup som importeres igjen -> ny lokal id ved lagring
//   B) fil delt med en annen brygger      -> mottakerens egen lokale id
//   C) samme fil importert flere ganger   -> ingen id-kollisjon
//
// Uten dette ville to nettlesere kunne ende opp med samme recipeId for det
// som i praksis er to uavhengige oppskrifter -- og et fremtidig .kbhbrew
// ville pekt på feil oppskrift. Import lander uansett i den aktive kladden
// (ikke direkte i lageret), så en fersk id oppstår naturlig først når
// brukeren faktisk trykker Lagre.
//
// recipeSchemaVersion følger derimot MED payloaden -- den beskriver
// oppskriftens form, ikke hvem som eier den.
function _importertRecipeUtenLokalId(recipe) {
  const ut = { ...recipe };
  delete ut.recipeId;
  return ut;
}
