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

  document.addEventListener("DOMContentLoaded", function () {
    initHero();
    initSidemeny();
  });
})();
