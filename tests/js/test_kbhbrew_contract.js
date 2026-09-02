// Kvernhaug Core -- PRI 3A.2 (issue #22): .kbhbrew V1 contract tests
// (Web-siden, web/js/brew_storage.js).
//
// Samme mønster som tests/js/test_kbhrecipe_contract.js: laster den ekte,
// uendrede web/js/brew_storage.js inn i en isolert Node "vm"-context --
// ingen module.exports i produksjonsfilen, ingen npm-avhengighet, ingen
// package.json, ingen testrammeverk. Kun Node sine egne innebygde
// moduler (fs, path, vm, assert).
//
// Dekker: den nye unknown-field-passthrough-implementasjonen (Owner
// decision #2, ratifisert i CORE_KBHBREW_V1.md §8) på alle relevante lag
// (topp-brew, actuals, sensing, learning) gjennom
// import -> lagring -> lesning -> eksport, at forbudte felt (brewId/
// recipeId) aldri kan lekke til en eksportert fil, at faktisk ABV aldri
// er et lagret/eksportert felt, at den frosne legacy Web-fixturen
// (tests/fixtures/legacy/web/kbhbrew_v1.json) fortsatt leses og
// eksporteres uendret, og import-identitetspolicyen (dedup på
// originBrewId) er upåvirket av denne rundens endring.
//
// Kjøres med:
//     node tests/js/test_kbhbrew_contract.js
//
// Exit code 0 = alle tester bestått. Exit code 1 = minst én feilet.
// MERK: kunne ikke kjøres i selve agent-bridge-sandboxen denne runden
// (ingen `node`-kommando i --allowedTools, kun python3/git/gh) -- kjør
// manuelt som del av review, samme som den eksisterende
// test_kbhrecipe_contract.js allerede krever.

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '..', '..');
const BREW_STORAGE_JS = path.join(ROOT, 'web', 'js', 'brew_storage.js');
const LEGACY_FIXTURE = path.join(ROOT, 'tests', 'fixtures', 'legacy', 'web', 'kbhbrew_v1.json');

// `const`-deklarasjoner i brew_storage.js eksponeres IKKE som egenskaper
// på vm-contexten (kun `var`/funksjonsdeklarasjoner blir det -- samme
// begrensning allerede dokumentert i test_kbhrecipe_contract.js). Verdien
// hardkodes derfor her, matchende BREW_PASSTHROUGH_NOKKEL i
// web/js/brew_storage.js.
const BREW_PASSTHROUGH_NOKKEL = '_kbhBrewUkjenteFelt';

function lastLegacyFixture() {
  return fs.readFileSync(LEGACY_FIXTURE, 'utf8');
}

// Ny, isolert context per test, med en minimal i-minnet localStorage-stub
// (kun get/set/removeItem, ingen event-model) -- samme mønster som
// test_kbhrecipe_contract.js sin nyContext(true).
function nyContext() {
  const lager = new Map();
  const ctx = {
    t: (k) => `[i18n:${k}]`,
    console,
    crypto: globalThis.crypto,
    localStorage: {
      getItem: (k) => (lager.has(k) ? lager.get(k) : null),
      setItem: (k, v) => lager.set(k, String(v)),
      removeItem: (k) => lager.delete(k),
    },
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(BREW_STORAGE_JS, 'utf8'), ctx, { filename: BREW_STORAGE_JS });
  return ctx;
}

// Et minimalt, men gyldig snapshot -- nok til å bestå _gyldigSnapshot().
function minimalSnapshot(navn) {
  return {
    recipe: { recipeSchemaVersion: 1, navn: navn || 'Testbrygg', volum: 20, effektivitet: 75, malt: [], humle: [] },
    ingredients: { malt: {}, humle: {}, gjaer: {} },
    equipment: null,
    predicted: { og: 1.05, fg: 1.012, abv: 5.0, ibu: 20, ebc: 10, buGu: 0.8, flavorProfile: {}, style: null },
    provenance: { engineVersion: 1, recipeSchemaVersion: 1, masterdata: { maltCount: 1, humleCount: 1, gjaerCount: 1 }, capturedAt: '2026-03-01T00:00:00.000Z' },
  };
}

// ─── Minimal testshell (samme stil som test_kbhrecipe_contract.js) ────────

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

// ─── 1-3: legacy Web .kbhbrew-fixture parses/importeres uendret ───────────

kjor('legacy kbhbrew_v1 fixture parses', () => {
  const ctx = nyContext();
  const res = ctx.parseKbhBrewInnhold(lastLegacyFixture());
  assert.strictEqual(res.ok, true);
  assert.strictEqual(res.brew.originBrewId, 'brew-22222222-2222-4222-8222-222222222222');
  assert.strictEqual(res.brew.status, 'done');
});

