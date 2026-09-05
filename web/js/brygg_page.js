// Runde 25C -- Bryggeloggen som brukeropplevelse. DOM-laget over
// brew_storage.js, samme oppdeling som pantry_page.js over pantry.js.
//
// GRUNNREGEL FOR HELE SIDEN: UI-et organiseres etter brukerens NESTE
// HANDLING, aldri etter datamodellen. Ordene "snapshot", "actuals" og
// "sensing" finnes ikke noe sted i det brukeren ser -- der står det
// "Fikk du målt OG?", "Står ølet fortsatt til gjæring?" og "Ville du
// brygget dette igjen?".
//
// Aktene er en FORTELLING, ikke en låst prosess. Hvilket kort et brygg
// får, utledes av bryggFase() -- altså av hva som faktisk er fylt ut --
// ikke av en lagret tilstandsmaskin. Ingen felt er påkrevd, alt kan
// fylles ut senere og i vilkårlig rekkefølge, og et brygg kan forkastes
// når som helst uten å slutte å være gyldig historikk.
//
// Hver handling skal gi noe TILBAKE, ikke bare kvittere med "Lagret".
// Derfor regnes faktisk effektivitet/ABV/utgjæring ut og vises umiddelbart
// (se faktiskEffektivitet()/faktiskUtgjaering() i brew_storage.js, som
// utleder alt fra det frosne snapshotet).

const SMAKS_SKALA_MAKS = 10;

function _fmtSg(v) {
  return isFinite(v) ? v.toFixed(3) : "–";
}

function _fmtProsent(v, desimaler = 0) {
  return isFinite(v) ? `${v.toFixed(desimaler).replace(".", ",")} %` : "–";
}

function _fmtVol(liter) {
  return isFinite(liter) ? formatVolume(liter, hentUnitSystem()) : "–";
}

function _planTekst(brew) {
  const p = brew.snapshot.predicted || {};
  return t("brygg.planLinje", {
    og: _fmtSg(p.og),
    fg: _fmtSg(p.fg),
    abv: isFinite(p.abv) ? p.abv.toFixed(1).replace(".", ",") : "–",
    volum: _fmtVol(parseFloat(brew.snapshot.recipe.volum)),
  });
}

// ─── Umiddelbar verdi tilbake (rundens viktigste UX-krav) ────────────────

function _tilbakemeldingBryggedag(brew) {
  const deler = [];
  const p = brew.snapshot.predicted || {};
  const a = brew.actuals || {};
  if (isFinite(a.og) && isFinite(p.og)) {
    const nokkel = a.og >= p.og ? "brygg.tilbakeOgOver" : "brygg.tilbakeOgUnder";
    deler.push(t(nokkel, { faktisk: _fmtSg(a.og), plan: _fmtSg(p.og) }));
  }
  const eff = faktiskEffektivitet(brew);
  const planEff = parseFloat(brew.snapshot.recipe.effektivitet);
  if (isFinite(eff) && isFinite(planEff)) {
    deler.push(t("brygg.tilbakeEffektivitet", { faktisk: _fmtProsent(eff), plan: _fmtProsent(planEff) }));
  }
  return deler.join(" ");
}

function _tilbakemeldingGjaering(brew) {
  const deler = [];
  const p = brew.snapshot.predicted || {};
  const abv = faktiskAbv(brew);
  if (isFinite(abv)) {
    deler.push(t("brygg.tilbakeAbv", {
      faktisk: abv.toFixed(1).replace(".", ","),
      plan: isFinite(p.abv) ? p.abv.toFixed(1).replace(".", ",") : "–",
    }));
  }
  const utg = faktiskUtgjaering(brew);
  if (isFinite(utg)) deler.push(t("brygg.tilbakeUtgjaering", { utgjaering: _fmtProsent(utg) }));
  const a = brew.actuals || {};
  if (isFinite(a.fg) && isFinite(p.fg)) {
    if (a.fg > p.fg + 0.004) deler.push(t("brygg.tilbakeFgHoyere"));
    else if (a.fg < p.fg - 0.004) deler.push(t("brygg.tilbakeFgLavere"));
  }
  return deler.join(" ");
}

// ─── Smakshjul: aldri 18 påkrevde felt ───────────────────────────────────
// "Ikke vurdert" og "vurdert likt som planlagt" er to forskjellige ting.
// Sier brukeren "ble som forventet", lagres den predikerte profilen som
// FAKTISK profil -- det er nøyaktig hva brukeren påstår -- og da finnes
// sensing.flavorProfile. Har brukeren ikke sagt noe, finnes den ikke.
// Ingen ny datamodell trengs for skillet.

