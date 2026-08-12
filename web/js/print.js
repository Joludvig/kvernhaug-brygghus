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
      <h1>${escHtml(oppskrift.navn)}</h1>
      <p class="doc-undertittel">${escHtml(undertittel)}</p>
      ${brygger ? `<p class="doc-brygger">${escHtml(brygger)}</p>` : ""}
    </div>`;
}

function _dokFooter() {
  return `<div class="doc-footer">Laget med Kvernhaug Brygghus Oppskriftsbygger</div>`;
}

// ─── A. Oppskriftsark ─────────────────────────────────────────────────────

function byggOppskriftsarkHtml(ctx) {
  const { oppskrift, maltRader, humleRader, effMalt, effHumle, effGjaer, gjaerId, stilAnalyse } = ctx;

  const stilNavn = stilAnalyse ? stilAnalyse.stil : null;
  const visStilNavn = oppskrift.valgtStil || (stilNavn && stilNavn !== "Kreativt Brygg" ? stilNavn : null);
  const stilLinje = visStilNavn
    ? `<p class="doc-stil">Ølstil: <strong>${escHtml(visStilNavn)}</strong></p>`
    : "";

  const maltRows = maltRader.map((m) => {
    const info = effMalt[m.id] || {};
    return `<tr><td>${escHtml(info.navn || "?")}</td><td>${escHtml(info.produsent || "")}</td><td>${m.mengde.toFixed(2)} kg</td></tr>`;
  }).join("");

  const humleRows = [...humleRader].sort((a, b) => b.tid - a.tid).map((h) => {
    const info = effHumle[h.id] || {};
    return `<tr><td>${escHtml(info.navn || "?")}</td><td>${h.gram} g</td><td>${(info.alfa ?? 0).toFixed(1)} %</td><td>${h.tid} min</td></tr>`;
  }).join("");

  const gjaerInfo = gjaerId ? effGjaer[gjaerId] : null;
  const utgjaering = gjaerInfo ? gjaerInfo.attenuation : (parseFloat(oppskrift.attenuationOverride) || 75) / 100;
  const gjaerHtml = gjaerInfo
    ? `<p>${escHtml(gjaerInfo.navn || "Gjær")}${gjaerInfo.produsent ? " · " + escHtml(gjaerInfo.produsent) : ""} — forventet utgjæring ${(utgjaering * 100).toFixed(0)} %</p>`
    : `<p class="hjelpetekst">Ingen gjær valgt.</p>`;

  const notaterHtml = oppskrift.notater
    ? `<h2>Notater</h2><p class="doc-notater">${escHtml(oppskrift.notater)}</p>`
    : "";

  const smakshjulHtml = ctx.smakshjulSvgOuterHtml
    ? `<h2>Smaksprofil</h2><div class="doc-smakshjul">${ctx.smakshjulSvgOuterHtml}</div>`
    : "";

  return `
    <div class="doc-a4">
      ${_dokHeader("Oppskriftsark", oppskrift)}
      <p class="doc-meta">${oppskrift.volum} L · ${oppskrift.effektivitet}% brygghuseffektivitet</p>
      ${stilLinje}
      <div class="doc-stats">
        <div><span>OG</span><strong>${_fmtOg(ctx.og)}</strong></div>
        <div><span>FG</span><strong>${_fmtFg(ctx.fg)}</strong></div>
        <div><span>ABV</span><strong>${_fmtAbv(ctx.abv)}</strong></div>
        <div><span>IBU</span><strong>${_fmtIbu(ctx.ibu)}</strong></div>
        <div><span>EBC</span><strong>${_fmtEbc(ctx.ebc)}</strong></div>
      </div>
      <h2>Malt</h2>
      <table class="doc-table"><thead><tr><th>Navn</th><th>Produsent</th><th>Mengde</th></tr></thead>
        <tbody>${maltRows || '<tr><td colspan="3">Ingen malt lagt til.</td></tr>'}</tbody></table>
      <h2>Humle</h2>
      <table class="doc-table"><thead><tr><th>Navn</th><th>Mengde</th><th>Alfasyre</th><th>Koketid</th></tr></thead>
        <tbody>${humleRows || '<tr><td colspan="4">Ingen humle lagt til.</td></tr>'}</tbody></table>
      <h2>Gjær</h2>
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
    return `<tr><td><input type="checkbox" class="doc-checkbox"></td><td>${escHtml(info.navn || "?")}</td><td>${m.mengde.toFixed(2)} kg</td></tr>`;
  }).join("");

  const humleRows = humleRader.map((h) => {
    const info = effHumle[h.id] || {};
    return `<tr><td><input type="checkbox" class="doc-checkbox"></td><td>${escHtml(info.navn || "?")}</td><td>${h.gram} g</td><td>${(info.alfa ?? 0).toFixed(1)} %</td></tr>`;
  }).join("");

  const gjaerInfo = gjaerId ? effGjaer[gjaerId] : null;
  const gjaerRows = gjaerInfo
    ? `<tr><td><input type="checkbox" class="doc-checkbox"></td><td colspan="2">${escHtml(gjaerInfo.navn || "Gjær")}</td></tr>`
    : "";

  return `
    <div class="doc-a4">
      ${_dokHeader("Handleliste", oppskrift)}
      <h2>Malt</h2>
      <table class="doc-table"><thead><tr><th></th><th>Navn</th><th>Mengde</th></tr></thead>
        <tbody>${maltRows || '<tr><td colspan="3">Ingen malt.</td></tr>'}</tbody></table>
      <h2>Humle</h2>
      <table class="doc-table"><thead><tr><th></th><th>Navn</th><th>Mengde</th><th>Alfasyre</th></tr></thead>
        <tbody>${humleRows || '<tr><td colspan="4">Ingen humle.</td></tr>'}</tbody></table>
      <h2>Gjær</h2>
      <table class="doc-table"><tbody>${gjaerRows || '<tr><td>Ingen gjær valgt.</td></tr>'}</tbody></table>
      ${_dokFooter()}
    </div>`;
}

