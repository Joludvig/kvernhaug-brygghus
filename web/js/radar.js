// Smakshjul — vanilla SVG-radardiagram, ingen eksterne avhengigheter.
//
// Valgt SVG fremfor Canvas: SVG-tekst forblir skarp på enhver skjerm-
// tetthet/zoom uten å måtte håndtere devicePixelRatio manuelt (viktig for
// kravet om ikke-avkuttede etiketter på mobil), skalerer responsivt via
// viewBox + CSS uten egen redraw-på-resize-logikk, og kan styles med de
// samme CSS-variablene (--gold, --pergament osv.) som resten av siden.
// Live-oppdatering er billig: kun datapolygonets 18 punkter endres per
// kalkulering, resten av SVG-en (akser/rutenett/etiketter) er statisk og
// bygges én gang. Plotly.js (som desktop-appen bruker) ble vurdert, men
// gir ingen reell fordel her — dette er ett enkelt, fast 0–10-skalert
// polygon med 18 faste akser, godt innenfor rekkevidde for en liten,
// hånd-skrevet komponent, og en CDN-avhengighet er nettopp det
// prosjektet bevisst har unngått for web-versjonen så langt.

const _SMAKSHJUL_VIEWBOX = 440;
const _SMAKSHJUL_SENTER = 220;
const _SMAKSHJUL_RADIUS = 142;
const _SMAKSHJUL_LABEL_RADIUS = 176;
const _SMAKSHJUL_RINGER = [0.25, 0.5, 0.75, 1.0];

const SVG_NS = "http://www.w3.org/2000/svg";

function _smakshjulPunkt(indeks, totalt, radius) {
  const vinkelGrader = (indeks / totalt) * 360;
  const vinkelRad = (vinkelGrader * Math.PI) / 180;
  return {
    x: _SMAKSHJUL_SENTER + radius * Math.sin(vinkelRad),
    y: _SMAKSHJUL_SENTER - radius * Math.cos(vinkelRad),
  };
}

function _punkterStreng(kategorier, verdiFor, radiusFor) {
  return kategorier
    .map((kat, i) => {
      const p = _smakshjulPunkt(i, kategorier.length, radiusFor(verdiFor(kat)));
      return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
    })
    .join(" ");
}

function _lagSvgEl(tag, attrs) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

// Bygger den statiske delen (rutenett, akser, etiketter) én gang, og
// returnerer en oppdateringsfunksjon som kun endrer datapolygonet.
function initSmakshjul(container, kategorier) {
  container.innerHTML = "";

  const svg = _lagSvgEl("svg", {
    viewBox: `0 0 ${_SMAKSHJUL_VIEWBOX} ${_SMAKSHJUL_VIEWBOX}`,
    class: "smakshjul-svg",
    role: "img",
    "aria-label": "Smakshjul — sensorisk profil basert på valgte ingredienser",
  });

  // Rutenett: konsentriske 18-kant-ringer i stedet for sirkler, slik at
  // ringene følger de samme aksene som dataene plottes mot.
  for (const andel of _SMAKSHJUL_RINGER) {
    const pts = _punkterStreng(kategorier, () => andel * 10, (v) => (v / 10) * _SMAKSHJUL_RADIUS);
    svg.appendChild(_lagSvgEl("polygon", { points: pts, class: "smakshjul-rutenett" }));
  }

  // Akselinjer fra sentrum til ytterkant, pluss etiketter.
  kategorier.forEach((kat, i) => {
    const ytre = _smakshjulPunkt(i, kategorier.length, _SMAKSHJUL_RADIUS);
    svg.appendChild(
      _lagSvgEl("line", {
        x1: _SMAKSHJUL_SENTER, y1: _SMAKSHJUL_SENTER, x2: ytre.x, y2: ytre.y,
        class: "smakshjul-akse",
      }),
    );

    const labelPos = _smakshjulPunkt(i, kategorier.length, _SMAKSHJUL_LABEL_RADIUS);
    const dx = labelPos.x - _SMAKSHJUL_SENTER;
    const dy = labelPos.y - _SMAKSHJUL_SENTER;
    let anchor = "middle";
    if (Math.abs(dx) > 12) anchor = dx > 0 ? "start" : "end";
    let baseline = "middle";
    if (dy < -_SMAKSHJUL_LABEL_RADIUS * 0.55) baseline = "text-after-edge";
    else if (dy > _SMAKSHJUL_LABEL_RADIUS * 0.55) baseline = "hanging";

    const text = _lagSvgEl("text", {
      x: labelPos.x, y: labelPos.y,
      "text-anchor": anchor,
      "dominant-baseline": baseline,
      class: "smakshjul-label",
    });
    text.textContent = kat;
    svg.appendChild(text);
  });

  const dataPolygon = _lagSvgEl("polygon", { points: "", class: "smakshjul-data" });
  svg.appendChild(dataPolygon);

  const dataPunkterGruppe = _lagSvgEl("g", { class: "smakshjul-punkter" });
  svg.appendChild(dataPunkterGruppe);

  container.appendChild(svg);

  return function oppdaterSmakshjul(poeng) {
    const pts = _punkterStreng(kategorier, (kat) => poeng[kat] || 0, (v) => (v / 10) * _SMAKSHJUL_RADIUS);
    dataPolygon.setAttribute("points", pts);

    dataPunkterGruppe.innerHTML = "";
    kategorier.forEach((kat, i) => {
      const verdi = poeng[kat] || 0;
      if (verdi <= 0) return;
      const p = _smakshjulPunkt(i, kategorier.length, (verdi / 10) * _SMAKSHJUL_RADIUS);
      dataPunkterGruppe.appendChild(_lagSvgEl("circle", { cx: p.x, cy: p.y, r: 3, class: "smakshjul-punkt" }));
    });
  };
}