function _byggSmakSliders(container, brew) {
  container.innerHTML = "";
  const predikert = (brew.snapshot.predicted && brew.snapshot.predicted.flavorProfile) || {};
  const faktisk = (brew.sensing && brew.sensing.flavorProfile) || {};
  for (const kategori of Object.keys(predikert)) {
    const rad = document.createElement("div");
    rad.className = "brygg-smak-rad";
    const label = document.createElement("label");
    label.textContent = t("brygg.smakKategori", {
      kategori,
      forventet: (predikert[kategori] || 0).toFixed(1).replace(".", ","),
    });
    const input = document.createElement("input");
    input.type = "range";
    input.min = "0";
    input.max = String(SMAKS_SKALA_MAKS);
    input.step = "0.5";
    input.className = "brygg-smak-slider";
    input.dataset.kategori = kategori;
    input.value = String(faktisk[kategori] !== undefined ? faktisk[kategori] : predikert[kategori] || 0);
    rad.appendChild(label);
    rad.appendChild(input);
    container.appendChild(rad);
  }
}

function _lesSmakSliders(container) {
  const ut = {};
  for (const el of container.querySelectorAll(".brygg-smak-slider")) {
    const n = parseFloat(el.value);
    if (isFinite(n)) ut[el.dataset.kategori] = n;
  }
  return ut;
}

// ─── Kortrendering ────────────────────────────────────────────────────────

function _visTilbakemelding(kort, tekst) {
  const el = kort.querySelector(".brygg-tilbakemelding");
  if (!tekst) {
    el.hidden = true;
    return;
  }
  el.textContent = tekst;
  el.hidden = false;
}

