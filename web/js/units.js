// Runde 21C/22 -- unit-readiness arkitektur + faktisk US customary-visning.
//
// Kvernhaug Brygghus lagrer og beregner alt internt i metriske
// canonical-verdier: volum i liter, maltvekt i kg, humlevekt i gram,
// temperatur i grader Celsius. Denne modulen samler formattering og
// parsing for BEGGE visningssystemer bak ett lite, gjenbrukbart
// grensesnitt -- ingen annen fil trenger å vite hvordan en gallon/pund/
// ounce/Fahrenheit-verdi regnes ut.
//
// unitSystem er alltid "metric" eller "us" (US customary -- IKKE
// Imperial/UK gallon). Canonical input/output er alltid metrisk uansett
// unitSystem; konvertering skjer kun i formatX()/parseX(). Ingen
// avrunding skjer noensinne på selve lagringen (recipe/utstyr-state) --
// kun i visningen.

const CANONICAL_VOLUME_UNIT = "L"; // liter -- all storage/beregning bruker dette

// US customary-konverteringer. Ikke Imperial/UK gallon.
const US_GALLON_L = 3.785411784; // 1 US gallon = 3.785411784 L
const LB_KG = 0.45359237; // 1 lb = 0.45359237 kg
const OZ_G = 28.349523125; // 1 oz = 28.349523125 g

// °F = °C x 9/5 + 32. Ingen brukerredigerbare temperaturfelt finnes i web
// per Runde 22 -- formatTemperature/parseTemperature finnes som fullført
// arkitektur-kontrakt, men er ikke koblet til noe UI ennå.

// ── Volum ──────────────────────────────────────────────────────────────

function formatVolumeNumber(liters, unitSystem = "metric") {
  if (unitSystem === "us") {
    return String(Math.round((liters / US_GALLON_L) * 100) / 100);
  }
  return Number.isInteger(liters) ? String(liters) : liters.toFixed(1).replace(/\.0$/, "");
}

function formatVolume(liters, unitSystem = "metric") {
  const enhet = unitSystem === "us" ? "US gal" : CANONICAL_VOLUME_UNIT;
  return `${formatVolumeNumber(liters, unitSystem)} ${enhet}`;
}

// Tolker en tallverdi brukeren har skrevet inn (i den angitte unitSystem)
// og returnerer canonical liter, urundet.
function parseVolume(displayValue, unitSystem = "metric") {
  const tall = parseFloat(displayValue);
  if (!isFinite(tall)) return NaN;
  return unitSystem === "us" ? tall * US_GALLON_L : tall;
}

// ── Maltvekt (kg canonical, lb i US-visning) ────────────────────────────

function formatMaltMassNumber(kg, unitSystem = "metric") {
  if (unitSystem === "us") {
    return String(Math.round((kg / LB_KG) * 100) / 100);
  }
  return String(Math.round(kg * 1000) / 1000);
}

function formatMaltMass(kg, unitSystem = "metric") {
  return unitSystem === "us" ? `${formatMaltMassNumber(kg, "us")} lb` : `${formatMaltMassNumber(kg, "metric")} kg`;
}

function parseMaltMass(displayValue, unitSystem = "metric") {
  const tall = parseFloat(displayValue);
  if (!isFinite(tall)) return NaN;
  return unitSystem === "us" ? tall * LB_KG : tall;
}

// ── Humlevekt (gram canonical, oz i US-visning) ─────────────────────────

function formatHopMassNumber(g, unitSystem = "metric") {
  if (unitSystem === "us") {
    return String(Math.round((g / OZ_G) * 100) / 100);
  }
  return String(Math.round(g));
}

function formatHopMass(g, unitSystem = "metric") {
  return unitSystem === "us" ? `${formatHopMassNumber(g, "us")} oz` : `${formatHopMassNumber(g, "metric")} g`;
}

function parseHopMass(displayValue, unitSystem = "metric") {
  const tall = parseFloat(displayValue);
  if (!isFinite(tall)) return NaN;
  return unitSystem === "us" ? tall * OZ_G : tall;
}

// ── Temperatur (°C canonical, °F i US-visning) -- IKKE i bruk i noe UI
// ennå, se filhode-kommentaren. ───────────────────────────────────────

function formatTemperature(celsius, unitSystem = "metric") {
  if (unitSystem === "us") {
    return `${Math.round((celsius * 9 / 5 + 32) * 10) / 10} °F`;
  }
  return `${Math.round(celsius * 10) / 10} °C`;
}

function parseTemperature(displayValue, unitSystem = "metric") {
  const tall = parseFloat(displayValue);
  if (!isFinite(tall)) return NaN;
  return unitSystem === "us" ? (tall - 32) * 5 / 9 : tall;
}
