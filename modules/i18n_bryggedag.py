"""NO/EN-tekster for bryggedagsflyten (#548): bryggemåte (prosessprofil),
vannkjemi, bryggedagsplan i appen og det eksporterte bryggedagsarket.

Dette er en ren datafil som slås inn i `modules.i18n.TEKSTER` (samme
`t()`-oppslag, samme `{param}`-interpolasjon, samme NO-fallback) — den er
skilt ut kun for at selve i18n.py ikke skal vokse med flere hundre linjer.
Norsk tekst her er ORD FOR ORD den teksten flyten viste før #548, slik at
norsk visning er uendret. Importerer ingenting.

Nøkkelprefikser:
  bdp.*  bryggedagspanelet (ui/brewday_panel.py)
  bx.*   eksportert bryggedagsark (modules/brewday_template.py)
  bd.*   felles for panel og ark (tilsetninger, gjærnoter, kokenote)
  pp.*   prosessprofiler og anbefalingsmotor (modules/process_profiles.py)
  pr.*   bryggemåte-panelet (ui/process_panel.py)
  wc.*   vannkjemi-logikk (modules/water_chemistry.py)
  wp.*   vannkjemi-panelet (ui/water_panel.py)

Lagrede data (profil-id-er, `navn` i lagrede profiler, brukerens notater,
oppskrifts- og produktnavn) oversettes ALDRI her — kun systemtekst.
"""

_K = {}


def _k(nokkel, no, en):
    _K[nokkel] = (no, en)


# ── Felles panel/ark: tilsetninger og gjærnoter ──────────────────────────────
_k("bd.tils.whirlfloc.navn", "Whirlfloc", "Whirlfloc")
_k("bd.tils.whirlfloc.dose", "½ tablett per 20 L", "½ tablet per 20 L")
_k("bd.tils.whirlfloc.timing", "15 min til kok slutt", "15 min before end of boil")
_k("bd.tils.whirlfloc.note", "Klaringsmiddel. Fremmer proteinagglutinasjon og klart øl.",
   "Fining agent. Promotes protein coagulation and clear beer.")
_k("bd.tils.irish_moss.navn", "Irish Moss", "Irish moss")
_k("bd.tils.irish_moss.dose", "1 ts per 20 L", "1 tsp per 20 L")
_k("bd.tils.irish_moss.timing", "15 min til kok slutt", "15 min before end of boil")
_k("bd.tils.irish_moss.note", "Naturlig klaringsmiddel. Rehydrer i kaldt vann i 20 min.",
   "Natural fining agent. Rehydrate in cold water for 20 min.")
_k("bd.tils.fermaid_o.navn", "Fermaid-O", "Fermaid-O")
_k("bd.tils.fermaid_o.dose", "0.25 g / L", "0.25 g / L")
_k("bd.tils.fermaid_o.timing", "Gjæringsstart (0–24 t)", "Start of fermentation (0–24 h)")
_k("bd.tils.fermaid_o.note", "Organisk gjærnæring. Tilsett ved pitching eller tidlig gjæring.",
   "Organic yeast nutrient. Add at pitching or early in fermentation.")
_k("bd.tils.yeast_nutrient.navn", "Gjærnæring", "Yeast nutrient")
_k("bd.tils.yeast_nutrient.dose", "0.5 g / L", "0.5 g / L")
_k("bd.tils.yeast_nutrient.timing", "15 min til kok slutt", "15 min before end of boil")
_k("bd.tils.yeast_nutrient.note", "Gir gjæren nitrogen og mikronæringsstoffer for frisk gjæring.",
   "Gives the yeast nitrogen and micronutrients for a healthy fermentation.")

_k("bd.gjaer_note.kveik", "Kveik — tåler høy temperatur (30–40°C). Underpitching er OK.",
   "Kveik — tolerates high temperatures (30–40°C). Underpitching is OK.")
_k("bd.gjaer_note.saison", "Saison — start lavt (20°C), la temperaturen stige gradvis til 26°C.",
   "Saison — start low (20°C) and let the temperature rise gradually to 26°C.")
_k("bd.gjaer_note.belgisk",
   "Belgisk gjær — temperatur påvirker esterkarakter sterkt. Start lavt for ryddigere profil.",
   "Belgian yeast — temperature strongly affects ester character. Start low for a cleaner profile.")
_k("bd.mesk.mashing", "Mesking", "Mashing")
_k("bd.kok.pilsner_anbefalt", "90 min anbefalt for Pilsnermalt.", "90 min recommended for pilsner malt.")
_k("bd.kok.pilsner_anbefalt_ark", "90 min anbefalt for Pilsnermalt", "90 min recommended for pilsner malt")

# ── Bryggedagspanel ──────────────────────────────────────────────────────────
_k("bdp.bryggemaate", "🧭 Bryggemåte: **{navn}**", "🧭 Brewing method: **{navn}**")
_k("bdp.batchnr", "Batchnummer", "Batch number")
_k("bdp.batchnr.placeholder", "f.eks. 2026-001", "e.g. 2026-001")
_k("bdp.dato", "Bryggedato", "Brew date")
_k("bdp.brygger", "Brygger", "Brewer")
_k("bdp.brygger.placeholder", "Navn", "Name")
_k("bdp.steg1", "🗒️ 1. Bryggeplan", "🗒️ 1. Brew plan")
_k("bdp.malt_tittel", "**🌾 Malt — {kg} kg**", "**🌾 Malt — {kg} kg**")
_k("bdp.vann_tittel", "**💧 Vann**", "**💧 Water**")
_k("bdp.meskevann", "Meskevann", "Mash water")
_k("bdp.skyllevann", "Skyllevann", "Sparge water")
_k("bdp.preboil", "Pre-boil", "Pre-boil")
_k("bdp.brewzilla_varsel",
   "⚠️ **BrewZilla 35 Gen4:** Estimert pre-boil {l} L overskrider anbefalt maks 30 L. Vurder å redusere batchstørrelse.",
   "⚠️ **BrewZilla 35 Gen4:** Estimated pre-boil {l} L exceeds the recommended maximum of 30 L. Consider reducing the batch size.")
_k("bdp.mesking_tittel", "**🌡️ Mesking**", "**🌡️ Mashing**")
_k("bdp.dekoksjon",
   "🔥 Dekoksjon: ta ut **{uttak} L** tykkmesk ved {fra}°C, kok {min} min, før tilbake for å nå {til}°C.",
   "🔥 Decoction: pull **{uttak} L** of thick mash at {fra}°C, boil {min} min, return it to reach {til}°C.")
_k("bdp.dobbelmesk",
   "🔁 Dobbelmesk: Mesk 1 ({m1} kg + {v1} L ferskt vann → {w1} L vørt) brukes som meskevann til Mesk 2 ({m2} kg → {w2} L sluttvørt).",
   "🔁 Double mash: Mash 1 ({m1} kg + {v1} L fresh water → {w1} L wort) is used as the mash water for Mash 2 ({m2} kg → {w2} L final wort).")
_k("bdp.koking_tittel", "**🔥 Koking**", "**🔥 Boil**")
_k("bdp.koketid", "Koketid", "Boil time")
_k("bdp.koketap", "Est. koketap", "Est. boil-off")
_k("bdp.postboil_est", "Est. post-boil", "Est. post-boil")
_k("bdp.humle_tittel", "**🌿 Humletilsetninger**", "**🌿 Hop additions**")
_k("bdp.humle_header", "| Tid igjen | Tilsatt etter | Humle | Gram | IBU |",
   "| Time left | Added after | Hop | Grams | IBU |")
_k("bdp.humle_forklaring",
   "«Tid igjen» = humlens egen koketid. «Tilsatt etter» = minutter etter kokestart, gitt {koketid} min total koketid.",
   "“Time left” = the hop's own boil time. “Added after” = minutes after the start of the boil, given {koketid} min total boil time.")
_k("bdp.humle_over_varsel",
   "⚠️ {n} humle markert over har lengre egen koketid enn total koketid ({koketid} min): {navn}. IBU-tabellen over viser oppskriftens PLANLAGTE bidrag (uendret tid) — se sammenligningen under for hva som faktisk er oppnåelig i denne koken.",
   "⚠️ {n} hop addition(s) marked above have a longer own boil time than the total boil time ({koketid} min): {navn}. The IBU table above shows the recipe's PLANNED contribution (time unchanged) — see the comparison below for what is actually achievable in this boil.")
