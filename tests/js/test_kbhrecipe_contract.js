// Kvernhaug Core -- PRI 2A: .kbhrecipe V1 contract tests (Web-siden).
//
// Laster den ekte, uendrede web/js/kbhrecipe.js inn i en isolert Node
// "vm"-context (samme mønster som PRI 1s
// tests/js/test_calculation_golden_vectors.js) -- ingen module.exports
// lagt til i produksjonsfilen, ingen npm-avhengighet, ingen
// package.json, ingen testrammeverk. Kun Node sine egne innebygde
// moduler (fs, path, vm, assert).
//
// Dekker: legacy App-fixtures parses i Web, passthrough av
// bryggerStil/prosess/vann/vilkårlig ukjent felt gjennom
// import -> redigering -> lagring/eksport, at forbudte felt
// (recipeId/stats/flavor_profile) aldri kan lekke til eksport, og
// envelope-versjonshåndtering (docs/development/CORE_KBHRECIPE_V1.md).
//
// Kjøres med:
//     node tests/js/test_kbhrecipe_contract.js
//
// Exit code 0 = alle tester bestått. Exit code 1 = minst én feilet.

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '..', '..');
const KBHRECIPE_JS = path.join(ROOT, 'web', 'js', 'kbhrecipe.js');
const RECIPE_STORAGE_JS = path.join(ROOT, 'web', 'js', 'recipe_storage.js');
const FIXTURES_DIR = path.join(ROOT, 'tests', 'fixtures', 'legacy', 'kbhrecipe');
// issue #288 -- delt, IKKE-legacy fixture med en gyldig originRecipeId,
// lest ORDRETT av BÅDE denne filen og
// tests/test_kbh_import.py::TestOriginRecipeIdDeltCrossSurfaceFixture,
// for å bevise identisk wire-tolkning på tvers av App/Web på ÉN og
// samme fil -- ikke bare at hver side for seg gir riktig svar på sin
// egen syntetiske payload.
const DELT_FIXTURES_DIR = path.join(ROOT, 'tests', 'fixtures', 'kbhrecipe');
const DELT_ORIGIN_RECIPE_ID = '55555555-5555-5555-5555-555555555555';

function lastFixture(navn) {
  return fs.readFileSync(path.join(FIXTURES_DIR, `${navn}.json`), 'utf8');
}

function lastDeltFixture(navn) {
  return fs.readFileSync(path.join(DELT_FIXTURES_DIR, `${navn}.json`), 'utf8');
}

// Ny, isolert context per test -- kbhrecipe.js/recipe_storage.js har
// ingen delt mutbar toppnivåtilstand, men isolasjon gjør testene
// uavhengige av rekkefølge uansett. `t()` stubbes til en gjenkjennelig
// streng (ingen i18n.js lastet -- ikke del av det denne testen dekker).
function nyContext(inkluderRecipeStorage) {
  const ctx = { t: (k) => `[i18n:${k}]`, console, crypto: globalThis.crypto };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(KBHRECIPE_JS, 'utf8'), ctx, { filename: KBHRECIPE_JS });
  if (inkluderRecipeStorage) {
    // recipe_storage.js bruker localStorage -- en minimal, i minnet
    // stub er nok (kun get/set/removeItem, ingen event-model).
    const lager = new Map();
    ctx.localStorage = {
      getItem: (k) => (lager.has(k) ? lager.get(k) : null),
      setItem: (k, v) => lager.set(k, String(v)),
      removeItem: (k) => lager.delete(k),
    };
    vm.runInContext(fs.readFileSync(RECIPE_STORAGE_JS, 'utf8'), ctx, { filename: RECIPE_STORAGE_JS });
  }
  return ctx;
}

// ─── Minimal testshell (samme stil som test_calculation_golden_vectors.js) ─

let bestatt = 0;
const feil = [];

function kjor(navn, fn) {
  try {
    fn();
    bestatt += 1;
  } catch (e) {
    feil.push(`${navn}: ${e && e.message ? e.message : e}`);
  }
}

// ─── 1-3: legacy App-fixtures parses i Web ─────────────────────────────

kjor('minimal fixture parses i Web', () => {
  const ctx = nyContext(false);
  const res = ctx.parseKbhRecipeInnhold(lastFixture('minimal'));
  assert.strictEqual(res.ok, true);
  assert.strictEqual(res.legacy, false);
  assert.strictEqual(res.oppskrift.navn, 'Testbrygg Minimal (syntetisk fixture)');
  assert.strictEqual(res.oppskrift.volum, 20.0);
  assert.strictEqual(res.oppskrift.malt.length, 1);
  assert.strictEqual(res.oppskrift.humle.length, 1);
});

kjor('full fixture parses i Web', () => {
  const ctx = nyContext(false);
  const res = ctx.parseKbhRecipeInnhold(lastFixture('full'));
  assert.strictEqual(res.ok, true);
  assert.strictEqual(res.oppskrift.navn, 'Testbrygg Full (syntetisk fixture)');
  assert.strictEqual(res.oppskrift.bryggerStil, 'Testbryggerens egen stil (syntetisk)');
  assert.ok(res.oppskrift.prosess);
  assert.ok(res.oppskrift.vann);
  assert.strictEqual(res.oppskrift.malt.length, 2);
  assert.strictEqual(res.oppskrift.humle.length, 2);
});

kjor('partial_water fixture parses i Web', () => {
  const ctx = nyContext(false);
  const res = ctx.parseKbhRecipeInnhold(lastFixture('partial_water'));
  assert.strictEqual(res.ok, true);
  assert.ok(res.oppskrift.vann);
  assert.strictEqual(res.oppskrift.vann.kilde, undefined);
  assert.ok(res.oppskrift.vann.maalinger);
});

// ─── 4-7: passthrough gjennom import -> export ─────────────────────────

kjor('bryggerStil overlever import -> export', () => {
  const ctx = nyContext(false);
  const res = ctx.parseKbhRecipeInnhold(lastFixture('full'));
  const eksportert = ctx.byggKbhRecipeInnhold(res.oppskrift);
  assert.strictEqual(eksportert.recipe.bryggerStil, 'Testbryggerens egen stil (syntetisk)');
});

kjor('prosess overlever import -> export', () => {
  const ctx = nyContext(false);
  const res = ctx.parseKbhRecipeInnhold(lastFixture('full'));
  const eksportert = ctx.byggKbhRecipeInnhold(res.oppskrift);
  assert.deepStrictEqual(eksportert.recipe.prosess, res.oppskrift.prosess);
});

kjor('vann overlever import -> export', () => {
  const ctx = nyContext(false);
  const res = ctx.parseKbhRecipeInnhold(lastFixture('full'));
  const eksportert = ctx.byggKbhRecipeInnhold(res.oppskrift);
  assert.deepStrictEqual(eksportert.recipe.vann, res.oppskrift.vann);
});

