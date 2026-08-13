// Runde 13 -- portabel .kbhrecipe-fil: en liten, versjonert JSON-wrapper
// rundt det eksisterende oppskriftsobjektet (samme form som samleOppskrift()/
// _gjenopprettOppskrift() i app.js), slik at vanlige brukere kan lagre,
// dele og åpne én fil uten å måtte forholde seg til "rå JSON" som konsept.
// Delt av app.js (Lagre og eksporter / "Åpne oppskriftsfil") og
// importer_page.js ("Åpne fil"-fanen) -- ingen egen backend, alt skjer
// lokalt i nettleseren.
//
// Format:
//   { format: "kbhrecipe", version: 1, exportedAt, generator, recipe: {...} }
// `recipe` er nøyaktig det samme oppskriftsobjektet som samleOppskrift()
// returnerer og _gjenopprettOppskrift() forventer -- ingen parallell
// datamodell. Eldre, rå oppskrifts-JSON (uten wrapper, fra tidligere
// eksport-runder) gjenkjennes og støttes fortsatt (se parseKbhRecipeInnhold).

const KBHRECIPE_FORMAT = "kbhrecipe";
const KBHRECIPE_VERSION = 1;

// Runde 13A -- delt "har denne oppskriften noe meningsfullt i seg?"-sjekk,
// brukt til å avgjøre om "Ny oppskrift"/"Åpne oppskriftsfil"/Importer-siden
// skal bekrefte før en aktiv kladd erstattes. Virker på et vanlig
// oppskriftsobjekt (samleOppskrift()-formen) -- kalles med samleOppskrift()
// sitt resultat i app.js, og med den lagrede AKTIV_KLADD_NOKKEL-verdien i
// importer_page.js (samme form, siden den alltid er skrevet av samme
// funksjon). Bevisst IKKE brygger/bryggeri -- de er brukerpreferanser (se
// forhandsutfyllIdentitetsPreferanse() i app.js), ikke oppskriftsinnhold
// brukeren ville reagert på å miste.
function oppskriftHarInnhold(o) {
  if (!o || typeof o !== "object") return false;
  return !!(
    (o.navn && o.navn !== "Uten navn") ||
    o.notater ||
    (Array.isArray(o.malt) && o.malt.length > 0) ||
    (Array.isArray(o.humle) && o.humle.length > 0) ||
    o.gjaerId ||
    o.gjaerCustom ||
    o.valgtStil ||
    (typeof o.volum === "number" && o.volum !== 20) ||
    (typeof o.effektivitet === "number" && o.effektivitet !== 75)
  );
}

// Windows-ugyldige tegn (\ / : * ? " < > |) fjernes; mellomrom blir
// bindestrek. Bevisst IKKE translitterert (Æ/Ø/Å/Unicode beholdes) --
// kun faktisk problematiske filsystemtegn fjernes.
function tryggFilnavn(navn) {
  let n = (navn || "").trim();
  if (!n || /^uten navn$/i.test(n)) n = "Kvernhaug-oppskrift";
  n = n.replace(/[\\/:*?"<>|]/g, "-").replace(/\s+/g, "-").replace(/-{2,}/g, "-").replace(/^-+|-+$/g, "");
  if (!n) n = "Kvernhaug-oppskrift";
  if (n.length > 80) n = n.slice(0, 80).replace(/-+$/g, "");
  return n;
}

function byggKbhRecipeInnhold(oppskrift) {
  return {
    format: KBHRECIPE_FORMAT,
    version: KBHRECIPE_VERSION,
    exportedAt: new Date().toISOString(),
    generator: "Kvernhaug Brygghus",
    recipe: oppskrift,
  };
}

function lastNedKbhRecipeFil(oppskrift) {
  const blob = new Blob([JSON.stringify(byggKbhRecipeInnhold(oppskrift), null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${tryggFilnavn(oppskrift.navn)}.kbhrecipe`;
  a.click();
  URL.revokeObjectURL(url);
}

// Lett heuristikk for "ser ut som en oppskrift" -- ikke en tung
// schema-validator, kun en sjekk på at minst ett kjent oppskriftsfelt
// finnes, slik at helt vilkårlig JSON avvises med en vennlig melding i
// stedet for å bli stille (og feilaktig) tolket som en tom oppskrift.
function _erGyldigOppskriftForm(obj) {
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) return false;
  const kjenteFelt = ["navn", "malt", "humle", "gjaerId", "gjaerCustom", "volum", "brygger", "bryggeri"];
  return kjenteFelt.some((felt) => felt in obj);
}

// Defensiv normalisering for import (ikke del av samleOppskrift()-
// kontrakten selv) -- en fil kan i prinsippet inneholde hva som helst,
// og malt/humle MÅ være arrays for at leggTilMaltRad()/leggTilHumleRad()
// ikke skal krasje på .forEach().
function _normaliserOppskriftForImport(raw) {
  const o = { ...raw };
  if (!Array.isArray(o.malt)) o.malt = [];
  if (!Array.isArray(o.humle)) o.humle = [];
  return o;
}

// Parser tekstinnholdet i en importert fil. Kjenner igjen BÅDE ny
// .kbhrecipe-wrapper OG gammel/rå oppskrifts-JSON (uten wrapper) --
// eksisterende brukere skal ikke måtte konvertere gamle filer manuelt.
// Returnerer { ok: true, oppskrift, legacy } eller { ok: false, melding }
// -- meldingen er alltid vennlig norsk tekst egnet til direkte visning,
// aldri en rå feil-/stacktrace-streng.
function parseKbhRecipeInnhold(tekst) {
  let parsed;
  try {
    parsed = JSON.parse(tekst);
  } catch (e) {
    console.warn("kbhrecipe: JSON.parse feilet", e);
    return { ok: false, melding: "Denne filen kunne ikke leses som en oppskriftsfil (ugyldig JSON)." };
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ok: false, melding: "Denne filen ser ikke ut som en gyldig Kvernhaug-oppskrift." };
  }

  if (parsed.format === KBHRECIPE_FORMAT) {
    const versjon = parsed.version;
    if (typeof versjon !== "number") {
      return { ok: false, melding: "Denne oppskriftsfilen mangler versjonsinformasjon og kan ikke åpnes sikkert her." };
    }
    if (versjon > KBHRECIPE_VERSION) {
      return { ok: false, melding: "Denne oppskriftsfilen er laget med en nyere versjon av Kvernhaug Brygghus og kan ikke åpnes sikkert her ennå." };
    }
    if (versjon !== KBHRECIPE_VERSION) {
      return { ok: false, melding: "Denne oppskriftsfilen bruker en versjon av oppskriftsformatet som ikke støttes her." };
    }
    if (!parsed.recipe || typeof parsed.recipe !== "object" || Array.isArray(parsed.recipe)) {
      return { ok: false, melding: "Denne oppskriftsfilen mangler selve oppskriften." };
    }
    return { ok: true, oppskrift: _normaliserOppskriftForImport(parsed.recipe), legacy: false };
  }

  // Ingen wrapper -- prøv som eldre, rå oppskrifts-JSON.
  if (_erGyldigOppskriftForm(parsed)) {
    return { ok: true, oppskrift: _normaliserOppskriftForImport(parsed), legacy: true };
  }

  return { ok: false, melding: "Denne filen ser ikke ut som en gyldig Kvernhaug-oppskrift." };
}