_k("bdp.ibu_planlagt", "IBU — oppskriftens planlagte", "IBU — recipe's planned")
_k("bdp.ibu_faktisk", "IBU — prosessens faktisk mulige", "IBU — actually achievable in this process")
_k("bdp.ingen_humle", "Ingen humle i oppskriften.", "No hops in the recipe.")
_k("bdp.gjaer_tittel", "**🧫 Gjær & Fermentering**", "**🧫 Yeast & Fermentation**")
_k("bdp.gjaer_pakker", "- **{navn}** — {pakker} pakke(r)", "- **{navn}** — {pakker} pack(s)")
_k("bdp.tils_tittel", "**🧪 Tilsetninger**", "**🧪 Additions**")
_k("bdp.tils_velg", "Velg tilsetninger", "Select additions")
_k("bdp.steg2", "🌡️ 2. Mesking", "🌡️ 2. Mashing")
_k("bdp.mesk_start", "Meskestart", "Mash start")
_k("bdp.mesk_slutt", "Meskeslutt", "Mash end")
_k("bdp.mesk_temp", "Temp obs. {n} (°C)", "Temp reading {n} (°C)")
_k("bdp.steg3", "🔥 3. Koking & Prøver", "🔥 3. Boil & Samples")
_k("bdp.preboil_maalinger", "**📐 Pre-boil målinger**", "**📐 Pre-boil measurements**")
_k("bdp.preboil_vol", "Pre-boil volum (L)", "Pre-boil volume (L)")
_k("bdp.preboil_sg", "Pre-boil SG", "Pre-boil SG")
_k("bdp.postboil_estimert", "Estimert post-boil", "Estimated post-boil")
_k("bdp.postboil_hjelp", "Pre-boil minus {koketap} L estimert koketap", "Pre-boil minus {koketap} L estimated boil-off")
_k("bdp.preboil_over_30",
   "⚠️ Målt pre-boil {l} L overskrider BrewZilla 35 anbefalt maks (30 L).",
   "⚠️ Measured pre-boil {l} L exceeds the BrewZilla 35 recommended maximum (30 L).")
_k("bdp.planlagt_og", "Planlagt OG", "Planned OG")
_k("bdp.forventet_og", "Forventet OG (etter kok)", "Expected OG (after boil)")
_k("bdp.avvik", "Avvik", "Deviation")
_k("bdp.kok_tils_tittel", "**🧪 Tilsetninger i koking**", "**🧪 Additions in the boil**")
_k("bdp.postboil_tittel", "**📐 Post-boil**", "**📐 Post-boil**")
_k("bdp.postboil_vol", "Post-boil volum (L)", "Post-boil volume (L)")
_k("bdp.steg4", "⚗️ 4. Overføring & OG", "⚗️ 4. Transfer & OG")
_k("bdp.og_maal", "OG (mål: {x})", "OG (target: {x})")
_k("bdp.faktisk", "Faktisk", "Actual")
_k("bdp.pitch_temp", "Pitching-temperatur (°C)", "Pitching temperature (°C)")
_k("bdp.overforing_notat", "Notat ved overføring", "Transfer note")
_k("bdp.overforing_notat.placeholder", "f.eks. klart, god aroma", "e.g. clear, good aroma")
_k("bdp.steg5", "🧬 5. Gjæring", "🧬 5. Fermentation")
_k("bdp.gjaering_start", "Gjæringsstart", "Fermentation start")
_k("bdp.coldcrash", "Cold crash / tapping", "Cold crash / packaging")
_k("bdp.inkbird", "Inkbird-temperatur (°C)", "Inkbird temperature (°C)")
_k("bdp.inkbird.placeholder", "f.eks. 20.2", "e.g. 20.2")
_k("bdp.trykk", "Gjæringstrykk", "Fermentation pressure")
_k("bdp.trykk.placeholder", "f.eks. 0.8 bar", "e.g. 0.8 bar")
_k("bdp.fg_maal", "FG (mål: {x})", "FG (target: {x})")
_k("bdp.abv_maal", "ABV (mål: {x})", "ABV (target: {x})")
_k("bdp.beregnet", "Beregnet", "Calculated")
_k("bdp.beregnet_abv", "Beregnet ABV", "Calculated ABV")
_k("bdp.lagre_tittel", "**💾 Lagre målinger til aktivt brygg**", "**💾 Save measurements to the active brew**")
_k("bdp.lagre_ingen_aktivt",
   "Ingen aktivt brygg å lagre til. Start et brygg med «▶️ Start nytt brygg» øverst, eller velg et brygg i Brygghistorikk over.",
   "No active brew to save to. Start a brew with “▶️ Start nytt brygg” at the top, or select a brew in the brew history above.")
_k("bdp.lagre_maal", "Målbrygg: **{navn}** · `{id}`", "Target brew: **{navn}** · `{id}`")
_k("bdp.uten_navn", "(uten navn)", "(unnamed)")
_k("bdp.lagre_knapp", "💾 Lagre OG/FG/post-boil-volum + bryggedato", "💾 Save OG/FG/post-boil volume + brew date")
_k("bdp.lagre_ugyldig", "❌ Ugyldig tall i felt: {felt}. Ingenting ble lagret.",
   "❌ Invalid number in field(s): {felt}. Nothing was saved.")
_k("bdp.lagre_ok", "✅ Lagret til `{id}`", "✅ Saved to `{id}`")
_k("bdp.steg6", "📊 6. Effektivitet", "📊 6. Efficiency")
_k("bdp.eff_mesk", "Maskeeffektivitet", "Mash efficiency")
_k("bdp.eff_bryggeri", "Brygghuseffektivitet", "Brewhouse efficiency")
_k("bdp.eff_planlagt", "Planlagt effektivitet", "Planned efficiency")
_k("bdp.eff_fyll_mesk", "Fyll inn pre-boil SG og volum (Steg 3) for maskeeffektivitet.",
   "Enter pre-boil SG and volume (Step 3) for mash efficiency.")
_k("bdp.eff_fyll_bryggeri", "Fyll inn faktisk OG (Steg 4) for brygghuseffektivitet.",
   "Enter actual OG (Step 4) for brewhouse efficiency.")
_k("bdp.sjekkliste_tittel", "**✅ Bryggedags-sjekkliste**", "**✅ Brew day checklist**")
_k("bdp.sjekk.0", "Utstyr rent", "Equipment clean")
_k("bdp.sjekk.1", "Meskevann varmt", "Mash water hot")
_k("bdp.sjekk.2", "Skylling ferdig", "Sparging done")
_k("bdp.sjekk.3", "Kok startet", "Boil started")
_k("bdp.sjekk.4", "Humle tilsatt", "Hops added")
_k("bdp.sjekk.5", "Nedkjøling ferdig", "Cooling done")
_k("bdp.sjekk.6", "Gjær tilsatt", "Yeast pitched")
_k("bdp.sjekk.7", "Gjæring startet", "Fermentation started")
_k("bdp.bekreft_avvik",
   "Jeg har sett avviket mellom planlagt og faktisk mulig IBU over, og vil eksportere likevel",
   "I have seen the deviation between planned and actually achievable IBU above, and want to export anyway")
_k("bdp.last_avvik", "🔒 Bryggedagsarket er låst til avviket over er bekreftet.",
   "🔒 The brew day sheet is locked until the deviation above is confirmed.")
_k("bdp.generer", "🖨️ Generer Bryggedagsark", "🖨️ Generate brew day sheet")
_k("bdp.last_ned", "📥 Last ned bryggedagsark", "📥 Download brew day sheet")
_k("bdp.print_hint", "💡 Åpne filen i nettleseren og trykk **Ctrl + P** for å skrive ut.",
   "💡 Open the file in a browser and press **Ctrl + P** to print.")

# ── Eksportert bryggedagsark ─────────────────────────────────────────────────
_k("bx.tittel", "Bryggedagsark — {navn}", "Brew day sheet — {navn}")
_k("bx.ingen_malt", "Ingen malt registrert.", "No malt registered.")
_k("bx.ingen_humle", "Ingen humle.", "No hops.")
_k("bx.th.tid_igjen", "Tid igjen", "Time left")
_k("bx.th.tilsatt_etter", "Tilsatt etter", "Added after")
_k("bx.th.humle", "Humle", "Hop")
_k("bx.th.gram", "Gram", "Grams")
_k("bx.avvik.rad", "{navn}: oppgitt <strong>{tid} min</strong> — total koketid er kun <strong>{koketid} min</strong>",
   "{navn}: specified <strong>{tid} min</strong> — total boil time is only <strong>{koketid} min</strong>")
_k("bx.avvik.tittel",
   "⚠️ AVVIK: humletid overstiger total koketid — IBU under er IKKE fysisk oppnåelig som oppgitt",
   "⚠️ DEVIATION: hop time exceeds total boil time — the IBU below is NOT physically achievable as specified")
