// Porting av modules/recipe_importer.py (DESKTOP-appens tekstimport-kontrakt,
// via ui/sidebar.py sin "📥 Importer oppskrift fra tekst"-expander). Samme
// regex-mønstre og samme flyt (parse -> fuzzy-match -> forhåndsvisning ->
// bekreft), portet 1:1 der det er mulig. Eneste reelle avvik: Pythons
// difflib.SequenceMatcher.ratio() er erstattet med en JS-implementasjon av
// samme Ratcliff/Obershelp-algoritme (lengste-felles-blokk, rekursivt) --
// samme prinsipp og terskel (0.6), men ikke bit-for-bit identisk output i
// alle kanttilfeller siden det er to uavhengige implementasjoner.
// Ingen DOM her -- ren beregningslogikk, gjenbrukt av web/js/importer_page.js.
//
// Runde 23 -- BEVISST avvik fra desktop-portens 1:1-prinsipp: web har (siden
// Runde 22) en Metric/US customary-visningsvelger som desktop ikke har, så
// fritekstimporten her forstår i tillegg US customary-enheter (US gal, lb,
// oz) desktop-parseren ikke kjenner til. Parseren tolker ALLTID enheten som
// faktisk står skrevet i teksten -- aldri brukerens valgte visningsenhet
// (unitSystem) -- og returnerer alltid canonical metrisk (liter/kg/gram),
// nøyaktig som før. Se formatX()/parseX() i units.js, hvis konstanter
// (US_GALLON_L/LB_KG/OZ_G) og parseVolume/parseMaltMass/parseHopMass
// gjenbrukes direkte her for selve konverteringen, slik at det kun finnes
// ÉN kilde til disse tallene i hele web-appen. "gal"/"gallon(s)" tolkes
// alltid som US gallon, aldri Imperial/UK gallon -- eksplisitt "imperial
// gallon(s)" gir en vennlig advarsel i stedet for en stille feilgjetning,
// se _reBatchImperial nedenfor.

const RECIPE_IMPORTER_TERSKEL = 0.6;

function _importerRatio(a, b) {
  a = a.toLowerCase();
  b = b.toLowerCase();
  if (a.length === 0 && b.length === 0) return 1;
  if (a.length === 0 || b.length === 0) return 0;

  function finnBlokk(alo, ahi, blo, bhi) {
    let bestI = alo, bestJ = blo, bestSize = 0;
    const b2j = {};
    for (let j = blo; j < bhi; j++) {
      const c = b[j];
      if (!b2j[c]) b2j[c] = [];
      b2j[c].push(j);
    }
    let j2len = {};
    for (let i = alo; i < ahi; i++) {
      const nyJ2len = {};
      const kandidater = b2j[a[i]] || [];
      for (const j of kandidater) {
        if (j < blo || j >= bhi) continue;
        const k = (j2len[j - 1] || 0) + 1;
        nyJ2len[j] = k;
        if (k > bestSize) {
          bestI = i - k + 1;
          bestJ = j - k + 1;
          bestSize = k;
        }
      }
      j2len = nyJ2len;
    }
    return { i: bestI, j: bestJ, size: bestSize };
  }

  function matchLengde(alo, ahi, blo, bhi) {
    const m = finnBlokk(alo, ahi, blo, bhi);
    if (m.size === 0) return 0;
    let total = m.size;
    if (m.i > alo && m.j > blo) total += matchLengde(alo, m.i, blo, m.j);
    if (m.i + m.size < ahi && m.j + m.size < bhi) total += matchLengde(m.i + m.size, ahi, m.j + m.size, bhi);
    return total;
  }

  const matches = matchLengde(0, a.length, 0, b.length);
  return (2 * matches) / (a.length + b.length);
}

