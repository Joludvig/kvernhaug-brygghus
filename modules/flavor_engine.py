# modules/flavor_engine.py
import plotly.graph_objects as go

def generer_smakshjul(valgt_malt_liste, flatt_malt_bibliotek, valgt_humle_liste, humle_data, total_ibu, valgt_gjaer, gjaer_data):
    """
    Normaliserer og samler smakspoeng for de 18 utvidede kategoriene,
    og tegner et skuddsikkert Plotly Radardiagram uten uendelige løkker.
    """
    # 1. Definer alle de 18 utvidede kategoriene fra din nye kravspesifikasjon
    smaks_kategorier = [
        "Maltfylde", "Brød", "Toast", "Karamell", "Honning", "Nøtter", 
        "Sjokolade", "Kaffe", "Røyk", "Bitterhet", "Furunål", "Jordlig", 
        "Krydder", "Sitrus", "Tropisk", "Fruktighet", "Steinfrukt", "Vinøs"
    ]
    
    # Start alle smakspoeng på 0
    poeng = {kat: 0.0 for kat in smaks_kategorier}
    
    # --- MALT-NORMALISERING (Prioritet 2) ---
    total_malt_vekt = sum(m["mengde"] for m in valgt_malt_liste if m["navn"] in flatt_malt_bibliotek)
    
    if total_malt_vekt > 0:
        for m in valgt_malt_liste:
            navn = m["navn"]
            mengde = m["mengde"]
            if navn in flatt_malt_bibliotek and mengde > 0:
                # Finn hvor stor PROSENTANDEL denne malten utgjør av hele mesken
                prosentandel = mengde / total_malt_vekt
                kat_data = flatt_malt_bibliotek[navn].get("kategorier", {})
                
                for kat, verdi in kat_data.items():
                    if kat in poeng:
                        # Smaken vektes ut fra prosentandel, ikke rå kilo! 
                        # Vi ganger med 1.2 for å få en fin visuell skala (0-10) på grafen
                        poeng[kat] += verdi * prosentandel * 1.2

    # --- HUMLE-NORMALISERING (Prioritet 2) ---
    total_humle_gram = sum(h["gram"] for h in valgt_humle_liste if h["navn"] in humle_data)
    
    if total_humle_gram > 0:
        for h in valgt_humle_liste:
            navn = h["navn"]
            gram = h["gram"]
            tid = h["tid"]
            if navn in humle_data and gram > 0:
                # Prosentandel av den totale humlemengden
                humle_prosent = gram / total_humle_gram
                h_kat = humle_data[navn].get("kategorier", {})
                
                # Aroma forsvinner ved koking, sene tilsetninger gir mer smak
                aroma_faktor = 1.0 if tid <= 5 else (0.5 if tid <= 15 else 0.1)
                
                for kat, verdi in h_kat.items():
                    if kat in poeng and kat != "Bitterhet":
                        # Normalisert humlesmak
                        poeng[kat] += (verdi * humle_prosent * 1.5) * aroma_faktor

    # --- GJÆRBIDRAG ---
    if valgt_gjaer in gjaer_data:
        g_kat = gjaer_data[valgt_gjaer].get("kategorier", {})
        for kat, verdi in g_kat.items():
            if kat in poeng:
                poeng[kat] += verdi

    # --- BITTERHET-AKSE (Normalisert ut fra reell IBU) ---
    poeng["Bitterhet"] = min(total_ibu / 8.0, 10.0)

    # Sikre at ingen smaker blir negative, og maks begrenses til 10 på skalaen
    for kat in poeng:
        poeng[kat] = max(0.0, min(poeng[kat], 10.0))

    # --- 2. LUKK SIRKELEN UTEN REKURSJONSBREMS! (Prioritet 1 Fix) ---
    verdier = [poeng[kat] for kat in smaks_kategorier]
    verdier.append(verdier[0]) # Legger til KUN DET FØRSTE TALLET, ikke hele listen!
    kategorier_lukket = smaks_kategorier + [smaks_kategorier[0]]

    # 3. Bygg Plotly-grafen med fast akseskala (Fix) og brygghusstil
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=verdier,
        theta=kategorier_lukket,
        fill='toself',
        fillcolor='rgba(211, 134, 61, 0.25)', 
        line=dict(color='rgb(184, 115, 51)', width=2.5)
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10], # FIKSET: Plotly krasjer ikke lenger pga. tomme klammer!
                showticklabels=False,
                gridcolor="rgba(255, 255, 255, 0.08)"
            ),
            angularaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.08)",
                tickfont=dict(size=11, color="#dddddd")
            ),
            bgcolor="rgba(0,0,0,0)"
        ),
        showlegend=False,
        margin=dict(l=50, r=50, t=20, b=20),
        height=400
    )
    
    return fig, poeng
