# Kvernhaug Brygghus — Web changelog

Historisk, runde-for-runde narrativ for web-versjonens utvikling: hvorfor ting endret seg, hva det var før, og hvilken runde som gjorde det. For dagens arkitektur/kontrakt, se [README.md](README.md) — dette dokumentet er kun historikk og trengs sjelden for vanlig arbeid.

Nyeste runde øverst.

## Runde 13A — «Ny oppskrift» og trygg erstatning av aktiv kladd (2026-08-14)

Manuell testing av Runde 13 viste at å åpne en `.kbhrecipe`-fil stille erstattet aktiv kladd uten varsel eller mulighet til å starte blankt. La til en «Ny oppskrift»-knapp (samme bootstrap-standardtilstand som ved førstegangsbesøk) og en delt `oppskriftHarInnhold()`-sjekk (`js/kbhrecipe.js`) som «Ny oppskrift», byggerens «Åpne oppskriftsfil» og Importer-sidens håndoverlevering alle bruker: bekreftelse spørres kun når aktiv kladd har reelt innhold, og aldri før en fil er validert. Brygger/Bryggeri ble bevisst holdt utenfor «har innhold»-sjekken — de er en lett brukerpreferanse (`kvernhaug_web_identitet`) i tillegg til å være del av selve oppskriften, og forhåndsutfylles på nytt rett etter nullstilling.

## Runde 13 — Portabel `.kbhrecipe`-fil (2026-08-14)

Introduserte den versjonerte `.kbhrecipe`-filwrapperen (`js/kbhrecipe.js`) som primær lagrings-/delingsflyt, med rå JSON-eksport nedgradert til et "Avansert"-felt. Før denne runden var rå, uwrappet JSON-eksport eneste fil-alternativ (fortsatt lest/støttet automatisk som legacy-format av `parseKbhRecipeInnhold()` — ingen manuell konvertering kreves for gamle filer).

## Runde 12C/12D — Malt kg/%-kontrakt revidert (2026-08-13)

Malt %-redigering gikk gjennom flere iterasjoner før den landet på dagens multi-rad-lås-kontrakt (se README "Hva den kan"): først en enkel live-kobling (12B), deretter en enkelt-rad-låsing med eksplisitt knapp (12C), til slutt dagens modell der FLERE manuelt redigerte rader kan være låst samtidig og resten fordeles kun mellom urørte rader (12D). Hver iterasjon var en bevisst UX-korreksjon basert på manuell testing, ikke en bugfiks på forrige runde.

## Runde 12 — Oppskriftsskalering + KBH Icon v1 (2026-08-12/13)

- **Skaler oppskrift**: portert fra `ui/recipe_card.py`s "📐 Skaler oppskrift" til Bryggmester. Til forskjell fra desktop (som i tillegg auto-endrer oppskriftsnavnet ved skalering) ble navne-auto-endringen bevisst IKKE portert til web.
- **KBH Icon v1**: nytt kompakt nav-/drawer-ikon (kråke + fullt pilsglass + gammel møllestein, transparent bakgrunn), et brukerlevert og godkjent motiv — IKKE en automatisk beskjæring av Master V1-kunsten slik forgjengeren (`kvernhaug_logo_kompakt.png`, fjernet denne runden) var. Master: `assets/branding/kbh_icon_v1.png` (1024×1536, urørt original), web-derivat 260×390. `.kompaktnav-logo`/`.sidemeny-logo` byttet fra `object-fit: cover` til `contain` fordi det nye motivet er en uklippet komposisjon som `cover` ville kappet i den runde 34-42px-badgen.

## Runde 11B — Nytt KBH Emblem (2026-08-12)

