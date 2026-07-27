# Kvernhaug Brygghus - Prosjektstatus (Juni 2026)

## Prosjektmål

Kvernhaug Brygghus er et personlig hobbyprosjekt laget for å hjelpe Jan-Ove med:

* utvikling av egne øloppskrifter
* oppskriftsanalyse
* bryggeplanlegging
* handlelister
* bryggedagsstøtte
* læring og dokumentasjon av egne brygg

Prosjektet er ikke ment å konkurrere med Brewfather.

Fokus er:

* enkelhet
* praktisk nytte
* hjemmebrygging
* én bruker

Eventuell deling med andre er en mulig fremtidig bonus, ikke et nåværende mål.

---

## Teknologi

* Python
* Streamlit
* JSON-baserte databaser
* VS Code
* Git

---

## Databaser

### Humle

`master_humle_v2.json`

Status:

* 60 humlesorter
* låst som sannhetskilde
* separate Eclipse 2021 og Eclipse 2024 entries
* butikkkoblinger mot Vestbrygg og Ølbrygging

### Gjær

`master_gjaer_v2.json`

Status:

* aktiv sannhetskilde
* butikkkoblinger
* v2-format

### Malt

`master_malt.json`

Viktig:

Filnavnet er legacy.

Strukturen tilsvarer v2-format.

Ikke rename filen nå.

Dokumentert som:

> master_malt.json = v2-format med gammelt filnavn

---

## Viktig beslutning - Malt

Det ble vurdert å innføre:

`pakke_gram: 1000`

for malt.

Beslutning:

IKKE gjør dette.

Begrunnelse:

Humle har én typisk pakningsstørrelse.

Malt finnes som:

* knust
* hel

og i flere pakningsstørrelser per butikk.

Malt trenger på sikt en variantmodell.

Ingen schema-endring gjøres nå.

Variantmodell utsettes til V1.5 (butikksammenligning).

---

## Butikkstrategi

Masterdatabaser er sannhetskilde.

Butikkdata brukes kun til:

* pris
* URL
* tilgjengelighet

Målet er:

```text
Master DB
+
Butikkdata
==========

Handleliste / Prisberegning
```

Ikke motsatt.

---

## Vestbrygg

Malt leveres i eksakte mengder.

Eksempel:

Bestiller bruker 4.58 kg malt,
leveres 4.58 kg malt.

Dette reduserer verdien av malt-inventory betydelig.

---

## Nåværende funksjoner

Fungerer:

* Oppskriftsbygger
* Stilmatching
* Sensorisk analyse
* Humleanalyse
* Gjæranalyse
* Handleliste
* Oppskriftslagring
* Brewday Plan
* Utskriftsvennlig Brewday Sheet

---

## Brewday Sheet

Status:

Ferdig.

To-kolonne-layout.

Mål:

* én A4-side
* svart/hvitt utskrift
* clipboard ved BrewZilla

Layout:

Venstre:

* Vann
* Mesking
* Kok

Høyre:

* Humle
* Gjær
* Fermentering

Bunn:

* Målinger
* Notater

Sommerglød-test bekreftet at løsningen fungerer.

---

## Første validering

Sommerglød V1

Resultat:

* 25 liter til gjæring
* OG 1.050
* volum traff mål
* Brewday Plan traff mål

Dette er første reelle validering av dagens BrewZilla-standardverdier.

Equipment Profile er fortsatt ønskelig, men ikke fordi dagens beregninger er dokumentert feil.

---

## Oppdatert Roadmap

V1.2
Bryggelogg

V1.3
Equipment Profile

V1.4
Inventory (humle/gjær)

V1.5
Butikksammenligning

---

## Bryggelogg - Viktig prinsipp

Bryggeloggen må være ekstremt enkel.

Mål:

Brukes på ekte bryggedager.

Ikke administrasjon.

Minimum:

* dato
* faktisk OG

Valgfritt:

* FG
* karakter
* smaksnotater
* lagringsnotater
* "neste gang"

Lav terskel er viktigere enn mange felt.

---

## Designprinsipper

Når nye features vurderes:

Spør først:

> "Løser dette et faktisk problem som oppstår under bruk?"

Ikke:

> "Ville dette vært kult å ha?"

Prosjektet skal først og fremst hjelpe Jan-Ove med å lage bedre øl og ha det gøy med hobbyen.