function _finnBesteTreff(navnSokt, db, terskel = RECIPE_IMPORTER_TERSKEL) {
  const sokt = navnSokt.toLowerCase().trim();
  let bestId = null, bestNavn = null, bestScore = 0;

  for (const [id, info] of Object.entries(db || {})) {
    if (!info || typeof info !== "object") continue;
    const kandidater = [id.replace(/_/g, " "), info.navn || info.display_name || ""];
    for (const kandidat of kandidater) {
      if (!kandidat) continue;
      const score = _importerRatio(sokt, kandidat);
      if (score > bestScore) {
        bestScore = score;
        bestId = id;
        bestNavn = info.navn || info.display_name || id;
      }
    }
  }

  if (bestScore >= terskel) return { id: bestId, navn: bestNavn, score: bestScore };
  return { id: null, navn: null, score: bestScore };
}

const _IMPORT_UNICODE_SPACES = "   ​­";

function _importerNormaliserTekst(text) {
  text = text.replace(/^﻿/, "");
  text = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  for (const tegn of _IMPORT_UNICODE_SPACES) {
    text = text.split(tegn).join(" ");
  }
  text = text.split("`").join("");
  return text;
}

// Runde 23 -- delt kg-konvertering for malt-linjer (både enkeltrader og
// "Total malt: ..."), gjenbrukt av begge steder unit-token dukker opp.
// kg/g dekkes ikke av parseMaltMass (den kjenner kun kg<->lb), så g
// regnes manuelt -- lb/lbs/pound/pounds går via samme US_GALLON/LB_KG-
// konstant som resten av appen via parseMaltMass(verdi, "us").
function _importerMaltKg(verdi, enhetRaa) {
  const enhet = enhetRaa.toLowerCase();
  if (enhet === "kg") return verdi;
  if (enhet === "g") return verdi / 1000.0;
  return parseMaltMass(verdi, "us");
}