_k("bx.avvik.planlagt", "Planlagt IBU", "Planned IBU")
_k("bx.avvik.faktisk", "Faktisk mulig IBU", "Actually achievable IBU")
_k("bx.vannkilde", "Vannkilde: <strong>{navn}</strong>", "Water source: <strong>{navn}</strong>")
_k("bx.ukjent_kilde", "Ukjent kildevann", "Unknown source water")
_k("bx.ny_kilde", "(ny, ikke opprettet ennå)", "(new, not created yet)")
_k("bx.maalprofil", "Målprofil: <strong>{navn}</strong>", "Target profile: <strong>{navn}</strong>")
_k("bx.ikke_valgt", "Ikke valgt", "Not selected")
_k("bx.salt_mesk", "{navn} ({form}) i meskevann: <strong>{g} g</strong>",
   "{navn} ({form}) in mash water: <strong>{g} g</strong>")
_k("bx.salt_skyll", "{navn} ({form}) i skyllevann: <strong>{g} g</strong>",
   "{navn} ({form}) in sparge water: <strong>{g} g</strong>")
_k("bx.maal_ph", "Mål meske-pH: <strong>{x}</strong>", "Target mash pH: <strong>{x}</strong>")
_k("bx.romtemp", "Romtemperatur", "Room temperature")
_k("bx.syre_ukjent_konsentrasjon", " (konsentrasjon ikke angitt)", " (concentration not specified)")
_k("bx.bryggemaate", "Bryggemåte: {navn}", "Brewing method: {navn}")
_k("bx.dekoksjon",
   "🔥 Dekoksjon: ta ut {uttak} L tykkmesk ved {fra}°C, kok {min} min, før tilbake for å nå {til}°C.",
   "🔥 Decoction: pull {uttak} L of thick mash at {fra}°C, boil {min} min, return it to reach {til}°C.")
_k("bx.dobbelmesk",
   "🔁 Dobbelmesk: Mesk 1 ({m1} kg + {v1} L ferskt vann → {w1} L vørt) brukes som meskevann til Mesk 2 ({m2} kg → {w2} L sluttvørt).",
   "🔁 Double mash: Mash 1 ({m1} kg + {v1} L fresh water → {w1} L wort) is used as the mash water for Mash 2 ({m2} kg → {w2} L final wort).")
_k("bx.tils_tittel", "Tilsetninger", "Additions")
_k("bx.th.tilsetning", "Tilsetning", "Addition")
_k("bx.th.dose", "Dose", "Dose")
_k("bx.th.tidspunkt", "Tidspunkt", "Timing")
_k("bx.faktisk_lbl", "Faktisk:", "Actual:")
_k("bx.malt_lbl", "Målt:", "Measured:")
_k("bx.maal_lbl", "Mål: {x}", "Target: {x}")
_k("bx.stat.preboil_sg", "Pre-boil SG", "Pre-boil SG")
_k("bx.stat.preboil_vol", "Pre-boil Vol", "Pre-boil Vol")
_k("bx.stat.postboil_vol", "Post-boil Vol", "Post-boil Vol")
_k("bx.stat.pitch", "Pitch temp", "Pitch temp")
_k("bx.stat.maskeeff", "Maskeeff", "Mash eff")
_k("bx.batchnr", "Batchnummer", "Batch number")
_k("bx.dato", "Bryggedato", "Brew date")
_k("bx.brygger", "Brygger", "Brewer")
_k("bx.malt_tittel", "Malt — {kg}", "Malt — {kg}")
_k("bx.vann_tittel", "Vann", "Water")
_k("bx.meskevann", "Meskevann: <strong>{l} L</strong>", "Mash water: <strong>{l} L</strong>")
_k("bx.skyllevann", "Skyllevann: <strong>{l} L</strong>", "Sparge water: <strong>{l} L</strong>")
_k("bx.preboil", "Pre-boil: <strong>{l} L</strong>", "Pre-boil: <strong>{l} L</strong>")
_k("bx.preboil_maks", "(maks 30 L — BrewZilla)", "(max 30 L — BrewZilla)")
_k("bx.faktisk_ph", "Faktisk meske-pH", "Actual mash pH")
_k("bx.maaletemp", "Måletemperatur", "Measurement temperature")
_k("bx.syre_tilsatt", "Syrer tilsatt", "Acid added")
_k("bx.mesking_tittel", "Mesking", "Mashing")
_k("bx.koking_tittel", "Koking", "Boil")
_k("bx.kok_linje", "{min} min kok", "{min} min boil")
_k("bx.koketap", "Est. koketap: <strong>{l} L</strong>", "Est. boil-off: <strong>{l} L</strong>")
_k("bx.humle_tittel", "Humle", "Hops")
_k("bx.gjaer_tittel", "Gjær", "Yeast")
_k("bx.pakker", "{n} pakke(r) anbefalt", "{n} pack(s) recommended")
_k("bx.gjaering_start", "Gjæringsstart", "Fermentation start")
_k("bx.coldcrash", "Cold crash / tapping", "Cold crash / packaging")
_k("bx.sjekkliste_tittel", "Bryggedags-sjekkliste", "Brew day checklist")
_k("bx.sjekk.0", "Utstyr", "Equipment")
_k("bx.sjekk.1", "Meskevann", "Mash water")
_k("bx.sjekk.2", "Skylling", "Sparging")
_k("bx.sjekk.3", "Kok", "Boil")
_k("bx.sjekk.4", "Humle", "Hops")
_k("bx.sjekk.5", "Nedkjølt", "Cooled")
_k("bx.sjekk.6", "Gjær", "Yeast")
_k("bx.sjekk.7", "Gjæring", "Fermentation")
_k("bx.maalinger_tittel", "Målinger", "Measurements")
_k("bx.eff_bryggeri", "Brygghuseffektivitet (plan: {x}%)", "Brewhouse efficiency (plan: {x}%)")
_k("bx.eff_abv", "Beregnet ABV", "Calculated ABV")
_k("bx.batch_til_gjaering", "Batch til gjæring", "Batch to fermentation")
_k("bx.notater", "Notater", "Notes")
_k("bx.effektivitet", "Effektivitet", "Efficiency")

# ── Prosessprofiler (standardtekster, oversatt ved visning — lagrede
# profiler beholder norsk tekst) ─────────────────────────────────────────────
_k("pp.navn.enkel_infusjon", "Enkel infusjon", "Single infusion")
_k("pp.navn.hochkurz", "Hochkurz (stegmesk)", "Hochkurz (step mash)")
_k("pp.navn.enkel_dekoksjon", "Enkel dekoksjon", "Single decoction")
_k("pp.navn.reiterated_mash", "Reiterated mash (dobbel mesk)", "Reiterated mash (double mash)")
_k("pp.navn.egendefinert", "Egendefinert prosess", "Custom process")
_k("pp.navn.egendefinert_prefiks", "Egendefinert – basert på ", "Custom – based on ")
_k("pp.besk.enkel_infusjon",
   "Én mesketemperatur (single-infusion). Raskest og enklest — passer de aller fleste ales og de fleste moderne lagerstiler.",
   "A single mash temperature (single infusion). Fastest and simplest — suits the vast majority of ales and most modern lager styles.")
_k("pp.besk.hochkurz",
   "Klassisk tysk to-trinns stegmesk: én hvile ved lavere temperatur etterfulgt av én hvile ved høyere temperatur (mer uforgjærbart sukker), og deretter mashout.",
   "Classic German two-step mash: one rest at a lower temperature followed by one rest at a higher temperature (more unfermentable sugar), then mashout.")
_k("pp.besk.enkel_dekoksjon",
   "Historisk teknikk: en del av mesken ('tykkmesken') tas ut, kokes 10-15 min for å utvikle melanoidiner (rik, bakt/toastet maltkarakter), og føres tilbake i hovedmesken for å heve temperaturen mot mashout. Uttaksvolumet beregnes av appen, men ALLE verdier kan redigeres fritt.",
   "Historic technique: part of the mash (the 'thick mash') is pulled off, boiled for 10-15 min to develop melanoidins (rich, baked/toasted malt character), and returned to the main mash to raise the temperature towards mashout. The app calculates the pull-off volume, but ALL values can be edited freely.")
_k("pp.besk.reiterated_mash",
   "Historisk 'dobbelmesk'-teknikk: maltmengden deles i to. Første mesk lages med fersk vann og lautres til en vørt. Denne vørten brukes SOM meskevann til den andre mesken, som deretter lautres til sluttvørt. Gir en svært maltrik, kompleks vørt, men er tidkrevende og kan gi redusert samlet effektivitet.",
   "Historic 'double mash' technique: the grain bill is split in two. The first mash is made with fresh water and lautered into a wort. This wort is used AS the mash water for the second mash, which is then lautered into the final wort. Gives a very malt-rich, complex wort, but is time-consuming and can reduce overall efficiency.")
