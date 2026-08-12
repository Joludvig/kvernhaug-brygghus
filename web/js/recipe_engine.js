// Delt, DOM-fri beregningsmotor -- brukes av BÅDE byggeren (app.js) og
// utskriftssiden (utskrift_page.js), slik at de to sidene aldri kan komme i
// utakt om hvordan en oppskrift regnes ut. Ingen avhengighet til
// document/window her -- kun calc.js/flavor.js/style.js sine rene funksjoner.
//
// En "oppskrift" i denne filen er alltid det samme, lagrings-/eksport-
// kompatible objektet som samleOppskrift()/_gjenopprettOppskrift() i app.js
// bruker: { navn, brygger, bryggeri, notater, volum, effektivitet, malt,
// humle, gjaerId, gjaerCustom, attenuationOverride, valgtStil, ... }.

// Delt HTML-escaping -- brukt av både app.js (stil-kort) og print.js
// (utskriftsdokumenter), begge laster denne filen.
function escHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

// Bygger "effektive" oppslagsobjekter (bibliotek + egendefinerte/overstyrte
// entries) slik at calc.js/flavor.js/style.js kan brukes helt uendret --
// portert fra app.js sin _effektiveDatasett(), nå uten avhengighet til
// gjaerCombobox/DOM.
function byggEffektiveDatasett(oppskrift, maltData, humleData, gjaerData) {
  const maltRader = oppskrift.malt || [];
  const humleRader = oppskrift.humle || [];

  const effMalt = { ...maltData };
  for (const m of maltRader) if (m.custom) effMalt[m.id] = m.custom;

  const effHumle = { ...humleData };
  for (const h of humleRader) {
    if (h.custom) effHumle[h.id] = h.custom;
    else if (h.alfaOverride != null && humleData[h.id]) effHumle[h.id] = { ...humleData[h.id], alfa: h.alfaOverride };
  }

  const effGjaer = { ...gjaerData };
  let gjaerId = oppskrift.gjaerId || null;
  const gjaerCustom = oppskrift.gjaerCustom || null;
  if (!gjaerId && gjaerCustom) {
    gjaerId = "egendefinert_gjaer";
    effGjaer[gjaerId] = gjaerCustom;
  }

  return { maltRader, humleRader, effMalt, effHumle, effGjaer, gjaerId };
}

function hentUtgjaeringForOppskrift(oppskrift, gjaerId, effGjaer) {
  if (gjaerId && effGjaer[gjaerId]) return effGjaer[gjaerId].attenuation;
  const manuell = parseFloat(oppskrift.attenuationOverride);
  return isFinite(manuell) ? manuell / 100 : 0.75;
}

// Kjører hele beregningskjeden (OG/FG/ABV/IBU/EBC, smaksprofil, stilmatch)
// for en gitt oppskrift -- samme rekkefølge og samme funksjoner som
// app.js sin beregnOgVisResultat(), men returnerer resultatet i stedet for
// å skrive til DOM-en.
function beregnOppskrift(oppskrift, maltData, humleData, gjaerData, bjcpStyles) {
  const volum = parseFloat(oppskrift.volum) || 0;
  const effektivitet = (parseFloat(oppskrift.effektivitet) || 0) / 100;

  const { maltRader, humleRader, effMalt, effHumle, effGjaer, gjaerId } =
    byggEffektiveDatasett(oppskrift, maltData, humleData, gjaerData);

  const og = beregnOG(maltRader, effMalt, volum, effektivitet);
  const ebc = beregnEBC(maltRader, effMalt, volum);
  const { fg, abv } = beregnFgOgAbv(og, hentUtgjaeringForOppskrift(oppskrift, gjaerId, effGjaer));
  const ibu = beregnTotalIBU(humleRader, effHumle, volum, og);

  const flavorProfile = beregnSmaksprofil(maltRader, effMalt, humleRader, effHumle, ibu, gjaerId, effGjaer);

  const recipeForStil = {
    malts: maltRader, hops: humleRader, yeast: gjaerId,
    stats: { og, fg, ibu, ebc, abv }, flavor_profile: flavorProfile,
  };
  const stilAnalyse = analyserStilOgBalanse(recipeForStil, bjcpStyles);

  return {
    volum, effektivitet, maltRader, humleRader, effMalt, effHumle, effGjaer, gjaerId,
    og, fg, abv, ibu, ebc, flavorProfile, stilAnalyse,
  };
}

// Robust, datadrevet sjekk for om oppskriften faktisk har nok innhold til at
// en stilmatch gir mening -- IKKE en visuell hardkoding. "Kreativt Brygg" er
// style_engine.py sin egen, meningsfulle betegnelse for "treffer ingen stil
// godt" (raw_score <= 40) og skal fortsatt vises når brukeren faktisk har
// lagt inn ingredienser som ikke treffer noe. Denne sjekken fanger kun det
// separate tilfellet "ingen ingredienser lagt inn ennå".
function harNokDataForStilmatch(maltRader, humleRader) {
  const harMalt = (maltRader || []).some((m) => m.id && m.mengde > 0);
  const harHumle = (humleRader || []).some((h) => h.id && h.gram > 0);
  return harMalt || harHumle;
}
