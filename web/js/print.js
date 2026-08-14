// Egne utskriftsvennlige dokumentmaler -- IKKE bare et print av byggerskjermen.
// Denne filen er ren presentasjonslogikk: hver bygg-funksjon tar et allerede
// FERDIG BEREGNET "dokumentkontekst"-objekt (se buildDokumentKontekst() under)
// og returnerer en HTML-streng. Den leser ALDRI live DOM-globaler selv --
// det gjør den brukbar fra både Oppskriftsbyggeren (utskrift.html, som henter
// aktiv kladd eller en lagret oppskrift) uten at print.js trenger å vite noe
// om hvor oppskriften kom fra.
//
// Bevisst nøytral handleliste: ingen butikk, pris, URL, lagerstatus eller
// pantry -- kun det oppskriften faktisk består av.
//
// Branding-prinsipp: brukerens ølnavn/brygger/bryggeri er hoveddokumentets
// identitet. Kvernhaug Brygghus vises kun diskret i _dokFooter().

// Bygger dokumentkonteksten fra en oppskrift + resultatet av
// recipe_engine.js sin beregnOppskrift(), pluss en ferdig smakshjul-SVG
// (bygget av kalleren via radar.js, siden print.js selv ikke initialiserer
// noe smakshjul -- den kan gjenbruke ett som allerede finnes på siden).
function byggDokumentKontekst(oppskrift, beregning, smakshjulSvgOuterHtml) {
  return {
    oppskrift,
    og: beregning.og, fg: beregning.fg, abv: beregning.abv, ibu: beregning.ibu, ebc: beregning.ebc,
    maltRader: beregning.maltRader, humleRader: beregning.humleRader,
    effMalt: beregning.effMalt, effHumle: beregning.effHumle, effGjaer: beregning.effGjaer,
    gjaerId: beregning.gjaerId, stilAnalyse: beregning.stilAnalyse,
    smakshjulSvgOuterHtml: smakshjulSvgOuterHtml || null,
  };
}

function _fmtOg(v) { return v.toFixed(3); }
function _fmtFg(v) { return v.toFixed(3); }
function _fmtAbv(v) { return v.toFixed(1).replace(".", ",") + " %"; }
function _fmtIbu(v) { return String(Math.round(v)); }
function _fmtEbc(v) { return String(Math.round(v)); }

function _dokHeader(undertittel, oppskrift) {
  const brygger = [oppskrift.brygger, oppskrift.bryggeri].filter(Boolean).join(" · ");
  return `
    <div class="doc-header">
      <h1>${escHtml(visningsnavn(oppskrift.navn))}</h1>
      <p class="doc-undertittel">${escHtml(undertittel)}</p>
      ${brygger ? `<p class="doc-brygger">${escHtml(brygger)}</p>` : ""}
    </div>`;
}

function _dokFooter() {
  return `<div class="doc-footer">${t("print.footer")}</div>`;
}

// ─── A. Oppskriftsark ─────────────────────────────────────────────────────

