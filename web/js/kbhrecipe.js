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

// PRI 2B (KBHR-008) -- støttet recipe-PAYLOAD-schema (ikke å forveksle med
// KBHRECIPE_VERSION over, som styrer selve ENVELOPE-formatet). Egen,
// lokal konstant -- IKKE recipe_storage.js sin RECIPE_SCHEMA_VERSION,
// fordi denne filen også lastes ALENE på importer.html (uten
// recipe_storage.js lastet i det hele tatt) -- samme begrunnelse som
// hvorfor KBHRECIPE_VERSION og OPPSKRIFT_STORE_VERSION allerede er to
// atskilte konstanter i to filer. Begge er 1 i dag og MÅ oppdateres
// sammen hvis/når Web noensinne innfører et nytt recipe-schema.
const KBHRECIPE_STOTTET_RECIPE_SCHEMA_VERSION = 1;

// PRI 2A -- kjente felt (docs/development/CORE_KBHRECIPE_V1.md). Brukes
// til å avgjøre hva Web GJENKJENNER ved import -- altså hva som IKKE skal
// fanges til passthrough (se KBHRECIPE_PASSTHROUGH_NOKKEL under). Dette er
// IKKE det samme som "hva Web faktisk skriver til en .kbhrecipe-fil" --
// se KBHRECIPE_EKSPORTERBARE_FELT for eksport-whitelisten.
//
// QA-korreksjon (KBHR-009): denne listen inneholder bevisst BÅDE Core
// V1-payloadfelt OG Web sine egne, allerede eksisterende interne felt
// (lagretDato) -- Web forstår begge deler like godt ved import, så ingen
// av dem skal feiltolkes som "ukjent" data og havne i passthrough. Men et
// felt Web bare bruker internt blir IKKE automatisk en del av
// .kbhrecipe-formatet bare fordi det står i denne listen -- se
// KBHRECIPE_WEB_INTERNE_FELT.
//
// PR #3 Chief review-korreksjon: `bryggerStil`, `prosess` og `vann` er
// BEVISST IKKE med i denne listen, selv om de er gyldige, kjente Core
// V1-felt (§3) -- Web har per i dag INGEN dedikert UI/state for dem
// (ingen DOM-felt, ingen egen variabel; verken samleOppskrift() eller
// _gjenopprettOppskrift() i app.js håndterer dem). Å regne dem som
// "kjent" her betydde tidligere at _normaliserOppskriftForImport()
// IKKE fanget dem til _kbhUkjenteFelt -- men siden ingenting ELLERS i
// Web faktisk holdt fast på dem heller, ble de stille mistet et sted
// mellom import og neste samleOppskrift()-kall (bekreftet: en reell,
// funnet regresjon i en faktisk import -> rediger -> lagre/eksporter-
// runde, se PR #3 Chief review). Retting: disse tre behandles nå
// EKSAKT som et vilkårlig, genuint ukjent fremtidig felt -- fanget opp
// og videreført opakt via KBHRECIPE_PASSTHROUGH_NOKKEL/_kbhUkjenteFelt
// (§6), som app.js allerede korrekt bærer gjennom hele
// redigerings-/lagringssyklusen for ALLE slike felt. Ingen endring i
// app.js var nødvendig -- kun denne klassifiseringen.
const KBHRECIPE_KJENTE_FELT = new Set([
  "recipeSchemaVersion", "navn", "volum", "effektivitet", "malt", "humle",
  "gjaerId", "gjaerCustom", "attenuationOverride", "valgtStil",
  "brygger", "bryggeri", "notater", "lagretDato",
]);

// Felt som ALDRI skal eksporteres og ALDRI skal bevares via passthrough,
// uansett hvor de dukker opp (importert fil, håndredigert lokalt lager) --
// V1 §4 (whitelist-regelen) og §6 (lokal identitet skal aldri lekke ut).
const KBHRECIPE_FORBUDTE_FELT = new Set(["recipeId", "stats", "flavor_profile"]);

// QA-korreksjon (KBHR-009) -- felt Web kjenner og eier internt, men som
// IKKE er en del av Core V1-interchange-payloaden (docs/development/
// CORE_KBHRECIPE_V1.md §3). lagretDato er Web sin egen "sist samlet"-
// metadata, satt på nytt av samleOppskrift() hver gang -- det er ikke
// noe brukeren "har" i oppskriften sin, og skal derfor aldri havne i en
// delt/eksportert fil, selv om Web selvsagt gjenkjenner det ved import
// (se KBHRECIPE_KJENTE_FELT over).
const KBHRECIPE_WEB_INTERNE_FELT = new Set(["lagretDato"]);

