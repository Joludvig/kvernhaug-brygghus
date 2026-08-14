// Mine oppskrifter-siden: én side, ett formål -- åpne, slette eller
// importere lagrede oppskrifter. Å "åpne" eller importere en oppskrift her
// skriver den til AKTIV_KLADD_NOKKEL og sender brukeren til byggeren, som
// gjenoppretter den derfra -- samme mekanisme som byggerens egen
// autolagrede kladd, se app.js.

const LAGRINGSNOKKEL = "kvernhaug_web_oppskrifter";
const AKTIV_KLADD_NOKKEL = "kvernhaug_web_aktiv_kladd";

function hentLagredeOppskrifter() {
  try {
    return JSON.parse(localStorage.getItem(LAGRINGSNOKKEL)) || {};
  } catch {
    return {};
  }
}

function lagreAlle(alle) {
  localStorage.setItem(LAGRINGSNOKKEL, JSON.stringify(alle));
}

// Runde 13B -- samme beskyttelse som byggerens "Åpne oppskriftsfil" og
// Importer-sidens håndoverlevering (app.js::apneOppskriftsfil,
// importer_page.js::apneIByggeren): bekreft før en eksisterende,
// meningsfull aktiv kladd overskrives. Samme oppskriftHarInnhold()-
// kontrakt fra kbhrecipe.js, ingen egen innholdsdetektor.
function _aktivKladdHarInnhold() {
  try {
    return oppskriftHarInnhold(JSON.parse(localStorage.getItem(AKTIV_KLADD_NOKKEL)));
  } catch {
    return false;
  }
}

function apneIByggeren(oppskrift) {
  if (_aktivKladdHarInnhold()) {
    const ok = confirm(t("oppskrift.apneConfirm"));
    if (!ok) return;
  }
  localStorage.setItem(AKTIV_KLADD_NOKKEL, JSON.stringify(oppskrift));
  window.location.href = "index.html";
}

function slettOppskrift(navn) {
  const alle = hentLagredeOppskrifter();
  delete alle[navn];
  lagreAlle(alle);
  visListe();
}

function visListe() {
  const alle = hentLagredeOppskrifter();
  const navnListe = Object.keys(alle);
  const listeEl = document.getElementById("oppskrift-liste");
  const meldingEl = document.getElementById("ingen-oppskrifter-melding");
  listeEl.innerHTML = "";
  meldingEl.style.display = navnListe.length === 0 ? "" : "none";

  for (const navn of navnListe) {
    const oppskrift = alle[navn];
    const li = document.createElement("li");
    li.className = "oppskrift-listeelement";

    const info = document.createElement("div");
    info.className = "oppskrift-listeelement-info";
    const tittel = document.createElement("span");
    tittel.className = "oppskrift-listeelement-navn";
    tittel.textContent = visningsnavn(navn);
    info.appendChild(tittel);
    if (oppskrift.lagretDato) {
      const dato = document.createElement("span");
      dato.className = "oppskrift-listeelement-dato";
      const d = new Date(oppskrift.lagretDato);
      const datoLokal = d.toLocaleDateString(gjeldendeSprak() === "en" ? "en-GB" : "no-NO");
      dato.textContent = isNaN(d) ? "" : t("mineOppskrifter.lagretDato", { dato: datoLokal });
      info.appendChild(dato);
    }
    li.appendChild(info);

    const knapperad = document.createElement("div");
    knapperad.className = "knapperad";

    const apneKnapp = document.createElement("button");
    apneKnapp.type = "button";
    apneKnapp.textContent = t("mineOppskrifter.apneKnapp");
    apneKnapp.addEventListener("click", () => apneIByggeren(oppskrift));
    knapperad.appendChild(apneKnapp);

    const slettKnapp = document.createElement("button");
    slettKnapp.type = "button";
    slettKnapp.className = "fjern-knapp";
    slettKnapp.textContent = "✕";
    slettKnapp.title = t("mineOppskrifter.slettTitle");
    slettKnapp.setAttribute("aria-label", t("mineOppskrifter.slettAriaLabel", { navn }));
    slettKnapp.addEventListener("click", () => {
      if (confirm(t("mineOppskrifter.slettConfirm", { navn }))) slettOppskrift(navn);
    });
    knapperad.appendChild(slettKnapp);

    li.appendChild(knapperad);
    listeEl.appendChild(li);
  }
}

function init() {
  visListe();
}

window.addEventListener("kvernhaug:sprakendret", visListe);

init();
