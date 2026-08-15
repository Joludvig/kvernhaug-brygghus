// Runde 25B -- .kbhbrew: datafundamentet for KBH sin hukommelse.
// DOM-fri, samme prinsipp/kontraktform som recipe_storage.js/pantry.js/
// equipment.js. INGEN UI i denne runden -- kun modellen.
//
// Et brygg er IKKE en oppskrift. En oppskrift er PLANEN; et brygg er den
// historiske HENDELSEN: hva vi planla, hva som faktisk skjedde, hva vi
// lærte. Derfor er de to atskilte objekter med hver sin lagring.
//
// FEM LAG (grensene går etter TIDSPUNKT og type sannhet):
//   1 identitet/livssyklus -- det eneste som endres gjennom hele levetiden
//   2 snapshot             -- frosset plan, skrives én gang, aldri igjen
//   3 actuals              -- målinger, sparsomme, alt valgfritt
//   4 sensing              -- brukerens opplevelse (subjektiv, kommer sent)
//   5 learning             -- hva vi tar med videre (nyttelasten)
//
// GRUNNPRINSIPP: lagre det som ikke kan gjenskapes, aldri det som kan.
// Predikert OG/FG/IBU/EBC/smaksprofil KAN ikke gjenskapes pålitelig senere
// (maltbibliotek korrigeres, alfasyrer oppdateres, beregningsmotoren
// forbedres, BJCP-data revideres) -- derfor fryses de. Avvik mellom plan og
// faktisk KAN alltid regnes ut fra to lagrede tall -- derfor lagres de
// ALDRI. Faktisk ABV regnes likeens ut ved visning fra actuals.og/fg.
//
// ET UFULLSTENDIG BRYGG ER GYLDIG. Brukeren kan skrive OG i dag, FG om tre
// uker og refleksjonen om tre måneder. Ingen felt i lag 3-5 er påkrevd, og
// ingen rekkefølge håndheves. Status er METADATA, ikke en tilstandsmaskin.

const BREW_NOKKEL = "kvernhaug_web_brygg";
const BREW_STORE_FORMAT = "kbh-brews";
const BREW_STORE_VERSION = 1;
const BREW_FIL_FORMAT = "kbhbrew";
const BREW_FIL_VERSION = 1;

// Bumpes MANUELT når calc.js/flavor.js/style.js endrer seg på en måte som
// gir andre tall for samme input. Da kan et gammelt brygg fortsatt leses
// som "beregnet med motor v1" i stedet for å se ut som en uforklarlig
// avvikende måling.
const KBH_ENGINE_VERSION = 1;

// Status er bevisst KUN tre verdier, og fritt omsettelige i alle retninger.
// "Har brygget OG?" / "har det FG?" er utledbart fra dataene selv og skal
// ikke dupliseres her. Et forkastet brygg (infisert, helt ut) er FULLVERDIG
// historikk -- ofte den mest lærerike -- ikke en feiltilstand som skjules.
const BREW_STATUSER = ["active", "done", "discarded"];

// Brukerens dom, bevisst ikke stjerner/poeng: spørsmålet er "ville jeg
// brygget denne igjen?", ikke "hvor mange poeng av 100".
const BREW_DOMMER = ["yes", "maybe", "no"];

function _tomBrewState() {
  return { format: BREW_STORE_FORMAT, version: BREW_STORE_VERSION, items: [] };
}