Høyrekortets fulle emblem byttet fra `master_v1_transparent.png` (liggende, 1125:900) til et brukerlevert, transparensrensket emblem: `assets/branding/kbh_emblem_master.png` (1024×1536, felles master for web OG desktop), web-derivat 780×1170. `.identitet-logo` gikk fra bredde- til høydestyrt CSS-sizing (`height: clamp(140px, 27vw, 310px)`) for å bevare samme visuelle fotavtrykk med det nye, stående sideforholdet. Ingen ny illustrasjon — kun rensket alfakanal. Identitetsblokken (fra Runde 10E/11B) fikk samtidig sin nåværende form: valgt Ølstil (ikke stilmatch-resultatet) + emblemet, etterfulgt av alltid synlig Smaksprofil og sammenleggbar Stilanalyse — erstattet den tidligere Smak/Stil-fanenavigasjonen.

## Polish-runde (2026-08-10)

- **To-lags palett revidert** etter visuell kontroll: bekreftet at desktop-appen kjører i Streamlits standard mørke tema (ingen `.streamlit/config.toml`) — kald skifer, ikke det varme brune fra oppskriftskortet. `--bg`/`--bg-sect`/`--bg-sect-2`/`--body`/`--muted` satt kalde som standard; `--warm-*` (fra `modules/card_template.py`/`ui/branding.py`) forbeholdt `.masthead` og `.bygger-hoyre`.
- **Typografi/tekstfarger**: `--muted`/`--warm-muted` lysnet for bedre kontrast. Feltlabels byttet fra `--muted` til `--body`. Seksjonsoverskrifter og gull-"eyebrow"-etiketter økt i størrelse/vekt.
- **Hjelp-TOC utvidet**: `.hjelp-layout` maks-bredde 1100px → 1400px, innholdskolonne 780px → 920px, TOC 200px → 230px — den gamle bredden ga en "halvparten av siden brukt"-følelse på brede skjermer. `hjelp/bryggedag.html` sine stegkort mistet samtidig en gul venstrestrek (det tallmerkede rundmerket ble vurdert visuelt anker nok alene).
- **Sticky høyrekort-fix**: `.bygger-hoyre` sin sticky `top`-offset var en fast `1rem`, mindre enn mastheadens faktiske høyde, så kortet kunne kollidere med headeren ved scroll. `chrome.js` måler nå mastheadens løpende høyde og skriver den til `--masthead-h`, som `.bygger-hoyre` sin `top: calc(var(--masthead-h) + 1rem)` leser.

## Runde 7–11B — IA-redesign (2026-08-12, visuelt godkjent)

Fullbredde IA-redesign: Mine oppskrifter-/Importer-/Utskrift-sider, ny bredere app-lignende Oppskriftsbygger-layout, og — arkitekturmessig viktigst — beregningsorkestreringen (effektivt datasett, OG/FG/ABV/IBU/EBC, smaksprofil, stilmatch) skilt ut fra `app.js` til `recipe_engine.js`. Før dette lå orkestreringen tett koblet til DOM-en inne i `app.js`; siden Utskrift-siden må kunne beregne en VILKÅRLIG valgt oppskrift uten byggerens skjema til stede, ble den skilt ut som rene, DOM-frie funksjoner delt av `app.js` og `utskrift_page.js`. Bryggelærling/Bryggmester ble samtidig gjort til **reelle** modi (førstegangsvalg + drawer-bryter) i stedet for en ren CSS-visningsbryter, med Bryggmesters første malt kg↔%-arbeidsflyt (portert fra `ui/malt_panel.py`) og mål-IBU→gram via portert inverse Tinseth. Se `docs/snapshots/2026-08-12_Web_Desktop_Runde_11B_Checkpoint.md` for full detalj.

## Runde 6 (HEAD `14668af`)

Egen Hjelp & bryggehåndbok (`hjelp/`), brukeridentitet (ølnavn/brygger/valgfritt bryggeri/notater) på selve oppskriften, og fire egne nøytrale A4-utskriftsdokumenter i stedet for et rått sideprint.

## Runde 1–5 — kjernefunksjonalitet

OG/FG/ABV/IBU/EBC, smakshjul, søkbare dropdown-felt, stilmatching mot Kvernhaug Brygghus sitt eget stilbibliotek, lokal lagring, JSON-eksport/import, to visningsmoduser, vennlig stilveiledning, egendefinerte ingredienser, deterministisk generert ingrediensdata.
