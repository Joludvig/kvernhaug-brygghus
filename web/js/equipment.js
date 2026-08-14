// Runde 21B -- Utstyrsprofiler V1. DOM-fri state-modul (samme prinsipp som
// recipe_engine.js), lastet FØR app.js. Bruker den globale t() fra i18n.js
// for brukervendte feilmeldinger -- samme ok/melding-kontrakt som
// web/js/kbhrecipe.js sin import-validering, ikke en ny oppfunnet.
//
// BEVISST V1-AVGRENSNING (se docs/ROADMAP.md Runde 21/21B): kettleCapacityL
// og maxRecommendedBatchL er REN metadata/brukerveiledning i denne runden.
// Ingen pre-boil-/meskevann-beregning legges til her eller i
// recipe_engine.js -- batchvolum-advarselen (app.js) sammenligner KUN mot
// et EKSPLISITT maxRecommendedBatchL, aldri en heuristikk utledet fra
// kettleCapacityL. Feltene boilOffLPerHour/deadSpaceL/mashRatioLPerKg/
// grainAbsorptionLPerKg (kjent fra desktop sin modules/equipment.py)
// eksponeres bevisst IKKE i V1 -- web bruker dem ikke i noen beregning
// ennå, og å la brukeren fylle dem ut ville gi et falskt inntrykk av at de
// påvirker resultatet.

const UTSTYR_NOKKEL = "kvernhaug_web_utstyr";
const UTSTYR_VERSION = 1;

// Eneste innebygde preset i V1. PROVENIENS (se
// web/hjelp/utstyr-brewzilla.html for full forklaring):
//   kettleCapacityL = 35  -> (A) FAKTISK PRODUKTSPESIFIKASJON -- ligger i
//     produktnavnet selv ("BrewZilla 35L").
//   maxRecommendedBatchL = 30 -> (D) KVERNHAUGS EGEN PRAKTISKE ANBEFALING,
//     IKKE en produsentoppgitt maksgrense -- en sikkerhetsmargin under
//     kjelens 35 L kapasitet for å unngå overkoking ved kraftig kok
//     (samme tall som allerede brukes i modules/brewday_calc.py sitt
//     "brewzilla_varsel" på desktop).
// Innebygde presets lagres ALDRI i localStorage -- kun i kode, slik at en
// fremtidig tall-justering ikke krever migrering av eksisterende brukeres
// lagrede state.
const BUILTIN_EQUIPMENT_PROFILES = [
  {
    id: "brewzilla-35-gen4-1",
    name: "BrewZilla 35L Gen 4.1",
    type: "preset",
    manufacturer: "KegLand",
    model: "BrewZilla 35L Gen 4.1",
    kettleCapacityL: 35,
    maxRecommendedBatchL: 30,
  },
];

function _tomUtstyrState() {
  return { format: "kbh-equipment", version: UTSTYR_VERSION, activeProfileId: null, profiles: [] };
}

// Trygg lesing -- manglende nøkkel, ugyldig JSON, feil format/version eller
// et profiles-felt som ikke er en liste faller ALLE tilbake til tom state.
// Kaster aldri -- skal ALDRI stoppe byggeren, se krav i Runde 21B.
function lesUtstyrState() {
  try {
    const raw = localStorage.getItem(UTSTYR_NOKKEL);
    if (!raw) return _tomUtstyrState();
    const parsed = JSON.parse(raw);
    if (
      !parsed || typeof parsed !== "object" ||
      parsed.format !== "kbh-equipment" ||
      parsed.version !== UTSTYR_VERSION ||
      !Array.isArray(parsed.profiles)
    ) {
      return _tomUtstyrState();
    }
    return {
      format: "kbh-equipment",
      version: UTSTYR_VERSION,
      activeProfileId: typeof parsed.activeProfileId === "string" ? parsed.activeProfileId : null,
      profiles: parsed.profiles.filter((p) => p && typeof p === "object" && typeof p.id === "string"),
    };
  } catch {
    return _tomUtstyrState();
  }
}

function _lagreUtstyrState(state) {
  try {
    localStorage.setItem(UTSTYR_NOKKEL, JSON.stringify(state));
  } catch {
    // F.eks. privat nettlesing / full lagringskvote -- trygg no-op, samme
    // prinsipp som resten av appens localStorage-skriving.
  }
}

