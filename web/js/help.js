// Hjelpeknapper ("?") -- ett delt popover-element, posisjonert ved klikk/tap
// (bevisst IKKE hover, som ikke fungerer på touch). Kort innhold: hva
// begrepet betyr + hvorfor brukeren bør bry seg, ikke lange forklaringer.

const HJELP_TEKSTER = {
  og: {
    tittel: "OG — Original Gravity",
    tekst: "Måler sukkerinnholdet i vørteren FØR gjæring. Høyere OG betyr mer sukker gjæren kan omdanne til alkohol — og dermed et sterkere, fyldigere øl.",
    lesMer: "hjelp/index.html#og",
  },
  fg: {
    tittel: "FG — Final Gravity",
    tekst: "Måler sukkeret som er IGJEN etter gjæring. Lav FG gir et tørt øl, høy FG gir mer restsødme og fylde.",
    lesMer: "hjelp/index.html#fg",
  },
  abv: {
    tittel: "ABV — Alkoholstyrke",
    tekst: "Alkoholprosenten i det ferdige ølet, regnet ut fra forskjellen mellom OG og FG.",
    lesMer: "hjelp/index.html#abv",
  },
  ibu: {
    tittel: "IBU — Bitterhet",
    tekst: "Måler humlebitterhet. Høyere tall betyr et mer bittert øl. Typiske ølstiler ligger mellom 10 og 70 IBU.",
    lesMer: "hjelp/index.html#ibu",
  },
  ebc: {
    tittel: "EBC — Farge",
    tekst: "Måler ølets farge, fra blekt gult (lave tall) til nesten sort (høye tall).",
    lesMer: "hjelp/index.html#ebc",
  },
  utgjaering: {
    tittel: "Utgjæring (attenuation)",
    tekst: "Hvor stor andel av sukkeret gjæren klarer å omdanne til alkohol. Høyere utgjæring gir et tørrere øl med lavere FG.",
    lesMer: "hjelp/index.html#utgjaering",
  },
  alfasyre: {
    tittel: "Alfasyre",
    tekst: "Prosentandel bitterstoffer i humlen. Høyere alfasyre gir mer bitterhet per gram humle — varierer normalt noe fra pose til pose, så juster gjerne tallet etter det som står på din egen pakke.",
    lesMer: "hjelp/index.html#alfasyre",
  },
  stilmatch: {
    tittel: "Stilmatch",
    tekst: "Sammenligner oppskriftens tall (OG/FG/ABV/IBU/EBC) mot typiske verdier for kjente ølstiler i Kvernhaug Brygghus sitt bibliotek, og viser hvor godt den passer.",
    lesMer: "hjelp/index.html#stilmatching",
  },
  smakshjul: {
    tittel: "Smakshjul",
    tekst: "Viser en forventet smaksprofil basert på malt, humle og gjær. Jo lenger ut mot kanten en akse strekker seg, jo mer fremtredende er den smaken ventet å bli.",
    lesMer: "hjelp/index.html#smakshjulet",
  },
};

let _hjelpPopover = null;
let _hjelpApenKnapp = null;

function _lukkHjelp() {
  if (_hjelpPopover) _hjelpPopover.hidden = true;
  if (_hjelpApenKnapp) _hjelpApenKnapp.setAttribute("aria-expanded", "false");
  _hjelpApenKnapp = null;
}

function _apneHjelp(knapp) {
  const nokkel = knapp.dataset.hjelp;
  const innhold = HJELP_TEKSTER[nokkel];
  if (!innhold) return;

  const lesMerHtml = innhold.lesMer
    ? `<a class="hjelp-les-mer" href="${innhold.lesMer}" target="_blank" rel="noopener">Les mer →</a>`
    : "";

  _hjelpPopover.innerHTML = `
    <div class="hjelp-popover-topp">
      <strong>${innhold.tittel}</strong>
      <button type="button" class="hjelp-lukk" aria-label="Lukk">✕</button>
    </div>
    <p>${innhold.tekst}</p>
    ${lesMerHtml}
  `;
  _hjelpPopover.hidden = false;
  _hjelpPopover.querySelector(".hjelp-lukk").addEventListener("click", _lukkHjelp);

  const knappRect = knapp.getBoundingClientRect();
  const popoverRect = _hjelpPopover.getBoundingClientRect();
  const margin = 10;

  let left = knappRect.left + knappRect.width / 2 - popoverRect.width / 2;
  left = Math.max(margin, Math.min(left, window.innerWidth - popoverRect.width - margin));

  let top = knappRect.bottom + 8;
  if (top + popoverRect.height > window.innerHeight - margin) {
    top = knappRect.top - popoverRect.height - 8;
  }
  top = Math.max(margin, top);

  _hjelpPopover.style.left = `${left}px`;
  _hjelpPopover.style.top = `${top}px`;

  knapp.setAttribute("aria-expanded", "true");
  _hjelpApenKnapp = knapp;
}

function initHjelp() {
  _hjelpPopover = document.createElement("div");
  _hjelpPopover.className = "hjelp-popover";
  _hjelpPopover.hidden = true;
  _hjelpPopover.setAttribute("role", "dialog");
  document.body.appendChild(_hjelpPopover);

  document.addEventListener("click", (e) => {
    const knapp = e.target.closest(".hjelp-knapp");
    if (knapp) {
      e.stopPropagation();
      if (_hjelpApenKnapp === knapp) {
        _lukkHjelp();
      } else {
        _apneHjelp(knapp);
      }
      return;
    }
    if (_hjelpApenKnapp && !e.target.closest(".hjelp-popover")) {
      _lukkHjelp();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") _lukkHjelp();
  });

  window.addEventListener("resize", _lukkHjelp);
}