// Den faktiske eksport-whitelisten (OPPGAVE 2 / KBHR-009): Core V1-felt
// Web faktisk skriver til en .kbhrecipe-fil. Kjente felt MINUS Web-interne
// felt MINUS eksplisitt forbudte felt. _byggKjentPayload() bruker DENNE,
// ikke KBHRECIPE_KJENTE_FELT direkte -- "et felt blir ikke del av
// .kbhrecipe bare fordi Web bruker det internt".
const KBHRECIPE_EKSPORTERBARE_FELT = new Set(
  [...KBHRECIPE_KJENTE_FELT].filter(
    (felt) => !KBHRECIPE_WEB_INTERNE_FELT.has(felt) && !KBHRECIPE_FORBUDTE_FELT.has(felt)
  )
);

// Internt metadatafelt (IKKE selv et V1-kontraktfelt) som bærer ukjente,
// importerte payload-felt gjennom import -> redigering -> lagring/eksport
// (KBHR-002, V1 §8 passthrough-loven). Ligger som en vanlig property på
// selve oppskriftsobjektet, slik at den flyter gjennom de eksisterende
// mekanismene (aktiv kladd, recipe_storage.js) uten noe eget rammeverk --
// men NØKKELEN selv skrives aldri til en faktisk .kbhrecipe-fil, kun
// INNHOLDET flettes inn (se byggKbhRecipeInnhold()).
const KBHRECIPE_PASSTHROUGH_NOKKEL = "_kbhUkjenteFelt";

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

// OPPGAVE C -- eksportgrensen bygger IKKE lenger `recipe: oppskrift`
// (en ukritisk wrapping av hele objektet). Payloaden bygges kontrollert:
// (A) eksporterbare V1-felt kopieres eksplisitt, (B) bevart passthrough fra
// import flettes inn KUN for nøkler et kjent felt ikke allerede dekker
// -- et felt brukeren faktisk har redigert vinner alltid over en gammel
// passthrough-verdi med samme navn -- og (C) forbudte felt filtreres
// eksplisitt bort på BÅDE steg, som et uavhengig andre vern i tillegg til
// at de aldri fanges til passthrough i utgangspunktet (se
// _normaliserOppskriftForImport()).
//
// QA-korreksjon (KBHR-009): bruker KBHRECIPE_EKSPORTERBARE_FELT, IKKE
// KBHRECIPE_KJENTE_FELT -- sistnevnte inkluderer også Web-interne felt
// (lagretDato) som Web gjenkjenner ved import, men som aldri skal skrives
// til selve .kbhrecipe-filen.
function _byggKjentPayload(oppskrift) {
  const payload = {};
  if (!oppskrift || typeof oppskrift !== "object") return payload;
  for (const felt of KBHRECIPE_EKSPORTERBARE_FELT) {
    if (KBHRECIPE_FORBUDTE_FELT.has(felt)) continue; // umulig i dag, men eksplisitt uansett
    if (felt in oppskrift && oppskrift[felt] !== undefined) {
      payload[felt] = oppskrift[felt];
    }
  }
  return payload;
}

