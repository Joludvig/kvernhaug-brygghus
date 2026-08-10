// BJCP-stilmatching portert fra modules/style_engine.py. Stilgrensene selv
// bor i data/bjcp_styles.json (generert fra samme kilde -- se web/README.md
// for hvordan de holdes i sync). Denne filen porterer selve scoringslogikken:
// numerisk avvik, styrkeklynge-demping, sensorisk avvik, signaturbonus/-straff
// og de harde takene -- se den norske Python-docstringen i style_engine.py
// for den fulle begrunnelsen bak hvert tall, som bevisst ikke er gjentatt her.

const _ENGLISH_ALE_MALTS = new Set(["fawcett_maris_otter", "pale_ale_malt", "golden_promise"]);
const _ENGLISH_ALE_HOPS = new Set(["east_kent_goldings", "fuggles", "goldings"]);
const _ENGLISH_ALE_YEASTS = new Set(["safale_s04", "wlp002", "wlp007", "wyeast_1318", "lalbrew_london"]);
const _DARK_MALT_IDS = new Set([
  "pale_chocolate", "roasted_barley", "carafa_special_1",
  "carafa_special_2", "carafa_special_3", "chocolate_wheat", "dark_wheat",
]);

const _HAZY_HOPS = new Set(["citra", "mosaic", "galaxy", "ekuanot", "sabro", "el_dorado", "azacca"]);
const _HAZY_MALTS = new Set(["oat_malt", "flaked_oats", "flaked_wheat", "wheat_malt"]);

const _BELGIAN_YEASTS = new Set([
  "wlp500", "wlp510", "wlp530", "wlp545",
  "wyeast_3787", "wyeast_3522", "wyeast_3724",
  "safbrew_t58", "safale_wb06",
]);

const _STOUT_MALTS = new Set(["roasted_barley", "black"]);

const _WEST_COAST_HOPS = new Set(["centennial", "chinook", "simcoe", "cascade", "amarillo", "columbus"]);
const _WEST_COAST_YEASTS = new Set(["safale_us_05", "wlp001", "wyeast_1056"]);

const _LAGER_YEASTS = new Set([
  "saflager_w3470", "saflager_s23", "saflager_s189", "saflager_e30",
  "lalbrew_diamond_lager", "lalbrew_nova_lager",
  "bohemian_lager_m84", "california_lager_m54", "bavarian_lager_m76",
  "wlp_800", "wlp_802", "wlp_810", "wlp_820", "wlp_830",
  "wlp_833", "wlp_838", "wlp_850", "wlp_940",
  "versa_lager_m24",
]);

const _ENGLISH_STYLES_BASE = new Set(["English Bitter", "Best Bitter", "ESB / Strong Bitter"]);
const _ENGLISH_STYLES_DARK = new Set(["Robust Porter"]);
const _LAGER_STYLES = new Set([
  "Tysk Pilsner", "Tsjekkisk Pilsner", "Münchener Dunkel",
  "Vienna Lager", "Märzen", "Historisk Wiesn-Märzen", "Festbier",
  "Heller Bock (Mai-Bock)", "Dunkles Bock", "Klassisk Røykøl (Rauchbier)",
]);
const _HAZY_STYLES = new Set(["Hazy IPA / NEIPA"]);
const _BELGIAN_STYLES = new Set(["Belgisk Witbier", "Belgisk Tripel", "Belgisk Dubbel"]);
const _STOUT_STYLES = new Set(["Irsk Tørr Stout", "Oatmeal Stout", "Robust Porter"]);

const _ENGLISH_ALE_BOOST = 20;
const _LAGER_BOCK_PENALTY = 20;
const _SIGNATURE_BOOST = 20;
const _SIGNATURE_PENALTY = 15;

const _EPS_OG = 0.0005;
const _EPS_FG = 0.0005;
const _EPS_IBU = 0.5;
const _EPS_EBC = 0.5;
const _EPS_ABV = 0.05;
const _EPS_SMAK = 0.05;

