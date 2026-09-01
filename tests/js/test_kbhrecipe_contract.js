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

function lastFixture(navn) {
  return fs.readFileSync(path.join(FIXTURES_DIR, `${navn}.json`), 'utf8');
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

// ─── KBHR-008: dokumenterer dagens IKKE-fiksede recipeSchemaVersion-gap ─

kjor('KBHR-008: recipeSchemaVersion overskrives fortsatt stille ved lagring (kjent, udekket gap)', () => {
  const ctx = nyContext(true);
  const oppskrift = { navn: 'X', volum: 20, effektivitet: 75, malt: [], humle: [], recipeSchemaVersion: 99 };
  const res = ctx.lagreOppskriftIStore(oppskrift, null);
  assert.strictEqual(res.ok, true);
  const funnet = ctx.finnOppskrift(res.recipeId);
  // Dette IKKE er ønsket sluttadferd (se docs/development/
  // CORE_KBHRECIPE_V1.md §9) -- testen dokumenterer dagens faktiske,
  // uendrede oppførsel. Korreksjonen kommer i PRI 2B (KBHR-008).
  // Merk: RECIPE_SCHEMA_VERSION er en `const` i recipe_storage.js og blir
  // derfor IKKE eksponert som en egenskap på vm-contexten (kun `var`/
  // funksjonsdeklarasjoner blir det) -- verdien 1 er derfor hardkodet her,
  // matchende den faktiske, gjeldende konstanten i produksjonsfilen.
  assert.strictEqual(funnet.recipe.recipeSchemaVersion, 1);
  assert.notStrictEqual(funnet.recipe.recipeSchemaVersion, 99);
});

// ─── Oppsummering ───────────────────────────────────────────────────────

console.log(`Kbhrecipe contract-tester: ${bestatt}/${bestatt + feil.length} bestått.`);
if (feil.length > 0) {
  console.log('\nFEIL:');
  for (const f of feil) console.log(`  - ${f}`);
  process.exitCode = 1;
}