_k("pp.besk.egendefinert",
   "Fritt redigerbar prosess — start tom eller kopiér en standardprofil som utgangspunkt.",
   "Freely editable process — start empty or copy a standard profile as a starting point.")
_k("pp.besk.brukerdefinert", "Brukerdefinert prosess.", "User-defined process.")
_k("pp.utstyr.enkel_infusjon", "Ingen spesielle krav utover vanlig meskekar.",
   "No special requirements beyond an ordinary mash vessel.")
_k("pp.utstyr.hochkurz",
   "Krever presis, stabil temperaturstyring gjennom flere steg — godt egnet for elektrisk mesk-kar (f.eks. BrewZilla), vanskeligere med kun gassbrenner og manuell temperaturstyring.",
   "Requires precise, stable temperature control through several steps — well suited to an electric mash vessel (e.g. BrewZilla), harder with only a gas burner and manual temperature control.")
_k("pp.utstyr.enkel_dekoksjon",
   "Krever en egen kjele (eller nok ledig kapasitet i hovedkjelen) til å koke en del av mesken separat, samt et kar/kjele å øse tykkmesken over i. Lang bryggedag — sett av ekstra tid.",
   "Requires a separate kettle (or enough spare capacity in the main kettle) to boil part of the mash separately, plus a vessel/kettle to ladle the thick mash into. Long brew day — allow extra time.")
_k("pp.utstyr.reiterated_mash",
   "Krever lauter-kapasitet for to fulle mesker etter hverandre, og et meskekar/kjele stort nok til hver delmengde korn for seg. Svært lang bryggedag (to fulle meske- og lauteresykluser).",
   "Requires lauter capacity for two full mashes in a row, and a mash vessel/kettle large enough for each portion of grain separately. Very long brew day (two full mash and lauter cycles).")
_k("pp.paavirkning.enkel_infusjon",
   "Nøytral referanse — verken ekstra kropp eller ekstra tørrhet utover det maltbill og gjær selv gir.",
   "Neutral reference — neither extra body nor extra dryness beyond what the grain bill and yeast give on their own.")
_k("pp.paavirkning.hochkurz",
   "Profilen bruker to separate temperaturhviler i sekvens, etterfulgt av mashout.",
   "The profile uses two separate temperature rests in sequence, followed by mashout.")
_k("pp.paavirkning.enkel_dekoksjon",
   "Kokingen av tykkmesken karamelliserer/melanoidinerer sukker og gir en dypere, rikere, mer 'bakt' maltkarakter og ofte noe mørkere farge enn samme oppskrift meskes med infusjon. Gjærbarhet påvirkes lite hvis hovedmeskens temperaturprofil for øvrig er lik.",
   "Boiling the thick mash caramelises/melanoidinises sugars and gives a deeper, richer, more 'baked' malt character and often a somewhat darker colour than the same recipe mashed by infusion. Fermentability is little affected if the main mash's temperature profile is otherwise the same.")
_k("pp.paavirkning.reiterated_mash",
   "Gir typisk en svært fyldig, maltrik vørt med redusert forutsigbarhet i endelig effektivitet (den andre mesken meskes ikke med rent vann, så enzymaktivitet/utbytte er vanskeligere å anslå presist enn ved vanlig infusjon).",
   "Typically gives a very full-bodied, malt-rich wort with reduced predictability in final efficiency (the second mash is not mashed with plain water, so enzyme activity/yield is harder to estimate precisely than with ordinary infusion).")
_k("pp.steg.hovedmesk", "Hovedmesk — enzymatisk konvertering", "Main mash — enzymatic conversion")
_k("pp.steg.mashout", "Mashout — stopper enzymaktivitet", "Mashout — stops enzyme activity")
_k("pp.steg.lavere", "Lavere temperaturhvile", "Lower temperature rest")
_k("pp.steg.hoyere", "Høyere temperaturhvile", "Higher temperature rest")
_k("pp.steg.startmesk", "Startmesk — før uttak", "Start mash — before pull-off")
_k("pp.steg.mashout_dek", "Mashout etter dekoksjon er ført tilbake", "Mashout after the decoction has been returned")
_k("pp.steg.mesk1", "Mesk 1 — fersk vann", "Mash 1 — fresh water")
_k("pp.steg.mesk2", "Mesk 2 — meskevann er vørt fra mesk 1", "Mash 2 — mash water is wort from mash 1")
_k("pp.steg.mashout_m2", "Mashout på mesk 2", "Mashout on mash 2")
_k("pp.steg.dek_kommentar", "Kok tykkmesken 10-15 min, rør ofte for å unngå svidd bunn.",
   "Boil the thick mash for 10-15 min, stirring often to avoid scorching.")
_k("pp.stegtype.infusjon", "Infusjon", "Infusion")
_k("pp.stegtype.mashout", "Mashout", "Mashout")
_k("pp.stegtype.dekoksjon_uttak", "Dekoksjon-uttak", "Decoction pull-off")
_k("pp.stegtype.dekoksjon_retur", "Dekoksjon-retur", "Decoction return")
_k("pp.stegtype.dekoksjon_uttak_kapital", "Dekoksjon uttak", "Decoction pull-off")
_k("pp.stegtype.dekoksjon_retur_kapital", "Dekoksjon retur", "Decoction return")
_k("pp.stegtype.infusjon_kapital", "Infusjon", "Infusion")
_k("pp.vansk.Lett", "Lett", "Easy")
_k("pp.vansk.Middels", "Middels", "Medium")
_k("pp.vansk.Krevende", "Krevende", "Demanding")
_k("pp.sparge.batch_sparge", "Batch sparge (skyller i én/to porsjoner)", "Batch sparge (rinses in one/two portions)")
_k("pp.sparge.no_sparge", "No-sparge (alt vann i mesken, ingen skylling)", "No-sparge (all water in the mash, no sparging)")
_k("pp.sparge.fly_sparge", "Fly sparge (kontinuerlig skylling)", "Fly sparge (continuous sparging)")
_k("pp.del.mesk1", "Mesk 1", "Mash 1")
_k("pp.del.mesk2", "Mesk 2", "Mash 2")
_k("pp.rm.v_lang", "Lang bryggedag: to fulle meske- og lauteresykluser etter hverandre.",
   "Long brew day: two full mash and lauter cycles in a row.")
_k("pp.rm.v_effektivitet",
   "Redusert/uforutsigbar effektivitet: mesk 2 meskes med vørt (ikke ferskt vann), så utbyttet er vanskeligere å anslå presist enn ved vanlig infusjon.",
   "Reduced/unpredictable efficiency: mash 2 is mashed with wort (not fresh water), so the yield is harder to estimate precisely than with ordinary infusion.")
_k("pp.rm.v_tykk",
   "Vørt fra mesk 1 ({faktisk} L) gir en tykkere mesk 2 enn normalt meskeforhold skulle tilsi ({anbefalt} L) — vurder å øke mesk 1-andelen eller tilsette noe ekstra vann.",
   "Wort from mash 1 ({faktisk} L) gives a thicker mash 2 than the normal mash ratio would suggest ({anbefalt} L) — consider increasing the mash 1 share or adding some extra water.")
_k("pp.utstyr.mesk_del",
   "{del}: estimert meskevolum {vol} L overskrider kjelekapasitet på {kjele} L.",
   "{del}: estimated mash volume {vol} L exceeds the kettle capacity of {kjele} L.")
_k("pp.utstyr.mesk",
   "Estimert meskevolum {vol} L overskrider kjelekapasitet på {kjele} L — vurder reiterated mash (dobbel mesk) eller et mindre batch.",
   "Estimated mash volume {vol} L exceeds the kettle capacity of {kjele} L — consider reiterated mash (double mash) or a smaller batch.")
_k("pp.anb.kapasitet",
   "Total maltmengde ({kg} kg) gir et estimert meskevolum ({vol} L) som overskrider kjelekapasiteten ({kjele} L).",
   "Total grain bill ({kg} kg) gives an estimated mash volume ({vol} L) that exceeds the kettle capacity ({kjele} L).")
_k("pp.anb.hoy_og",
   "Mål-OG ({og}) er svært høy (>= {grense}) — én enkelt mesk vil normalt ikke klare å ekstrahere nok sukker/passe meskeforhold i ett kar.",
   "Target OG ({og}) is very high (>= {grense}) — a single mash will normally not be able to extract enough sugar/fit the mash ratio in one vessel.")
_k("pp.anb.dekoksjon_historisk",
   "{stil} er historisk knyttet til dekoksjonsmesking, og historisk autentisitet er etterspurt.",
   "{stil} is historically tied to decoction mashing, and historical authenticity was requested.")
