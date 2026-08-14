// Utskrift-siden: egen side med ett formål -- skrive ut oppskriften som
// oppskriftsark/handleliste/bryggedagsark/bryggelogg. Fungerer på DEN AKTIVE,
// også ulagrede, kladden fra byggeren (AKTIV_KLADD_NOKKEL), eller på en
// tidligere lagret oppskrift. Skriver ALDRI selv til AKTIV_KLADD_NOKKEL --
// å forhåndsvise en lagret oppskrift her skal aldri overskrive det brukeren
// faktisk holder på med i Oppskriftsbyggeren. "Tilbake til byggeren" er
// derfor en helt vanlig lenke; kladden er urørt uansett hva som er gjort her.

const LAGRINGSNOKKEL = "kvernhaug_web_oppskrifter";
const AKTIV_KLADD_NOKKEL = "kvernhaug_web_aktiv_kladd";

let maltData = {}, humleData = {}, gjaerData = {}, bjcpStyles = {};
let valgtOppskrift = null;
let sisteBeregning = null;
let oppdaterSmakshjul = null;

async function lastData() {
  const [malt, humle, gjaer, stiler] = await Promise.all([
    fetch(KBH_ROOT + "data/malt.json").then((r) => r.json()),
    fetch(KBH_ROOT + "data/humle.json").then((r) => r.json()),
    fetch(KBH_ROOT + "data/gjaer.json").then((r) => r.json()),
    fetch(KBH_ROOT + "data/bjcp_styles.json").then((r) => r.json()),
  ]);
  maltData = malt; humleData = humle; gjaerData = gjaer; bjcpStyles = stiler;
}

function hentAktivKladd() {
  try {
    return JSON.parse(localStorage.getItem(AKTIV_KLADD_NOKKEL));
  } catch {
    return null;
  }
}

function hentLagredeOppskrifter() {
  try {
    return JSON.parse(localStorage.getItem(LAGRINGSNOKKEL)) || {};
  } catch {
    return {};
  }
}

function velgOppskrift(valgtVerdi) {
  const kladd = hentAktivKladd();
  const lagrede = hentLagredeOppskrifter();
  if (valgtVerdi === "__aktiv__") valgtOppskrift = kladd;
  else if (valgtVerdi && valgtVerdi.startsWith("lagret:")) valgtOppskrift = lagrede[valgtVerdi.slice(7)];
  else valgtOppskrift = kladd || Object.values(lagrede)[0] || null;

  if (!valgtOppskrift) return;

  sisteBeregning = beregnOppskrift(valgtOppskrift, maltData, humleData, gjaerData, bjcpStyles);
  if (oppdaterSmakshjul) oppdaterSmakshjul(sisteBeregning.flavorProfile);

  document.getElementById("utskrift-info-navn").textContent = valgtOppskrift.navn || t("identitet.utenNavn");
  document.getElementById("utskrift-info-tall").textContent = t("utskrift.infoTall", {
    og: sisteBeregning.og.toFixed(3), fg: sisteBeregning.fg.toFixed(3),
    abv: sisteBeregning.abv.toFixed(1).replace(".", ","),
    ibu: Math.round(sisteBeregning.ibu), ebc: Math.round(sisteBeregning.ebc),
  });
}

function byggValgliste() {
  const kladd = hentAktivKladd();
  const lagrede = hentLagredeOppskrifter();
  const tomTilstand = document.getElementById("utskrift-tom-tilstand");
  const innhold = document.getElementById("utskrift-innhold");

  if (!kladd && Object.keys(lagrede).length === 0) {
    tomTilstand.hidden = false;
    innhold.hidden = true;
    return;
  }
  tomTilstand.hidden = true;
  innhold.hidden = false;

  const select = document.getElementById("utskrift-oppskrift-velger");
  select.innerHTML = "";

  if (kladd) {
    const opt = document.createElement("option");
    opt.value = "__aktiv__";
    opt.textContent = t("utskrift.velgerAktivt", { navn: kladd.navn || t("identitet.utenNavn") });
    select.appendChild(opt);
  }
  for (const navn of Object.keys(lagrede)) {
    const opt = document.createElement("option");
    opt.value = `lagret:${navn}`;
    opt.textContent = navn;
    select.appendChild(opt);
  }

  select.addEventListener("change", () => velgOppskrift(select.value));
  velgOppskrift(select.value);
}

function _hentDokKontekst() {
  const svg = document.querySelector("#smakshjul-container svg");
  return byggDokumentKontekst(valgtOppskrift, sisteBeregning, svg ? svg.outerHTML : null);
}

function initUtskriftKnapper() {
  document.getElementById("print-oppskriftsark-knapp").addEventListener("click", () =>
    _skrivUtDokument(byggOppskriftsarkHtml, _hentDokKontekst(), "oppskriftsark"));
  document.getElementById("print-handleliste-knapp").addEventListener("click", () =>
    _skrivUtDokument(byggHandlelisteHtml, _hentDokKontekst(), "handleliste"));
  document.getElementById("print-bryggedagsark-knapp").addEventListener("click", () =>
    _skrivUtDokument(byggBryggedagsarkHtml, _hentDokKontekst(), "bryggedagsark"));
  document.getElementById("print-bryggelogg-knapp").addEventListener("click", () =>
    _skrivUtDokument(byggBryggeloggHtml, _hentDokKontekst(), "bryggelogg"));
  window.addEventListener("afterprint", _tilbakestillEtterPrint);
}

async function init() {
  await lastData();
  oppdaterSmakshjul = initSmakshjul(document.getElementById("smakshjul-container"), SMAKS_KATEGORIER);
  byggValgliste();
  initUtskriftKnapper();
}

window.addEventListener("kvernhaug:sprakendret", () => {
  oppdaterSmakshjul = initSmakshjul(document.getElementById("smakshjul-container"), SMAKS_KATEGORIER);
  byggValgliste();
});

init();