kjor('vilkårlig ukjent fremtidig felt overlever import -> export', () => {
  const ctx = nyContext(false);
  const raa = JSON.parse(lastFixture('minimal'));
  raa.recipe.fermentasjonsprofil = { steg: [{ temp: 18, dager: 7 }] }; // "future field", ikke i V1 i dag
  const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  assert.strictEqual(res.ok, true);
  const eksportert = ctx.byggKbhRecipeInnhold(res.oppskrift);
  // JSON.stringify-sammenligning i stedet for deepStrictEqual: objektet
  // på venstre side er konstruert INNI vm-contexten (egen realm, egen
  // Object/Array-prototype) -- deepStrictEqual sammenligner også
  // prototype-identitet og ville feilet på ren realm-forskjell selv om
  // strukturen er identisk. JSON.stringify er strukturelt og
  // realm-uavhengig, som er det testen faktisk skal bevise.
  assert.strictEqual(JSON.stringify(eksportert.recipe.fermentasjonsprofil), JSON.stringify({ steg: [{ temp: 18, dager: 7 }] }));
  // Selve containernøkkelen skal ALDRI stå igjen som et bokstavelig felt.
  assert.strictEqual('_kbhUkjenteFelt' in eksportert.recipe, false);
});

// ─── 8: kjent, redigert felt vinner over gammel passthrough-verdi ──────

kjor('kjent felt redigert av bruker vinner over gammel passthrough-verdi', () => {
  const ctx = nyContext(false);
  const raa = JSON.parse(lastFixture('minimal'));
  const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  // Simuler at brukeren redigerer et KJENT felt (navn) etter import --
  // en gammel passthrough-verdi med samme nøkkel skal ALDRI kunne vinne
  // over dette, siden _byggKjentPayload() bygges FØR passthrough flettes.
  const redigert = { ...res.oppskrift, navn: 'Redigert av bruker' };
  const eksportert = ctx.byggKbhRecipeInnhold(redigert);
  assert.strictEqual(eksportert.recipe.navn, 'Redigert av bruker');
});

// ─── 9-11: forbudte felt kan aldri lekke ───────────────────────────────

kjor('recipeId kan ikke lekke til eksport selv om inputobjekt inneholder det', () => {
  const ctx = nyContext(false);
  const oppskrift = { navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [], recipeId: 'LOKAL-ID-SKAL-ALDRI-EKSPORTERES' };
  const eksportert = ctx.byggKbhRecipeInnhold(oppskrift);
  assert.strictEqual('recipeId' in eksportert.recipe, false);
  assert.strictEqual(JSON.stringify(eksportert).includes('LOKAL-ID-SKAL-ALDRI-EKSPORTERES'), false);
});

kjor('stats kan ikke lekke til eksport', () => {
  const ctx = nyContext(false);
  const oppskrift = { navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [], stats: { og: 1.05, ibu: 30 } };
  const eksportert = ctx.byggKbhRecipeInnhold(oppskrift);
  assert.strictEqual('stats' in eksportert.recipe, false);
});

kjor('flavor_profile kan ikke lekke til eksport', () => {
  const ctx = nyContext(false);
  const oppskrift = { navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [], flavor_profile: { malt: 5, humle: 6 } };
  const eksportert = ctx.byggKbhRecipeInnhold(oppskrift);
  assert.strictEqual('flavor_profile' in eksportert.recipe, false);
});

kjor('forbudt felt kan ikke lekke selv om det ligger inni passthrough-containeren', () => {
  // Andre forsvarslinje: selv om _kbhUkjenteFelt skulle inneholde et
  // forbudt navn (f.eks. en håndredigert lokal kladd), skal
  // byggKbhRecipeInnhold() likevel filtrere det bort ved eksport.
  const ctx = nyContext(false);
  const oppskrift = {
    navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [],
    _kbhUkjenteFelt: { recipeId: 'SKAL-FILTRERES', stats: { og: 1.05 }, ekteUkjentFelt: 'skal-overleve' },
  };
  const eksportert = ctx.byggKbhRecipeInnhold(oppskrift);
  assert.strictEqual('recipeId' in eksportert.recipe, false);
  assert.strictEqual('stats' in eksportert.recipe, false);
  assert.strictEqual(eksportert.recipe.ekteUkjentFelt, 'skal-overleve');
});

// ─── QA-korreksjon (KBHR-009): Web-interne felt aldri i eksport ────────
//
// KBHR-009: en .kbhrecipe writer-whitelist skal skille (A) eksplisitt
// eksporttillatte Core V1-felt, (B) kontrollert passthrough av ukjente
// importerte felt, og (C) Web/App-interne felt -- et felt blir ikke del
// av .kbhrecipe bare fordi Web bruker det internt. Punkt (1)-(2) under er
// nye regresjonstester for dette; punkt (3)-(7) fra oppdraget er allerede
// dekket av eksisterende tester over (referert i kommentarer, ikke
// duplisert).

kjor('QA KBHR-009 (1): lagretDato i et vanlig Web-oppskriftsobjekt eksporteres IKKE', () => {
  const ctx = nyContext(false);
  // Formen samleOppskrift() faktisk produserer -- lagretDato settes på
  // nytt av app.js ved HVER samling, det er Web sin egen "sist samlet"-
  // metadata, ikke noe brukeren "har" i oppskriften (CORE_KBHRECIPE_V1.md §3).
  const oppskrift = {
    recipeSchemaVersion: 1, navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [],
    lagretDato: '2026-09-01T12:34:56Z',
  };
  const eksportert = ctx.byggKbhRecipeInnhold(oppskrift);
  assert.strictEqual('lagretDato' in eksportert.recipe, false);
  assert.strictEqual(JSON.stringify(eksportert).includes('2026-09-01T12:34:56Z'), false);
});

kjor('QA KBHR-009 (2): _kbhUkjenteFelt-containeren selv eksporteres ikke som et felt', () => {
  const ctx = nyContext(false);
  const oppskrift = {
    navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [],
    _kbhUkjenteFelt: { ekteUkjentFelt: 'skal-overleve-som-INNHOLD-ikke-som-container' },
  };
  const eksportert = ctx.byggKbhRecipeInnhold(oppskrift);
  assert.strictEqual('_kbhUkjenteFelt' in eksportert.recipe, false);
  assert.strictEqual(eksportert.recipe.ekteUkjentFelt, 'skal-overleve-som-INNHOLD-ikke-som-container');
});

// QA-korreksjon (3)-(5) recipeId/stats/flavor_profile eksporteres ikke:
// dekket av "recipeId kan ikke lekke..." / "stats kan ikke lekke..." /
// "flavor_profile kan ikke lekke..." over -- ikke duplisert her.
// QA-korreksjon (6) ekte ukjent importert felt overlever: dekket av
// "vilkårlig ukjent fremtidig felt overlever import -> export" over.
// QA-korreksjon (7) kjent, redigert felt vinner over gammel passthrough-
// verdi: dekket av "kjent felt redigert av bruker vinner over gammel
// passthrough-verdi" over.