function _byggKort(brew) {
  const fase = bryggFase(brew);
  const kort = document.getElementById("brygg-kort-mal").content.firstElementChild.cloneNode(true);
  kort.dataset.brewId = brew.brewId;

  kort.querySelector(".brygg-kort-navn").textContent =
    visningsnavn(brew.snapshot.recipe.navn) || t("identitet.utenNavn");
  kort.querySelector(".brygg-kort-plan").textContent = _planTekst(brew);
  const faseEl = kort.querySelector(".brygg-fase");
  faseEl.textContent = t(`brygg.fase.${fase}`);
  faseEl.classList.add(`brygg-fase-${fase}`);

  const sporsmal = kort.querySelector(".brygg-sporsmal");
  const primar = kort.querySelector(".brygg-primar");
  const forkastKnapp = kort.querySelector(".brygg-forkast");
  forkastKnapp.textContent = t("brygg.forkastKnapp");
  kort.querySelector(".brygg-slett").title = t("brygg.slettTitle");
  kort.querySelector(".brygg-slett").setAttribute("aria-label", t("brygg.slettTitle"));

  if (fase === "bryggedag") {
    // AKT 2 -- ilden. Maksimalt to tall. Ingen analyser, ingen grafer,
    // ingen valg. Brukeren står ved meskekaret med våte hender.
    sporsmal.textContent = t("brygg.sporsmalBryggedag");
    const rad = kort.querySelector(".brygg-felt-bryggedag");
    rad.hidden = false;
    kort.querySelector(".brygg-og-label").textContent = t("brygg.ogLabel");
    kort.querySelector(".brygg-volum-label").textContent = t("brygg.volumLabel", {
      enhet: hentUnitSystem() === "us" ? "US gal" : "L",
    });
    const volumFelt = kort.querySelector(".brygg-volum");
    volumFelt.placeholder = formatVolumeNumber(parseFloat(brew.snapshot.recipe.volum) || 0, hentUnitSystem());
    primar.textContent = t("brygg.settTilGjaering");
    primar.addEventListener("click", () => {
      const og = parseFloat(kort.querySelector(".brygg-og").value);
      const volumInn = kort.querySelector(".brygg-volum").value;
      const endringer = { actuals: {} };
      if (isFinite(og)) endringer.actuals.og = og;
      if (String(volumInn).trim() !== "") {
        const liter = parseVolume(volumInn, hentUnitSystem());
        if (isFinite(liter)) endringer.actuals.volumeL = liter;
      }
      if (!isFinite(og)) return _visTilbakemelding(kort, t("brygg.trengerOg"));
      endringer.brewedAt = new Date().toISOString();
      const res = oppdaterBrygg(brew.brewId, endringer);
      if (!res.ok) return _visTilbakemelding(kort, res.melding);
      visLogg(_tilbakemeldingBryggedag(res.brew), brew.brewId);
    });
  } else if (fase === "gjaering") {
    // AKT 3 -- tiden.
    sporsmal.textContent = t("brygg.sporsmalGjaering");
    kort.querySelector(".brygg-felt-gjaering").hidden = false;
    kort.querySelector(".brygg-fg-label").textContent = t("brygg.fgLabel");
    primar.textContent = t("brygg.lagreFg");
    primar.addEventListener("click", () => {
      const fg = parseFloat(kort.querySelector(".brygg-fg").value);
      if (!isFinite(fg)) return _visTilbakemelding(kort, t("brygg.trengerFg"));
      const res = oppdaterBrygg(brew.brewId, { actuals: { fg } });
      if (!res.ok) return _visTilbakemelding(kort, res.melding);
      visLogg(_tilbakemeldingGjaering(res.brew), brew.brewId);
    });
    _visTilbakemelding(kort, _tilbakemeldingBryggedag(brew));
  } else if (fase === "smaking" || fase === "ferdig") {
    // AKT 4 -- dommen. Starter med ETT spørsmål, ikke et skjema.
    sporsmal.textContent = t("brygg.sporsmalSmaking");
    const domBlokk = kort.querySelector(".brygg-felt-smaking");
    domBlokk.hidden = false;
    for (const knapp of kort.querySelectorAll(".brygg-dom-knapp")) {
      knapp.textContent = t(`brygg.dom.${knapp.dataset.dom}`);
      const valgt = brew.sensing && brew.sensing.judgment === knapp.dataset.dom;
      knapp.setAttribute("aria-pressed", String(!!valgt));
      knapp.addEventListener("click", () => {
        const res = oppdaterBrygg(brew.brewId, { sensing: { judgment: knapp.dataset.dom } });
        if (!res.ok) return _visTilbakemelding(kort, res.melding);
        visLogg(t("brygg.tilbakeDom"), brew.brewId);
      });
    }

    kort.querySelector(".brygg-smak-sporsmal").textContent = t("brygg.smakSporsmal");
    const somForventet = kort.querySelector(".brygg-smak-som-forventet");
    const harVurdertSmak = !!(brew.sensing && brew.sensing.flavorProfile);
    somForventet.textContent = harVurdertSmak ? t("brygg.smakVurdert") : t("brygg.smakSomForventet");
    somForventet.disabled = harVurdertSmak;
    somForventet.addEventListener("click", () => {
      const predikert = (brew.snapshot.predicted && brew.snapshot.predicted.flavorProfile) || {};
      const res = oppdaterBrygg(brew.brewId, { sensing: { flavorProfile: { ...predikert } } });
      if (!res.ok) return _visTilbakemelding(kort, res.melding);
      visLogg(t("brygg.tilbakeSmakLagret"), brew.brewId);
    });

    const detaljer = kort.querySelector(".brygg-smak-detaljer");
    kort.querySelector(".brygg-smak-summary").textContent = t("brygg.smakJusterSummary");
    _byggSmakSliders(kort.querySelector(".brygg-smak-sliders"), brew);
    detaljer.addEventListener("toggle", () => {
      if (!detaljer.open) return;
      // Lagres først når brukeren trykker "Lagre notat" -- ingen skjult
      // autolagring av 18 verdier brukeren kanskje bare kikket på.
      kort.querySelector(".brygg-lagre-notat").hidden = false;
    });

    // "Neste gang" er førsteklasses informasjon, ikke et notatfelt nederst.
    const laering = kort.querySelector(".brygg-laering");
    laering.hidden = false;
    kort.querySelector(".brygg-nesteganglabel").textContent = t("brygg.nesteGangLabel");
    const nesteGangFelt = kort.querySelector(".brygg-nestegang");
    nesteGangFelt.placeholder = t("brygg.nesteGangPlaceholder");
    nesteGangFelt.value = (brew.learning && brew.learning.nextTime) || "";
    kort.querySelector(".brygg-laering-summary").textContent = t("brygg.laeringMerSummary");
    kort.querySelector(".brygg-fungerte-label").textContent = t("brygg.fungerteLabel");
    kort.querySelector(".brygg-fungerte").value = (brew.learning && brew.learning.whatWorked) || "";
    kort.querySelector(".brygg-endret-label").textContent = t("brygg.endretLabel");
    kort.querySelector(".brygg-endret").value = (brew.learning && brew.learning.whatChanged) || "";

    const lagreNotat = kort.querySelector(".brygg-lagre-notat");
    lagreNotat.textContent = t("brygg.lagreNotat");
    lagreNotat.hidden = false;
    lagreNotat.addEventListener("click", () => {
      const endringer = {
        learning: {
          nextTime: nesteGangFelt.value,
          whatWorked: kort.querySelector(".brygg-fungerte").value,
          whatChanged: kort.querySelector(".brygg-endret").value,
        },
      };
      if (detaljer.open) endringer.sensing = { flavorProfile: _lesSmakSliders(kort.querySelector(".brygg-smak-sliders")) };
      const res = oppdaterBrygg(brew.brewId, endringer);
      if (!res.ok) return _visTilbakemelding(kort, res.melding);
      visLogg(t("brygg.tilbakeNotatLagret"), brew.brewId);
    });

    primar.textContent = t("brygg.avsluttKnapp");
    primar.addEventListener("click", () => {
      const res = oppdaterBrygg(brew.brewId, {
        status: "done",
        learning: {
          nextTime: nesteGangFelt.value,
          whatWorked: kort.querySelector(".brygg-fungerte").value,
          whatChanged: kort.querySelector(".brygg-endret").value,
        },
      });
      if (!res.ok) return _visTilbakemelding(kort, res.melding);
      visLogg(t("brygg.tilbakeAvsluttet"), null);
    });

    _visTilbakemelding(kort, _tilbakemeldingGjaering(brew));
  } else if (fase === "forkastet") {
    sporsmal.textContent = t("brygg.sporsmalForkastet");
    const laering = kort.querySelector(".brygg-laering");
    laering.hidden = false;
    kort.querySelector(".brygg-nesteganglabel").textContent = t("brygg.nesteGangLabel");
    const nesteGangFelt = kort.querySelector(".brygg-nestegang");
    nesteGangFelt.placeholder = t("brygg.nesteGangForkastetPlaceholder");
    nesteGangFelt.value = (brew.learning && brew.learning.nextTime) || "";
    kort.querySelector(".brygg-laering-mer").hidden = true;
    const lagreNotat = kort.querySelector(".brygg-lagre-notat");
    lagreNotat.textContent = t("brygg.lagreNotat");
    lagreNotat.hidden = false;
    lagreNotat.addEventListener("click", () => {
      const res = oppdaterBrygg(brew.brewId, { learning: { nextTime: nesteGangFelt.value } });
      if (!res.ok) return _visTilbakemelding(kort, res.melding);
      visLogg(t("brygg.tilbakeNotatLagret"), brew.brewId);
    });
    primar.textContent = t("brygg.gjenopptaKnapp");
    primar.addEventListener("click", () => {
      const res = oppdaterBrygg(brew.brewId, { status: "active" });
      if (!res.ok) return _visTilbakemelding(kort, res.melding);
      visLogg(null, brew.brewId);
    });
    forkastKnapp.hidden = true;
  }

  forkastKnapp.addEventListener("click", () => {
    if (!confirm(t("brygg.forkastConfirm"))) return;
    const res = oppdaterBrygg(brew.brewId, { status: "discarded" });
    if (!res.ok) return _visTilbakemelding(kort, res.melding);
    visLogg(t("brygg.tilbakeForkastet"), brew.brewId);
  });
  kort.querySelector(".brygg-slett").addEventListener("click", () => {
    if (!confirm(t("brygg.slettConfirm"))) return;
    if (!slettBrygg(brew.brewId)) return _visTilbakemelding(kort, t("brygg.feilLagring"));
    visLogg(null, null);
  });

  return kort;
}