_k("pp.anb.hochkurz",
   "{stil} er en tradisjonell tysk/østerriksk lagerstil som vanligvis meskes med Hochkurz-stegmesk for rundere maltkarakter.",
   "{stil} is a traditional German/Austrian lager style that is usually mashed with a Hochkurz step mash for a rounder malt character.")
_k("pp.anb.dekoksjon_alt",
   "Dekoksjon er tilgjengelig som et mer historisk autentisk, men også mer tidkrevende alternativ.",
   "Decoction is available as a more historically authentic, but also more time-consuming, alternative.")
_k("pp.anb.standard",
   "Ingen spesielle krav funnet for valgt/nærmeste stil, maltbase eller utstyr — enkel infusjon er raskest og passer de fleste ales, stout og moderne lagerstiler.",
   "No special requirements found for the selected/closest style, malt base or equipment — single infusion is the fastest and suits most ales, stouts and modern lager styles.")

# ── Bryggemåte-panelet ───────────────────────────────────────────────────────
_k("pr.tittel", "🧭 Bryggemåte", "🧭 Brewing method")
_k("pr.intro",
   "Prosessprofilen beskriver HVORDAN ølet meskes og kokes — helt adskilt fra oppskriften (malt/humle/gjær). Å bytte bryggemåte endrer aldri ingredienslisten.",
   "The process profile describes HOW the beer is mashed and boiled — completely separate from the recipe (malt/hops/yeast). Changing the brewing method never changes the ingredient list.")
_k("pr.historisk", "Ønsker historisk autentisitet", "Prefer historical authenticity")
_k("pr.historisk.hjelp", "Foretrekk historiske teknikker (f.eks. dekoksjon) der stilen støtter det.",
   "Prefer historical techniques (e.g. decoction) where the style supports it.")
_k("pr.anbefalt", "💡 **Anbefalt bryggemåte: {navn}**", "💡 **Recommended brewing method: {navn}**")
_k("pr.reparert", "En inkonsistent prosessprofil ble oppdaget og reparert til standardmalen.",
   "An inconsistent process profile was detected and repaired to the standard template.")
_k("pr.velg", "Velg bryggemåte (anbefalingen setter ALDRI valget automatisk — du må selv velge)",
   "Choose brewing method (the recommendation NEVER sets the choice automatically — you must choose yourself)")
_k("pr.anbefalt_suffiks", "  ⭐ anbefalt", "  ⭐ recommended")
_k("pr.vanskelighetsgrad", "Vanskelighetsgrad", "Difficulty")
_k("pr.ekstra_tid", "Ekstra tidsbruk", "Extra time")
_k("pr.skyllemetode", "Skyllemetode", "Sparge method")
_k("pr.utstyr", "⚙️ **Utstyr:** {x}", "⚙️ **Equipment:** {x}")
_k("pr.paavirkning", "🧬 **Forventet påvirkning på kropp/utgjæring:** {x}",
   "🧬 **Expected effect on body/attenuation:** {x}")
_k("pr.meskesteg", "🌡️ Meskesteg (redigerbare)", "🌡️ Mash steps (editable)")
_k("pr.temp", "Temp (°C)", "Temp (°C)")
_k("pr.min", "Min", "Min")
_k("pr.type", "Type", "Type")
_k("pr.kommentar", "Kommentar", "Comment")
_k("pr.fjern_steg", "Fjern steg", "Remove step")
_k("pr.legg_til_steg", "➕ Legg til meskesteg", "➕ Add mash step")
_k("pr.redigering_oppdaget",
   "Redigering oppdaget — byttet til «{navn}» slik at endringene dine ikke overskrives.",
   "Edit detected — switched to “{navn}” so your changes are not overwritten.")
_k("pr.total_koketid", "Total koketid (min)", "Total boil time (min)")
_k("pr.dek_tittel", "🔥 Dekoksjonsdetaljer", "🔥 Decoction details")
_k("pr.dek_fra", "Fra temp (°C)", "From temp (°C)")
_k("pr.dek_til", "Til temp (°C)", "To temp (°C)")
_k("pr.dek_koketid", "Koketid uttak (min)", "Boil time of pull-off (min)")
_k("pr.dek_auto", "Bruk automatisk beregnet uttaksvolum", "Use automatically calculated pull-off volume")
_k("pr.dek_foreslatt", "Foreslått uttaksvolum", "Suggested pull-off volume")
_k("pr.dek_manuell", "Uttaksvolum (L) — overstyrt manuelt", "Pull-off volume (L) — manually overridden")
_k("pr.rm_tittel", "🔁 Dobbelmesk — vann- og volumflyt", "🔁 Double mash — water and volume flow")
_k("pr.rm_andel", "Andel av maltmengden i mesk 1", "Share of the grain bill in mash 1")
_k("pr.rm_flyt",
   "**Mesk 1:** {m1} kg malt + {v1} L ferskt vann → **{w1} L vørt**\n\n**Mesk 2:** {m2} kg malt + {v2} L (= vørten fra mesk 1, IKKE ferskt vann) → **{w2} L sluttvørt**",
   "**Mash 1:** {m1} kg malt + {v1} L fresh water → **{w1} L wort**\n\n**Mash 2:** {m2} kg malt + {v2} L (= the wort from mash 1, NOT fresh water) → **{w2} L final wort**")
_k("pr.humle_over_varsel",
   "⚠️ {n} humletilsetning(er) har lengre egen koketid enn total koketid ({koketid} min): {navn}. Disse kan ikke få full IBU-utnyttelse innenfor denne koken — se «Humletilsetninger» i Bryggedag-fanen for oppskriftens planlagte IBU vs. prosessens faktisk mulige IBU.",
   "⚠️ {n} hop addition(s) have a longer own boil time than the total boil time ({koketid} min): {navn}. These cannot reach full IBU utilisation within this boil — see “Hop additions” in the Brew day tab for the recipe's planned IBU vs. the process's actually achievable IBU.")
_k("pr.notater", "Egne notater om denne bryggemåten", "Your own notes on this brewing method")

# ── Vannkjemi-logikk (modules/water_chemistry.py) ────────────────────────────
_k("wc.salt.cacl2_2h2o.navn", "Kalsiumklorid-dihydrat", "Calcium chloride dihydrate")
_k("wc.salt.cacl2_vannfri.navn", "Kalsiumklorid (vannfri)", "Calcium chloride (anhydrous)")
_k("wc.salt.gips.navn", "Gips", "Gypsum")
_k("wc.salt.epsomsalt.navn", "Epsomsalt", "Epsom salt")
_k("wc.salt.vanlig_salt.navn", "Vanlig salt", "Table salt")
_k("wc.salt.natron.navn", "Natron", "Baking soda")
_k("wc.salt.kalsiumkarbonat.navn", "Kalsiumkarbonat", "Calcium carbonate")
_k("wc.salt.cacl2_vannfri.advarsel",
   "Vannfri CaCl2 er sterkt hygroskopisk og gir MER ion per gram enn dihydratformen — bland aldri sammen doseringer for de to.",
   "Anhydrous CaCl2 is strongly hygroscopic and gives MORE ion per gram than the dihydrate form — never mix doses for the two.")
_k("wc.salt.kalsiumkarbonat.advarsel",
   "Svært lav løselighet i vann uten CO2 — i praksis løses ofte mindre enn beregnet, og effekten er langsom og vanskelig å forutsi presist. Foretrekk normalt natron for HCO3-justering.",
   "Very low solubility in water without CO2 — in practice often less dissolves than calculated, and the effect is slow and hard to predict precisely. Normally prefer baking soda for HCO3 adjustment.")
_k("wc.syre.melkesyre.navn", "Melkesyre", "Lactic acid")
_k("wc.syre.fosforsyre.navn", "Fosforsyre", "Phosphoric acid")
_k("wc.status.under", "under", "below")
_k("wc.status.over", "over", "above")
_k("wc.status.innenfor", "innenfor", "within")
_k("wc.status.ukjent", "ukjent", "unknown")
_k("wc.v.ukjent_kilde", "Kildevann er ukjent — ingen ionverdier er registrert. Appen dikter ikke opp tall.",
   "Source water is unknown — no ion values are registered. The app does not make up numbers.")
_k("wc.v.hco3_mangler", "Alkalitet/HCO3 mangler for kildevannet — meske-pH-vurderingen blir mindre pålitelig.",
   "Alkalinity/HCO3 is missing for the source water — the mash pH assessment becomes less reliable.")
_k("wc.v.vekt",
   "{navn}: total mengde ({gram} g) er under vektens praktiske oppløsning ({opplosning} g) — vurder å lage en fortynnet stamløsning.",
   "{navn}: total amount ({gram} g) is below the scale's practical resolution ({opplosning} g) — consider making a diluted stock solution.")