const _KRITISK_NORM_TERSKEL = 0.5;
const _KRITISK_ANTALL_FOR_TAK = 2;
const _TAK_KRITISK = 80;
const _MANGE_AVVIK_ANTALL_FOR_TAK = 3;
const _TAK_FLERE_AVVIK = 85;
const _TAK_AVVIK = 95;

const _STYRKEKLYNGE_NEST_VEKT = 0.375;
const _STYRKEKLYNGE_TREDJE_VEKT = 0.175;

function _fmtKomma(verdi, desimaler) {
  return verdi.toFixed(desimaler).replace(".", ",");
}

function _fmtOmradeHeltall(verdi) {
  return Number.isInteger(verdi) ? String(verdi) : _fmtKomma(verdi, 1);
}

// Returnerer { d: score_endring, tekst: mangel_tekst|null, kritisk: bool }
function _avvikNumerisk(verdi, lo, hi, eps, vektUnder, vektOver, tekstUnder, tekstOver) {
  const bredde = Math.max(hi - lo, 1e-9);
  if (verdi < lo - eps) {
    const diff = lo - verdi;
    const normalisert = diff / bredde;
    return { d: -(normalisert * vektUnder), tekst: tekstUnder(diff), kritisk: normalisert >= _KRITISK_NORM_TERSKEL };
  }
  if (verdi > hi + eps) {
    const diff = verdi - hi;
    const normalisert = diff / bredde;
    return { d: -(normalisert * vektOver), tekst: tekstOver(diff), kritisk: normalisert >= _KRITISK_NORM_TERSKEL };
  }
  return { d: 0.0, tekst: null, kritisk: false };
}

function _kombinerStyrkeklynge(dOg, dFg, dAbv) {
  const straffer = [-dOg, -dFg, -dAbv].sort((a, b) => b - a);
  const kombinert = straffer[0] + straffer[1] * _STYRKEKLYNGE_NEST_VEKT + straffer[2] * _STYRKEKLYNGE_TREDJE_VEKT;
  return -kombinert;
}

function _avvikSensorisk(reellVerdi, minVerdi, eps = _EPS_SMAK, vekt = 5) {
  if (reellVerdi < minVerdi - eps) {
    const diff = minVerdi - reellVerdi;
    return { d: -(diff * vekt), diff };
  }
  return { d: 0.0, diff: null };
}

// recipe: { malts: [{id, mengde}], hops: [{id, gram, tid}], yeast: id,
//           stats: {og, fg, ibu, ebc, abv}, flavor_profile: {...} }
function detectRecipeSignatures(recipe) {
  const malts = new Set(recipe.malts.map((m) => m.id));
  const hops = new Set(recipe.hops.map((h) => h.id));
  const yeast = recipe.yeast || "";

  const harFellesElement = (a, b) => [...a].some((x) => b.has(x));

  const englishAle =
    harFellesElement(malts, _ENGLISH_ALE_MALTS) ||
    harFellesElement(hops, _ENGLISH_ALE_HOPS) ||
    _ENGLISH_ALE_YEASTS.has(yeast);

  const hazy = harFellesElement(hops, _HAZY_HOPS) && harFellesElement(malts, _HAZY_MALTS);

  const belgian = _BELGIAN_YEASTS.has(yeast);

  const stout = recipe.malts.some((m) => _STOUT_MALTS.has(m.id) && (m.mengde || 0) >= 0.15);

  const westCoast = harFellesElement(hops, _WEST_COAST_HOPS) && _WEST_COAST_YEASTS.has(yeast);

  const lager = _LAGER_YEASTS.has(yeast);

  return {
    english_ale: englishAle,
    dark_malt: harFellesElement(malts, _DARK_MALT_IDS),
    hazy,
    belgian,
    stout,
    west_coast: westCoast,
    lager,
  };
}