function _byggFerdigRad(brew) {
  const li = document.getElementById("brygg-ferdig-mal").content.firstElementChild.cloneNode(true);
  li.querySelector(".utstyr-rad-navn").textContent =
    visningsnavn(brew.snapshot.recipe.navn) || t("identitet.utenNavn");
  const abv = faktiskAbv(brew);
  li.querySelector(".utstyr-rad-detalj").textContent = t("brygg.ferdigDetalj", {
    og: _fmtSg(brew.actuals.og),
    fg: _fmtSg(brew.actuals.fg),
    abv: isFinite(abv) ? abv.toFixed(1).replace(".", ",") : "–",
  });
  const nesteGangEl = li.querySelector(".brygg-ferdig-nestegang");
  if (brew.learning && brew.learning.nextTime) {
    nesteGangEl.textContent = t("brygg.ferdigNesteGang", { tekst: brew.learning.nextTime });
  } else {
    nesteGangEl.hidden = true;
  }
  const merke = li.querySelector(".brygg-dom-merke");
  if (brew.sensing && brew.sensing.judgment) {
    merke.textContent = t(`brygg.dom.${brew.sensing.judgment}`);
    merke.classList.add(`brygg-dom-${brew.sensing.judgment}`);
  } else {
    merke.hidden = true;
  }
  const gjenapne = li.querySelector(".brygg-gjenapne");
  gjenapne.textContent = t("brygg.gjenapneKnapp");
  gjenapne.addEventListener("click", () => {
    const res = oppdaterBrygg(brew.brewId, { status: "active" });
    if (!res.ok) return _visBryggVarsel(res.melding);
    visLogg(null, brew.brewId);
  });
  const slett = li.querySelector(".brygg-slett");
  slett.textContent = t("utstyr.slett");
  slett.addEventListener("click", () => {
    if (!confirm(t("brygg.slettConfirm"))) return;
    if (!slettBrygg(brew.brewId)) return _visBryggVarsel(t("brygg.feilLagring"));
    visLogg(null, null);
  });
  return li;
}

