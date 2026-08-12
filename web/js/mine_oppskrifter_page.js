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

function apneIByggeren(oppskrift) {
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
    tittel.textContent = navn;
    info.appendChild(tittel);
    if (oppskrift.lagretDato) {
      const dato = document.createElement("span");
      dato.className = "oppskrift-listeelement-dato";
      const d = new Date(oppskrift.lagretDato);
      dato.textContent = isNaN(d) ? "" : `Lagret ${d.toLocaleDateString("no-NO")}`;
      info.appendChild(dato);
    }
    li.appendChild(info);

    const knapperad = document.createElement("div");
    knapperad.className = "knapperad";

    const apneKnapp = document.createElement("button");
    apneKnapp.type = "button";
    apneKnapp.textContent = "Åpne i byggeren";
    apneKnapp.addEventListener("click", () => apneIByggeren(oppskrift));
    knapperad.appendChild(apneKnapp);

    const slettKnapp = document.createElement("button");
    slettKnapp.type = "button";
    slettKnapp.className = "fjern-knapp";
    slettKnapp.textContent = "✕";
    slettKnapp.title = "Slett";
    slettKnapp.setAttribute("aria-label", `Slett ${navn}`);
    slettKnapp.addEventListener("click", () => {
      if (confirm(`Slette "${navn}"? Dette kan ikke angres.`)) slettOppskrift(navn);
    });
    knapperad.appendChild(slettKnapp);

    li.appendChild(knapperad);
    listeEl.appendChild(li);
  }
}

function init() {
  visListe();
}

init();
