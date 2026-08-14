// Runde 22 -- global måleenhet-preferanse (metric/US customary).
//
// Helt uavhengig av språkvalg (se sprakvelger-drawer/index.html) og av
// recipe-/utstyr-state -- dette er en ren klient-side UI-preferanse, ikke
// oppskrift- eller utstyrsdata. Samme sikre lese/lagre-mønster som
// equipment.js: manglende/korrupt/ugyldig state faller alltid trygt
// tilbake til metric, kaster aldri.
const PREFERANSER_NOKKEL = "kvernhaug_web_preferanser";
const PREFERANSER_VERSION = 1;
const GYLDIGE_UNIT_SYSTEMER = ["metric", "us"];

function _tomPreferanser() {
  return { format: "kbh-preferences", version: PREFERANSER_VERSION, unitSystem: "metric" };
}

function lesPreferanser() {
  try {
    const raw = localStorage.getItem(PREFERANSER_NOKKEL);
    if (!raw) return _tomPreferanser();
    const parsed = JSON.parse(raw);
    if (
      !parsed || typeof parsed !== "object" ||
      parsed.format !== "kbh-preferences" ||
      parsed.version !== PREFERANSER_VERSION ||
      !GYLDIGE_UNIT_SYSTEMER.includes(parsed.unitSystem)
    ) {
      return _tomPreferanser();
    }
    return { format: "kbh-preferences", version: PREFERANSER_VERSION, unitSystem: parsed.unitSystem };
  } catch {
    return _tomPreferanser();
  }
}

function _lagrePreferanser(pref) {
  try {
    localStorage.setItem(PREFERANSER_NOKKEL, JSON.stringify(pref));
  } catch {}
}

function hentUnitSystem() {
  return lesPreferanser().unitSystem;
}

// Ugyldig input faller trygt tilbake til metric i stedet for å lagre noe
// korrupt -- returnerer alltid det faktisk lagrede systemet.
function settUnitSystem(system) {
  const gyldig = GYLDIGE_UNIT_SYSTEMER.includes(system) ? system : "metric";
  _lagrePreferanser({ format: "kbh-preferences", version: PREFERANSER_VERSION, unitSystem: gyldig });
  return gyldig;
}