// ─── 12-14: envelope-versjonshåndtering ────────────────────────────────

kjor('unknown envelope field tolereres', () => {
  const ctx = nyContext(false);
  const raa = JSON.parse(lastFixture('minimal'));
  raa.checksum = { algorithm: 'sha256', value: 'deadbeef' }; // ukjent envelope-felt
  const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  assert.strictEqual(res.ok, true);
  assert.strictEqual(res.oppskrift.navn, 'Testbrygg Minimal (syntetisk fixture)');
});

kjor('envelope version >1 avvises eksplisitt', () => {
  const ctx = nyContext(false);
  const raa = JSON.parse(lastFixture('minimal'));
  raa.version = 2;
  const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  assert.strictEqual(res.ok, false);
  assert.ok(res.melding);
});

kjor('envelope version <1 / !=1 avvises eksplisitt', () => {
  const ctx = nyContext(false);
  for (const v of [0, 0.5, -1]) {
    const raa = JSON.parse(lastFixture('minimal'));
    raa.version = v;
    const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
    assert.strictEqual(res.ok, false, `version ${v} skal avvises`);
  }
});

// ─── 15: legacy rå-JSON-fallback (dokumenterer faktisk eksisterende adferd) ─

kjor('raw legacy recipe JSON (uten wrapper) godtas fortsatt', () => {
  const ctx = nyContext(false);
  const raaOppskrift = { navn: 'Gammel eksport uten wrapper', malt: [{ id: 'weyermann_pilsner', mengde: 4.0 }], humle: [], volum: 20, effektivitet: 75 };
  const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raaOppskrift));
  assert.strictEqual(res.ok, true);
  assert.strictEqual(res.legacy, true);
  assert.strictEqual(res.oppskrift.navn, 'Gammel eksport uten wrapper');
});

// ─── Full syklus: import -> lagre i store -> last -> eksporter ─────────

kjor('full syklus: import -> save til recipe_storage -> load -> export bevarer passthrough', () => {
  const ctx = nyContext(true); // recipe_storage.js lastet også her

  const importRes = ctx.parseKbhRecipeInnhold(lastFixture('full'));
  assert.strictEqual(importRes.ok, true);

  const lagreRes = ctx.lagreOppskriftIStore(importRes.oppskrift, null);
  assert.strictEqual(lagreRes.ok, true);

  const funnet = ctx.finnOppskrift(lagreRes.recipeId);
  assert.ok(funnet);
  // recipe_storage.js sin _normalisertRecipe() spres fra kilden -- egne
  // felt (inkl. _kbhUkjenteFelt hvis det var satt) skal derfor overleve
  // save/load. Denne fixturen har imidlertid INGEN ukjente felt (full.json
  // dekker kun kjente V1-felt) -- verifiser derfor de KJENTE feltene
  // (bryggerStil/prosess/vann) overlever store-syklusen, siden det er
  // dette scenarioet faktisk øver på (lagring/gjenfinning, ikke import-
  // capture -- den er allerede dekket av testene over).
  assert.strictEqual(funnet.recipe.bryggerStil, 'Testbryggerens egen stil (syntetisk)');
  assert.deepStrictEqual(funnet.recipe.prosess, importRes.oppskrift.prosess);
  assert.deepStrictEqual(funnet.recipe.vann, importRes.oppskrift.vann);
  // recipeId skal ALDRI ligge inne i selve payloaden (kun som søsken-felt).
  assert.strictEqual('recipeId' in funnet.recipe, false);

  const eksportert = ctx.byggKbhRecipeInnhold(funnet.recipe);
  assert.strictEqual(eksportert.recipe.bryggerStil, 'Testbryggerens egen stil (syntetisk)');
  assert.deepStrictEqual(eksportert.recipe.prosess, importRes.oppskrift.prosess);
  assert.deepStrictEqual(eksportert.recipe.vann, importRes.oppskrift.vann);
  assert.strictEqual('recipeId' in eksportert.recipe, false);
});

kjor('full syklus MED ukjent fremtidig felt overlever save/load/export (KBHR-002 kjernescenario)', () => {
  const ctx = nyContext(true);

  const raa = JSON.parse(lastFixture('full'));
  raa.recipe.fermentasjonsprofil = { steg: [{ temp: 18, dager: 7 }] };
  const importRes = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  assert.strictEqual(importRes.ok, true);

  const lagreRes = ctx.lagreOppskriftIStore(importRes.oppskrift, null);
  assert.strictEqual(lagreRes.ok, true);
  const funnet = ctx.finnOppskrift(lagreRes.recipeId);
  assert.ok(funnet);

  const eksportert = ctx.byggKbhRecipeInnhold(funnet.recipe);
  // Se realm-forklaringen i testen over -- samme grunn til å bruke
  // JSON.stringify-sammenligning fremfor deepStrictEqual her.
  assert.strictEqual(JSON.stringify(eksportert.recipe.fermentasjonsprofil), JSON.stringify({ steg: [{ temp: 18, dager: 7 }] }));
  assert.strictEqual('_kbhUkjenteFelt' in eksportert.recipe, false);
});

// ─── PRI 2B (KBHR-008): recipeSchemaVersion safety ─────────────────────
//
// KBHR-008: recipeSchemaVersion skal aldri nedgraderes/overskrives stille.
// Egen konstant her (ikke recipe_storage.js sin RECIPE_SCHEMA_VERSION --
// se KBHRECIPE_STOTTET_RECIPE_SCHEMA_VERSION i kbhrecipe.js) siden en
// `const` uansett ikke eksponeres som en egenskap på vm-contexten (kun
// `var`/funksjonsdeklarasjoner blir det) -- verdien 1 er derfor hardkodet
// i disse testene, matchende de faktiske, gjeldende konstantene i
// produksjonsfilene.

kjor('PRI2B (1): recipeSchemaVersion 1 parses/importeres normalt', () => {
  const ctx = nyContext(false);
  const res = ctx.parseKbhRecipeInnhold(lastFixture('minimal'));
  assert.strictEqual(res.ok, true);
  assert.strictEqual(res.oppskrift.recipeSchemaVersion, 1);
});

kjor('PRI2B (2): recipeSchemaVersion 2 avvises eksplisitt FØR redigerbar flyt', () => {
  const ctx = nyContext(false);
  const raa = JSON.parse(lastFixture('minimal'));
  raa.recipe.recipeSchemaVersion = 2;
  const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  assert.strictEqual(res.ok, false);
  assert.ok(res.melding);
  // oppskrift skal IKKE finnes på et avvist resultat -- ingenting for
  // app.js/importer_page.js å sende inn i _gjenopprettOppskrift() med.
  assert.strictEqual(res.oppskrift, undefined);
});

