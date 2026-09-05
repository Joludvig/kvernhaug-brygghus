// Kvernhaug Core -- PRI 1: golden cross-runtime calculation tests
// (JavaScript-siden).
//
// Leser den SAMME teknologiuavhengige, Core-eide fixturen som
// tests/test_calculation_golden_vectors.py
// (core/calculation_golden_vectors.json) og kjører hver vector
// gjennom DAGENS produksjonsimplementasjon i web/js/calc.js -- IKKE en
// kopi av formlene, og web/js/calc.js er IKKE endret for å muliggjøre
// dette (ingen module.exports lagt til i produksjonsfilen): scriptet
// laster calc.js sin rå kildetekst inn i en isolert Node "vm"-context
// og henter ut funksjonene den definerer, akkurat slik nettleseren
// ville gjort med et vanlig <script>-tag.
//
// Bevisst minimal testinfrastruktur: null npm-avhengigheter, ingen
// package.json, ingen testrammeverk -- kun Node sine egne
// innebygde moduler (fs, path, vm, assert). Web-arkitekturen sier
// selv "ingen build-steg, ingen npm-avhengigheter" (web/README.md);
// dette scriptet respekterer det prinsippet.
//
// Kjøres med:
//     node tests/js/test_calculation_golden_vectors.js
//
// Exit code 0 = alle vectors bestått. Exit code 1 = minst én feilet
// (feilene listes ut før exit).

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..', '..');
const VECTORS_PATH = path.join(ROOT, 'core', 'calculation_golden_vectors.json');
const CALC_JS_PATH = path.join(ROOT, 'web', 'js', 'calc.js');

function lastProduksjonsfunksjoner() {
  const kilde = fs.readFileSync(CALC_JS_PATH, 'utf8');
  const context = {};
  vm.createContext(context);
  new vm.Script(kilde, { filename: CALC_JS_PATH }).runInContext(context);
  const paakrevde = [
    'beregnOG', 'beregnEBC', 'beregnFgOgAbv', 'beregnTotalIBU', 'beregnGramFraIBU',
    'beregnAbvFraOgFg',
  ];
  for (const navn of paakrevde) {
    if (typeof context[navn] !== 'function') {
      throw new Error(`web/js/calc.js definerte ikke forventet funksjon: ${navn}`);
    }
  }
  return context;
}

// --- Adaptere: canonical vector-inputs -> faktiske funksjonsargumenter ----
// Reshaper KUN felt/enheter -- ingen beregning gjøres her (samme
// prinsipp og samme struktur som Python-testens adaptere).

function lagAdaptere(fns) {
  return {
    og(inputs) {
      const valgtMaltListe = inputs.malts.map((m, i) => ({ id: `malt_${i}`, mengde: m.amount_kg }));
      const maltData = {};
      inputs.malts.forEach((m, i) => { maltData[`malt_${i}`] = { potensiale: m.potential_sg }; });
      return { og_sg: fns.beregnOG(valgtMaltListe, maltData, inputs.batch_volume_l, inputs.efficiency_fraction) };
    },
    fg_abv(inputs) {
      const { fg, abv } = fns.beregnFgOgAbv(inputs.og_sg, inputs.attenuation_fraction);
      return { fg_sg: fg, abv_percent: abv };
    },
    ebc_morey(inputs) {
      const valgtMaltListe = inputs.malts.map((m, i) => ({ id: `malt_${i}`, mengde: m.amount_kg }));
      const maltData = {};
      inputs.malts.forEach((m, i) => { maltData[`malt_${i}`] = { ebc: m.ebc }; });
      return { ebc: fns.beregnEBC(valgtMaltListe, maltData, inputs.batch_volume_l) };
    },
    tinseth_ibu(inputs) {
      const valgtHumleListe = inputs.hops.map((h, i) => ({ id: `hop_${i}`, gram: h.amount_g, tid: h.boil_time_min }));
      const humleData = {};
      inputs.hops.forEach((h, i) => { humleData[`hop_${i}`] = { alfa: h.alpha_acid_percent }; });
      return { ibu: fns.beregnTotalIBU(valgtHumleListe, humleData, inputs.batch_volume_l, inputs.wort_gravity_sg) };
    },
    inverse_tinseth(inputs) {
      const gram = fns.beregnGramFraIBU(
        inputs.target_ibu, inputs.alpha_acid_percent, inputs.boil_time_min,
        inputs.batch_volume_l, inputs.wort_gravity_sg,
      );
      return { hop_amount_g: gram };
    },
    measured_abv(inputs) {
      const { standard, highGravity } = fns.beregnAbvFraOgFg(inputs.og_sg, inputs.fg_sg);
      return { abv_standard_percent: standard, abv_high_gravity_percent: highGravity };
    },
  };
}

function main() {
  const data = JSON.parse(fs.readFileSync(VECTORS_PATH, 'utf8'));
  const fns = lastProduksjonsfunksjoner();
  const adaptere = lagAdaptere(fns);

  let bestatt = 0;
  const feil = [];

  for (const c of data.cases) {
    const adapter = adaptere[c.calculation];
    if (!adapter) {
      feil.push(`${c.id}: ukjent calculation-type "${c.calculation}"`);
      continue;
    }
    const faktisk = adapter(c.inputs);
    let caseOk = true;
    for (const [felt, forventetVerdi] of Object.entries(c.expected)) {
      const avvik = Math.abs(faktisk[felt] - forventetVerdi);
      if (!(avvik <= c.tolerance)) {
        caseOk = false;
        feil.push(
          `${c.id} (${c.calculation}.${felt}): fikk ${faktisk[felt]}, forventet ${forventetVerdi}, ` +
          `avvik ${avvik} > toleranse ${c.tolerance}`,
        );
      }
    }
    if (caseOk) bestatt += 1;
  }

  console.log(`Golden vectors: ${bestatt}/${data.cases.length} bestått.`);
  if (feil.length > 0) {
    console.log('\nFEIL:');
    for (const f of feil) console.log(`  - ${f}`);
    process.exitCode = 1;
  }
}

main();