kjor('legacy kbhbrew_v1 fixture importeres med fersk lokal brewId, uendret originBrewId', () => {
  const ctx = nyContext();
  const res = ctx.parseKbhBrewInnhold(lastLegacyFixture());
  const imp = ctx.importerBrygg(res.brew);
  assert.strictEqual(imp.ok, true);
  assert.ok(imp.brew.brewId);
  assert.strictEqual(imp.brew.originBrewId, 'brew-22222222-2222-4222-8222-222222222222');
  assert.strictEqual(imp.brew.recipeId, null);
});

kjor('legacy kbhbrew_v1 fixture: actual_abv aldri tilstede etter import (kun og/fg lagres)', () => {
  const ctx = nyContext();
  const res = ctx.parseKbhBrewInnhold(lastLegacyFixture());
  const imp = ctx.importerBrygg(res.brew);
  assert.strictEqual('actual_abv' in imp.brew.actuals, false);
  assert.strictEqual('abv' in imp.brew.actuals, false);
  const faktisk = ctx.faktiskAbv(imp.brew);
  assert.ok(Math.abs(faktisk - (1.053 - 1.01) * 131.25) < 1e-9);
});

// ─── 4-7: ukjent felt overlever import -> eksport, per lag ────────────────

kjor('ukjent TOPP-nivå felt i importert fil overlever import -> eksport', () => {
  const ctx = nyContext();
  const raa = JSON.parse(lastLegacyFixture());
  raa.brew.batchNumber = 'B-2026-014'; // fremtidig felt, ikke i V1 i dag
  const res = ctx.parseKbhBrewInnhold(JSON.stringify(raa));
  assert.strictEqual(res.ok, true);
  const imp = ctx.importerBrygg(res.brew);
  assert.strictEqual(imp.ok, true);
  assert.strictEqual(imp.brew[BREW_PASSTHROUGH_NOKKEL] === undefined, false);
  assert.strictEqual(imp.brew[BREW_PASSTHROUGH_NOKKEL].batchNumber, 'B-2026-014');

  const eksportert = ctx.byggKbhBrewInnhold(imp.brew);
  assert.strictEqual(eksportert.brew.batchNumber, 'B-2026-014');
  assert.strictEqual('_kbhBrewUkjenteFelt' in eksportert.brew, false);
});

kjor('ukjent ACTUALS-felt overlever import -> eksport', () => {
  const ctx = nyContext();
  const raa = JSON.parse(lastLegacyFixture());
  raa.brew.actuals.mashPh = 5.4;
  const res = ctx.parseKbhBrewInnhold(JSON.stringify(raa));
  const imp = ctx.importerBrygg(res.brew);
  assert.strictEqual(imp.brew.actuals.mashPh, undefined, 'ukjent felt skal IKKE ligge som direkte egenskap');
  assert.strictEqual(imp.brew.actuals[BREW_PASSTHROUGH_NOKKEL].mashPh, 5.4);

  const eksportert = ctx.byggKbhBrewInnhold(imp.brew);
  assert.strictEqual(eksportert.brew.actuals.mashPh, 5.4);
  assert.strictEqual('_kbhBrewUkjenteFelt' in eksportert.brew.actuals, false);
  // kjente actuals-felt skal fortsatt være riktige.
  assert.strictEqual(eksportert.brew.actuals.og, 1.053);
});

kjor('ukjent SENSING-felt overlever import -> eksport', () => {
  const ctx = nyContext();
  const raa = JSON.parse(lastLegacyFixture());
  raa.brew.sensing.aromaNotes = 'syntetisk aromanotat';
  const res = ctx.parseKbhBrewInnhold(JSON.stringify(raa));
  const imp = ctx.importerBrygg(res.brew);
  const eksportert = ctx.byggKbhBrewInnhold(imp.brew);
  assert.strictEqual(eksportert.brew.sensing.aromaNotes, 'syntetisk aromanotat');
  assert.strictEqual('_kbhBrewUkjenteFelt' in eksportert.brew.sensing, false);
  assert.strictEqual(eksportert.brew.sensing.judgment, 'yes');
});

kjor('ukjent LEARNING-felt overlever import -> eksport', () => {
  const ctx = nyContext();
  const raa = JSON.parse(lastLegacyFixture());
  raa.brew.learning.equipmentNotes = 'syntetisk utstyrsnotat';
  const res = ctx.parseKbhBrewInnhold(JSON.stringify(raa));
  const imp = ctx.importerBrygg(res.brew);
  const eksportert = ctx.byggKbhBrewInnhold(imp.brew);
  assert.strictEqual(eksportert.brew.learning.equipmentNotes, 'syntetisk utstyrsnotat');
  assert.strictEqual('_kbhBrewUkjenteFelt' in eksportert.brew.learning, false);
  assert.strictEqual(eksportert.brew.learning.nextTime, raa.brew.learning.nextTime);
});