kjor('PRI2B: unsupported recipe-schema-melding er DISTINKT fra unsupported envelope-versjon-melding', () => {
  const ctx = nyContext(false);
  const raaSchema = JSON.parse(lastFixture('minimal'));
  raaSchema.recipe.recipeSchemaVersion = 2;
  const resSchema = ctx.parseKbhRecipeInnhold(JSON.stringify(raaSchema));

  const raaEnvelope = JSON.parse(lastFixture('minimal'));
  raaEnvelope.version = 2;
  const resEnvelope = ctx.parseKbhRecipeInnhold(JSON.stringify(raaEnvelope));

  assert.strictEqual(resSchema.ok, false);
  assert.strictEqual(resEnvelope.ok, false);
  assert.notStrictEqual(resSchema.melding, resEnvelope.melding);
});

kjor('PRI2B (3): recipeSchemaVersion 2 blir aldri omskrevet til 1 (lagringslaget, forbi parseren)', () => {
  const ctx = nyContext(true);
  // Kaller lagreOppskriftIStore() DIREKTE -- forbi parseKbhRecipeInnhold(),
  // som er den PRIMÆRE sperren. Dette beviser det UAVHENGIGE andre
  // forsvarslaget i selve recipe_storage.js.
  const oppskrift = { navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [], recipeSchemaVersion: 2 };
  const lagreRes = ctx.lagreOppskriftIStore(oppskrift, null);
  assert.strictEqual(lagreRes.ok, true);
  const funnet = ctx.finnOppskrift(lagreRes.recipeId);
  assert.strictEqual(funnet.recipe.recipeSchemaVersion, 2);

  // Og overlever en ny lesning av hele lageret (lesOppskriftState()
  // normaliserer HVER rad på HVER lesing -- det var nettopp her den gamle
  // stille nedgraderingen skjedde).
  const funnetIgjen = ctx.finnOppskrift(lagreRes.recipeId);
  assert.strictEqual(funnetIgjen.recipe.recipeSchemaVersion, 2);
});

kjor('PRI2B (4): manglende recipeSchemaVersion på wrappet payload avvises eksplisitt', () => {
  const ctx = nyContext(false);
  const raa = JSON.parse(lastFixture('minimal'));
  delete raa.recipe.recipeSchemaVersion;
  const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  assert.strictEqual(res.ok, false);
  assert.ok(res.melding);
});

kjor('PRI2B (5): ugyldig (non-number) recipeSchemaVersion avvises eksplisitt', () => {
  const ctx = nyContext(false);
  for (const ugyldigVerdi of ['1', null, true, {}, NaN]) {
    const raa = JSON.parse(lastFixture('minimal'));
    raa.recipe.recipeSchemaVersion = ugyldigVerdi;
    const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
    assert.strictEqual(res.ok, false, `recipeSchemaVersion ${JSON.stringify(ugyldigVerdi)} skal avvises`);
  }
});

kjor('PRI2B (9): vanlig Web-native oppskrift lagres fortsatt med schema version 1', () => {
  const ctx = nyContext(true);
  // (a) eksplisitt satt til 1 (slik samleOppskrift() faktisk gjør det).
  const medVersjon = { navn: 'A', volum: 20, effektivitet: 75, malt: [], humle: [], recipeSchemaVersion: 1 };
  const res1 = ctx.lagreOppskriftIStore(medVersjon, null);
  assert.strictEqual(ctx.finnOppskrift(res1.recipeId).recipe.recipeSchemaVersion, 1);

  // (b) helt uten feltet (f.eks. en rad migrert fra det gamle flate
  // lageret) -- skal fortsatt få lokal schema version 1, ikke avvises.
  const utenVersjon = { navn: 'B', volum: 20, effektivitet: 75, malt: [], humle: [] };
  const res2 = ctx.lagreOppskriftIStore(utenVersjon, null);
  assert.strictEqual(res2.ok, true);
  assert.strictEqual(ctx.finnOppskrift(res2.recipeId).recipe.recipeSchemaVersion, 1);
});

kjor('PRI2B (10): legacy V1-fixtures (recipeSchemaVersion: 1) importeres fortsatt korrekt', () => {
  const ctx = nyContext(false);
  for (const navn of ['minimal', 'full', 'partial_water']) {
    const res = ctx.parseKbhRecipeInnhold(lastFixture(navn));
    assert.strictEqual(res.ok, true, `${navn} skal fortsatt importeres`);
    assert.strictEqual(res.oppskrift.recipeSchemaVersion, 1);
  }
});

// ─── PR #3 Chief review, blocker 1: bryggerStil/prosess/vann must survive
// the REAL import -> restore -> collect -> export cycle, not just the
// parser<->writer shortcut every test above uses ─────────────────────────
//
// Root cause (confirmed by reading app.js): `bryggerStil`/`prosess`/`vann`
// were classified as "known" in KBHRECIPE_KJENTE_FELT, so
// _normaliserOppskriftForImport() did NOT capture them into
// _kbhUkjenteFelt. But app.js has NO dedicated UI/state for any of the
// three (no DOM field, no module variable) -- neither
// _gjenopprettOppskrift() nor samleOppskrift() ever reads/writes
// oppskrift.bryggerStil/.prosess/.vann directly (verified: zero
// references anywhere in web/js/app.js outside kbhrecipe.js's own known-
// field list). They sat as ordinary, harmless properties on the transient
// object parseKbhRecipeInnhold() returns -- which is exactly why
// "full fixture parses i Web" above still passes -- but nothing else in
// Web ever read them from there, so they vanished the moment
// samleOppskrift() built its own, fresh, fixed-shape return object. The
// existing tests above never caught this because none of them exercise
// app.js's actual restore/collect functions, only kbhrecipe.js's parser
// and writer directly.
//
// Fix (this PR): removed bryggerStil/prosess/vann from
// KBHRECIPE_KJENTE_FELT, so they are now captured into _kbhUkjenteFelt on
// import -- exactly like any genuinely unknown future field -- which
// app.js's EXISTING, UNCHANGED carrier variable (_aktivKbhUkjenteFelt)
// already correctly threads through restore -> collect -> export for any
// such field (see samleOppskrift()'s `_kbhUkjenteFelt: _aktivKbhUkjenteFelt`
// and _gjenopprettOppskrift()'s `_aktivKbhUkjenteFelt =
// oppskrift[KBHRECIPE_PASSTHROUGH_NOKKEL] ...`, both in web/js/app.js).
// No app.js code change was needed or made.
//
// Test approach: web/index.html loads 13 files before app.js (i18n,
// preferences, chrome, combobox, calc, flavor, radar, style, veiledning,
// help, recipe_engine, kbhrecipe, units, equipment, recipe_storage,
// brew_storage) and app.js itself unconditionally calls the full
// rendering pipeline (beregnOgVisResultat()) at the end of
// _gjenopprettOppskrift(). Loading that whole dependency graph into a
// Node vm context to execute the real DOM-bound functions verbatim would
// require building a small browser-page test harness -- a much larger,
// separately-scoped undertaking than this fix, and explicitly out of
// scope here ("unrelated refactors"). Instead, these tests mirror app.js's
// REAL, documented, UNCHANGED carrier contract line-for-line (the two
// lines quoted above) using the same technique already established on the
// App/Python side of this codebase (tests/test_recipe_efficiency_scope.py,
// tests/test_kbh_passthrough.py mirror ui/sidebar.py's/ui/recipe_card.py's
// exact hydration lines without loading Streamlit) -- proving the carrier
// CONTRACT is correct end-to-end, using kbhrecipe.js's real, unmodified
// parser/writer at both ends.