// ─── C. Bryggedagsark ─────────────────────────────────────────────────────

function byggBryggedagsarkHtml(ctx) {
  const { oppskrift, maltRader, humleRader, effMalt, effHumle } = ctx;

  const maltRows = maltRader.map((m) => {
    const info = effMalt[m.id] || {};
    return `<tr><td>${escHtml(info.navn || "?")}</td><td>${m.mengde.toFixed(2)} kg</td></tr>`;
  }).join("");

  const humleRows = [...humleRader].sort((a, b) => b.tid - a.tid).map((h) => {
    const info = effHumle[h.id] || {};
    return `<tr><td>${escHtml(info.navn || "?")}</td><td>${h.gram} g</td><td>${h.tid} min</td></tr>`;
  }).join("");

  return `
    <div class="doc-a4">
      ${_dokHeader("Bryggedagsark", oppskrift)}
      <p class="doc-meta">Bryggedato: <span class="doc-blank doc-blank-inline"></span>&nbsp;&nbsp;&nbsp; Batch: ${oppskrift.volum} L</p>
      <h2>Ingredienser</h2>
      <table class="doc-table"><thead><tr><th>Malt</th><th>Mengde</th></tr></thead>
        <tbody>${maltRows || '<tr><td colspan="2">Ingen malt.</td></tr>'}</tbody></table>
      <table class="doc-table"><thead><tr><th>Humletilsetning</th><th>Mengde</th><th>Tidspunkt</th></tr></thead>
        <tbody>${humleRows || '<tr><td colspan="3">Ingen humle.</td></tr>'}</tbody></table>
      <h2>Planlagte tall</h2>
      <table class="doc-table doc-maal">
        <tr><td>Planlagt OG</td><td>${_fmtOg(ctx.og)}</td><td>Faktisk OG</td><td class="doc-blank"></td></tr>
        <tr><td>Planlagt volum</td><td>${oppskrift.volum} L</td><td>Faktisk volum</td><td class="doc-blank"></td></tr>
      </table>
      <h2>Sjekkliste</h2>
      <ul class="doc-sjekkliste">
        <li><input type="checkbox"> Klargjør utstyr og ingredienser</li>
        <li><input type="checkbox"> Varm opp meskevann</li>
        <li><input type="checkbox"> Tilsett malt / mesk</li>
        <li><input type="checkbox"> Mashout (hvis relevant)</li>
        <li><input type="checkbox"> Skyll (hvis metoden bruker det)</li>
        <li><input type="checkbox"> Kok</li>
        <li><input type="checkbox"> Humletilsetninger som planlagt over</li>
        <li><input type="checkbox"> Kjøl ned</li>
        <li><input type="checkbox"> Mål OG</li>
        <li><input type="checkbox"> Overfør til gjæringskar og tilsett gjær</li>
      </ul>
      <h2>Notater fra bryggedagen</h2>
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
      ${_dokHeader("Bryggelogg", oppskrift)}
      <table class="doc-table doc-maal">
        <tr><td>Bryggedato</td><td class="doc-blank"></td><td>Batch</td><td class="doc-blank">${oppskrift.volum} L</td></tr>
        <tr><td>Faktisk OG</td><td class="doc-blank"></td><td>Faktisk FG</td><td class="doc-blank"></td></tr>
        <tr><td>Faktisk ABV</td><td class="doc-blank"></td><td>Faktisk volum</td><td class="doc-blank"></td></tr>
        <tr><td>Gjær</td><td class="doc-blank" colspan="3"></td></tr>
        <tr><td>Gjæringstemp.</td><td class="doc-blank"></td><td>Karbonering</td><td class="doc-blank"></td></tr>
      </table>
      <h2>Viktige datoer</h2>
      <table class="doc-table doc-maal">
        <tr><td>Overført til gjæring</td><td class="doc-blank"></td></tr>
        <tr><td>Ferdig gjæret</td><td class="doc-blank"></td></tr>
        <tr><td>Flasket / fatet</td><td class="doc-blank"></td></tr>
        <tr><td>Klar til smaking</td><td class="doc-blank"></td></tr>
      </table>
      <h2>Bryggedagsnotater</h2>
      <div class="doc-notatfelt"></div>
      <h2>Gjæringsnotater</h2>
      <div class="doc-notatfelt"></div>
      <h2>Smaksnotater</h2>
      <div class="doc-notatfelt"></div>
      <h2>Hva fungerte bra?</h2>
      <div class="doc-notatfelt doc-notatfelt-liten"></div>
      <h2>Hva bør endres neste gang?</h2>
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
