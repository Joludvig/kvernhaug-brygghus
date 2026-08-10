// Egne utskriftsvennlige dokumentmaler -- IKKE bare et print av byggerskjermen.
// Hvert ark (oppskriftsark/handleliste/bryggedagsark/bryggelogg) bygges fra
// live oppskriftsdata rett før utskrift og injiseres i sin egen skjulte
// .utskrift-dokument-container. body[data-utskrift="..."] + @media print i
// style.css sørger for at KUN valgt ark vises på papiret -- resten av siden
// (header/main/footer) skjules automatisk for den utskriften.
//
// Bevisst nøytral handleliste: ingen butikk, pris, URL, lagerstatus eller
// pantry -- kun det oppskriften faktisk består av.
//
// Branding-prinsipp: brukerens ølnavn/brygger/bryggeri er hoveddokumentets
// identitet. Kvernhaug Brygghus vises kun diskret i _dokFooter().

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

function _hentLiveDokumentdata() {
  const maltRader = lesMaltRader();
  const humleRader = lesHumleRader();
  const { effMalt, effHumle, effGjaer, gjaerId } = _effektiveDatasett(maltRader, humleRader);
  const oppskrift = samleOppskrift();
  return { maltRader, humleRader, effMalt, effHumle, effGjaer, gjaerId, oppskrift };
}

// ─── A. Oppskriftsark ─────────────────────────────────────────────────────

function byggOppskriftsarkHtml() {
  const { maltRader, humleRader, effMalt, effHumle, effGjaer, gjaerId, oppskrift } = _hentLiveDokumentdata();

  const stilNavn = sisteStilAnalyse ? sisteStilAnalyse.stil : null;
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
  const gjaerHtml = gjaerInfo
    ? `<p>${escHtml(gjaerInfo.navn || "Gjær")}${gjaerInfo.produsent ? " · " + escHtml(gjaerInfo.produsent) : ""} — forventet utgjæring ${(hentUtgjaering() * 100).toFixed(0)} %</p>`
    : `<p class="hjelpetekst">Ingen gjær valgt.</p>`;

  const notaterHtml = oppskrift.notater
    ? `<h2>Notater</h2><p class="doc-notater">${escHtml(oppskrift.notater)}</p>`
    : "";

  const svg = document.querySelector("#smakshjul-container svg");
  const smakshjulHtml = svg ? `<h2>Smaksprofil</h2><div class="doc-smakshjul">${svg.outerHTML}</div>` : "";

  return `
    <div class="doc-a4">
      ${_dokHeader("Oppskriftsark", oppskrift)}
      <p class="doc-meta">${oppskrift.volum} L · ${oppskrift.effektivitet}% brygghuseffektivitet</p>
      ${stilLinje}
      <div class="doc-stats">
        <div><span>OG</span><strong>${document.getElementById("res-og").textContent}</strong></div>
        <div><span>FG</span><strong>${document.getElementById("res-fg").textContent}</strong></div>
        <div><span>ABV</span><strong>${document.getElementById("res-abv").textContent}</strong></div>
        <div><span>IBU</span><strong>${document.getElementById("res-ibu").textContent}</strong></div>
        <div><span>EBC</span><strong>${document.getElementById("res-ebc").textContent}</strong></div>
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

function byggHandlelisteHtml() {
  const { maltRader, humleRader, effMalt, effHumle, effGjaer, gjaerId, oppskrift } = _hentLiveDokumentdata();

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

function byggBryggedagsarkHtml() {
  const { maltRader, humleRader, effMalt, effHumle, oppskrift } = _hentLiveDokumentdata();

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
        <tr><td>Planlagt OG</td><td>${document.getElementById("res-og").textContent}</td><td>Faktisk OG</td><td class="doc-blank"></td></tr>
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
// et praktisk ark å fylle ut med penn (se product-runden sitt eksplisitte
// "ikke gjør det til et skjema med 100 felter").

function byggBryggeloggHtml() {
  const { oppskrift } = _hentLiveDokumentdata();
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

// ─── Utskrift-trigger ─────────────────────────────────────────────────────

function _skrivUtDokument(byggFn, dokumentType) {
  const container = document.getElementById(`utskrift-${dokumentType}`);
  container.innerHTML = byggFn();
  document.body.dataset.utskrift = dokumentType;
  window.print();
}

function _tilbakestillEtterPrint() {
  delete document.body.dataset.utskrift;
}

function initUtskrift() {
  document.getElementById("print-oppskriftsark-knapp").addEventListener("click", () => _skrivUtDokument(byggOppskriftsarkHtml, "oppskriftsark"));
  document.getElementById("print-handleliste-knapp").addEventListener("click", () => _skrivUtDokument(byggHandlelisteHtml, "handleliste"));
  document.getElementById("print-bryggedagsark-knapp").addEventListener("click", () => _skrivUtDokument(byggBryggedagsarkHtml, "bryggedagsark"));
  document.getElementById("print-bryggelogg-knapp").addEventListener("click", () => _skrivUtDokument(byggBryggeloggHtml, "bryggelogg"));
  window.addEventListener("afterprint", _tilbakestillEtterPrint);
}
