# Kvernhaug Brygghus

En webapp for hjemmebryggere. Du legger inn malt, humle og gjær — appen regner ut OG, IBU, EBC og ABV live, matcher oppskriften mot BJCP-stiler, og lager en komplett bryggedagsplan med vannberegninger, meskeplan og gjæranbefalinger. Alt lagres lokalt og kjøres i nettleseren via Streamlit, uten ekstern server eller database.

---

## Hva er bygget

**Oppskriftsbygger**
Malttabell med andeler (redistribuerer proporsjonalt ved endring), humleplan med Tinseth IBU-beregning, gjærvelger med utgjæringsgrad og fermenteringstemperatur. Batch-volum og oppskriftsnavn er redigerbare.

**Analyse og stil**
22 BJCP-stiler med scoring. Sensorisk smakshjul basert på malt- og humlekategorier. Balanseanalyse og feilmeldinger (underhopping, overhopping, etc.).

**Lagring og import**
Oppskrifter lagres som JSON og lastes fra sidebar. Fritekst-importer forstår kg, g og prosent, gjenkjenner ingrediensnavn og setter batch-størrelse automatisk.

**Handleliste**
Genereres fra gjeldende oppskrift med prisestimat og produktlenker per butikk (Vestbrygg / Ølbrygging.no). Butikk velges globalt.

**Bryggeplan og utskrift**
Bryggeplan med meskevann, skyllevann, pre-boil, meskeplan, koketid, humletilsetninger og gjæranbefalinger. To nedlastbare A4-ark: ett kompakt oppskriftsark og ett bryggedagsark med avkrysningsbokser og skrivefelt.

**Datapipeline**
AI-scraper henter rådata fra Vestbrygg og Ølbrygging. Tre masterfiler (`master_malt.json`, `master_humle_v2.json`, `master_gjaer_v2.json`) er manuelt kuratert med aliases, sensoriske tags og butikk-match. Import-panelet synkroniserer priser til runtime-filene appen leser fra.

---

## Teknisk

**Stack:** Python + Streamlit. Kjører lokalt i nettleseren, uten ekstern server eller database.

```
ui/          → én fil per panel (malt, humle, gjær, shopping, brewday, ...)
modules/     → beregningslogikk (recipe_context, brewday_calc, store_matcher, ...)
data/        → masterfiler (rediger her) + runtime-filer (genereres)
docs/        → ROADMAP.md, MASTER_DATA_FLOW.md
```

All beregning skjer i `recipe_context.py` én gang per render. Panelene leser fra det ferdige kontekst-objektet.

**Starte appen:**
```
streamlit run app.py
```

---

## Planlagt fremover

| Versjon | Hva |
|---------|-----|
| V1.1.x | Polering etter ekte bryggedag (Sommerglød) |
| V1.2 | Bryggelogg — dato + OG er nok til å opprette en logg |
| V1.3 | Utstyrsprofil — erstatte hardkodede BrewZilla 35L-verdier |
| V1.4 | Inventory — spore humle og gjær på lager |
| V1.5 | Butikksammenligning — side-om-side kostnad Vestbrygg vs. Ølbrygging |

Se [docs/ROADMAP.md](docs/ROADMAP.md) for detaljer.