function byggOppskriftsarkHtml(ctx) {
  const { oppskrift, maltRader, humleRader, effMalt, effHumle, effGjaer, gjaerId, stilAnalyse } = ctx;

  const stilNavn = stilAnalyse ? stilAnalyse.stil : null;
  const visStilNavn = oppskrift.valgtStil || (stilNavn && stilNavn !== "Kreativt Brygg" ? stilNavn : null);
  const stilLinje = visStilNavn
    ? `<p class="doc-stil">${t("print.olstilLabel")} <strong>${escHtml(stilVisningsnavn(visStilNavn))}</strong></p>`
    : "";

  const maltRows = maltRader.map((m) => {
    const info = effMalt[m.id] || {};
    return `<tr><td>${escHtml(info.navn || "?")}</td><td>${escHtml(info.produsent || "")}</td><td>${formatMaltMass(m.mengde, hentUnitSystem())}</td></tr>`;
  }).join("");

  const humleRows = [...humleRader].sort((a, b) => b.tid - a.tid).map((h) => {
    const info = effHumle[h.id] || {};
    return `<tr><td>${escHtml(info.navn || "?")}</td><td>${formatHopMass(h.gram, hentUnitSystem())}</td><td>${(info.alfa ?? 0).toFixed(1)} %</td><td>${h.tid} min</td></tr>`;
  }).join("");

  const gjaerInfo = gjaerId ? effGjaer[gjaerId] : null;
  const utgjaering = gjaerInfo ? gjaerInfo.attenuation : (parseFloat(oppskrift.attenuationOverride) || 75) / 100;
  const gjaerHtml = gjaerInfo
    ? `<p>${escHtml(gjaerInfo.navn || t("print.gjaerNavnFallback"))}${gjaerInfo.produsent ? " · " + escHtml(gjaerInfo.produsent) : ""}${t("print.utgjaeringSuffix", { pct: (utgjaering * 100).toFixed(0) })}</p>`
    : `<p class="hjelpetekst">${t("print.ingenGjaerValgt")}</p>`;

  const notaterHtml = oppskrift.notater
    ? `<h2>${t("print.notaterTittel")}</h2><p class="doc-notater">${escHtml(oppskrift.notater)}</p>`
    : "";

  const smakshjulHtml = ctx.smakshjulSvgOuterHtml
    ? `<h2>${t("builder.smaksprofil.tittel")}</h2><div class="doc-smakshjul">${ctx.smakshjulSvgOuterHtml}</div>`
    : "";

  return `
    <div class="doc-a4">
      ${_dokHeader(t("print.oppskriftsark.undertittel"), oppskrift)}
      <p class="doc-meta">${t("print.meta", { vol: formatVolume(oppskrift.volum, hentUnitSystem()), eff: oppskrift.effektivitet })}</p>
      ${stilLinje}
      <div class="doc-stats">
        <div><span>OG</span><strong>${_fmtOg(ctx.og)}</strong></div>
        <div><span>FG</span><strong>${_fmtFg(ctx.fg)}</strong></div>
        <div><span>ABV</span><strong>${_fmtAbv(ctx.abv)}</strong></div>
        <div><span>IBU</span><strong>${_fmtIbu(ctx.ibu)}</strong></div>
        <div><span>EBC</span><strong>${_fmtEbc(ctx.ebc)}</strong></div>
      </div>
      <h2>${t("print.maltTittel")}</h2>
      <table class="doc-table"><thead><tr><th>${t("print.navnKol")}</th><th>${t("print.produsentKol")}</th><th>${t("print.mengdeKol")}</th></tr></thead>
        <tbody>${maltRows || `<tr><td colspan="3">${t("print.oppskriftsark.ingenMalt")}</td></tr>`}</tbody></table>
      <h2>${t("print.humleTittel")}</h2>
      <table class="doc-table"><thead><tr><th>${t("print.navnKol")}</th><th>${t("print.mengdeKol")}</th><th>${t("print.alfasyreKol")}</th><th>${t("print.koketidKol")}</th></tr></thead>
        <tbody>${humleRows || `<tr><td colspan="4">${t("print.oppskriftsark.ingenHumle")}</td></tr>`}</tbody></table>
      <h2>${t("print.gjaerTittel")}</h2>
      ${gjaerHtml}
      ${smakshjulHtml}
      ${notaterHtml}
      ${_dokFooter()}
    </div>`;
}

// ─── B. Handleliste ───────────────────────────────────────────────────────
// Bevisst nøytral: kun navn/mengde/alfasyre (for riktig humlepose) --
// ALDRI butikk, pris, URL, lagerstatus eller pantry.