function parseRecipeText(text) {
  text = _importerNormaliserTekst(text);

  // Runde 23 -- humle/malt-enhetsgruppene er utvidet med US customary
  // (oz for humle, lb/lbs/pound/pounds for malt) i tillegg til de
  // opprinnelige g/kg. "kg" står FØR "g" i malt-alternativet (regex-
  // alternering velger første treff, ikke lengste), akkurat som før --
  // ellers uendret matchrekkefølge/-presedens fra før Runde 23.
  const reHumle = /^\s*(\d+[.,]?\d*)\s*(g|oz|ounces?)\s+(.+?)\s+(\d+)\s*min\s*$/i;
  const reMalt = /^\s*(\d+[.,]?\d*)\s*(kg|g|lbs?|pounds?)\s+(.+?)\s*$/i;
  const reTotalMalt = /^totalt?\s*malt\s*:?\s*(\d+[.,]?\d*)\s*(kg|g|lbs?|pounds?)\b/i;
  const reMaltPct = /^\s*(\d+[.,]?\d*)\s*%\s+(.+?)\s*$/i;
  const reMetadata = /^(?:batch(?:\s*size)?|volum(?:e)?|boil|kok(?:etid)?|efficiency|effektivitet|og|fg|ibu|abv)\s*:/i;
  // Eksplisitt "imperial gal(lon(s))" sjekkes FØR den vanlige batch-
  // regexen under, slik at Kvernhaug aldri stille tolker Imperial/UK
  // gallon som US gallon -- se filhode-kommentaren.
  const reBatchImperial = /^(?:batch(?:\s*size)?|volum(?:e)?)\s*:\s*(\d+[.,]?\d*)\s*imperial\s*gal(?:lons?)?\b/i;
  const reBatch = /^(?:batch(?:\s*size)?|volum(?:e)?)\s*:\s*(\d+[.,]?\d*)\s*(us\s*gal(?:lons?)?|gal(?:lons?)?|l(?:iters?|itres?)?)?\b/i;
  const reLabel = /^(?:recipe|navn|name|oppskrift)\s*:\s*(.+)$/i;

  const maltListe = [], humleListe = [], gjaerListe = [], pctMaltListe = [];
  let totalMaltKg = null;
  let oppskriftNavn = null;
  let batchLiter = null;
  const warnings = [];

  for (let linje of text.split("\n")) {
    linje = linje.trim();
    if (!linje || linje.startsWith("#")) continue;

    let m = reBatchImperial.exec(linje);
    if (m) {
      warnings.push(t("import.advarselImperialGallon"));
      continue;
    }

    m = reBatch.exec(linje);
    if (m) {
      const verdi = parseFloat(m[1].replace(",", "."));
      const enhet = (m[2] || "").toLowerCase().replace(/\s+/g, "");
      batchLiter = enhet.includes("gal") ? parseVolume(verdi, "us") : parseVolume(verdi, "metric");
      continue;
    }
    if (reMetadata.test(linje)) continue;

    m = reTotalMalt.exec(linje);
    if (m) {
      totalMaltKg = _importerMaltKg(parseFloat(m[1].replace(",", ".")), m[2]);
      continue;
    }

    m = reHumle.exec(linje);
    if (m) {
      const verdi = parseFloat(m[1].replace(",", "."));
      const enhet = m[2].toLowerCase();
      const gram = enhet === "g" ? parseHopMass(verdi, "metric") : parseHopMass(verdi, "us");
      humleListe.push({ navn: m[3].trim(), gram, tid: parseInt(m[4], 10) });
      continue;
    }

    m = reMaltPct.exec(linje);
    if (m) {
      pctMaltListe.push({ navn: m[2].trim(), pct: parseFloat(m[1].replace(",", ".")) });
      continue;
    }

    m = reMalt.exec(linje);
    if (m) {
      const mengde = _importerMaltKg(parseFloat(m[1].replace(",", ".")), m[2]);
      maltListe.push({ navn: m[3].trim(), mengde });
      continue;
    }

    if (oppskriftNavn === null && !/\d/.test(linje) && maltListe.length + humleListe.length + pctMaltListe.length === 0) {
      const mLabel = reLabel.exec(linje);
      oppskriftNavn = mLabel ? mLabel[1].trim() : linje;
    } else {
      gjaerListe.push({ navn: linje });
    }
  }

  if (pctMaltListe.length) {
    const totalPct = pctMaltListe.reduce((sum, p) => sum + p.pct, 0);
    if (Math.abs(totalPct - 100.0) > 5.0) {
      warnings.push(t("import.advarselProsentSum", { sum: totalPct.toFixed(1) }));
    }
    if (totalMaltKg === null) {
      warnings.push(t("import.advarselManglerTotal"));
    } else {
      for (const p of pctMaltListe) {
        maltListe.push({ navn: p.navn, mengde: Math.round((p.pct / 100.0) * totalMaltKg * 1000) / 1000 });
      }
    }
  }

  return { malt: maltListe, humle: humleListe, gjaer: gjaerListe, warnings, navn: oppskriftNavn, batch_liter: batchLiter };
}

function matchImportedIngredients(parsed, maltDb, humleDb, gjaerDb) {
  const matchedMalt = [], matchedHumle = [], unmatched = [];

  for (const item of parsed.malt) {
    const { id, navn, score } = _finnBesteTreff(item.navn, maltDb);
    if (id) matchedMalt.push({ navn: item.navn, id, display_name: navn, mengde: item.mengde, score: Math.round(score * 100) / 100 });
    else unmatched.push({ navn: item.navn, kategori: "malt" });
  }

  for (const item of parsed.humle) {
    const { id, navn, score } = _finnBesteTreff(item.navn, humleDb);
    if (id) matchedHumle.push({ navn: item.navn, id, display_name: navn, gram: item.gram, tid: item.tid, score: Math.round(score * 100) / 100 });
    else unmatched.push({ navn: item.navn, kategori: "humle" });
  }

  let matchedGjaer = null;
  let bestScore = 0;
  for (const item of parsed.gjaer) {
    const { id, navn, score } = _finnBesteTreff(item.navn, gjaerDb);
    if (id && score > bestScore) {
      bestScore = score;
      matchedGjaer = { navn: item.navn, id, display_name: navn, score: Math.round(score * 100) / 100 };
    }
  }
  if (!matchedGjaer) {
    for (const item of parsed.gjaer) unmatched.push({ navn: item.navn, kategori: "gjaer" });
  }

  return { matched: { malt: matchedMalt, humle: matchedHumle, gjaer: matchedGjaer }, unmatched };
}
