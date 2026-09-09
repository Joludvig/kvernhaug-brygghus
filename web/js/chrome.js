// Delt "app-krom" for alle sider: hero-banner/kompakt sticky-nav-bytte ved
// scroll, og uttrekkbar venstremeny (drawer). Samme markup/klassenavn på
// alle HTML-sidene -- se .hero/.kompaktnav/.sidemeny i css/style.css.
(function () {
  function initHero() {
    var hero = document.querySelector(".hero");
    var kompaktnav = document.querySelector(".kompaktnav");
    if (!hero || !kompaktnav) return;

    // .hero er IKKE sticky -- den ruller bort som vanlig sideinnhold.
    // .kompaktnav er et helt separat, fast element, skjult (transform+
    // opacity) til man har scrollet forbi hero-banneret. Terskelen er
    // hero-banderets egen høyde minus kompaktnav sin høyde, slik at
    // kompaktnav dukker opp akkurat idet hero-banneret forsvinner under
    // toppen av viewporten -- ingen tomrom, ingen overlapp.
    function oppdater() {
      var terskel = hero.offsetHeight - kompaktnav.offsetHeight;
      var synlig = window.scrollY > terskel;
      kompaktnav.classList.toggle("synlig", synlig);
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
      settAriaExpanded("true");
      document.body.classList.add("sidemeny-aktiv");
      var forsteLenke = meny.querySelector("a, button");
      if (forsteLenke) forsteLenke.focus();
    }

    function lukk() {
      meny.classList.remove("apen");
      bakteppe.classList.remove("apen");
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
