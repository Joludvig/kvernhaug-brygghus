// Stilveiledning — vennlig, tre-nivås tekst ("innenfor" / "litt utenfor" /
// "tydelig utenfor") bygget fra style.js sitt felt_avvik. Dette er en NY,
// web-only presentasjon oppå den eksisterende, verifiserte scoringen —
// selve tallene/rangeringen i style.js er UENDRET av dette laget.
//
// "Tydelig"-grensen er bevisst satt til NØYAKTIG samme terskel (0,5) som
// style.js allerede bruker internt for "kritisk avvik", slik at "tydelig
// utenfor" her betyr det samme som "kritisk" der — ingen ny, oppfunnet skala.
const _VEILEDNING_TYDELIG_TERSKEL = 0.5;

const _FELT_LABEL = {
  og: "Styrken i vørteren (OG)",
  fg: "Restsødmen (FG)",
  ibu: "Bitterheten (IBU)",
  ebc: "Fargen (EBC)",
  abv: "Alkoholstyrken (ABV)",
};

const _FELT_TIPS = {
  ibu: { under: "mer bitterhumle (lengre koketid eller høyere alfasyre)", over: "mindre bitterhumle eller kortere koketid" },
  ebc: { under: "litt mer spesialmalt (karamell/røstet)", over: "litt mindre spesialmalt (karamell/røstet)" },
  og: { under: "mer malt eller høyere brygghuseffektivitet", over: "mindre malt eller lavere brygghuseffektivitet" },
  fg: { under: "en gjær med lavere utgjæring", over: "en gjær med høyere utgjæring" },
  abv: { under: "mer malt/høyere OG", over: "mindre malt/lavere OG" },
};

const _KONSEPT_ADJEKTIV = {
  og: { over: "sterkere", under: "svakere" },
  ebc: { over: "mørkere", under: "lysere" },
  ibu: { over: "mer bitter", under: "mindre bitter" },
  fg: { over: "fyldigere", under: "tørrere" },
};

function _feltOmrade(felt, lo, hi) {
  if (felt === "ibu" || felt === "ebc") return `${_fmtOmradeHeltall(lo)}–${_fmtOmradeHeltall(hi)}${felt === "ibu" ? " IBU" : " EBC"}`;
  if (felt === "abv") return `${_fmtKomma(lo, 1)}–${_fmtKomma(hi, 1)} %`;
  return `${_fmtKomma(lo, 3)}–${_fmtKomma(hi, 3)}`;
}

function _feltNivaOgSetning(felt, avvik, stilNavn) {
  if (!avvik.retning) return { niva: "innenfor", tekst: null };
  const niva = avvik.normalisert >= _VEILEDNING_TYDELIG_TERSKEL ? "tydelig" : "litt";
  const retningsord = avvik.retning === "under" ? "lavere" : "høyere";

  let tekst = `${_FELT_LABEL[felt]} er ${niva} ${retningsord} enn typisk for ${stilNavn}. Vanlig område: ${_feltOmrade(felt, avvik.lo, avvik.hi)}.`;
  if (niva === "tydelig" && _FELT_TIPS[felt]) {
    tekst += ` Tips: ${_FELT_TIPS[felt][avvik.retning]} vil trekke oppskriften nærmere stilen.`;
  }
  return { niva, tekst };
}

function _listeMedOg(liste) {
  if (liste.length === 1) return liste[0];
  return `${liste.slice(0, -1).join(", ")} og ${liste[liste.length - 1]}`;
}

function _byggSamletOppsummering(feltAvvik, stilNavn) {
  const antallAvvikende = ["og", "fg", "ibu", "ebc", "abv"].filter((f) => feltAvvik[f].retning).length;
  if (antallAvvikende < 2) return null;

  const adjektiver = [];
  for (const felt of ["og", "ebc", "ibu", "fg"]) {
    const a = feltAvvik[felt];
    if (a.retning) adjektiver.push(_KONSEPT_ADJEKTIV[felt][a.retning]);
  }
  if (adjektiver.length < 2) return null;

  return `Oppskriften din er ${_listeMedOg(adjektiver)} enn typisk for ${stilNavn}. Se «Nærliggende stiler» under for et konkret alternativ som kan passe bedre.`;
}

// stilEntry: ett element fra sisteStilAnalyse.stil_liste (har .felt_avvik)
function byggStilVeiledning(stilEntry, stilNavn) {
  const felter = ["og", "fg", "ibu", "ebc", "abv"];
  const linjer = [];
  let alleInnenfor = true;

  for (const felt of felter) {
    const { niva, tekst } = _feltNivaOgSetning(felt, stilEntry.felt_avvik[felt], stilNavn);
    if (niva !== "innenfor") {
      alleInnenfor = false;
      linjer.push({ felt, niva, tekst });
    }
  }

  return {
    alleInnenfor,
    linjer,
    samlet: _byggSamletOppsummering(stilEntry.felt_avvik, stilNavn),
  };
}
