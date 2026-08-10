// Smaksprofil-beregning portert fra modules/flavor_engine.py (kun poeng-
// beregningen -- selve Plotly-radardiagrammet i Python-filen er UI og
// porteres ikke). Brukes som inndata til style.js sin sensoriske matching.

const SMAKS_KATEGORIER = [
  "Maltfylde", "Brød", "Toast", "Karamell", "Honning", "Nøtter",
  "Sjokolade", "Kaffe", "Røyk", "Bitterhet", "Furunål", "Jordlig",
  "Krydder", "Sitrus", "Tropisk", "Fruktighet", "Steinfrukt", "Vinøs",
];

const _SPECIALTY_KATEGORIER = new Set(["Sjokolade", "Kaffe", "Røyk", "Karamell"]);

// maltListe: [{id, mengde}], humleListe: [{id, gram, tid}]
function beregnSmaksprofil(maltListe, maltData, humleListe, humleData, totalIbu, gjaerId, gjaerData) {
  const poeng = {};
  for (const kat of SMAKS_KATEGORIER) poeng[kat] = 0.0;

  const totalMaltVekt = maltListe
    .filter((m) => maltData[m.id])
    .reduce((sum, m) => sum + m.mengde, 0);

  if (totalMaltVekt > 0) {
    for (const m of maltListe) {
      const entry = maltData[m.id];
      if (entry && m.mengde > 0) {
        const prosentandel = m.mengde / totalMaltVekt;
        const katData = entry.kategorier || {};
        for (const [kat, verdi] of Object.entries(katData)) {
          if (kat in poeng) {
            const skala = _SPECIALTY_KATEGORIER.has(kat) ? Math.pow(prosentandel, 0.55) : prosentandel;
            poeng[kat] += verdi * skala * 1.2;
          }
        }
      }
    }
  }

  const totalHumleGram = humleListe
    .filter((h) => humleData[h.id])
    .reduce((sum, h) => sum + h.gram, 0);

  if (totalHumleGram > 0) {
    for (const h of humleListe) {
      const entry = humleData[h.id];
      if (entry && h.gram > 0) {
        const humleProsent = h.gram / totalHumleGram;
        const hKat = entry.kategorier || {};
        const aromaFaktor = h.tid <= 5 ? 1.0 : h.tid <= 15 ? 0.5 : 0.1;
        for (const [kat, verdi] of Object.entries(hKat)) {
          if (kat in poeng && kat !== "Bitterhet") {
            poeng[kat] += verdi * humleProsent * 1.5 * aromaFaktor;
          }
        }
      }
    }
  }

  const gjaerEntry = gjaerData[gjaerId];
  if (gjaerEntry) {
    const gKat = gjaerEntry.kategorier || {};
    for (const [kat, verdi] of Object.entries(gKat)) {
      if (kat in poeng) poeng[kat] += verdi;
    }
  }

  poeng["Bitterhet"] = Math.min(totalIbu / 8.0, 10.0);

  for (const kat of Object.keys(poeng)) {
    poeng[kat] = Math.max(0.0, Math.min(poeng[kat], 10.0));
  }

  return poeng;
}