// ─── 8: kjent felt redigert av bruker vinner over gammel passthrough-verdi ─

kjor('kjent felt (status) satt via oppdaterBrygg vinner over evt. gammel passthrough-verdi med samme navn', () => {
  const ctx = nyContext();
  const opprettet = ctx.opprettBrygg({ snapshot: minimalSnapshot('X'), recipeId: null });
  assert.strictEqual(opprettet.ok, true);
  const oppdatert = ctx.oppdaterBrygg(opprettet.brew.brewId, { status: 'done' });
  assert.strictEqual(oppdatert.ok, true);
  assert.strictEqual(oppdatert.brew.status, 'done');
});

kjor('stale passthrough-innslag med samme navn som et kjent felt gjenopplives aldri', () => {
  // Regresjonsvakt: en fil kan i prinsippet allerede bære en (avlegs, feil,
  // eller fra en annen klientversjon) _kbhBrewUkjenteFelt-container hvis
  // nøkler kolliderer med et navn som ER et kjent felt (f.eks. "og"). Det
  // ekte kjente feltet skal ALLTID vinne, og den avlegse container-verdien
  // skal IKKE overleve videre i en ny normalisering -- ellers kunne den en
  // dag lekke tilbake dersom det ekte feltet senere ble fjernet.
  const ctx = nyContext();
  const raa = JSON.parse(lastLegacyFixture());
  raa.brew.actuals._kbhBrewUkjenteFelt = { og: 999, genuineUnknown: 'keep-me' };
  const res = ctx.parseKbhBrewInnhold(JSON.stringify(raa));
  const imp = ctx.importerBrygg(res.brew);
  assert.strictEqual(imp.brew.actuals.og, 1.053, 'det ekte kjente feltet skal vinne');
  assert.strictEqual(imp.brew.actuals[BREW_PASSTHROUGH_NOKKEL].og, undefined, 'stale og-verdi skal IKKE overleve i containeren');
  assert.strictEqual(imp.brew.actuals[BREW_PASSTHROUGH_NOKKEL].genuineUnknown, 'keep-me');

  const eksportert = ctx.byggKbhBrewInnhold(imp.brew);
  assert.strictEqual(eksportert.brew.actuals.og, 1.053);
  assert.strictEqual(eksportert.brew.actuals.genuineUnknown, 'keep-me');
});

// ─── 9-10: forbudte/container-felt kan aldri lekke til fil ────────────────

kjor('passthrough-containeren selv eksporteres aldri som et bokstavelig felt på noe lag', () => {
  const ctx = nyContext();
  const raa = JSON.parse(lastLegacyFixture());
  raa.brew.batchNumber = 'B-1';
  raa.brew.actuals.mashPh = 5.4;
  raa.brew.sensing.aromaNotes = 'x';
  raa.brew.learning.equipmentNotes = 'y';
  const res = ctx.parseKbhBrewInnhold(JSON.stringify(raa));
  const imp = ctx.importerBrygg(res.brew);
  const eksportert = ctx.byggKbhBrewInnhold(imp.brew);
  assert.strictEqual('_kbhBrewUkjenteFelt' in eksportert.brew, false);
  assert.strictEqual('_kbhBrewUkjenteFelt' in eksportert.brew.actuals, false);
  assert.strictEqual('_kbhBrewUkjenteFelt' in eksportert.brew.sensing, false);
  assert.strictEqual('_kbhBrewUkjenteFelt' in eksportert.brew.learning, false);
});

kjor('brewId/recipeId kan aldri lekke til eksport, selv hvis de skulle stå i en passthrough-container', () => {
  const ctx = nyContext();
  const opprettet = ctx.opprettBrygg({ snapshot: minimalSnapshot('X'), recipeId: 'lokal-recipe-id' });
  assert.strictEqual(opprettet.ok, true);
  // Andre forsvarslinje: simuler at en korrupt/håndredigert lagret rad har
  // forbudte navn liggende i selve passthrough-containeren.
  const forfalsket = {
    ...opprettet.brew,
    [BREW_PASSTHROUGH_NOKKEL]: { brewId: 'SKAL-ALDRI-EKSPORTERES', recipeId: 'SKAL-ALDRI-EKSPORTERES', ekteUkjentFelt: 'skal-overleve' },
  };
  const eksportert = ctx.byggKbhBrewInnhold(forfalsket);
  assert.strictEqual('brewId' in eksportert.brew, false);
  assert.strictEqual('recipeId' in eksportert.brew, false);
  assert.strictEqual(JSON.stringify(eksportert).includes('SKAL-ALDRI-EKSPORTERES'), false);
  assert.strictEqual(eksportert.brew.ekteUkjentFelt, 'skal-overleve');
});

