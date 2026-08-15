// Runde 24B -- DOM-fri sammenligningsmotor: oppskrift (required) vs. lager
// (available) -> shortage/status. Ren funksjon av (oppskrift, pantryItems,
// masterdata) -- ingen avhengighet til document/window, samme prinsipp som
// recipe_engine.js. Lastet FØR pantry_page.js, ETTER pantry.js.
//
// IDENTITY: matcher UTELUKKENDE på samme masterdata-id-skjema som
// pantry.js/oppskriftene allerede bruker (se pantry.js sitt filhode).
// Egendefinerte oppskrift-rader (rad.custom truthy) matches ALDRI mot
// pantry -- verken mot biblioteksvarer eller egendefinerte pantry-varer.
// De havner i "ikke sporet"-listen i stedet, aldri i shortage-tallene. Se
// Runde 24 pkt. 6/8 og Runde 24B pkt. 6 -- dette er bevisst sikkerhet mot
// feil matching, ikke en mangel som skal "fikses" med fuzzy-logikk senere.
//
// GJÆR (Runde 24B pkt. 5): dagens oppskriftsmodell har ingen eksplisitt
// pakke-count -- en valgt gjaerId telles derfor som required = 1 pakke.
// Ingen pitch-rate-beregning.
//
// RESERVE-MARGIN ("knapp", Runde 24B pkt. 7): rent rådgivende, teller
// ALDRI som shortage. malt: mindre enn 5% overskudd av required regnes som
// knapt; humle: mindre enn 10%. Gjær har ingen knapp-vurdering. Terskler
// er bevisste, runde tall -- ikke noe presisjonskrav.

const PANTRY_KNAPP_MARGIN = { malt: 0.05, humle: 0.10 };

function _pantryStatusForRad(type, required, available) {
  const shortage = Math.max(0, required - available);
  if (shortage > 0) return { shortage, status: "mangler" };
  const margin = PANTRY_KNAPP_MARGIN[type];
  if (margin != null && required > 0 && available - required < required * margin) {
    return { shortage: 0, status: "knapp" };
  }
  return { shortage: 0, status: "nok" };
}

function _summerPantryTilgjengelig(pantryItems, ingredientType, id) {
  return pantryItems
    .filter((i) => i.ingredientType === ingredientType && i.id === id && !i.custom)
    .reduce((sum, i) => sum + i.mengde, 0);
}

// null -> id finnes ikke i gjeldende masterdata (fjernet/omdøpt ingrediens
// siden oppskriften ble lagret) -- UI-laget viser en trygg "ukjent vare"-
// fallback i stedet for å gjette et navn (Runde 24B pkt. 14).
function _navnForId(masterdata, id) {
  const info = masterdata[id];
  return info ? info.navn : null;
}

// Summerer alle rader (på tvers av f.eks. flere humletilsetninger ved ulik
// koketid) med samme masterdata-id FØR sammenligning mot lager. Rader med
// .custom hoppes over her -- de håndteres separat som "ikke sporet".
function _aggreger(rader, mengdeNokkel) {
  const sum = new Map();
  for (const rad of rader) {
    if (rad.custom || !rad.id) continue;
    sum.set(rad.id, (sum.get(rad.id) || 0) + (rad[mengdeNokkel] || 0));
  }
  return sum;
}

function beregnPantryStatus(oppskrift, pantryItems, maltData, humleData, gjaerData) {
  const maltRader = oppskrift.malt || [];
  const humleRader = oppskrift.humle || [];

  const malt = [..._aggreger(maltRader, "mengde").entries()].map(([id, required]) => {
    const available = _summerPantryTilgjengelig(pantryItems, "malt", id);
    return { id, navn: _navnForId(maltData, id), required, available, ..._pantryStatusForRad("malt", required, available) };
  });

  const humle = [..._aggreger(humleRader, "gram").entries()].map(([id, required]) => {
    const available = _summerPantryTilgjengelig(pantryItems, "humle", id);
    return { id, navn: _navnForId(humleData, id), required, available, ..._pantryStatusForRad("humle", required, available) };
  });

  let gjaer = null;
  if (oppskrift.gjaerId) {
    const required = 1;
    const available = _summerPantryTilgjengelig(pantryItems, "gjaer", oppskrift.gjaerId);
    gjaer = {
      id: oppskrift.gjaerId,
      navn: _navnForId(gjaerData, oppskrift.gjaerId),
      required, available,
      ..._pantryStatusForRad("gjaer", required, available),
    };
  }

  const ikkeSporet = [];
  for (const rad of maltRader) {
    if (rad.custom) ikkeSporet.push({ ingredientType: "malt", navn: rad.custom.navn, required: rad.mengde });
  }
  for (const rad of humleRader) {
    if (rad.custom) ikkeSporet.push({ ingredientType: "humle", navn: rad.custom.navn, required: rad.gram });
  }
  if (!oppskrift.gjaerId && oppskrift.gjaerCustom) {
    ikkeSporet.push({ ingredientType: "gjaer", navn: oppskrift.gjaerCustom.navn, required: 1 });
  }

  const sporet = [...malt, ...humle, ...(gjaer ? [gjaer] : [])];

  return {
    malt, humle, gjaer, ikkeSporet,
    antallMangler: sporet.filter((r) => r.status === "mangler").length,
    antallIkkeSporet: ikkeSporet.length,
    altPaaLager: sporet.length > 0 && sporet.every((r) => r.status !== "mangler"),
  };
}