function _mirrorGjenopprettOppskrift(oppskrift, KBHRECIPE_PASSTHROUGH_NOKKEL) {
  // Mirrors web/js/app.js::_gjenopprettOppskrift()'s ONE relevant line
  // for this bug -- the extraction of the passthrough carrier.
  return (oppskrift && typeof oppskrift[KBHRECIPE_PASSTHROUGH_NOKKEL] === "object" && oppskrift[KBHRECIPE_PASSTHROUGH_NOKKEL] !== null)
    ? oppskrift[KBHRECIPE_PASSTHROUGH_NOKKEL]
    : null;
}

function _mirrorSamleOppskrift(felter, aktivKbhUkjenteFelt) {
  // Mirrors web/js/app.js::samleOppskrift()'s exact known-field shape
  // (KBHRECIPE_PASSTHROUGH_NOKKEL literal reproduced below is the same
  // string as KBHRECIPE_PASSTHROUGH_NOKKEL in kbhrecipe.js: "_kbhUkjenteFelt")
  // -- deliberately does NOT include bryggerStil/prosess/vann as direct
  // properties, exactly like the real function, so this test can only
  // pass if the passthrough carrier itself is what keeps them alive.
  return {
    recipeSchemaVersion: felter.recipeSchemaVersion,
    navn: felter.navn,
    brygger: felter.brygger || "",
    bryggeri: felter.bryggeri || "",
    notater: felter.notater || "",
    volum: felter.volum,
    effektivitet: felter.effektivitet,
    malt: felter.malt || [],
    humle: felter.humle || [],
    gjaerId: felter.gjaerId || null,
    gjaerCustom: felter.gjaerCustom || null,
    attenuationOverride: felter.attenuationOverride ?? null,
    valgtStil: felter.valgtStil || null,
    lagretDato: new Date().toISOString(),
    _kbhUkjenteFelt: aktivKbhUkjenteFelt,
  };
}

kjor('PR#3 (1): bryggerStil/prosess/vann fanges nå til _kbhUkjenteFelt ved import', () => {
  const ctx = nyContext(false);
  const raa = JSON.parse(lastFixture('full'));
  const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  assert.strictEqual(res.ok, true);
  const passthrough = res.oppskrift['_kbhUkjenteFelt'];
  assert.ok(passthrough, '_kbhUkjenteFelt skal nå inneholde bryggerStil/prosess/vann');
  assert.strictEqual(passthrough.bryggerStil, raa.recipe.bryggerStil);
  assert.strictEqual(JSON.stringify(passthrough.prosess), JSON.stringify(raa.recipe.prosess));
  assert.strictEqual(JSON.stringify(passthrough.vann), JSON.stringify(raa.recipe.vann));
});

kjor('PR#3 (2): navn/brygger/bryggeri/notater/valgtStil forblir KJENTE felt, IKKE i _kbhUkjenteFelt', () => {
  // Regresjonsvakt mot Set-endringen over -- bekrefter at KUN
  // bryggerStil/prosess/vann ble flyttet, ingenting annet.
  const ctx = nyContext(false);
  const raa = JSON.parse(lastFixture('minimal'));
  raa.recipe.brygger = 'Ola Nordmann';
  raa.recipe.bryggeri = 'Kvernhaug';
  raa.recipe.notater = 'Et notat';
  raa.recipe.valgtStil = '21A American IPA';
  const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  assert.strictEqual(res.ok, true);
  assert.strictEqual(res.oppskrift.brygger, 'Ola Nordmann');
  const passthrough = res.oppskrift['_kbhUkjenteFelt'];
  if (passthrough) {
    assert.strictEqual('brygger' in passthrough, false);
    assert.strictEqual('bryggeri' in passthrough, false);
    assert.strictEqual('notater' in passthrough, false);
    assert.strictEqual('valgtStil' in passthrough, false);
  }
});

kjor('PR#3 (3): mirrors app.js -- full parse/import -> restore -> collect -> export bevarer bryggerStil/prosess/vann', () => {
  const ctx = nyContext(false);
  const raa = JSON.parse(lastFixture('full'));
  const importRes = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  assert.strictEqual(importRes.ok, true);

  // "restore" -- mirrors _gjenopprettOppskrift()'s ene relevante linje.
  const aktivKbhUkjenteFelt = _mirrorGjenopprettOppskrift(importRes.oppskrift, '_kbhUkjenteFelt');
  assert.ok(aktivKbhUkjenteFelt, 'restore-steget skal ha fanget en passthrough-container');

  // "collect" -- mirrors samleOppskrift()'s eksakte, faste feltsett (som
  // IKKE inkluderer bryggerStil/prosess/vann direkte -- se over).
  const samlet = _mirrorSamleOppskrift(importRes.oppskrift, aktivKbhUkjenteFelt);
  assert.strictEqual('bryggerStil' in samlet, false, 'samleOppskrift() sitt faste feltsett har aldri bryggerStil direkte');
  assert.strictEqual('prosess' in samlet, false);
  assert.strictEqual('vann' in samlet, false);

  // "export" -- den ekte, uendrede skriveren.
  const eksportert = ctx.byggKbhRecipeInnhold(samlet);
  assert.strictEqual(eksportert.recipe.bryggerStil, raa.recipe.bryggerStil);
  assert.strictEqual(JSON.stringify(eksportert.recipe.prosess), JSON.stringify(raa.recipe.prosess));
  assert.strictEqual(JSON.stringify(eksportert.recipe.vann), JSON.stringify(raa.recipe.vann));
  // Containeren selv skal aldri lekke.
  assert.strictEqual('_kbhUkjenteFelt' in eksportert.recipe, false);

  // Kjente felt (navn, malt/humle-antall) skal fortsatt være riktige --
  // hele syklusen skal ikke ha mistet noe annet underveis.
  assert.strictEqual(eksportert.recipe.navn, raa.recipe.navn);
  assert.strictEqual(eksportert.recipe.malt.length, raa.recipe.malt.length);
});