// ─── 11: legacy fixture kjente felt uendret gjennom hele syklusen ─────────

kjor('legacy kbhbrew_v1 fixture: kjente felt uendret gjennom import -> eksport', () => {
  const ctx = nyContext();
  const raaTekst = lastLegacyFixture();
  const res = ctx.parseKbhBrewInnhold(raaTekst);
  const imp = ctx.importerBrygg(res.brew);
  const eksportert = ctx.byggKbhBrewInnhold(imp.brew);
  const original = JSON.parse(raaTekst);
  assert.strictEqual(eksportert.brew.originBrewId, original.brew.originBrewId);
  assert.strictEqual(eksportert.brew.status, original.brew.status);
  assert.strictEqual(eksportert.brew.createdAt, original.brew.createdAt);
  assert.strictEqual(eksportert.brew.brewedAt, original.brew.brewedAt);
  assert.strictEqual(JSON.stringify(eksportert.brew.actuals), JSON.stringify(original.brew.actuals));
  assert.strictEqual(JSON.stringify(eksportert.brew.sensing), JSON.stringify(original.brew.sensing));
  assert.strictEqual(JSON.stringify(eksportert.brew.learning), JSON.stringify(original.brew.learning));
  assert.strictEqual('brewId' in eksportert.brew, false);
});

// ─── 12: envelope-versjon/format avvises eksplisitt (uendret oppførsel) ───

kjor('ukjent .kbhbrew envelope-format avvises', () => {
  const ctx = nyContext();
  const raa = JSON.parse(lastLegacyFixture());
  raa.format = 'kbhrecipe';
  const res = ctx.parseKbhBrewInnhold(JSON.stringify(raa));
  assert.strictEqual(res.ok, false);
  assert.ok(res.melding);
});

kjor('envelope version !=1 avvises eksplisitt', () => {
  const ctx = nyContext();
  const raa = JSON.parse(lastLegacyFixture());
  raa.version = 2;
  const res = ctx.parseKbhBrewInnhold(JSON.stringify(raa));
  assert.strictEqual(res.ok, false);
  assert.ok(res.melding);
});

// ─── 13: duplikat-identitetspolicy upåvirket av passthrough-endringen ─────

kjor('samme originBrewId importert to ganger gir eksplisitt duplikat, ikke stille duplisering', () => {
  const ctx = nyContext();
  const res1 = ctx.parseKbhBrewInnhold(lastLegacyFixture());
  const imp1 = ctx.importerBrygg(res1.brew);
  assert.strictEqual(imp1.ok, true);

  const res2 = ctx.parseKbhBrewInnhold(lastLegacyFixture());
  const imp2 = ctx.importerBrygg(res2.brew);
  assert.strictEqual(imp2.ok, false);
  assert.strictEqual(imp2.duplikat, true);
});

// ─── 14: full syklus via localStorage-backet lager ────────────────────────

kjor('full syklus: opprett -> oppdater med ukjent actuals-felt -> lagre -> les -> eksporter bevarer det', () => {
  const ctx = nyContext();
  const opprettet = ctx.opprettBrygg({ snapshot: minimalSnapshot('Full syklus'), recipeId: null });
  assert.strictEqual(opprettet.ok, true);

  const oppdatert = ctx.oppdaterBrygg(opprettet.brew.brewId, {
    actuals: { og: 1.05, fg: 1.01, mashPh: 5.3 },
  });
  assert.strictEqual(oppdatert.ok, true);
  assert.strictEqual(oppdatert.brew.actuals.og, 1.05);
  assert.strictEqual(oppdatert.brew.actuals[BREW_PASSTHROUGH_NOKKEL].mashPh, 5.3);

  // Ny lesning av HELE lageret (lesBrewState() normaliserer hver rad på
  // nytt hver gang) -- beviser idempotens, ikke bare enkeltoppdateringen.
  const funnet = ctx.finnBrygg(opprettet.brew.brewId);
  assert.ok(funnet);
  assert.strictEqual(funnet.actuals[BREW_PASSTHROUGH_NOKKEL].mashPh, 5.3);

  const eksportert = ctx.byggKbhBrewInnhold(funnet);
  assert.strictEqual(eksportert.brew.actuals.mashPh, 5.3);
  assert.strictEqual(eksportert.brew.actuals.og, 1.05);
});

// ─── Oppsummering ───────────────────────────────────────────────────────

console.log(`Kbhbrew contract-tester: ${bestatt}/${bestatt + feil.length} bestått.`);
if (feil.length > 0) {
  console.log('\nFEIL:');
  for (const f of feil) console.log(`  - ${f}`);
  process.exitCode = 1;
}
