// Verktøy-siden (issue #77): frittstående ABV-kalkulator. Ingen
// oppskrift/brygg-state involvert i det hele tatt -- kun de to
// tallfeltene på denne siden og web/js/calc.js sin beregnAbvFraOgFg().
//
// UI-presentasjonsterskel (ikke en del av Core-kontrakten) for når
// high-gravity-estimatet vises i tillegg til standardestimatet -- se
// "Measured-gravity ABV (issue #77)" i
// docs/development/CORE_CALCULATION_CONTRACT.md. Samme terskel som
// ui/abv_calculator_panel.py sin tilsvarende konstant i App.
const VERKTOY_HOY_GRAVITET_TERSKEL_OG = 1.070;

function _formatterProsent(verdi) {
  return `${verdi.toFixed(1).replace(".", ",")} %`;
}

function _oppdaterAbvKalkulator() {
  const ogFelt = document.getElementById("verktoy-abv-og");
  const fgFelt = document.getElementById("verktoy-abv-fg");
  const feilElement = document.getElementById("verktoy-abv-feil");
  const normalBoks = document.getElementById("verktoy-abv-resultat-normal");
  const hoygravBoks = document.getElementById("verktoy-abv-resultat-hoygrav");
  const hoygravForklaring = document.getElementById("verktoy-abv-hoygrav-forklaring");

  const og = parseFloat(ogFelt.value);
  const fg = parseFloat(fgFelt.value);

  if (Number.isNaN(og) || Number.isNaN(fg)) {
    feilElement.textContent = t("verktoy.abv.ugyldigInput");
    feilElement.hidden = false;
    normalBoks.hidden = true;
    hoygravBoks.hidden = true;
    hoygravForklaring.hidden = true;
    return;
  }

  let resultat;
  try {
    resultat = beregnAbvFraOgFg(og, fg);
  } catch {
    feilElement.textContent = t("verktoy.abv.ugyldigInput");
    feilElement.hidden = false;
    normalBoks.hidden = true;
    hoygravBoks.hidden = true;
    hoygravForklaring.hidden = true;
    return;
  }

  feilElement.hidden = true;
  feilElement.textContent = "";

  if (og >= VERKTOY_HOY_GRAVITET_TERSKEL_OG) {
    document.getElementById("verktoy-abv-standard-tall").textContent = _formatterProsent(resultat.standard);
    document.getElementById("verktoy-abv-hoygrav-tall").textContent = _formatterProsent(resultat.highGravity);
    normalBoks.hidden = true;
    hoygravBoks.hidden = false;
    hoygravForklaring.hidden = false;
  } else {
    document.getElementById("verktoy-abv-normal-tall").textContent = _formatterProsent(resultat.standard);
    normalBoks.hidden = false;
    hoygravBoks.hidden = true;
    hoygravForklaring.hidden = true;
  }
}

function _initAbvKalkulator() {
  document.getElementById("verktoy-abv-og").addEventListener("input", _oppdaterAbvKalkulator);
  document.getElementById("verktoy-abv-fg").addEventListener("input", _oppdaterAbvKalkulator);
  _oppdaterAbvKalkulator();
}

_initAbvKalkulator();