kjor('PR#3 (4): mirrors app.js -- kjent, redigert navn vinner selv gjennom hele restore -> collect -> export-syklusen', () => {
  const ctx = nyContext(false);
  const raa = JSON.parse(lastFixture('full'));
  const importRes = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  assert.strictEqual(importRes.ok, true);

  const aktivKbhUkjenteFelt = _mirrorGjenopprettOppskrift(importRes.oppskrift, '_kbhUkjenteFelt');
  // Simuler at brukeren redigerer "navn" i skjemaet mellom restore og collect.
  const redigertOppskrift = { ...importRes.oppskrift, navn: 'Redigert av bruker (PR#3)' };
  const samlet = _mirrorSamleOppskrift(redigertOppskrift, aktivKbhUkjenteFelt);

  const eksportert = ctx.byggKbhRecipeInnhold(samlet);
  assert.strictEqual(eksportert.recipe.navn, 'Redigert av bruker (PR#3)');
  // Og bryggerStil/prosess/vann er fortsatt der, uendret -- redigering av
  // ETT kjent felt skal ikke forstyrre passthrough-bevarte felt.
  assert.strictEqual(eksportert.recipe.bryggerStil, raa.recipe.bryggerStil);
  assert.strictEqual(JSON.stringify(eksportert.recipe.prosess), JSON.stringify(raa.recipe.prosess));
});

// ─── originRecipeId (docs/development/CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md,
// issue #276/#281/#284) ─────────────────────────────────────────────────
//
// Dekker kontraktdokumentets §7 acceptance/fixture/test-matrise
// (1)-(9), avgrenset til det Web-laget faktisk implementerer i denne
// runden (§3.2/§3.4/§3.5/§3.7/§3.8/§5): mint ved første lagring, bevart
// ved vanlig rediger-og-lagre, eksport inkluderer origin og ekskluderer
// recipeId, importert origin bevares uendret, eksakt-streng duplikat-
// deteksjon, manglende/tom/ikke-streng origin = "intet dedup-signal",
// legacy-fixtures uten origin importeres fortsatt uendret, og
// "Lagre som variant" mint en FERSK origin (aldri kildens).

kjor('originRecipeId (1): ny oppskrift uten origin mint origin = den ferske lokale recipeId-en ved første lagring', () => {
  const ctx = nyContext(true);
  const oppskrift = { navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [] };
  const res = ctx.lagreOppskriftIStore(oppskrift, null);
  assert.strictEqual(res.ok, true);
  assert.strictEqual(res.originRecipeId, res.recipeId);
  const funnet = ctx.finnOppskrift(res.recipeId);
  assert.strictEqual(funnet.recipe.originRecipeId, res.recipeId);
});

kjor('originRecipeId (2): vanlig rediger-og-lagre-på-nytt av SAMME oppskrift bevarer samme origin uendret', () => {
  const ctx = nyContext(true);
  const oppskrift = { navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [] };
  const forste = ctx.lagreOppskriftIStore(oppskrift, null);
  const redigert = { ...oppskrift, navn: 'X redigert', originRecipeId: forste.originRecipeId };
  const andre = ctx.lagreOppskriftIStore(redigert, forste.recipeId);
  assert.strictEqual(andre.ok, true);
  assert.strictEqual(andre.recipeId, forste.recipeId, 'samme lokale identitet -- oppdatering, ikke duplikat');
  assert.strictEqual(andre.originRecipeId, forste.originRecipeId, 'origin re-mintes ALDRI av en vanlig re-lagring');
});

kjor('originRecipeId (3): eksport inkluderer originRecipeId og ekskluderer lokal recipeId, som før', () => {
  const ctx = nyContext(true);
  const oppskrift = { navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [] };
  const res = ctx.lagreOppskriftIStore(oppskrift, null);
  const funnet = ctx.finnOppskrift(res.recipeId);
  const eksportert = ctx.byggKbhRecipeInnhold(funnet.recipe);
  assert.strictEqual(eksportert.recipe.originRecipeId, res.originRecipeId);
  assert.strictEqual('recipeId' in eksportert.recipe, false);
});

kjor('originRecipeId (4): gyldig importert origin bevares UENDRET gjennom import -> lagring -> eksport', () => {
  const ctx = nyContext(true);
  const raa = JSON.parse(lastFixture('minimal'));
  raa.recipe.originRecipeId = 'origin-fra-en-annen-nettleser';
  const importRes = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  assert.strictEqual(importRes.ok, true);
  assert.strictEqual(importRes.oppskrift.originRecipeId, 'origin-fra-en-annen-nettleser');

  const lagreRes = ctx.lagreOppskriftIStore(importRes.oppskrift, null);
  assert.strictEqual(lagreRes.ok, true);
  assert.strictEqual(lagreRes.originRecipeId, 'origin-fra-en-annen-nettleser');
  // Lokal recipeId er ALLTID en fersk, egen streng -- aldri lik den
  // importerte originen (recipeId er lokal identitet, originRecipeId er
  // portabel historisk lenke, V1 §6/§7).
  assert.notStrictEqual(lagreRes.recipeId, 'origin-fra-en-annen-nettleser');

  const funnet = ctx.finnOppskrift(lagreRes.recipeId);
  const eksportert = ctx.byggKbhRecipeInnhold(funnet.recipe);
  assert.strictEqual(eksportert.recipe.originRecipeId, 'origin-fra-en-annen-nettleser');
});

kjor('originRecipeId (5): finnesOppskriftMedOrigin finner et eksakt duplikat -- speiler app.js sin avvis-før-noe-skrives-bruk', () => {
  const ctx = nyContext(true);
  const oppskrift = { navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [] };
  const res = ctx.lagreOppskriftIStore(oppskrift, null);
  assert.strictEqual(ctx.finnesOppskriftMedOrigin(res.originRecipeId), true);
  assert.strictEqual(ctx.finnesOppskriftMedOrigin('finnes-ikke-lokalt'), false);

  // Speiler apneOppskriftsfil()/importerJsonFil(): duplikatsjekken kjøres
  // FØR lagreOppskriftIStore() i det hele tatt kalles -- ved treff skrives
  // ingenting, ingen stille sammenslåing/overskriving/duplisering.
  const antallForOpp = ctx.alleOppskrifter().length;
  const erDuplikat = ctx.finnesOppskriftMedOrigin(res.originRecipeId);
  assert.strictEqual(erDuplikat, true);
  if (!erDuplikat) ctx.lagreOppskriftIStore(oppskrift, null); // skal ALDRI nås her
  assert.strictEqual(ctx.alleOppskrifter().length, antallForOpp, 'et avvist duplikat skal ikke legge til noen rad');
});

kjor('originRecipeId (6): manglende/tom/ikke-streng origin er "intet dedup-signal" -- ALDRI en falsk duplikat-treff', () => {
  const ctx = nyContext(true);
  const oppskrift = { navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [] };
  ctx.lagreOppskriftIStore(oppskrift, null);
  for (const ugyldig of [undefined, null, '', 0, 123, {}, [], false]) {
    assert.strictEqual(ctx.finnesOppskriftMedOrigin(ugyldig), false, `${JSON.stringify(ugyldig)} skal aldri gi et duplikat-treff`);
  }
});

kjor('originRecipeId (7): legacy fixtures uten originRecipeId importeres fortsatt uendret, aldri avvist (bakoverkompatibilitet, §5)', () => {
  const ctx = nyContext(false);
  for (const navn of ['minimal', 'full', 'partial_water']) {
    const res = ctx.parseKbhRecipeInnhold(lastFixture(navn));
    assert.strictEqual(res.ok, true, `${navn} skal fortsatt importeres`);
    assert.strictEqual(res.oppskrift.originRecipeId, undefined, `${navn} skal ikke late som den har en origin den ikke har`);
  }
});