_k("wc.v.na", "Høyt natrium: {v} ppm (grense {grense} ppm) — kan gi salt/skarp smak.",
   "High sodium: {v} ppm (limit {grense} ppm) — can give a salty/sharp taste.")
_k("wc.v.mg", "Høyt magnesium: {v} ppm (grense {grense} ppm) — kan gi bitter/skarp bismak.",
   "High magnesium: {v} ppm (limit {grense} ppm) — can give a bitter/sharp off-taste.")
_k("wc.v.cl", "Svært høyt klorid: {v} ppm (grense {grense} ppm).",
   "Very high chloride: {v} ppm (limit {grense} ppm).")
_k("wc.v.so4", "Svært høyt sulfat: {v} ppm (grense {grense} ppm) — kan gi skarp/tørr bitterhet.",
   "Very high sulfate: {v} ppm (limit {grense} ppm) — can give a sharp/dry bitterness.")
_k("wc.v.ca_lav",
   "Lavt kalsium: {v} ppm (grense {grense} ppm) — kan gi svakere enzym-/gjæraktivitet og dårligere klaring.",
   "Low calcium: {v} ppm (limit {grense} ppm) — can give weaker enzyme/yeast activity and poorer clarity.")
_k("wc.v.ca_hoy",
   "Høyt kalsium: {v} ppm (grense {grense} ppm) — trolig unødvendig høy mineralbelastning, vurder å redusere saltmengden.",
   "High calcium: {v} ppm (limit {grense} ppm) — probably an unnecessarily high mineral load, consider reducing the salt amount.")
_k("wc.v.utenfor", "{ion} ({v} ppm) er {status} målområdet ({min}–{maks} ppm).",
   "{ion} ({v} ppm) is {status} the target range ({min}–{maks} ppm).")
_k("wc.v.kilde_over",
   "Kildevannets {ion} ({v} ppm) er allerede over målprofilens maks ({maks} ppm) — salter kan bare tilsette ioner, aldri fjerne dem. Målprofilen kan ikke nås med de valgte saltene alene.",
   "The source water's {ion} ({v} ppm) is already above the target profile's maximum ({maks} ppm) — salts can only add ions, never remove them. The target profile cannot be reached with the selected salts alone.")
_k("wc.v.syre_prosent", "{navn}: konsentrasjon (%) er ikke angitt — kan ikke beregne syrestyrke presist.",
   "{navn}: concentration (%) is not specified — acid strength cannot be calculated precisely.")
_k("wc.v.syre_standardnavn", "Syre", "Acid")
_k("wc.v.sum", "Summen av meske- og skylletilsetning stemmer ikke med totalmengden — mulig avrundingsfeil i fordelingen.",
   "The sum of the mash and sparge additions does not match the total amount — possible rounding error in the split.")
_k("wc.anb.ingen", "Ingen målprofiler er lagret.", "No target profiles are saved.")
_k("wc.anb.stil", "{stil} står oppført under anbefalte stiler for «{profil}».",
   "{stil} is listed under recommended styles for “{profil}”.")
_k("wc.anb.balansert",
   "Ingen målprofil er spesifikt knyttet til denne stilen — «Balansert ale» er et nøytralt utgangspunkt for de fleste ølstiler.",
   "No target profile is specifically tied to this style — “Balanced ale” is a neutral starting point for most beer styles.")
_k("wc.anb.forste", "Ingen spesifikk anbefaling funnet — viser første tilgjengelige målprofil.",
   "No specific recommendation found — showing the first available target profile.")
_k("wc.fs.ugyldig_volum", "Ugyldig vannvolum — kan ikke beregne saltforslag.",
   "Invalid water volume — cannot calculate a salt suggestion.")
_k("wc.fs.naer",
   "Kildevannet ligger allerede nær målområdet for klorid/sulfat — ingen salter foreslått.",
   "The source water is already close to the target range for chloride/sulfate — no salts suggested.")
_k("wc.fs.cacl2", "Kalsiumklorid løfter Ca og Cl", "Calcium chloride raises Ca and Cl")
_k("wc.fs.gips", "gips løfter Ca og SO4", "gypsum raises Ca and SO4")
_k("wc.fs.merk",
   " Merk: {ioner} kan IKKE nås med kun kalsiumklorid og gips — dette krever andre salter (f.eks. natron for HCO3) eller ligger allerede utenfor målområdet i kildevannet, som salter aldri kan rette opp (de tilsetter, aldri fjerner, ioner). Målprofilen er IKKE fullt oppnådd med dette forslaget alene.",
   " Note: {ioner} can NOT be reached with calcium chloride and gypsum alone — this requires other salts (e.g. baking soda for HCO3) or is already outside the target range in the source water, which salts can never correct (they add ions, never remove them). The target profile is NOT fully achieved with this suggestion alone.")
_k("wc.fs.delvis",
   " {ioner} er fortsatt utenfor målområdet med denne mengden — juster gram-tallene fritt for å nærme deg midten av intervallet.",
   " {ioner} is still outside the target range with this amount — adjust the gram values freely to get closer to the middle of the range.")

# ── Vannkjemi-panelet ────────────────────────────────────────────────────────
_k("wp.tittel", "💧 Vannkjemi", "💧 Water chemistry")
_k("wp.intro",
   "Vannbehandlingen beskriver HVILKET VANN ølet brygges med og hvordan det justeres med salter/syrer — helt adskilt fra oppskriften, bryggemåten og utstyrsprofilen. Appen anbefaler, men endrer aldri vannplanen uten at du selv velger det.",
   "Water treatment describes WHICH WATER the beer is brewed with and how it is adjusted with salts/acids — completely separate from the recipe, the brewing method and the equipment profile. The app recommends, but never changes the water plan unless you choose to.")
_k("wp.hvorfor_tittel", "ℹ️ Hvorfor disse tallene betyr noe (kort intro)", "ℹ️ Why these numbers matter (short intro)")
_k("wp.hvorfor",
   "- **pH** — påvirker meskeenzymene og hvor godt stivelsen omdannes til sukker. Målområdet under er veiledende, ikke et eksakt fasitall.\n- **Ca (kalsium)** — trolig det viktigste enkeltionet i bryggevann; bidrar bl.a. til gjærhelse/flokkulering og påvirker vannkjemien indirekte.\n- **Mg (magnesium)** — næringsstoff i små mengder; høye nivåer kan gi uønsket smak.\n- **Na (natrium)** — moderate nivåer kan gi et rundere, fyldigere preg; for mye kan bli salt/skarpt.\n- **Cl (klorid)** — forbindes ofte med rundere malt-/munnfølelse.\n- **SO4 (sulfat)** — forbindes ofte med tørrere, skarpere humlebitterhet.\n- **Cl:SO4** — gir et grovt signal om retning (malt vs. humle), men er IKKE en fasit alene — de faktiske ionenivåene betyr også noe.",
   "- **pH** — affects the mash enzymes and how well the starch is converted to sugar. The target range below is indicative, not an exact answer.\n- **Ca (calcium)** — probably the most important single ion in brewing water; contributes to yeast health/flocculation among other things and affects the water chemistry indirectly.\n- **Mg (magnesium)** — a nutrient in small amounts; high levels can give unwanted flavours.\n- **Na (sodium)** — moderate levels can give a rounder, fuller impression; too much can become salty/harsh.\n- **Cl (chloride)** — often associated with a rounder malt/mouthfeel.\n- **SO4 (sulfate)** — often associated with a drier, sharper hop bitterness.\n- **Cl:SO4** — gives a rough signal of direction (malt vs. hops), but is NOT an answer on its own — the actual ion levels matter too.")
_k("wp.vannbehandling_tittel", "💧 Vannbehandling (forberedelse)", "💧 Water treatment (preparation)")
_k("wp.kildevann", "**Kildevann**", "**Source water**")
_k("wp.ukjent_kildevann", "❓ Ukjent kildevann", "❓ Unknown source water")
_k("wp.ny_kilde_valg", "➕ Ny egendefinert kilde …", "➕ New custom source …")
_k("wp.velg_kildevann", "Velg kildevann", "Choose source water")
_k("wp.ny_kilde_navn", "Navn på ny kilde", "Name of new source")
_k("wp.ny_kilde_placeholder", "f.eks. Egen brønn 2026", "e.g. Own well 2026")
_k("wp.opprett_kilde", "➕ Opprett kilde", "➕ Create source")
_k("wp.opprettet_kilde", "Opprettet kilde «{navn}» — fyll inn ionverdier under.",
   "Created source “{navn}” — fill in the ion values below.")