function byggHandlelisteHtml(ctx) {
  const { oppskrift, maltRader, humleRader, effMalt, effHumle, effGjaer, gjaerId } = ctx;

  const maltRows = maltRader.map((m) => {
    const info = effMalt[m.id] || {};
    return `<tr><td><input type="checkbox" class="doc-checkbox"></td><td>${escHtml(info.navn || "?")}</td><td>${formatMaltMass(m.mengde, hentUnitSystem())}</td></tr>`;
  }).join("");

  const humleRows = humleRader.map((h) => {
    const info = effHumle[h.id] || {};
    return `<tr><td><input type="checkbox" class="doc-checkbox"></td><td>${escHtml(info.navn || "?")}</td><td>${formatHopMass(h.gram, hentUnitSystem())}</td><td>${(info.alfa ?? 0).toFixed(1)} %</td></tr>`;
  }).join("");

  const gjaerInfo = gjaerId ? effGjaer[gjaerId] : null;
  const gjaerRows = gjaerInfo
    ? `<tr><td><input type="checkbox" class="doc-checkbox"></td><td colspan="2">${escHtml(gjaerInfo.navn || t("print.gjaerNavnFallback"))}</td></tr>`
    : "";

  return `
    <div class="doc-a4">
      ${_dokHeader(t("print.handleliste.undertittel"), oppskrift)}
      <h2>${t("print.maltTittel")}</h2>
      <table class="doc-table"><thead><tr><th></th><th>${t("print.navnKol")}</th><th>${t("print.mengdeKol")}</th></tr></thead>
        <tbody>${maltRows || `<tr><td colspan="3">${t("print.ingenMalt")}</td></tr>`}</tbody></table>
      <h2>${t("print.humleTittel")}</h2>
      <table class="doc-table"><thead><tr><th></th><th>${t("print.navnKol")}</th><th>${t("print.mengdeKol")}</th><th>${t("print.alfasyreKol")}</th></tr></thead>
        <tbody>${humleRows || `<tr><td colspan="4">${t("print.ingenHumle")}</td></tr>`}</tbody></table>
      <h2>${t("print.gjaerTittel")}</h2>
      <table class="doc-table"><tbody>${gjaerRows || `<tr><td>${t("print.ingenGjaerValgt")}</td></tr>`}</tbody></table>
      ${_dokFooter()}
    </div>`;
}

// ─── C. Bryggedagsark ─────────────────────────────────────────────────────

function byggBryggedagsarkHtml(ctx) {
  const { oppskrift, maltRader, humleRader, effMalt, effHumle } = ctx;

  const maltRows = maltRader.map((m) => {
    const info = effMalt[m.id] || {};
    return `<tr><td>${escHtml(info.navn || "?")}</td><td>${formatMaltMass(m.mengde, hentUnitSystem())}</td></tr>`;
  }).join("");

  const humleRows = [...humleRader].sort((a, b) => b.tid - a.tid).map((h) => {
    const info = effHumle[h.id] || {};
    return `<tr><td>${escHtml(info.navn || "?")}</td><td>${formatHopMass(h.gram, hentUnitSystem())}</td><td>${h.tid} min</td></tr>`;
  }).join("");

  const sjekkliste = Array.from({ length: 10 }, (_, i) => t(`print.sjekkliste.${i}`))
    .map((tekst) => `<li><input type="checkbox"> ${tekst}</li>`)
    .join("");

  return `
    <div class="doc-a4">
      ${_dokHeader(t("print.bryggedagsark.undertittel"), oppskrift)}
      <p class="doc-meta">${t("print.bryggedato")} <span class="doc-blank doc-blank-inline"></span>&nbsp;&nbsp;&nbsp; ${t("print.batch", { vol: formatVolume(oppskrift.volum, hentUnitSystem()) })}</p>
      <h2>${t("print.ingrediensTittel")}</h2>
      <table class="doc-table"><thead><tr><th>${t("print.maltTittel")}</th><th>${t("print.mengdeKol")}</th></tr></thead>
        <tbody>${maltRows || `<tr><td colspan="2">${t("print.ingenMalt")}</td></tr>`}</tbody></table>
      <table class="doc-table"><thead><tr><th>${t("print.humletilsetningKol")}</th><th>${t("print.mengdeKol")}</th><th>${t("print.tidspunktKol")}</th></tr></thead>
        <tbody>${humleRows || `<tr><td colspan="3">${t("print.ingenHumle")}</td></tr>`}</tbody></table>
      <h2>${t("print.planlagteTallTittel")}</h2>
      <table class="doc-table doc-maal">
        <tr><td>${t("print.planlagtOg")}</td><td>${_fmtOg(ctx.og)}</td><td>${t("print.faktiskOg")}</td><td class="doc-blank"></td></tr>
        <tr><td>${t("print.planlagtVolum")}</td><td>${formatVolume(oppskrift.volum, hentUnitSystem())}</td><td>${t("print.faktiskVolum")}</td><td class="doc-blank"></td></tr>
      </table>
      <h2>${t("print.sjekklisteTittel")}</h2>
      <ul class="doc-sjekkliste">
        ${sjekkliste}
      </ul>
      <h2>${t("print.notaterFraBryggedagenTittel")}</h2>
      <div class="doc-notatfelt"></div>
      ${_dokFooter()}
    </div>`;
}