function byggKbhRecipeInnhold(oppskrift) {
  const payload = _byggKjentPayload(oppskrift);

  const passthrough = oppskrift && oppskrift[KBHRECIPE_PASSTHROUGH_NOKKEL];
  if (passthrough && typeof passthrough === "object" && !Array.isArray(passthrough)) {
    for (const [nokkel, verdi] of Object.entries(passthrough)) {
      if (KBHRECIPE_FORBUDTE_FELT.has(nokkel)) continue;
      if (nokkel === KBHRECIPE_PASSTHROUGH_NOKKEL) continue;
      if (!(nokkel in payload)) payload[nokkel] = verdi;
    }
  }

  return {
    format: KBHRECIPE_FORMAT,
    version: KBHRECIPE_VERSION,
    exportedAt: new Date().toISOString(),
    generator: "Kvernhaug Brygghus",
    recipe: payload,
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
// Runde 25A -- recipeId strippes ALLTID ved import. En recipeId er lokal
// lagringsidentitet i én nettleser, aldri global identitet. Skulle en fil
// likevel inneholde en (håndredigert, eller fra et fremtidig format), må
// den ikke adopteres: to nettlesere ville da kunne ende med samme id for
// to uavhengige oppskrifter. Se recipe_storage.js for hele policyen.
// recipeSchemaVersion beholdes derimot -- den beskriver payloadens form.
//
// PRI 2A (KBHR-002) -- ethvert payload-felt SOM IKKE er et kjent V1-/
// Web-felt fanges til KBHRECIPE_PASSTHROUGH_NOKKEL, slik at bryggerStil,
// prosess, vann og et vilkårlig fremtidig felt overlever
// import -> redigering -> lagring/eksport uten at Web trenger å forstå
// dem (V1 §8, passthrough-loven). Forbudte felt (recipeId, stats,
// flavor_profile) kan ALDRI havne der, uansett hva filen inneholder.
function _normaliserOppskriftForImport(raw) {
  const o = { ...raw };
  delete o.recipeId;
  if (!Array.isArray(o.malt)) o.malt = [];
  if (!Array.isArray(o.humle)) o.humle = [];

  const ukjente = {};
  for (const [nokkel, verdi] of Object.entries(raw)) {
    if (nokkel === "recipeId") continue;
    if (KBHRECIPE_KJENTE_FELT.has(nokkel)) continue;
    if (KBHRECIPE_FORBUDTE_FELT.has(nokkel)) continue;
    if (nokkel === KBHRECIPE_PASSTHROUGH_NOKKEL) continue; // ingen nøstet passthrough
    ukjente[nokkel] = verdi;
  }
  if (Object.keys(ukjente).length > 0) o[KBHRECIPE_PASSTHROUGH_NOKKEL] = ukjente;
  else delete o[KBHRECIPE_PASSTHROUGH_NOKKEL];

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
    return { ok: false, melding: t("kbhrecipe.ugyldigJson") };
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ok: false, melding: t("kbhrecipe.ikkeGyldigOppskrift") };
  }

  if (parsed.format === KBHRECIPE_FORMAT) {
    const versjon = parsed.version;
    if (typeof versjon !== "number") {
      return { ok: false, melding: t("kbhrecipe.manglerVersjon") };
    }
    if (versjon > KBHRECIPE_VERSION) {
      return { ok: false, melding: t("kbhrecipe.nyereVersjon") };
    }
    if (versjon !== KBHRECIPE_VERSION) {
      return { ok: false, melding: t("kbhrecipe.ustottetVersjon") };
    }
    if (!parsed.recipe || typeof parsed.recipe !== "object" || Array.isArray(parsed.recipe)) {
      return { ok: false, melding: t("kbhrecipe.manglerOppskrift") };
    }

    // PRI 2B (KBHR-008) -- envelope `version` (sjekket over) og
    // `recipeSchemaVersion` (payloadens EGET schema) er to ULIKE ting. En
    // helt gyldig envelope kan likevel bære en recipe-payload med et nyere
    // eller ukjent schema Web ikke skal late som den forstår. Avvises HER,
    // FØR oppskriften noensinne når vanlig redigerbar flyt
    // (_gjenopprettOppskrift()) eller lagres lokalt -- se
    // docs/development/CORE_KBHRECIPE_V1.md §9. Egen, distinkt melding fra
    // envelope-avvisningen over, slik at de to feilårsakene ikke blandes
    // sammen.
    const recipeSchemaVersion = parsed.recipe.recipeSchemaVersion;
    if (typeof recipeSchemaVersion !== "number" || !Number.isFinite(recipeSchemaVersion)) {
      return { ok: false, melding: t("kbhrecipe.manglerRecipeSchemaVersion") };
    }
    if (recipeSchemaVersion !== KBHRECIPE_STOTTET_RECIPE_SCHEMA_VERSION) {
      return { ok: false, melding: t("kbhrecipe.ustottetRecipeSchemaVersion") };
    }

    return { ok: true, oppskrift: _normaliserOppskriftForImport(parsed.recipe), legacy: false };
  }

  // Ingen wrapper -- prøv som eldre, rå oppskrifts-JSON. recipeSchemaVersion
  // fantes ikke i formatet før wrapperen ble innført, så denne veien
  // beholder sin eksisterende, mer tolerante oppførsel UENDRET (§12 --
  // "preserved as-is") -- IKKE den nye, strenge recipeSchemaVersion-
  // kontrollen over, som kun gjelder den wrappede .kbhrecipe-formen.
  if (_erGyldigOppskriftForm(parsed)) {
    return { ok: true, oppskrift: _normaliserOppskriftForImport(parsed), legacy: true };
  }

  return { ok: false, melding: t("kbhrecipe.ikkeGyldigOppskrift") };
}
