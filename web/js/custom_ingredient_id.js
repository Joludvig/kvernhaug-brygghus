// PRI 4C (issue #50) -- Web-side adopsjon av Core sin custom-ingredient
// identity-kontrakt (docs/development/CORE_CUSTOM_INGREDIENT_IDENTITY_V1.md).
// DOM-fri delt modul (samme prinsipp som equipment.js/recipe_engine.js),
// lastet FØR app.js/pantry.js -- de to eneste stedene i Web som i dag
// oppretter NYE egendefinerte ingredienser (kontraktens §3: ETT delt,
// opakt navnerom for custom malt/humle/gjær/pantry -- ikke lenger tre
// separate egen_*-navnerom).
//
// Allerede lagrede legacy `egen_*`-ider (app.js sin gamle nyEgendefinertId(),
// pantry.js sin gamle nyPantryCustomId()) er PERMANENT grandfatret av
// kontraktens §9 og røres ALDRI av denne filen -- den styrer kun ID-er
// mintet FRA OG MED nå.

const CUSTOM_INGREDIENT_ID_PREFIX = "kbh-custom-";

// Kontraktens §5 krever en kryptografisk sterk kilde. crypto.randomUUID()
// finnes ikke i alle kontekster (kun "secure context") -- i motsetning til
// pantry.js/equipment.js/recipe_storage.js/brew_storage.js sine egne
// id-generatorer (som har et svakt Date.now()+Math.random()-fallback, godt
// nok for DERES formål) faller denne ALDRI tilbake til noe ikke-kryptografisk,
// siden kontraktens eksakte kbh-custom-<uuidv4>-format er normativt her, ikke
// bare "ser unik nok ut". crypto.getRandomValues() er derimot tilgjengelig i
// enhver kontekst en nettleser kan kjøre denne filen i, så det er valgt som
// den universelle veien -- crypto.randomUUID() brukes kun som en ren
// snarvei når den finnes.
function _uuidV4() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // versjon 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 10xx
  const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0"));
  return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex.slice(6, 8).join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10, 16).join("")}`;
}

// Én ingrediens-rad i .kbhrecipe-formen (samleOppskrift()/_gjenopprettOppskrift()
// i app.js) sine egendefinerte id-er -- malt[]/humle[] bærer id+custom side
// om side, gjaerCustom bærer sin egen id INNI seg (se app.js). Brukes både på
// lagrede oppskrifter (recipe_storage.js) og på frosne brygg-snapshots
// (brew_storage.js sitt snapshot.recipe er en dypkopi av nøyaktig samme form).
function _customIngredientIderIOppskrift(recipe) {
  if (!recipe || typeof recipe !== "object") return [];
  const ider = [];
  for (const rad of Array.isArray(recipe.malt) ? recipe.malt : []) {
    if (rad && rad.custom && typeof rad.id === "string" && rad.id) ider.push(rad.id);
  }
  for (const rad of Array.isArray(recipe.humle) ? recipe.humle : []) {
    if (rad && rad.custom && typeof rad.id === "string" && rad.id) ider.push(rad.id);
  }
  if (!recipe.gjaerId && recipe.gjaerCustom && typeof recipe.gjaerCustom.id === "string" && recipe.gjaerCustom.id) {
    ider.push(recipe.gjaerCustom.id);
  }
  return ider;
}

// Chief-runde (PR #52 review): AKTIV_KLADD_NOKKEL -- den aktive, ulagrede
// kladden i byggeren -- er et FJERDE lokalt lagringssted som kan holde en
// custom-ingrediens-id, fordi app.js autolagrer den assemblerte oppskriften
// dit ved HVER beregning (se app.js sin hentAktivKladd()/AKTIV_KLADD_NOKKEL-
// kommentar), altså lenge før raden noensinne havner i alleOppskrifter(),
// pantry eller et brygg-snapshot. Uten denne kilden ville et
// generasjonstids-kollisjon-forsøk mot en id som KUN finnes i den aktive
// kladden bli akseptert, i strid med kontraktens §6. AKTIV_KLADD_NOKKEL er
// en konstant (ikke en funksjon som de tre andre kildene over), definert i
// BÅDE app.js og pantry_page.js -- begge alltid lastet ETTER denne filen
// (se <script>-rekkefølgen i index.html/pantry.html) -- så samme
// feature-detection-prinsipp (typeof ... !== "undefined") brukes her også.
function _aktivKladdCustomIngredientIder() {
  if (typeof AKTIV_KLADD_NOKKEL === "undefined") return [];
  try {
    return _customIngredientIderIOppskrift(JSON.parse(localStorage.getItem(AKTIV_KLADD_NOKKEL)));
  } catch {
    return [];
  }
}

// Kontraktens §6 -- kollisjonssjekken ved MINTING må dekke ETHVERT lokalt
// lagringssted som kan holde en custom-ingrediens-id i dag: pantry, alle
// lagrede oppskrifter, alle frosne brygg-snapshots, og den aktive kladden
// (ALDRI kun samlingen man er i ferd med å skrive til). Hver kilde er
// bevisst feature-detected (typeof ... === "function"/"undefined") i stedet
// for antatt lastet -- denne filen lastes kun på de to sidene som faktisk
// MINTER nye id-er (index.html, pantry.html). Begge sider laster nå alle
// tre lagrings-modulene (pantry.js/recipe_storage.js/brew_storage.js) i
// tillegg til denne filen, slik at feature-detecten alltid finner alle tre
// der -- se <script>-rekkefølgen i index.html/pantry.html.
function alleLokaleCustomIngredientIder() {
  const ider = new Set();
  if (typeof allePantryItems === "function") {
    for (const item of allePantryItems()) {
      if (item && item.custom && typeof item.id === "string" && item.id) ider.add(item.id);
    }
  }
  if (typeof alleOppskrifter === "function") {
    for (const rad of alleOppskrifter()) {
      for (const id of _customIngredientIderIOppskrift(rad.recipe)) ider.add(id);
    }
  }
  if (typeof alleBrygg === "function") {
    for (const brew of alleBrygg()) {
      const recipe = brew && brew.snapshot ? brew.snapshot.recipe : null;
      for (const id of _customIngredientIderIOppskrift(recipe)) ider.add(id);
    }
  }
  for (const id of _aktivKladdCustomIngredientIder()) ider.add(id);
  return ider;
}

// Mint en fersk custom-ingrediens-id i kontraktens kanoniske format
// (§3: `kbh-custom-<uuidv4>`). Generasjonstids-kollisjon (statistisk sett
// forsvinnende usannsynlig med UUIDv4, men kontraktens §6 krever likevel
// defensiv håndtering): mint en NY id i stedet for å gjenbruke/overskrive
// -- aldri omvendt. Kalles av app.js (malt/humle/gjær) og pantry.js
// (pantry custom-varer) -- de eneste to stedene Web oppretter en NY
// egendefinert ingrediens i dag.
function nyCustomIngredientId() {
  const kjente = alleLokaleCustomIngredientIder();
  let id = `${CUSTOM_INGREDIENT_ID_PREFIX}${_uuidV4()}`;
  while (kjente.has(id)) {
    id = `${CUSTOM_INGREDIENT_ID_PREFIX}${_uuidV4()}`;
  }
  return id;
}