// bjcpStiler: data fra web/data/bjcp_styles.json (navn -> krav)
function analyserStilOgBalanse(recipe, bjcpStiler) {
  const stats = recipe.stats;
  const og = stats.og;
  const fg = stats.fg;
  const ibu = stats.ibu;
  const ebc = stats.ebc;
  const abv = stats.abv;
  const flavor = recipe.flavor_profile || {};

  const gravityPoints = (og - 1) * 1000;
  const buGu = gravityPoints > 0 ? ibu / gravityPoints : 0.0;

  const stilMatcher = [];

  for (const [stilNavn, krav] of Object.entries(bjcpStiler)) {
    let score = 100.0;
    const mangler = [];
    const onsketSensorisk = [];
    let kritiskeAvvik = 0;

    const ogRes = _avvikNumerisk(
      og, krav.og[0], krav.og[1], _EPS_OG, 30, 30,
      (diff) => `For lav styrke i vørteren: OG ${_fmtKomma(og, 3)} — stilområde ${_fmtKomma(krav.og[0], 3)}–${_fmtKomma(krav.og[1], 3)} — ${_fmtKomma(diff, 3)} under`,
      (diff) => `For høy styrke i vørteren: OG ${_fmtKomma(og, 3)} — stilområde ${_fmtKomma(krav.og[0], 3)}–${_fmtKomma(krav.og[1], 3)} — ${_fmtKomma(diff, 3)} over`,
    );
    if (ogRes.tekst) mangler.push(ogRes.tekst);

    const fgRes = _avvikNumerisk(
      fg, krav.fg[0], krav.fg[1], _EPS_FG, 25, 25,
      (diff) => `For lav FG: ${_fmtKomma(fg, 3)} — stilområde ${_fmtKomma(krav.fg[0], 3)}–${_fmtKomma(krav.fg[1], 3)} — ${_fmtKomma(diff, 3)} under`,
      (diff) => `For høy FG: ${_fmtKomma(fg, 3)} — stilområde ${_fmtKomma(krav.fg[0], 3)}–${_fmtKomma(krav.fg[1], 3)} — ${_fmtKomma(diff, 3)} over`,
    );
    if (fgRes.tekst) mangler.push(fgRes.tekst);

    const ibuRes = _avvikNumerisk(
      ibu, krav.ibu[0], krav.ibu[1], _EPS_IBU, 25, 20,
      (diff) => `For lav bitterhet: ${_fmtKomma(ibu, 1)} IBU — stilområde ${_fmtOmradeHeltall(krav.ibu[0])}–${_fmtOmradeHeltall(krav.ibu[1])} IBU — ${_fmtKomma(diff, 1)} IBU under`,
      (diff) => `For høy bitterhet: ${_fmtKomma(ibu, 1)} IBU — stilområde ${_fmtOmradeHeltall(krav.ibu[0])}–${_fmtOmradeHeltall(krav.ibu[1])} IBU — ${_fmtKomma(diff, 1)} IBU over`,
    );
    score += ibuRes.d;
    if (ibuRes.tekst) mangler.push(ibuRes.tekst);
    if (ibuRes.kritisk) kritiskeAvvik += 1;

    const ebcRes = _avvikNumerisk(
      ebc, krav.ebc[0], krav.ebc[1], _EPS_EBC, 15, 12,
      (diff) => `For lys farge: ${_fmtKomma(ebc, 1)} EBC — stilområde ${_fmtOmradeHeltall(krav.ebc[0])}–${_fmtOmradeHeltall(krav.ebc[1])} EBC — ${_fmtKomma(diff, 1)} EBC under`,
      (diff) => `For mørk farge: ${_fmtKomma(ebc, 1)} EBC — stilområde ${_fmtOmradeHeltall(krav.ebc[0])}–${_fmtOmradeHeltall(krav.ebc[1])} EBC — ${_fmtKomma(diff, 1)} EBC over`,
    );
    score += ebcRes.d;
    if (ebcRes.tekst) mangler.push(ebcRes.tekst);
    if (ebcRes.kritisk) kritiskeAvvik += 1;

    const abvRes = _avvikNumerisk(
      abv, krav.abv[0], krav.abv[1], _EPS_ABV, 25, 25,
      (diff) => `For lav alkohol: ${_fmtKomma(abv, 2)} % — stilområde ${_fmtKomma(krav.abv[0], 1)}–${_fmtKomma(krav.abv[1], 1)} % — ${_fmtKomma(diff, 2)} prosentpoeng under`,
      (diff) => `For høy alkohol: ${_fmtKomma(abv, 2)} % — stilområde ${_fmtKomma(krav.abv[0], 1)}–${_fmtKomma(krav.abv[1], 1)} % — ${_fmtKomma(diff, 2)} prosentpoeng over`,
    );
    if (abvRes.tekst) mangler.push(abvRes.tekst);

    score += _kombinerStyrkeklynge(ogRes.d, fgRes.d, abvRes.d);
    if (ogRes.kritisk || fgRes.kritisk || abvRes.kritisk) kritiskeAvvik += 1;

    for (const [smaksNavn, minVerdi] of Object.entries(krav.smak_krav)) {
      const reellVerdi = flavor[smaksNavn] || 0.0;
      const res = _avvikSensorisk(reellVerdi, minVerdi);
      if (res.diff !== null) {
        score += res.d;
        onsketSensorisk.push(
          `Ønsket sensorisk preg av *${smaksNavn.toLowerCase()}* (har ${reellVerdi.toFixed(1)}, stilen ber om ${minVerdi.toFixed(1)}+)`,
        );
      }
    }

    const rawScore = Math.max(0, Math.min(Math.trunc(score), 100));

    stilMatcher.push({
      stil: stilNavn, score: rawScore, raw_score: rawScore,
      mangler, onsket_sensorisk: onsketSensorisk,
      kritiske_avvik: kritiskeAvvik,
      beskrivelse: krav.beskrivelse, prio: krav.prio, kat_navn: krav.kat_navn,
      bjcp_offisiell: krav.bjcp_offisiell !== undefined ? krav.bjcp_offisiell : true,
    });
  }

  const sigs = detectRecipeSignatures(recipe);

  for (const s of stilMatcher) {
    const stil = s.stil;
    s.signaturbonus = 0;

    if (sigs.english_ale) {
      const ogMax = bjcpStiler[stil].og[1];
      if (og <= ogMax + 0.020) {
        if (_ENGLISH_STYLES_BASE.has(stil)) {
          s.score = Math.min(100, s.score + _ENGLISH_ALE_BOOST);
          s.signaturbonus += _ENGLISH_ALE_BOOST;
        } else if (_ENGLISH_STYLES_DARK.has(stil) && sigs.dark_malt) {
          s.score = Math.min(100, s.score + _ENGLISH_ALE_BOOST);
          s.signaturbonus += _ENGLISH_ALE_BOOST;
        }
      }
      if (_LAGER_STYLES.has(stil)) {
        s.score = Math.max(0, s.score - _LAGER_BOCK_PENALTY);
        s.signaturbonus -= _LAGER_BOCK_PENALTY;
      }
    }

    if (sigs.lager && _LAGER_STYLES.has(stil)) {
      s.score = Math.min(100, s.score + _SIGNATURE_BOOST);
      s.signaturbonus += _SIGNATURE_BOOST;
    }

    if (sigs.hazy) {
      if (_HAZY_STYLES.has(stil)) {
        s.score = Math.min(100, s.score + _SIGNATURE_BOOST);
        s.signaturbonus += _SIGNATURE_BOOST;
      } else if (_LAGER_STYLES.has(stil)) {
        s.score = Math.max(0, s.score - _SIGNATURE_PENALTY);
        s.signaturbonus -= _SIGNATURE_PENALTY;
      }
    }

    if (sigs.belgian) {
      if (_BELGIAN_STYLES.has(stil)) {
        s.score = Math.min(100, s.score + _SIGNATURE_BOOST);
        s.signaturbonus += _SIGNATURE_BOOST;
      } else if (_ENGLISH_STYLES_BASE.has(stil)) {
        s.score = Math.max(0, s.score - _SIGNATURE_PENALTY);
        s.signaturbonus -= _SIGNATURE_PENALTY;
      }
    }

    if (sigs.stout && _STOUT_STYLES.has(stil)) {
      s.score = Math.min(100, s.score + _SIGNATURE_BOOST);
      s.signaturbonus += _SIGNATURE_BOOST;
    }
  }

  for (const s of stilMatcher) {
    if (s.kritiske_avvik >= _KRITISK_ANTALL_FOR_TAK) {
      s.score = Math.min(s.score, _TAK_KRITISK);
    } else if (s.mangler.length >= _MANGE_AVVIK_ANTALL_FOR_TAK) {
      s.score = Math.min(s.score, _TAK_FLERE_AVVIK);
    } else if (s.mangler.length > 0 || s.onsket_sensorisk.length > 0) {
      s.score = Math.min(s.score, _TAK_AVVIK);
    }
  }

  stilMatcher.sort((a, b) => (a.prio - b.prio) || (b.score - a.score));

  const toppMatchReell = stilMatcher.reduce((best, s) => (s.raw_score > best.raw_score ? s : best), stilMatcher[0]);
  const dominantStil = toppMatchReell.raw_score > 40 ? toppMatchReell.stil : "Kreativt Brygg";

  const balanseNotater = [];
  const problemer = [];

  if (buGu > 0.85) {
    balanseNotater.push("🔥 Humledominert: Bitterheten vil dominere kraftig over maltprofilen din.");
  } else if (buGu < 0.38) {
    balanseNotater.push("🌾 Maltdominert: Lav bitterhet gjør at restsødmen fra kornene vil merkes godt.");
  } else {
    balanseNotater.push("⚖️ Harmonisk balansert: Forholdet mellom sødme og bitterhet oppleves veldig balansert.");
  }

  if (fg >= 1.018 && abv < 6.0) {
    problemer.push("⚠️ Fare for tung sødme: Høy FG betyr uforgjærbart sukker. Ølet kan bli klissete.");
  } else if (fg <= 1.006) {
    balanseNotater.push("🍃 Ekstremt tørt brygg: Gjæren har spist opp nesten alt sukkeret.");
  }

  if ((flavor["Kaffe"] || 0) > 6 && ebc > 80 && buGu > 0.8) {
    problemer.push("☕ Askeaktig finish: Kombinasjonen av mørkt brentmalt og høy bitterhet kan skape en skarp ettersmak.");
  }

  if ((flavor["Tropisk"] || 0) + (flavor["Fruktighet"] || 0) > 8 && fg > 1.016 && ibu < 35) {
    problemer.push("🧃 Juice/sirup-fare: Tropisk humle, høy restsødme og lav bitterhet kan gi et søtt, sirupaktig resultat.");
  }

  if ((flavor["Røyk"] || 0) > 4 && ((flavor["Sitrus"] || 0) > 3 || (flavor["Tropisk"] || 0) > 3)) {
    problemer.push("🔥 Sensorisk konflikt: Røykmalt og sitrus-/tropisk humle slåss mot hverandre — disse smaknuansene forsterker ikke hverandre.");
  }

  if (sigs.belgian && (flavor["Tropisk"] || 0) + (flavor["Sitrus"] || 0) > 8) {
    problemer.push("🇧🇪 Stilkollisjon: Belgisk gjær og aggressive amerikanske humler kan overvelde gjærens esterprofil — vurder nøytral gjær for humledrevne stiler.");
  }

  if (sigs.english_ale) balanseNotater.push("🇬🇧 Britisk ale-signatur: Maris Otter / EKG / britisk gjær gir klassisk pub ale-karakter.");
  if (sigs.hazy) balanseNotater.push("🌀 Hazy-signatur: Tropiske humler kombinert med myk malt (havre/hvete) peker mot NEIPA / Hazy IPA.");
  if (sigs.belgian) balanseNotater.push("🇧🇪 Belgisk signatur: Gjæren vil dominere med krydrede fenol- og esternoter — typisk pepper, nellik og frukt.");
  if (sigs.stout) balanseNotater.push("☕ Stout-signatur: Røstet bygg / sort malt gir brent espresso-karakter og sort farge.");
  if (sigs.west_coast) balanseNotater.push("🏄 West Coast-signatur: Ren, tørr gjær og bittre aromatiske humler gir klassisk West Coast IPA-profil.");
  if (sigs.lager) balanseNotater.push("🍺 Lager-signatur: Lagergjær peker mot pilsner og lagerstiler.");

  return { stil: dominantStil, stil_liste: stilMatcher, bu_gu: buGu, balanse: balanseNotater, problemer };
}