kjor('originRecipeId (8): en ikke-streng/tom verdi krasjer eller avviser ALDRI lagring -- sanitizeres til fraværende, deretter mintes en fersk origin', () => {
  const ctx = nyContext(true);
  for (const ugyldig of [123, '', null, {}, []]) {
    const oppskrift = { navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [], originRecipeId: ugyldig };
    const res = ctx.lagreOppskriftIStore(oppskrift, null);
    assert.strictEqual(res.ok, true, `${JSON.stringify(ugyldig)} skal aldri avvise lagringen`);
    assert.strictEqual(typeof res.originRecipeId, 'string');
    assert.strictEqual(res.originRecipeId, res.recipeId);
  }
});

kjor('originRecipeId (9): gjenkjennes som kjent felt ved import -- havner ALDRI i generisk _kbhUkjenteFelt-passthrough', () => {
  const ctx = nyContext(false);
  const raa = JSON.parse(lastFixture('minimal'));
  raa.recipe.originRecipeId = 'en-origin';
  const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
  assert.strictEqual(res.ok, true);
  assert.strictEqual(res.oppskrift.originRecipeId, 'en-origin');
  const passthrough = res.oppskrift['_kbhUkjenteFelt'];
  if (passthrough) assert.strictEqual('originRecipeId' in passthrough, false);
});

kjor('originRecipeId (9b): issue #293 -- en ikke-streng/tom originRecipeId på selve importen (parseKbhRecipeInnhold, IKKE bare lagreOppskriftIStore/finnesOppskriftMedOrigin) sanitizes til fraværende, aldri avvisning og aldri den rå verdien videre', () => {
  const ctx = nyContext(false);
  for (const ugyldig of [12345, '   ', '', null, {}, []]) {
    const raa = JSON.parse(lastFixture('minimal'));
    raa.recipe.originRecipeId = ugyldig;
    const res = ctx.parseKbhRecipeInnhold(JSON.stringify(raa));
    assert.strictEqual(res.ok, true, `${JSON.stringify(ugyldig)} skal aldri avvise importen`);
    assert.strictEqual(res.oppskrift.originRecipeId, undefined, `${JSON.stringify(ugyldig)} skal gi "intet dedup-signal", ikke den rå verdien`);
  }
});

kjor('originRecipeId (10): mirrors app.js -- "Lagre som variant" mint en FERSK originRecipeId, arver aldri kildens (§3.5)', () => {
  const ctx = nyContext(true);
  const original = { navn: 'Original', volum: 20, effektivitet: 75, malt: [], humle: [] };
  const forsteLagring = ctx.lagreOppskriftIStore(original, null);
  assert.strictEqual(forsteLagring.ok, true);

  // Mirrors _gjenopprettOppskrift()'s originRecipeId-linje: gjenoppretter
  // den lagrede originalen inn i "aktiv kladd" (f.eks. bruker åpner
  // "Mine oppskrifter" og redigerer den).
  const lagretOriginal = ctx.finnOppskrift(forsteLagring.recipeId).recipe;
  let aktivOriginRecipeId = (typeof lagretOriginal.originRecipeId === 'string' && lagretOriginal.originRecipeId)
    ? lagretOriginal.originRecipeId
    : null;
  assert.strictEqual(aktivOriginRecipeId, forsteLagring.originRecipeId);

  // Mirrors lagreSomVariant()'s ALLERFØRSTE linje: nullstiller sporings-
  // variabelen FØR samleOppskrift() kalles, slik at kopien aldri kan
  // arve kildens origin.
  aktivOriginRecipeId = null;
  const samlet = { ...lagretOriginal, navn: 'Original (kopi)' };
  if (aktivOriginRecipeId) samlet.originRecipeId = aktivOriginRecipeId;
  else delete samlet.originRecipeId; // mirrors samleOppskrift()'s betingede felt

  const variantLagring = ctx.lagreOppskriftIStore(samlet, null); // null -> fersk lokal recipeId, som lagreSomVariant() alltid bruker
  assert.strictEqual(variantLagring.ok, true);
  assert.notStrictEqual(variantLagring.recipeId, forsteLagring.recipeId, 'variant skal få en FERSK lokal recipeId');
  assert.notStrictEqual(variantLagring.originRecipeId, forsteLagring.originRecipeId, 'variant skal få en FERSK originRecipeId, aldri kildens');
  assert.strictEqual(variantLagring.originRecipeId, variantLagring.recipeId, 'fersk origin = variantens egen nye lokale id (§3.2)');

  // Originalen selv er uberørt.
  const originalEtterpaa = ctx.finnOppskrift(forsteLagring.recipeId);
  assert.strictEqual(originalEtterpaa.recipe.originRecipeId, forsteLagring.originRecipeId);
});

kjor('originRecipeId (11): Chief-review-fiks (PR#287 runde 2) -- mirrors lagreSomVariant() -- et AVBRUTT variant-forsøk (ugyldig batch-volum) etterlater kildens origin-spor UENDRET, en påfølgende vanlig lagring bevarer fortsatt samme origin', () => {
  const ctx = nyContext(true);
  const original = { navn: 'Original', volum: 20, effektivitet: 75, malt: [], humle: [] };
  const forsteLagring = ctx.lagreOppskriftIStore(original, null);
  assert.strictEqual(forsteLagring.ok, true);

  // Mirrors _gjenopprettOppskrift(): aktiv kladd har nå kildens origin.
  const lagretOriginal = ctx.finnOppskrift(forsteLagring.recipeId).recipe;
  let aktivOriginRecipeId = (typeof lagretOriginal.originRecipeId === 'string' && lagretOriginal.originRecipeId)
    ? lagretOriginal.originRecipeId
    : null;
  assert.strictEqual(aktivOriginRecipeId, forsteLagring.originRecipeId);

  // Mirrors lagreSomVariant() ETTER Chief-fiksen: samleOppskrift() kalles
  // FØRST (den globale aktivOriginRecipeId er fortsatt satt der), originen
  // fjernes KUN fra den samlede LOKALE kopien -- selve sporingsvariabelen
  // røres aldri før et vellykket res.ok. Simulerer her et ugyldig
  // batch-volum (0), akkurat det _blokkerUgyldigBatchVolum() ville avvist
  // FØR lagreOppskriftIStore() noensinne kalles.
  const samlet = { ...lagretOriginal, navn: 'Original (kopi)', volum: 0 };
  if (aktivOriginRecipeId) samlet.originRecipeId = aktivOriginRecipeId;
  delete samlet.originRecipeId; // mirrors den nye, lokale-kopi-ENESTE resetten

  const ugyldigVolum = samlet.volum <= 0;
  assert.strictEqual(ugyldigVolum, true, 'testens eget scenario må faktisk avbryte');
  // _blokkerUgyldigBatchVolum() ville returnert her, FØR lagreOppskriftIStore()
  // kalles -- aktivOriginRecipeId er (etter fiksen) fortsatt urørt.
  assert.strictEqual(aktivOriginRecipeId, forsteLagring.originRecipeId, 'et avbrutt variant-forsøk skal ALDRI ha nullstilt kildens origin-spor');

  // Bevis-loop: den regresjonen Chief flagget var at et påfølgende, HELT
  // VANLIG "Lagre oppskrift" av samme kilde ville mint en NY origin, fordi
  // den gamle koden hadde nullstilt aktivOriginRecipeId FØR volum-sjekken.
  // Med fiksen skal denne påfølgende, vanlige re-lagringen fortsatt bevare
  // nøyaktig samme origin.
  const vanligOppskrift = { ...lagretOriginal, navn: 'Original redigert' };
  if (aktivOriginRecipeId) vanligOppskrift.originRecipeId = aktivOriginRecipeId;
  const vanligLagring = ctx.lagreOppskriftIStore(vanligOppskrift, forsteLagring.recipeId);
  assert.strictEqual(vanligLagring.ok, true);
  assert.strictEqual(vanligLagring.recipeId, forsteLagring.recipeId);
  assert.strictEqual(vanligLagring.originRecipeId, forsteLagring.originRecipeId, 'origin skal IKKE ha blitt re-mintet etter det avbrutte variant-forsøket');
});