// ─── Hovedvisning ─────────────────────────────────────────────────────────

// Issue #74 -- vedvarende varsel når lesBrewState() ikke klarte å tolke
// den lagrede rådataen (i stedet for å late som bryggeloggen bare er tom),
// og et engangsvarsel for et mislykket skriveforsøk fra den "ferdige"
// listens handlinger (som ikke har et per-kort .brygg-tilbakemelding-
// element, se #brygg-ferdig-mal). Elementet finnes ikke i HTML-kildene
// (unngår enhver web/en/-generatorsynk) -- opprettes lat ved første behov,
// samme "hjelpetekst utstyr-advarsel"-stil som utstyr-batch-advarsel
// (app.js/index.html) allerede bruker for tilsvarende ikke-blokkerende
// varsler.
function _bryggVarselEl() {
  let el = document.getElementById("brygg-varsel");
  if (el) return el;
  el = document.createElement("p");
  el.id = "brygg-varsel";
  el.className = "hjelpetekst utstyr-advarsel";
  el.setAttribute("aria-live", "polite");
  el.hidden = true;
  document.getElementById("brygg-tom-melding").insertAdjacentElement("afterend", el);
  return el;
}

function _visBryggVarsel(tekst) {
  const el = _bryggVarselEl();
  el.textContent = tekst;
  el.hidden = false;
}

function visLogg(tilbakemelding, fremhevBrewId) {
  if (bryggStateErKorrupt()) {
    _visBryggVarsel(t("brygg.feilKorrupt"));
  } else {
    const varselEl = document.getElementById("brygg-varsel");
    if (varselEl) varselEl.hidden = true;
  }

  const alle = alleBrygg();
  // Nyeste først -- det brukeren jobber med nå står øverst.
  alle.sort((a, b) => String(b.createdAt || "").localeCompare(String(a.createdAt || "")));

  const ferdige = alle.filter((b) => bryggFase(b) === "ferdig" && b.status === "done");
  const aktive = alle.filter((b) => !ferdige.includes(b));

  document.getElementById("brygg-tom-melding").hidden = alle.length !== 0;
  document.getElementById("brygg-aktive-blokk").hidden = aktive.length === 0;
  document.getElementById("brygg-ferdige-blokk").hidden = ferdige.length === 0;

  const aktivListe = document.getElementById("brygg-aktive-liste");
  aktivListe.innerHTML = "";
  for (const brew of aktive) aktivListe.appendChild(_byggKort(brew));

  const ferdigListe = document.getElementById("brygg-ferdige-liste");
  ferdigListe.innerHTML = "";
  for (const brew of ferdige) ferdigListe.appendChild(_byggFerdigRad(brew));

  if (tilbakemelding && fremhevBrewId) {
    const kort = aktivListe.querySelector(`[data-brew-id="${fremhevBrewId}"]`);
    if (kort) _visTilbakemelding(kort, tilbakemelding);
  }
}

function init() {
  visLogg(null, null);
}

document.addEventListener("kvernhaug:enhetendret", () => visLogg(null, null));
window.addEventListener("kvernhaug:sprakendret", () => visLogg(null, null));

init();