_k("wp.demo_suffiks", " (demo — ikke permanent)", " (demo — not permanent)")
_k("wp.ny_kilde_midlertidig", "(ny, ikke opprettet ennå)", "(new, not created yet)")
_k("wp.ukjent_kilde_navn", "Ukjent kildevann", "Unknown source water")
_k("wp.ingen_ionverdier", "Ingen ionverdier registrert — appen dikter ikke opp tall for en ukjent kilde.",
   "No ion values registered — the app does not make up numbers for an unknown source.")
_k("wp.rediger_kilde", "🔬 Rediger kildeprofil", "🔬 Edit source profile")
_k("wp.navn", "Navn", "Name")
_k("wp.sted", "Sted/lokasjon", "Location")
_k("wp.analyseaar", "Analyseår", "Analysis year")
_k("wp.ph_ukjent", "pH ukjent", "pH unknown")
_k("wp.ph", "pH", "pH")
_k("wp.kilde_notater", "Notater (laboratorium/kilde, måletype osv.)", "Notes (laboratory/source, type of measurement etc.)")
_k("wp.lagre_kilde", "💾 Lagre denne kildeprofilen", "💾 Save this source profile")
_k("wp.kilde_lagret", "Kildeprofil lagret!", "Source profile saved!")
_k("wp.ion_ukjent", "{ion} ukjent", "{ion} unknown")
_k("wp.maalprofil", "**Målprofil**", "**Target profile**")
_k("wp.maalprofil_forklaring",
   "Målprofilen er en HELT ANNEN ting enn kildevannet over — kildevannet er hva som faktisk kommer ut av springen/brønnen din, målprofilen er hva du ØNSKER å oppnå etter salttilsetning. Jordalsvatnet 2025 er aldri et valg her, kun under «Kildevann».",
   "The target profile is something COMPLETELY different from the source water above — the source water is what actually comes out of your tap/well, the target profile is what you WANT to achieve after adding salts. Jordalsvatnet 2025 is never a choice here, only under “Source water”.")
_k("wp.ingen_maalprofiler", "Ingen målprofiler er lagret ennå.", "No target profiles are saved yet.")
_k("wp.anbefalt_maal", "💡 **Anbefalt målprofil: {navn}**", "💡 **Recommended target profile: {navn}**")
_k("wp.velg_maal", "Velg målprofil (anbefalingen setter ALDRI valget automatisk — du må selv velge)",
   "Choose target profile (the recommendation NEVER sets the choice automatically — you must choose yourself)")
_k("wp.anbefalt_suffiks", "  ⭐ anbefalt", "  ⭐ recommended")
_k("wp.rediger_maal", "🎯 Rediger målprofil (min/maks per ion)", "🎯 Edit target profile (min/max per ion)")
_k("wp.opprinnelse", "Opprinnelse: {x}", "Origin: {x}")
_k("wp.type", "Type: {x}", "Type: {x}")
_k("wp.profiltype.house_profile", "Husprofil", "House profile")
_k("wp.profiltype.custom_profile", "Egendefinert profil", "Custom profile")
_k("wp.historisk_profil", "Historisk profil", "Historical profile")
_k("wp.ion_min", "{ion} min (ppm)", "{ion} min (ppm)")
_k("wp.ion_maks", "{ion} maks (ppm)", "{ion} max (ppm)")
_k("wp.ph_min", "Meske-pH min", "Mash pH min")
_k("wp.ph_maks", "Meske-pH maks", "Mash pH max")
_k("wp.lagre_maal", "💾 Lagre målprofil", "💾 Save target profile")
_k("wp.maal_lagret", "Målprofil lagret!", "Target profile saved!")
_k("wp.vannmengder", "**Vannmengder (fra bryggedagsplanen)**", "**Water volumes (from the brew day plan)**")
_k("wp.vannmengder_linje",
   "Meskevann {mesk} L · Skyllevann {skyll} L · Totalt {total} L (samme tall som i Bryggeplan).",
   "Mash water {mesk} L · Sparge water {skyll} L · Total {total} L (same numbers as in Brew plan).")
_k("wp.salter_tittel", "**Foreslåtte salter**", "**Suggested salts**")
_k("wp.salter_forklaring",
   "Saltforslaget justerer klorid og sulfat ut fra kildevann og valgt målprofil (kalsiumklorid + gips). Det tar ikke hensyn til kornregningens innvirkning på meske-pH, så alkalitet/HCO3 kan fortsatt kreve egen vurdering. Kontroller meske-pH på bryggedagen.",
   "The salt suggestion adjusts chloride and sulfate based on the source water and the selected target profile (calcium chloride + gypsum). It does not account for the grain bill's effect on mash pH, so alkalinity/HCO3 may still need separate assessment. Check the mash pH on brew day.")
_k("wp.beregn_forslag", "🧮 Beregn saltforslag", "🧮 Calculate salt suggestion")
_k("wp.forslag_toast", "Saltforslag beregnet — fritt redigerbart under.", "Salt suggestion calculated — freely editable below.")
_k("wp.salt", "Salt", "Salt")
_k("wp.gram_totalt", "Gram (totalt)", "Grams (total)")
_k("wp.renhet", "Renhet (%)", "Purity (%)")
_k("wp.fjern_salt", "Fjern salt", "Remove salt")
_k("wp.legg_til_salt", "➕ Legg til salt manuelt", "➕ Add salt manually")
_k("wp.fordeling_tittel", "**Fordeling mellom meske- og skyllevann**", "**Split between mash and sparge water**")
_k("wp.fordeling.proporsjonal", "Proporsjonalt (etter vannmengde)", "Proportional (by water volume)")
_k("wp.fordeling.alt_i_mesk", "Alt i meskevannet", "All in the mash water")
_k("wp.fordeling.egendefinert", "Egendefinert andel", "Custom share")
_k("wp.fordelingsmetode", "Fordelingsmetode", "Split method")
_k("wp.fordeling_andel", "Andel av hvert salt i meskevannet", "Share of each salt in the mash water")
_k("wp.tabell_salt_header", "| Salt | Totalt | Meskevann | Skyllevann |", "| Salt | Total | Mash water | Sparge water |")
_k("wp.ingen_salter", "Ingen salter lagt til ennå.", "No salts added yet.")
_k("wp.sluttprofil", "**Forventet sluttprofil**", "**Expected final profile**")
_k("wp.mo.full_match", "Målprofilen er fullt oppnådd med de valgte saltene.",
   "The target profile is fully achieved with the selected salts.")
_k("wp.mo.delvis_match",
   "Delvis måloppnåelse — noen ioner er utenfor, men kan justeres ved å endre mengden av de valgte saltene.",
   "Partial target achievement — some ions are outside the range, but can be adjusted by changing the amount of the selected salts.")
_k("wp.mo.uoppnaelig_med_valgte_salter", "Målprofilen kan IKKE nås fullt ut med de valgte saltene alene.",
   "The target profile can NOT be fully reached with the selected salts alone.")
_k("wp.mo.ukjent", "Ingen målprofil valgt — måloppnåelse kan ikke vurderes.",
   "No target profile selected — target achievement cannot be assessed.")
_k("wp.mo.merknad_kan", "kan justeres med et av de valgte saltene", "can be adjusted with one of the selected salts")
_k("wp.mo.merknad_kan_ikke",
   "IKKE oppnåelig med de valgte saltene (krever andre salter, eller kildevannet er allerede utenfor i en retning salter ikke kan rette)",
   "NOT achievable with the selected salts (requires other salts, or the source water is already outside the range in a direction salts cannot correct)")
_k("wp.mo.avvik_linje", "– {ion}: {status} målområdet — {merknad}.", "– {ion}: {status} the target range — {merknad}.")
_k("wp.ionrapport_header", "| Ion | Start | Tilført | Ferdig | Mål | Status |", "| Ion | Start | Added | Final | Target | Status |")
_k("wp.klorid", "Klorid (Cl)", "Chloride (Cl)")
_k("wp.sulfat", "Sulfat (SO4)", "Sulfate (SO4)")
_k("wp.forhold", "Cl:SO4-forhold ≈ {x}", "Cl:SO4 ratio ≈ {x}")
_k("wp.forhold_ukjent", "Cl:SO4-forhold: —", "Cl:SO4 ratio: —")
_k("wp.forhold_note", " — kun en referanse, ikke det eneste kvalitetsmålet. Se de absolutte ionnivåene over.",
   " — only a reference, not the only quality measure. See the absolute ion levels above.")