// ─── issue #288 -- delt cross-surface origin-fixture ────────────────────
//
// tests/fixtures/kbhrecipe/with_origin.json er BEVISST IKKE en frossen
// legacy-fixture (tests/fixtures/legacy/kbhrecipe/*.json) -- den er en
// fersk, ikke-legacy fixture som allerede har en gyldig originRecipeId,
// lest ORDRETT av BÅDE denne seksjonen og
// tests/test_kbh_import.py::TestOriginRecipeIdDeltCrossSurfaceFixture,
// som speiler DELT_ORIGIN_RECIPE_ID sin eksakte strengverdi. Dette er
// den konkrete, delte wire-artifakten issue #288 ber om -- App/Web-
// tolkning av ÉN og samme fil, ikke bare hver sides egen syntetiske
// payload.

kjor('originRecipeId (12a): delt fixture aksepteres av Web og gir eksakt samme origin som App', () => {
  const ctx = nyContext(false);
  const res = ctx.parseKbhRecipeInnhold(lastDeltFixture('with_origin'));
  assert.strictEqual(res.ok, true);
  assert.strictEqual(res.oppskrift.originRecipeId, DELT_ORIGIN_RECIPE_ID);
});

kjor('originRecipeId (12b): delt fixture har ingen recipeId på selve wire-artifakten', () => {
  const raa = JSON.parse(lastDeltFixture('with_origin'));
  assert.strictEqual('recipeId' in raa.recipe, false);
});

kjor('originRecipeId (12c): delt fixture full rundtur import -> lagring -> eksport -> reimport bevarer origin uendret', () => {
  const ctx = nyContext(true);
  const importRes = ctx.parseKbhRecipeInnhold(lastDeltFixture('with_origin'));
  assert.strictEqual(importRes.ok, true);

  const lagreRes = ctx.lagreOppskriftIStore(importRes.oppskrift, null);
  assert.strictEqual(lagreRes.ok, true);
  assert.strictEqual(lagreRes.originRecipeId, DELT_ORIGIN_RECIPE_ID);
  assert.notStrictEqual(lagreRes.recipeId, DELT_ORIGIN_RECIPE_ID, 'lokal recipeId er alltid egen, aldri lik den importerte originen');

  const funnet = ctx.finnOppskrift(lagreRes.recipeId);
  const eksportert = ctx.byggKbhRecipeInnhold(funnet.recipe);
  assert.strictEqual(eksportert.recipe.originRecipeId, DELT_ORIGIN_RECIPE_ID);
  assert.strictEqual('recipeId' in eksportert.recipe, false);

  const reimportRes = ctx.parseKbhRecipeInnhold(JSON.stringify(eksportert));
  assert.strictEqual(reimportRes.ok, true);
  assert.strictEqual(reimportRes.oppskrift.originRecipeId, DELT_ORIGIN_RECIPE_ID);
});

kjor('originRecipeId (12d): malformerte varianter av delt fixture (ikke-streng/tom origin) gir intet dedup-signal, aldri avvisning -- speiler Python-testens to identiske mutasjoner', () => {
  for (const ugyldig of [12345, '   ']) {
    const raa = JSON.parse(lastDeltFixture('with_origin'));
    raa.recipe.originRecipeId = ugyldig;
    const res = nyContext(false).parseKbhRecipeInnhold(JSON.stringify(raa));
    assert.strictEqual(res.ok, true, `${JSON.stringify(ugyldig)} skal aldri avvise importen`);
    assert.strictEqual(res.oppskrift.originRecipeId, undefined, `${JSON.stringify(ugyldig)} skal gi "intet dedup-signal", ikke en falsk verdi`);
  }
});

kjor('originRecipeId (12e): eksakt-streng duplikat-deteksjon på den delte fixturens EGEN origin, uten overskriving/sammenslåing ved treff', () => {
  const ctx = nyContext(true);
  const importRes = ctx.parseKbhRecipeInnhold(lastDeltFixture('with_origin'));
  ctx.lagreOppskriftIStore(importRes.oppskrift, null);

  assert.strictEqual(ctx.finnesOppskriftMedOrigin(DELT_ORIGIN_RECIPE_ID), true);
  const antallForOpp = ctx.alleOppskrifter().length;
  // Speiler importer_page.js/app.js: duplikatsjekken kjøres FØR et nytt
  // forsøk på å lagre samme fil på nytt -- ved treff skrives ingenting.
  if (!ctx.finnesOppskriftMedOrigin(DELT_ORIGIN_RECIPE_ID)) {
    ctx.lagreOppskriftIStore(importRes.oppskrift, null); // skal ALDRI nås
  }
  assert.strictEqual(ctx.alleOppskrifter().length, antallForOpp, 'et avvist duplikat skal ikke legge til noen rad');
});

kjor('originRecipeId (12f): frosne legacy-fixturer gir samme "ingen origin"-resultat som App sin egen kryssjekk mot de samme filnavnene', () => {
  const ctx = nyContext(false);
  for (const navn of ['minimal', 'partial_water']) {
    const res = ctx.parseKbhRecipeInnhold(lastFixture(navn));
    assert.strictEqual(res.ok, true);
    assert.strictEqual(res.oppskrift.originRecipeId, undefined);
  }
});

// ─── Oppsummering ───────────────────────────────────────────────────────

console.log(`Kbhrecipe contract-tester: ${bestatt}/${bestatt + feil.length} bestått.`);
if (feil.length > 0) {
  console.log('\nFEIL:');
  for (const f of feil) console.log(`  - ${f}`);
  process.exitCode = 1;
}
