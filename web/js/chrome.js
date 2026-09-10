// Delt "app-krom" for alle sider: hero-banner/kompakt sticky-nav-bytte ved
// scroll, og uttrekkbar venstremeny (drawer). Samme markup/klassenavn på
// alle HTML-sidene -- se .hero/.kompaktnav/.sidemeny i css/style.css.
(function () {
  function initHero() {
    var hero = document.querySelector(".hero");
    var kompaktnav = document.querySelector(".kompaktnav");
    if (!hero || !kompaktnav) return;

    // Chief review (issue #209) -- den ratifiserte A2-03-kontrakten (§3.1,
    // akseptansematrise M15/M16) krever TO trinn i rekkefølge når
    // .kompaktnav blir inert mens den fortsatt inneholder det aktive
    // elementet: (1) native inert-fikseringsregel flytter først fokus til
    // <body> -- det skjer automatisk idet kompaktnav.inert settes til true
    // nedenfor, ingen egen kode trengs for selve trinnet -- og (2) den
    // *neste* Tab-tasten (fremover, ikke Shift+Tab) skal deretter lande på
    // sidens første fokuserbare kontroll (en skip-lenke om siden har en,
    // ellers #meny-knapp-hero), IKKE der nettleseren ellers ville gjenopptatt
    // sekvensiell fokusnavigasjon (empirisk: like etter kompaktnavs gamle
    // DOM-posisjon, et vilkårlig midtsidepunkt). Bare (2) krever egen kode --
    // fanget her som en engangslytter som venter på nøyaktig den neste
    // fremover-Tab-tasten etter at <body> har fått fokus via fikseringen.
    var venterPaaTrygtTabMaal = false;

    function trygtTabMaal() {
      return (
        document.querySelector(".hopp-til-innhold") ||
        document.getElementById("meny-knapp-hero")
      );
    }

    document.addEventListener("keydown", function (e) {
      if (!venterPaaTrygtTabMaal || e.key !== "Tab") return;
      venterPaaTrygtTabMaal = false;
      if (e.shiftKey || document.activeElement !== document.body) return;
      var mal = trygtTabMaal();
      if (mal) {
        e.preventDefault();
        mal.focus();
      }
    });

    // .hero er IKKE sticky -- den ruller bort som vanlig sideinnhold.
    // .kompaktnav er et helt separat, fast element, skjult (transform+
    // opacity) til man har scrollet forbi hero-banneret. Terskelen er
    // hero-banderets egen høyde minus kompaktnav sin høyde, slik at
    // kompaktnav dukker opp akkurat idet hero-banneret forsvinner under
    // toppen av viewporten -- ingen tomrom, ingen overlapp.
    function oppdater() {
      var terskel = hero.offsetHeight - kompaktnav.offsetHeight;
      var synlig = window.scrollY > terskel;
      var blirInert = !synlig && kompaktnav.classList.contains("synlig");
      var holderFokus = blirInert && kompaktnav.contains(document.activeElement);
      kompaktnav.classList.toggle("synlig", synlig);
      kompaktnav.inert = !synlig;
      if (holderFokus) {
        venterPaaTrygtTabMaal = true;
      } else if (synlig) {
        // Chief review (issue #209, round 5) -- .kompaktnav became active/
        // visible again (user scrolled back down) before the armed listener
        // above ever saw its one-shot Tab: the M15 fallback context no
        // longer applies, so disarm it. Left armed, a later Tab from
        // <body> -- reached here by any means, not necessarily the M15
        // fixup -- would incorrectly redirect focus to the now-scrolled-away
        // #meny-knapp-hero instead of following normal sequential order.
        venterPaaTrygtTabMaal = false;
      }
      document.documentElement.style.setProperty(
        "--kompaktnav-h",
        (synlig ? kompaktnav.offsetHeight : 0) + "px"
      );
    }

    window.addEventListener("scroll", oppdater, { passive: true });
    window.addEventListener("resize", oppdater);
    oppdater();

    // B11 -- native fragment-scroll (sidelasting med #hash i URL-en, eller
    // klikk på en #anker-lenke i samme dokument) kan skje før
    // --kompaktnav-h har fått riktig verdi, eller kan selv gjøre kompaktnav
    // synlig ETTER at hoppet allerede er utført (scroll-hendelsen som
    // oppdaterer --kompaktnav-h trigges av scrollen, ikke omvendt) -- da
    // skjer ingen automatisk ny scroll. korrigerAnkerScroll() kjører
    // oppdater() på nytt og gjentar scrollIntoView når målet finnes, og er
    // trygg å kalle flere ganger (samme mål havner samme sted hver gang).
    function korrigerAnkerScroll() {
      var hash = location.hash;
      if (!hash || hash.length < 2) return;
      var mal;
      try {
        mal = document.getElementById(decodeURIComponent(hash.slice(1)));
      } catch (e) {
        mal = null;
      }
      if (!mal) return;
      oppdater();
      mal.scrollIntoView();
      window.requestAnimationFrame(function () {
        oppdater();
        mal.scrollIntoView();
      });
    }

    if (location.hash) {
      korrigerAnkerScroll();
      window.addEventListener("load", korrigerAnkerScroll);
    }
    window.addEventListener("hashchange", korrigerAnkerScroll);
  }

  function initSidemeny() {
    var knapper = document.querySelectorAll(".meny-knapp");
    var meny = document.querySelector(".sidemeny");
    var bakteppe = document.querySelector(".sidemeny-bakteppe");
    var lukkKnapp = document.querySelector(".sidemeny-lukk");
    if (!knapper.length || !meny || !bakteppe) return;

    var sisteApnetFra = null;

    // Drawer starter lukket (ingen "apen"-klasse i markup) -- sett inert i
    // tråd med samme konvensjon: JS-styrt ved DOMContentLoaded, ikke bakt
    // inn i HTML-kilden (se A2-03-kontrakten §3.1).
    meny.inert = true;
    bakteppe.inert = true;

    function apen() {
      return meny.classList.contains("apen");
    }

    function settAriaExpanded(verdi) {
      knapper.forEach(function (k) {
        k.setAttribute("aria-expanded", verdi);
      });
    }

    function apne(fraKnapp) {
      sisteApnetFra = fraKnapp || knapper[0];
      meny.classList.add("apen");
      bakteppe.classList.add("apen");
      meny.inert = false;
      bakteppe.inert = false;
      settAriaExpanded("true");
      document.body.classList.add("sidemeny-aktiv");
      var forsteLenke = meny.querySelector("a, button");
      if (forsteLenke) forsteLenke.focus();
    }

    function lukk() {
      meny.classList.remove("apen");
      bakteppe.classList.remove("apen");
      meny.inert = true;
      bakteppe.inert = true;
      settAriaExpanded("false");
      document.body.classList.remove("sidemeny-aktiv");
      if (sisteApnetFra) sisteApnetFra.focus();
    }

    knapper.forEach(function (knapp) {
      knapp.addEventListener("click", function () {
        if (apen()) lukk();
        else apne(knapp);
      });
    });
    bakteppe.addEventListener("click", lukk);
    if (lukkKnapp) lukkKnapp.addEventListener("click", lukk);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && apen()) lukk();
    });
    // A2-03 half 2 / #186 OPTION A -- Tab/Shift+Tab er ikke tidligere
    // begrenset til den åpne skuffen, så fokus kan lekke ut i bakgrunnen bak
    // det pekerblokkerende bakteppet. Samme alltid-tilkoblede, selv-vaktende
    // mønster som Escape-lytteren over.
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Tab" || !apen()) return;
      var fokuserbare = Array.from(meny.querySelectorAll("a, button"));
      if (!fokuserbare.length) return;
      var forste = fokuserbare[0];
      var siste = fokuserbare[fokuserbare.length - 1];
      var aktivIndeks = fokuserbare.indexOf(document.activeElement);
      if (e.shiftKey) {
        if (aktivIndeks <= 0) {
          e.preventDefault();
          siste.focus();
        }
      } else if (aktivIndeks === -1 || aktivIndeks === fokuserbare.length - 1) {
        e.preventDefault();
        forste.focus();
      }
    });
  }

  // Runde 22 -- måleenhet-toggle (metric/US customary), samme sted i
  // drawer-menyen på alle sider som språkvelgeren, men uten sideoppfrisking
  // (unitSystem lagres og en global hendelse varsler siden om at synlige
  // tall bør rerendres). Ren visnings-toggle -- ingen egen "lukk meny"-
  // logikk her, samme mønster som modus-knapp-bytte.
  function initEnhet() {
    var knapper = document.querySelectorAll(".enhet-knapp");
    if (!knapper.length) return;

    function oppdaterAktiv() {
      var system = hentUnitSystem();
      knapper.forEach(function (k) {
        var aktiv = k.dataset.enhet === system;
        k.classList.toggle("aktiv", aktiv);
        k.setAttribute("aria-pressed", String(aktiv));
      });
    }

    knapper.forEach(function (knapp) {
      knapp.addEventListener("click", function () {
        var nyttSystem = settUnitSystem(knapp.dataset.enhet);
        oppdaterAktiv();
        document.dispatchEvent(new CustomEvent("kvernhaug:enhetendret", { detail: { unitSystem: nyttSystem } }));
      });
    });

    oppdaterAktiv();
  }

  document.addEventListener("DOMContentLoaded", function () {
    initHero();
    initSidemeny();
    initEnhet();
  });
})();