function _genererBrewId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return `brew-${crypto.randomUUID()}`;
  return `brew-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

// ─── Lag 2: snapshot ──────────────────────────────────────────────────────

// Plukker ut de FULLE masterdata-oppføringene for kun de ingrediensene
// oppskriften faktisk refererer. Bevisst hele oppføringen, ikke et utvalg
// felt: beregningene bruker i dag potensiale/ebc/alfa/attenuation/kategorier,
// og signaturdeteksjonen i style.js bruker selve id-ene -- men et
// håndplukket utvalg ville stille blitt feil den dagen en beregning tar i
// bruk et felt til. Snittet er lite (typisk 3-8 malt, 2-6 humle, 1 gjær).
// Egendefinerte ingredienser ligger allerede i recipe-payloaden og hentes
// derfor ikke herfra.
function _frysIngredienser(oppskrift, maltData, humleData, gjaerData) {
  const ut = { malt: {}, humle: {}, gjaer: {} };
  for (const rad of oppskrift.malt || []) {
    if (!rad.custom && rad.id && maltData[rad.id]) ut.malt[rad.id] = { ...maltData[rad.id] };
  }
  for (const rad of oppskrift.humle || []) {
    if (!rad.custom && rad.id && humleData[rad.id]) ut.humle[rad.id] = { ...humleData[rad.id] };
  }
  if (oppskrift.gjaerId && gjaerData[oppskrift.gjaerId]) {
    ut.gjaer[oppskrift.gjaerId] = { ...gjaerData[oppskrift.gjaerId] };
  }
  return ut;
}

// Fryser KUN de språkuavhengige delene av stilanalysen. analyserStilOgBalanse()
// returnerer også `balanse`, `problemer` og per-stil `mangler`/
// `onsket_sensorisk` -- alle bygget med t() og dermed på brukerens språk da.
// De skal ALDRI inn i historikken: et brygg lagret på norsk må ikke vise
// norsk tekst for en bruker som senere leser i EN. Stilnavnet er derimot en
// stabil datanøkkel fra bjcp_styles.json (samme rolle som en malt-id), ikke
// oversatt tekst.
function _frysStil(stilAnalyse) {
  if (!stilAnalyse) return null;
  const topp = (stilAnalyse.stil_liste || []).find((s) => s.stil === stilAnalyse.stil);
  return {
    stil: stilAnalyse.stil,
    score: topp && isFinite(topp.raw_score) ? topp.raw_score : null,
  };
}

// Bygger det frosne snapshotet: "hva visste KBH da dette brygget startet?"
// Skrives ÉN gang, ved opprettelse, og endres deretter aldri -- heller ikke
// for å rette en skrivefeil. Uforanderligheten ER poenget.
//
// beregning = returverdien fra beregnOppskrift() i recipe_engine.js.
// Bevisst IKKE frosset: SVG/grafikk, UI-tilstand, språkvalg,
// enhetspreferanse (alt lagres canonical), og de fulle masterdata-
// objektene (effMalt/effHumle/effGjaer inneholder HELE biblioteket).
function byggBrewSnapshot(oppskrift, beregning, maltData, humleData, gjaerData, utstyrsprofil) {
  const buGu = beregning.stilAnalyse && isFinite(beregning.stilAnalyse.bu_gu) ? beregning.stilAnalyse.bu_gu : null;
  return {
    recipe: JSON.parse(JSON.stringify(oppskrift)),
    ingredients: _frysIngredienser(oppskrift, maltData, humleData, gjaerData),
    equipment: utstyrsprofil ? { ...utstyrsprofil } : null,
    predicted: {
      og: beregning.og,
      fg: beregning.fg,
      abv: beregning.abv,
      ibu: beregning.ibu,
      ebc: beregning.ebc,
      buGu: buGu,
      flavorProfile: { ...(beregning.flavorProfile || {}) },
      style: _frysStil(beregning.stilAnalyse),
    },
    provenance: {
      engineVersion: KBH_ENGINE_VERSION,
      recipeSchemaVersion: oppskrift.recipeSchemaVersion !== undefined ? oppskrift.recipeSchemaVersion : null,
      // Svak, men ærlig masterdata-markør: antall oppføringer i biblioteket
      // på bryggetidspunktet. Datafilene har ingen egen versjonsstempling i
      // dag (se web/README.md "Ingrediensdata") -- de frosne oppføringene
      // over er uansett den autoritative kopien av hva som FAKTISK ble brukt.
      masterdata: {
        maltCount: Object.keys(maltData || {}).length,
        humleCount: Object.keys(humleData || {}).length,
        gjaerCount: Object.keys(gjaerData || {}).length,
      },
      capturedAt: new Date().toISOString(),
    },
  };
}

// ─── Validering ───────────────────────────────────────────────────────────

function _erObjekt(o) {
  return !!o && typeof o === "object" && !Array.isArray(o);
}

function _gyldigSnapshot(s) {
  if (!_erObjekt(s)) return false;
  if (!_erObjekt(s.recipe)) return false;
  if (!_erObjekt(s.predicted)) return false;
  return true;
}

// Et brygg er gyldig så snart det har identitet og et frosset snapshot.
// Lag 3-5 er ALLE valgfrie -- se filhodet: et ufullstendig brygg er gyldig
// historikk, ikke en feiltilstand.
function _gyldigBrew(b) {
  if (!_erObjekt(b)) return false;
  if (typeof b.brewId !== "string" || !b.brewId) return false;
  if (!BREW_STATUSER.includes(b.status)) return false;
  return _gyldigSnapshot(b.snapshot);
}

function _tallEllerUndefined(v) {
  const n = typeof v === "number" ? v : parseFloat(v);
  return isFinite(n) ? n : undefined;
}

function _tekstEllerUndefined(v) {
  if (typeof v !== "string") return undefined;
  const t = v.trim();
  return t ? t : undefined;
}

// Alle actuals-felt er valgfrie og lagres canonical (SG-punkter som tall,
// volum i liter). Faktisk ABV lagres ALDRI -- den regnes ut fra og/fg ved
// visning, se filhodet.
function _normaliserActuals(a) {
  if (!_erObjekt(a)) return {};
  const ut = {};
  const og = _tallEllerUndefined(a.og);
  const fg = _tallEllerUndefined(a.fg);
  const volumeL = _tallEllerUndefined(a.volumeL);
  if (og !== undefined) ut.og = og;
  if (fg !== undefined) ut.fg = fg;
  if (volumeL !== undefined) ut.volumeL = volumeL;
  const notes = _tekstEllerUndefined(a.notes);
  if (notes) ut.notes = notes;
  return ut;
}

function _normaliserSensing(s) {
  if (!_erObjekt(s)) return {};
  const ut = {};
  if (BREW_DOMMER.includes(s.judgment)) ut.judgment = s.judgment;
  if (_erObjekt(s.flavorProfile)) {
    const fp = {};
    for (const [k, v] of Object.entries(s.flavorProfile)) {
      const n = _tallEllerUndefined(v);
      if (n !== undefined) fp[k] = n;
    }
    if (Object.keys(fp).length) ut.flavorProfile = fp;
  }
  const notes = _tekstEllerUndefined(s.notes);
  if (notes) ut.notes = notes;
  return ut;
}

// nextTime er den viktigste enkeltverdien i hele modellen -- fremtidig
// hukommelse. De to andre gir den kontekst.
function _normaliserLearning(l) {
  if (!_erObjekt(l)) return {};
  const ut = {};
  const whatWorked = _tekstEllerUndefined(l.whatWorked);
  const whatChanged = _tekstEllerUndefined(l.whatChanged);
  const nextTime = _tekstEllerUndefined(l.nextTime);
  if (whatWorked) ut.whatWorked = whatWorked;
  if (whatChanged) ut.whatChanged = whatChanged;
  if (nextTime) ut.nextTime = nextTime;
  return ut;
}

function _normaliserBrew(b) {
  const ut = {
    brewId: b.brewId,
    // SVAK referanse: kun til navigasjon/gruppering ("vis alle brygg av
    // denne oppskriften"). Visning skal ALDRI avhenge av den -- snapshotet
    // er autoritativt. Slettes eller omdøpes oppskriften, er brygget
    // fortsatt komplett og lesbart.
    recipeId: typeof b.recipeId === "string" && b.recipeId ? b.recipeId : null,
    // Reservert for fremtidig delt batch (samme vørter, to gjæringskar).
    // Ikke brukt i V1, men et tomt felt nå er billig -- en migrering senere
    // er ikke.
    parentBrewId: typeof b.parentBrewId === "string" && b.parentBrewId ? b.parentBrewId : null,
    // Filidentitet, se identitetspolicyen nederst i filen.
    originBrewId: typeof b.originBrewId === "string" && b.originBrewId ? b.originBrewId : b.brewId,
    status: b.status,
    createdAt: typeof b.createdAt === "string" ? b.createdAt : new Date().toISOString(),
    snapshot: b.snapshot,
    actuals: _normaliserActuals(b.actuals),
    sensing: _normaliserSensing(b.sensing),
    learning: _normaliserLearning(b.learning),
  };
  const brewedAt = _tekstEllerUndefined(b.brewedAt);
  if (brewedAt) ut.brewedAt = brewedAt;
  return ut;
}

// ─── Lesing/skriving ──────────────────────────────────────────────────────

function lesBrewState() {
  let raa;
  try {
    raa = localStorage.getItem(BREW_NOKKEL);
  } catch {
    return _tomBrewState();
  }
  if (!raa) return _tomBrewState();

  let parsed;
  try {
    parsed = JSON.parse(raa);
  } catch {
    return _tomBrewState();
  }
  if (
    !_erObjekt(parsed) ||
    parsed.format !== BREW_STORE_FORMAT ||
    parsed.version !== BREW_STORE_VERSION ||
    !Array.isArray(parsed.items)
  ) {
    return _tomBrewState();
  }
  return {
    format: BREW_STORE_FORMAT,
    version: BREW_STORE_VERSION,
    items: parsed.items.filter(_gyldigBrew).map(_normaliserBrew),
  };
}

// Skriver og VERIFISERER ved tilbakelesing. Returnerer boolean -- lagring
// skal aldri feile stille og aldri late som den lyktes (Runde 25A pkt. 13,
// samme kontrakt som recipe_storage.js).
function _skrivBrewState(state) {
  let serialisert;
  try {
    serialisert = JSON.stringify(state);
  } catch {
    return false;
  }
  try {
    localStorage.setItem(BREW_NOKKEL, serialisert);
    return localStorage.getItem(BREW_NOKKEL) === serialisert;
  } catch {
    return false;
  }
}

function alleBrygg() {
  return lesBrewState().items;
}

function finnBrygg(brewId) {
  if (!brewId) return null;
  return alleBrygg().find((b) => b.brewId === brewId) || null;
}

function bryggForOppskrift(recipeId) {
  if (!recipeId) return [];
  return alleBrygg().filter((b) => b.recipeId === recipeId);
}

// ─── CRUD ─────────────────────────────────────────────────────────────────

// Oppretter et brygg fra et ferdig bygget snapshot. recipeId er valgfri --
// et brygg fra en ulagret kladd er like gyldig som et fra en lagret
// oppskrift.
function opprettBrygg({ snapshot, recipeId, parentBrewId }) {
  if (!_gyldigSnapshot(snapshot)) return { ok: false, melding: t("brygg.feilUgyldigSnapshot") };
  const state = lesBrewState();
  const brewId = _genererBrewId();
  const brew = _normaliserBrew({
    brewId,
    recipeId: recipeId || null,
    parentBrewId: parentBrewId || null,
    originBrewId: brewId,
    status: "active",
    createdAt: new Date().toISOString(),
    snapshot,
    actuals: {}, sensing: {}, learning: {},
  });
  state.items.push(brew);
  if (!_skrivBrewState(state)) return { ok: false, melding: t("brygg.feilLagring") };
  return { ok: true, brew };
}

// Oppdaterer lag 1 (status), 3 (actuals), 4 (sensing) og 5 (learning).
// Snapshotet er UTELUKKET fra endring -- det er hele poenget med at det er
// frosset. Alle felt kan fylles ut når som helst, i hvilken som helst
// rekkefølge, og endres i ettertid.
function oppdaterBrygg(brewId, endringer) {
  const state = lesBrewState();
  const idx = state.items.findIndex((b) => b.brewId === brewId);
  if (idx === -1) return { ok: false, melding: t("brygg.feilFinnesIkke") };
  const forrige = state.items[idx];

  if (endringer.status !== undefined && !BREW_STATUSER.includes(endringer.status)) {
    return { ok: false, melding: t("brygg.feilUgyldigStatus") };
  }

  const oppdatert = {
    ...forrige,
    status: endringer.status !== undefined ? endringer.status : forrige.status,
    actuals: endringer.actuals !== undefined ? _normaliserActuals({ ...forrige.actuals, ...endringer.actuals }) : forrige.actuals,
    sensing: endringer.sensing !== undefined ? _normaliserSensing({ ...forrige.sensing, ...endringer.sensing }) : forrige.sensing,
    learning: endringer.learning !== undefined ? _normaliserLearning({ ...forrige.learning, ...endringer.learning }) : forrige.learning,
    snapshot: forrige.snapshot,
  };
  const brewedAt = _tekstEllerUndefined(endringer.brewedAt);
  if (brewedAt) oppdatert.brewedAt = brewedAt;

  state.items[idx] = oppdatert;
  if (!_skrivBrewState(state)) return { ok: false, melding: t("brygg.feilLagring") };
  return { ok: true, brew: oppdatert };
}

function slettBrygg(brewId) {
  const state = lesBrewState();
  const forrige = state.items.length;
  state.items = state.items.filter((b) => b.brewId !== brewId);
  if (state.items.length === forrige) return false;
  return _skrivBrewState(state);
}

// ─── Avledede verdier -- ALDRI lagret, alltid beregnet ────────────────────
// Se filhodet: avvik kan alltid gjenskapes fra to lagrede tall, og skal
// derfor aldri persisteres. Faktisk ABV likeens.

function faktiskAbv(brew) {
  const og = brew && brew.actuals ? brew.actuals.og : undefined;
  const fg = brew && brew.actuals ? brew.actuals.fg : undefined;
  if (!isFinite(og) || !isFinite(fg)) return null;
  return (og - fg) * 131.25;
}

function planVsFaktisk(brew) {
  if (!brew || !brew.snapshot) return null;
  const p = brew.snapshot.predicted || {};
  const a = brew.actuals || {};
  const diff = (faktisk, planlagt) =>
    isFinite(faktisk) && isFinite(planlagt) ? { planlagt, faktisk, avvik: faktisk - planlagt } : null;
  return {
    og: diff(a.og, p.og),
    fg: diff(a.fg, p.fg),
    abv: diff(faktiskAbv(brew), p.abv),
    volumL: diff(a.volumeL, brew.snapshot.recipe ? brew.snapshot.recipe.volum : undefined),
  };
}

// Faktisk effektivitet, utledet UTELUKKENDE fra det frosne snapshotet --
// aldri fra det levende biblioteket eller ved å kjøre beregnOG() på nytt.
// Det er nettopp poenget: et brygg fra i fjor skal gi samme svar i dag.
//
// beregnOG() i calc.js er (OG-1)*1000 = totalePoeng * eff * 8.3454 / volum.
// Fra planen kjenner vi OG, eff og volum, og kan derfor eliminere
// totalePoeng helt:
//   effFaktisk = (OGfaktisk-1) * volumFaktisk * effPlan
//                / ((OGplan-1) * volumPlan)
// Mangler faktisk volum, brukes planlagt volum -- da måler tallet ren
// meskeutnyttelse ved forventet volum.
function faktiskEffektivitet(brew) {
  if (!brew || !brew.snapshot) return null;
  const plan = brew.snapshot.predicted || {};
  const recipe = brew.snapshot.recipe || {};
  const a = brew.actuals || {};
  const ogFaktisk = a.og;
  const ogPlan = plan.og;
  const effPlan = parseFloat(recipe.effektivitet);
  const volumPlan = parseFloat(recipe.volum);
  const volumFaktisk = isFinite(a.volumeL) ? a.volumeL : volumPlan;
  if (!isFinite(ogFaktisk) || !isFinite(ogPlan) || !isFinite(effPlan) || !isFinite(volumPlan)) return null;
  if (ogPlan <= 1 || volumPlan <= 0 || effPlan <= 0) return null;
  return ((ogFaktisk - 1) * volumFaktisk * effPlan) / ((ogPlan - 1) * volumPlan);
}

// Tilsynelatende utgjæringsgrad i prosent, (OG-FG)/(OG-1).
function faktiskUtgjaering(brew) {
  const a = (brew && brew.actuals) || {};
  if (!isFinite(a.og) || !isFinite(a.fg) || a.og <= 1) return null;
  return ((a.og - a.fg) / (a.og - 1)) * 100;
}

// Den sirkulære læringssløyfen (Runde 25C): hent KUN den ene tekststrengen
// som trengs for å vise "Erfaring fra forrige gang" før et nytt brygg
// startes. Bevisst lettvekts -- laster ikke hele historikken inn i UI-et.
// Nyeste brygg med et utfylt nextTime vinner.
function sisteErfaringForOppskrift(recipeId) {
  if (!recipeId) return null;
  const kandidater = alleBrygg().filter(
    (b) => b.recipeId === recipeId && b.learning && b.learning.nextTime
  );
  if (!kandidater.length) return null;
  kandidater.sort((a, b) => String(b.createdAt || "").localeCompare(String(a.createdAt || "")));
  const nyeste = kandidater[0];
  return {
    nextTime: nyeste.learning.nextTime,
    navn: nyeste.snapshot && nyeste.snapshot.recipe ? nyeste.snapshot.recipe.navn : null,
    createdAt: nyeste.createdAt,
  };
}

// Hva trenger dette brygget NÅ? UI-et organiseres etter dette, ikke etter
// datamodellen og ikke etter status alene -- status er brukerens egen
// markering, mens fasen utledes av hva som faktisk er fylt ut.
//   "bryggedag"  -> ingen OG ennå
//   "gjaering"   -> OG målt, venter på FG
//   "smaking"    -> FG målt, ingen dom ennå
//   "ferdig"     -> dom avgitt
//   "forkastet"  -> brukeren har markert brygget som forkastet
function bryggFase(brew) {
  if (!brew) return null;
  if (brew.status === "discarded") return "forkastet";
  const a = brew.actuals || {};
  if (!isFinite(a.og)) return "bryggedag";
  if (!isFinite(a.fg)) return "gjaering";
  if (!brew.sensing || !brew.sensing.judgment) return "smaking";
  return "ferdig";
}

// ─── .kbhbrew-fil ─────────────────────────────────────────────────────────
//
// IDENTITETSPOLICY (Runde 25B oppgave 3). Brygg skiller seg fra oppskrifter
// på ett avgjørende punkt: en importert .kbhrecipe lander i den aktive
// kladden og blir først lagret når brukeren trykker Lagre -- mens en
// importert .kbhbrew er en HISTORIKK-gjenoppretting som må skrives rett i
// lageret. Å bare mynte ny id ved hver import (recipe-policyen) ville
// dermed duplisert hele historikken hver gang samme backup ble importert.
//
// Derfor skilles tre begreper:
//   brewId       -- LOKAL lagringsidentitet. Myntes alltid lokalt, adopteres
//                   ALDRI fra en fil. Hindrer id-kollisjon mellom nettlesere.
//   originBrewId -- HISTORISK/fil-identitet. Følger med filen og identifiserer
//                   den samme historiske hendelsen på tvers av maskiner.
//   filformat    -- {format:"kbhbrew", version, exportedAt, generator, brew}
//
//   A) egen historikk til ny maskin -> originBrewId bevares, ny lokal brewId
//   B) delt med en annen brygger    -> ingen id-kollisjon, kilden er sporbar
//   C) samme fil importert flere ganger -> gjenkjennes på originBrewId og
//      dupliseres ikke stille
//
// Ingen sammenslåing/overskriving skjer automatisk -- parseren rapporterer
// duplikat, og et fremtidig UI-lag avgjør hva som skal skje.

function byggKbhBrewInnhold(brew) {
  return {
    format: BREW_FIL_FORMAT,
    version: BREW_FIL_VERSION,
    exportedAt: new Date().toISOString(),
    generator: "Kvernhaug Brygghus",
    brew: {
      originBrewId: brew.originBrewId || brew.brewId,
      parentBrewId: brew.parentBrewId || null,
      status: brew.status,
      createdAt: brew.createdAt,
      brewedAt: brew.brewedAt,
      snapshot: brew.snapshot,
      actuals: brew.actuals,
      sensing: brew.sensing,
      learning: brew.learning,
    },
  };
}

// Returnerer { ok: true, brew } eller { ok: false, melding }. Wrapper-feil
// avviser HELE filen -- samme kontrakt som .kbhpantry (Runde 24C pkt. 17).
// Den returnerte brew-en har ENNÅ ingen lokal brewId; den myntes i
// importerBrygg().
function parseKbhBrewInnhold(tekst) {
  let parsed;
  try {
    parsed = JSON.parse(tekst);
  } catch {
    return { ok: false, melding: t("brygg.feilUgyldigJson") };
  }
  if (!_erObjekt(parsed) || parsed.format !== BREW_FIL_FORMAT) {
    return { ok: false, melding: t("brygg.feilUgyldigFil") };
  }
  if (parsed.version !== BREW_FIL_VERSION) {
    return { ok: false, melding: t("brygg.feilVersjon") };
  }
  if (!_erObjekt(parsed.brew) || !_gyldigSnapshot(parsed.brew.snapshot)) {
    return { ok: false, melding: t("brygg.feilUgyldigFil") };
  }
  return { ok: true, brew: parsed.brew };
}

// Skriver en importert brew til lageret med FERSK lokal brewId. Returnerer
// { ok:false, duplikat:true } dersom samme historiske hendelse allerede
// finnes (originBrewId), i stedet for å duplisere stille.
function importerBrygg(filBrew) {
  const origin = typeof filBrew.originBrewId === "string" && filBrew.originBrewId ? filBrew.originBrewId : null;
  if (origin && alleBrygg().some((b) => b.originBrewId === origin)) {
    return { ok: false, duplikat: true, melding: t("brygg.feilDuplikat") };
  }
  const state = lesBrewState();
  const brew = _normaliserBrew({
    brewId: _genererBrewId(),
    // Den svake oppskriftsreferansen er LOKAL og følger derfor aldri med en
    // fil -- oppskrift-id-ene i mottakerens nettleser er andre enn i
    // avsenderens. Snapshotet gjør brygget lesbart uansett.
    recipeId: null,
    parentBrewId: filBrew.parentBrewId || null,
    originBrewId: origin || _genererBrewId(),
    status: BREW_STATUSER.includes(filBrew.status) ? filBrew.status : "done",
    createdAt: filBrew.createdAt,
    brewedAt: filBrew.brewedAt,
    snapshot: filBrew.snapshot,
    actuals: filBrew.actuals,
    sensing: filBrew.sensing,
    learning: filBrew.learning,
  });
  state.items.push(brew);
  if (!_skrivBrewState(state)) return { ok: false, melding: t("brygg.feilLagring") };
  return { ok: true, brew };
}
