// Runde 21C -- unit-readiness arkitektur.
//
// Kvernhaug Brygghus lagrer og beregner alt internt i metriske
// canonical-verdier: volum i liter, maltvekt i kg, humlevekt i gram,
// temperatur i grader Celsius. Denne modulen samler volum-formattering og
// -parsing bak ett lite, gjenbrukbart grensesnitt, slik at en fremtidig
// US customary-visning (gallons/lb/oz/°F) kan legges til uten å måtte
// spore opp spredte hardkodede " L"-strenger i UI-koden.
//
// Bevisst V1C-avgrensning: kun volum er implementert her. Masse (kg/g) og
// temperatur (°C) har ingen formatter ennå -- se docs/ROADMAP.md for
// begrunnelse og anbefalt scope for en fremtidig Runde 22 (full US
// customary-støtte). Ingen UI i web kaller unitSystem="us" i dag; NO og EN
// viser begge metrisk. Recipe-data og utstyrsprofiler forblir rene
// metric-tall (liter) -- denne modulen endrer ikke lagringsformat.

const CANONICAL_VOLUME_UNIT = "L"; // liter -- all storage/beregning bruker dette

// Fremtidige US customary-konverteringer (arkitektur-kontrakt for en senere
// runde -- kun volum er faktisk koblet til noe UI i dag). Ikke Imperial/UK
// gallon.
const US_GALLON_L = 3.785411784; // 1 US gallon = 3.785411784 L
const LB_KG = 0.45359237; // 1 lb = 0.45359237 kg -- ikke i bruk ennå
const OZ_G = 28.349523125; // 1 oz = 28.349523125 g -- ikke i bruk ennå

// °F = °C x 9/5 + 32 -- ikke i bruk ennå, ingen formatter/parser for
// temperatur i V1C.

function formatVolumeNumber(liters) {
  return Number.isInteger(liters) ? String(liters) : liters.toFixed(1).replace(/\.0$/, "");
}

// unitSystem: "metric" (default) eller "us". Canonical input er alltid
// liter, uansett unitSystem -- konvertering skjer kun i visningen.
function formatVolume(liters, unitSystem = "metric") {
  if (unitSystem === "us") {
    const gallons = Math.round((liters / US_GALLON_L) * 100) / 100;
    return `${gallons} gal`;
  }
  return `${formatVolumeNumber(liters)} ${CANONICAL_VOLUME_UNIT}`;
}

// Tolker en tallverdi brukeren har skrevet inn (i den angitte unitSystem)
// og returnerer canonical liter, urundet. Rund kun ved visning, aldri ved
// lagring.
function parseVolume(displayValue, unitSystem = "metric") {
  const tall = parseFloat(displayValue);
  if (!isFinite(tall)) return NaN;
  return unitSystem === "us" ? tall * US_GALLON_L : tall;
}
