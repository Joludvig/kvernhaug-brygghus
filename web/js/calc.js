// Beregningsformler portert fra modules/calculations.py (Python, Streamlit-appen).
// Ren JS, ingen avhengigheter -- hold i sync manuelt hvis formlene endres i Python-siden.

const KG_TIL_LB = 2.2046226218;
const LITER_TIL_US_GALLON = 0.2641720524;
const SRM_TIL_EBC_FAKTOR = 1.97;
const MALT_EBC_TIL_LOVIBOND_A = 1.2;
const MALT_EBC_TIL_LOVIBOND_B = 2.65;

// valgtMaltListe: [{ id, mengde }] -- mengde i kg. maltData: { id: { potensiale, ebc } }
function beregnOG(valgtMaltListe, maltData, volum, effektivitet) {
  let totalePoeng = 0;
  for (const m of valgtMaltListe) {
    const entry = maltData[m.id];
    if (entry) {
      const potensiale = entry.potensiale ?? 1.036;
      totalePoeng += m.mengde * (potensiale - 1) * 1000;
    }
  }
  if (volum === 0) return 1.0;
  return 1 + ((totalePoeng * effektivitet * 8.3454) / volum) / 1000;
}

function beregnEBC(valgtMaltListe, maltData, volum) {
  if (volum <= 0) return 0;
  let mcu = 0;
  const volumGal = volum * LITER_TIL_US_GALLON;
  for (const m of valgtMaltListe) {
    const entry = maltData[m.id];
    if (entry) {
      const maltLovibond = (entry.ebc + MALT_EBC_TIL_LOVIBOND_A) / MALT_EBC_TIL_LOVIBOND_B;
      const mengdeLb = m.mengde * KG_TIL_LB;
      mcu += (mengdeLb * maltLovibond) / volumGal;
    }
  }
  const srm = 1.4922 * Math.pow(mcu, 0.6859);
  return srm * SRM_TIL_EBC_FAKTOR;
}

// Invers Tinseth -- portert fra modules/calculations.py::beregn_gram_fra_ibu().
// Beregner gram humle for et ønsket IBU-bidrag fra ÉN tilsetning, gitt
// alfasyre, koketid og oppskriftens (allerede beregnede) OG/volum. Brukes
// KUN via en eksplisitt "Beregn gram"-handling (Bryggmester) -- aldri live
// på hvert tastetrykk, for å unngå en feedback-loop med den vanlige
// gram->IBU-beregningen over.
function beregnGramFraIBU(maalIbu, alfaProsent, tid, volum, beregnetOg) {
  if (alfaProsent <= 0 || volum <= 0 || beregnetOg <= 1.0 || maalIbu <= 0 || tid <= 0) return 0.0;
  const bigness = 1.65 * Math.pow(0.000125, beregnetOg - 1);
  const times = (1 - Math.exp(-0.04 * tid)) / 4.15;
  const utnyttelse = bigness * times;
  if (utnyttelse <= 0) return 0.0;
  const gram = (maalIbu * volum) / (1000 * (alfaProsent / 100.0) * utnyttelse);
  return Math.round(gram * 10) / 10;
}

function beregnFgOgAbv(og, attenuation) {
  if (og <= 1.0) return { fg: 1.0, abv: 0.0 };
  const fg = 1 + (og - 1) * (1 - attenuation);
  const abv = (og - fg) * 131.25;
  return { fg, abv };
}

// valgtHumleListe: [{ id, gram, tid }] -- tid i minutter. humleData: { id: { alfa } }
function beregnTotalIBU(valgtHumleListe, humleData, volum, beregnetOG) {
  if (volum === 0 || beregnetOG <= 1.0) return 0;

  let totalIBU = 0;
  const bignessFaktor = 1.65 * Math.pow(0.000125, beregnetOG - 1);

  for (const h of valgtHumleListe) {
    const entry = humleData[h.id];
    if (entry && h.gram > 0) {
      const alfa = entry.alfa ?? 5.0;
      let utnyttelse;
      if (h.tid === 0) {
        utnyttelse = 0.0;
      } else {
        const timesFaktor = (1 - Math.exp(-0.04 * h.tid)) / 4.15;
        utnyttelse = bignessFaktor * timesFaktor;
      }
      const alfaDesimal = alfa / 100.0;
      const mgPerLiterAlfa = (h.gram * 1000 * alfaDesimal) / volum;
      totalIBU += mgPerLiterAlfa * utnyttelse;
    }
  }
  return totalIBU;
}