function alleUtstyrsprofiler() {
  return [...BUILTIN_EQUIPMENT_PROFILES, ...lesUtstyrState().profiles];
}

function hentUtstyrsprofil(id) {
  if (!id) return null;
  return alleUtstyrsprofiler().find((p) => p.id === id) || null;
}

// null = "ingen utstyrsprofil valgt" -- gjelder både når feltet aldri er
// satt (ny bruker) og når den lagrede ID-en peker på en profil som ikke
// lenger finnes (f.eks. en slettet custom-profil).
function hentAktivUtstyrsprofil() {
  return hentUtstyrsprofil(lesUtstyrState().activeProfileId);
}

// Ugyldig/ukjent id (annet enn null) ignoreres stille -- aktiv profil
// endres da ikke.
function aktiverUtstyrsprofil(id) {
  const state = lesUtstyrState();
  if (id === null) {
    state.activeProfileId = null;
  } else if (hentUtstyrsprofil(id)) {
    state.activeProfileId = id;
  } else {
    return state.activeProfileId;
  }
  _lagreUtstyrState(state);
  return state.activeProfileId;
}

function _genererUtstyrId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return "custom-" + crypto.randomUUID();
  return "custom-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
}

// Returnerer en OVERSATT feilmelding (streng) ved ugyldige felt, ellers
// null. maxRecommendedBatchL er valgfritt -- kun validert når faktisk satt.
function _validerUtstyrsfelt({ name, kettleCapacityL, maxRecommendedBatchL }) {
  if (!name || !String(name).trim()) return t("utstyr.feilNavnPakrevd");
  const kap = parseFloat(kettleCapacityL);
  if (!isFinite(kap) || kap <= 0) return t("utstyr.feilKapasitetPositiv");
  if (maxRecommendedBatchL !== undefined && maxRecommendedBatchL !== null && String(maxRecommendedBatchL).trim() !== "") {
    const maks = parseFloat(maxRecommendedBatchL);
    if (!isFinite(maks) || maks <= 0) return t("utstyr.feilMaksPositiv");
    if (maks > kap) return t("utstyr.feilMaksOverstigerKapasitet");
  }
  return null;
}

function _byggCustomProfilfelt(felter) {
  const maks = felter.maxRecommendedBatchL !== undefined && felter.maxRecommendedBatchL !== null && String(felter.maxRecommendedBatchL).trim() !== ""
    ? parseFloat(felter.maxRecommendedBatchL)
    : undefined;
  return {
    name: String(felter.name).trim(),
    manufacturer: (felter.manufacturer || "").toString().trim() || undefined,
    model: (felter.model || "").toString().trim() || undefined,
    kettleCapacityL: parseFloat(felter.kettleCapacityL),
    maxRecommendedBatchL: maks,
    notes: (felter.notes || "").toString().trim() || undefined,
  };
}

// Returnerer { ok: true, profile } eller { ok: false, melding } -- samme
// kontrakt som kbhrecipe.js sin importvalidering.
function opprettCustomUtstyrsprofil(felter) {
  const feil = _validerUtstyrsfelt(felter);
  if (feil) return { ok: false, melding: feil };
  const state = lesUtstyrState();
  const profil = { id: _genererUtstyrId(), type: "custom", ..._byggCustomProfilfelt(felter) };
  state.profiles.push(profil);
  _lagreUtstyrState(state);
  return { ok: true, profile: profil };
}

function oppdaterCustomUtstyrsprofil(id, felter) {
  const feil = _validerUtstyrsfelt(felter);
  if (feil) return { ok: false, melding: feil };
  const state = lesUtstyrState();
  const idx = state.profiles.findIndex((p) => p.id === id);
  if (idx === -1) return { ok: false, melding: t("utstyr.feilFinnesIkke") };
  const oppdatert = { ...state.profiles[idx], ..._byggCustomProfilfelt(felter) };
  state.profiles[idx] = oppdatert;
  _lagreUtstyrState(state);
  return { ok: true, profile: oppdatert };
}

function slettCustomUtstyrsprofil(id) {
  const state = lesUtstyrState();
  state.profiles = state.profiles.filter((p) => p.id !== id);
  if (state.activeProfileId === id) state.activeProfileId = null;
  _lagreUtstyrState(state);
}