_k("wp.varsler_tittel", "**Varsler**", "**Warnings**")
_k("wp.ingen_varsler", "Ingen varsler.", "No warnings.")
_k("wp.syrer_tittel", "**Syrer**", "**Acids**")
_k("wp.syre", "Syre", "Acid")
_k("wp.konsentrasjon", "Konsentrasjon (%)", "Concentration (%)")
_k("wp.konsentrasjon_hjelp", "0 = ikke angitt.", "0 = not specified.")
_k("wp.mengde_ml", "Mengde (mL)", "Amount (mL)")
_k("wp.fjern_syre", "🗑️ Fjern syre", "🗑️ Remove acid")
_k("wp.legg_til_syre", "➕ Legg til syre", "➕ Add acid")
_k("wp.meske_ph_tittel", "**Meske-pH**", "**Mash pH**")
_k("wp.onsket_ph", "🎯 Ønsket meske-pH: **{x}**", "🎯 Desired mash pH: **{x}**")
_k("wp.maalt_ph", "Faktisk målt meske-pH", "Actual measured mash pH")
_k("wp.maalt_ph_hjelp", "0.00 = ikke målt ennå.", "0.00 = not measured yet.")
_k("wp.maaletid", "Måletidspunkt (min etter innmesk)", "Time of measurement (min after dough-in)")
_k("wp.maaletid_hjelp", "Standard: 10–15 minutter etter innmesk.", "Standard: 10–15 minutes after dough-in.")
_k("wp.romtemp", "Prøven avkjølt til romtemperatur før måling", "Sample cooled to room temperature before measuring")
_k("wp.kilde_ph_advarsel",
   "Vannets kildepH brukes ALDRI alene til å forutsi meske-pH — dette feltet registrerer kun en faktisk, egen måling.",
   "The water's source pH is NEVER used alone to predict mash pH — this field only records an actual measurement of your own.")
_k("wp.utstyr_tittel", "🧰 Utstyr og måling (sjekkliste)", "🧰 Equipment and measuring (checklist)")
_k("wp.utstyr.0", "pH-meter kalibrert med pH 4,01 og 7,00 bufferløsning",
   "pH meter calibrated with pH 4.01 and 7.00 buffer solutions")
_k("wp.utstyr.1", "Oppbevaringsvæske til elektroden", "Storage solution for the electrode")
_k("wp.utstyr.2", "Vekt med minst 0,1 g oppløsning — helst 0,01 g for små tilsetninger",
   "Scale with at least 0.1 g resolution — preferably 0.01 g for small additions")
_k("wp.utstyr.3", "Rent prøveglass", "Clean sample glass")
_k("wp.utstyr.4", "Avkjøl pH-prøven til måletemperatur før avlesning",
   "Cool the pH sample to measuring temperature before reading")
_k("wp.utstyr_info", "Informasjonstekst, ikke produktanbefaling.", "Informational text, not a product recommendation.")

# ── Medfølgende målprofiler (data/water_targets.json) — kun VISNING ──────────
# Norsk tekst her er ORD FOR ORD den medfølgende profilteksten. Oversettelsen
# brukes bare når den lagrede teksten er identisk med den (se
# water_chemistry.maalprofil_tekst) — en omdøpt/redigert profil vises alltid
# uendret.
_k('wc.maal.kvernhaug_maltpreget_tysk_lager.name',
   'Maltpreget tysk lager',
   'Malt-forward German lager')
_k('wc.maal.kvernhaug_maltpreget_tysk_lager.description',
   'Kvernhaug-bryggeprofil for maltpregede tyske/østerrikske lagerstiler — IKKE en påstått historisk München-vannprofil. Historisk Wiesn-Märzen, Märzen, Festbier, Vienna Lager, Dunkel og Bock kan anbefales denne profilen, men brukeren må alltid bekrefte valget selv.',
   'Kvernhaug brewing profile for malt-forward German/Austrian lager styles — NOT a claimed historical Munich water profile. Historisk Wiesn-Märzen, Märzen, Festbier, Vienna Lager, Dunkel and Bock may be recommended this profile, but the user must always confirm the choice themselves.')
_k('wc.maal.kvernhaug_maltpreget_tysk_lager.kort_hjelpetekst',
   'Kvernhaug-husprofil laget for maltpregede tyske lagerøl.',
   'Kvernhaug house profile made for malt-forward German lagers.')
_k('wc.maal.lys_lager_pils.name',
   'Lys lager og pils',
   'Pale lager and pils')
_k('wc.maal.lys_lager_pils.description',
   'Kvernhaug-bryggeprofil for lyse, sarte lagerstiler — mykt vann med lav alkalitet, slik at det blekeste maltet ikke må kjempe mot høy resterende alkalitet for å nå riktig meske-pH. IKKE en påstått historisk vannprofil for noe spesifikt bryggested.',
   'Kvernhaug brewing profile for pale, delicate lager styles — soft water with low alkalinity, so the palest malt does not have to fight high residual alkalinity to reach the right mash pH. NOT a claimed historical water profile for any specific brewing location.')
_k('wc.maal.lys_lager_pils.kort_hjelpetekst',
   'Kvernhaug-husprofil laget for lyse, sarte lagerstiler.',
   'Kvernhaug house profile made for pale, delicate lager styles.')
_k('wc.maal.balansert_ale.name',
   'Balansert ale',
   'Balanced ale')
_k('wc.maal.balansert_ale.description',
   'Kvernhaug-bryggeprofil som nøytralt utgangspunkt for de fleste ale-stiler — moderate ionnivåer uten sterk vekting mot klorid eller sulfat. Brukes som fallback av anbefalingsmotoren når ingen mer spesifikk profil matcher stilen.',
   'Kvernhaug brewing profile as a neutral starting point for most ale styles — moderate ion levels without a strong weighting towards chloride or sulfate. Used as the fallback by the recommendation engine when no more specific profile matches the style.')
_k('wc.maal.balansert_ale.kort_hjelpetekst',
   'Kvernhaug-husprofil — nøytralt utgangspunkt for de fleste ale-stiler.',
   'Kvernhaug house profile — a neutral starting point for most ale styles.')
_k('wc.maal.mork_maltol_porter_stout.name',
   'Mørk maltøl – porter/stout',
   'Dark beer — porter/stout')
_k('wc.maal.mork_maltol_porter_stout.description',
   'Kvernhaug-bryggeprofil for mørke, ristede ølstiler. Ristet malt er naturlig surt og senker meske-pH på egen hånd — denne profilen har derfor bevisst høyere resterende alkalitet (HCO3) enn de lysere profilene, for å motvirke det og unngå en for lav meske-pH. Kloridtung, moderat/lav sulfat for en rund, ikke skarp bitterhet.',
   'Kvernhaug brewing profile for dark, roasted beer styles. Roasted malt is naturally acidic and lowers mash pH on its own — this profile therefore deliberately has higher residual alkalinity (HCO3) than the paler profiles, to counteract that and avoid a too-low mash pH. Chloride-heavy, moderate/low sulfate for a round, not sharp bitterness.')
_k('wc.maal.mork_maltol_porter_stout.kort_hjelpetekst',
   'Kvernhaug-husprofil laget for mørke, ristede ølstiler.',
   'Kvernhaug house profile made for dark, roasted beer styles.')
_k('wc.maal.humledrevet_ol.name',
   'Humledrevet øl',
   'Hop-forward beer')
_k('wc.maal.humledrevet_ol.description',
   'Kvernhaug-bryggeprofil for humlepregede stiler — høy sulfat for å fremheve en skarp, tørr bitterhet, lav klorid og lav alkalitet for et rent, sprøtt uttrykk. Høyere kalsium støtter god gjærhelse/utfelling i sterkere, humlerike brygg.',
   'Kvernhaug brewing profile for hop-forward styles — high sulfate to emphasise a sharp, dry bitterness, low chloride and low alkalinity for a clean, crisp expression. Higher calcium supports good yeast health/precipitation in stronger, hop-rich brews.')
_k('wc.maal.humledrevet_ol.kort_hjelpetekst',
   'Kvernhaug-husprofil laget for humlepregede stiler.',
   'Kvernhaug house profile made for hop-forward styles.')
_k('wc.maal.egendefinert.name',
   'Egendefinert målprofil',
   'Custom target profile')
_k('wc.maal.egendefinert.description',
   'Fritt redigerbar målprofil — start med disse grensene eller endre dem fritt. Anbefales aldri automatisk for noen stil, og overskrives aldri av appen; dine egne grenser bevares uendret helt til du selv redigerer og lagrer på nytt.',
   'Freely editable target profile — start with these limits or change them freely. Never recommended automatically for any style, and never overwritten by the app; your own limits are preserved unchanged until you edit and save again.')
_k('wc.maal.egendefinert.kort_hjelpetekst',
   'Fritt redigerbar profil — sett dine egne grenser og notér gjerne kilden selv.',
   'Freely editable profile — set your own limits and preferably note the source yourself.')
_k('wc.maal.egendefinert.origin',
   'Egendefinert',
   'Custom')


BRYGGEDAG_TEKSTER = {
    "no": {k: v[0] for k, v in _K.items()},
    "en": {k: v[1] for k, v in _K.items()},
}