// ─── D. Bryggelogg ────────────────────────────────────────────────────────
// Rent papirskjema -- ingen digital lagring av loggdata denne runden, kun
// et praktisk ark å fylle ut med penn.

function byggBryggeloggHtml(ctx) {
  const { oppskrift } = ctx;
  return `
    <div class="doc-a4">
      ${_dokHeader(t("print.bryggelogg.undertittel"), oppskrift)}
      <table class="doc-table doc-maal">
        <tr><td>${t("print.bryggedato2")}</td><td class="doc-blank"></td><td>${t("print.batchKol")}</td><td class="doc-blank">${formatVolume(oppskrift.volum, hentUnitSystem())}</td></tr>
        <tr><td>${t("print.faktiskOg")}</td><td class="doc-blank"></td><td>${t("print.faktiskFg")}</td><td class="doc-blank"></td></tr>
        <tr><td>${t("print.faktiskAbv")}</td><td class="doc-blank"></td><td>${t("print.faktiskVolum")}</td><td class="doc-blank"></td></tr>
        <tr><td>${t("print.gjaerLabel")}</td><td class="doc-blank" colspan="3"></td></tr>
        <tr><td>${t("print.gjaeringstemp")}</td><td class="doc-blank"></td><td>${t("print.karbonering")}</td><td class="doc-blank"></td></tr>
      </table>
      <h2>${t("print.viktigeDatoerTittel")}</h2>
      <table class="doc-table doc-maal">
        <tr><td>${t("print.overfortTilGjaering")}</td><td class="doc-blank"></td></tr>
        <tr><td>${t("print.ferdigGjaeret")}</td><td class="doc-blank"></td></tr>
        <tr><td>${t("print.flasketFatet")}</td><td class="doc-blank"></td></tr>
        <tr><td>${t("print.klarTilSmaking")}</td><td class="doc-blank"></td></tr>
      </table>
      <h2>${t("print.bryggedagsnotaterTittel")}</h2>
      <div class="doc-notatfelt"></div>
      <h2>${t("print.gjaeringsnotaterTittel")}</h2>
      <div class="doc-notatfelt"></div>
      <h2>${t("print.smaksnotaterTittel")}</h2>
      <div class="doc-notatfelt"></div>
      <h2>${t("print.hvaFungerteBra")}</h2>
      <div class="doc-notatfelt doc-notatfelt-liten"></div>
      <h2>${t("print.hvaBorEndres")}</h2>
      <div class="doc-notatfelt doc-notatfelt-liten"></div>
      ${_dokFooter()}
    </div>`;
}

// ─── Utskrift-trigger (kalt fra utskrift_page.js) ────────────────────────

function _skrivUtDokument(byggFn, ctx, dokumentType) {
  const container = document.getElementById(`utskrift-${dokumentType}`);
  container.innerHTML = byggFn(ctx);
  document.body.dataset.utskrift = dokumentType;
  window.print();
}

function _tilbakestillEtterPrint() {
  delete document.body.dataset.utskrift;
}
