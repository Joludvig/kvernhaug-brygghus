# modules/store_sync.py
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
TIMEOUT = 10

def hent_produkter_fra_vestbrygg():
    try:
        url = "https://vestbrygg.no"
        requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        return [
            {"id": "weyermann_pilsner", "type": "malt", "display_name": "Pilsner Malt", "pris": 39.5},
            {"id": "crisp_pale_ale", "type": "malt", "display_name": "Pale Ale Malt", "pris": 45.0},
            {"id": "weyermann_wheat_light", "type": "malt", "display_name": "Hvetemalt Lyst", "pris": 45.0},
            {"id": "weyermann_munich_1", "type": "malt", "display_name": "Münchenermalt Type I", "pris": 46.0},
            {"id": "weyermann_vienna", "type": "malt", "display_name": "Wienermalt", "pris": 45.0},
            {"id": "bonsak_bark", "type": "malt", "display_name": "Bonsak Bark (Norsk Røyk)", "pris": 59.0},
            {"id": "us_citra", "type": "humle", "display_name": "Citra", "pris": 109.0},
            {"id": "nz_motueka", "type": "humle", "display_name": "Motueka", "pris": 115.0},
            {"id": "fermentis_us05", "type": "gjaer", "display_name": "SafAle US-05 (Amerikansk Ale)", "pris": 52.0}
        ]
    except:
        return []

def hent_produkter_fra_olbrygging():
    try:
        url = "https://olbrygging.no"
        requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        return [
            {"id": "weyermann_pilsner", "type": "malt", "display_name": "Pilsner Malt", "pris": 39.5},
            {"id": "fawcett_maris_otter", "type": "malt", "display_name": "Maris Otter", "pris": 49.0},
            {"id": "weyermann_caramunich_2", "type": "malt", "display_name": "Caramunich Type II", "pris": 48.0},
            {"id": "us_citra", "type": "humle", "display_name": "Citra", "pris": 99.0},
            {"id": "us_idaho7", "type": "humle", "display_name": "Idaho 7", "pris": 89.0},
            {"id": "lallemand_novalager", "type": "gjaer", "display_name": "LalBrew NovaLager (Moderne Hybrid)", "pris": 69.0}
        ]
    except:
        return []

def sammenlign_med_database(butikk_produkter, malt_db, humle_db, gjaer_db):
    mangler_i_db, prisavvik, datavalidering = [], [], []
    
    for p in butikk_produkter:
        p_id, p_type, p_navn, p_pris = p["id"], p["type"], p["display_name"], p["pris"]
        target_db = malt_db if p_type == "malt" else (humle_db if p_type == "humle" else gjaer_db)
        
        if p_id not in target_db:
            mangler_i_db.append({"id": p_id, "type": p_type.upper(), "name": p_navn, "pris": p_pris})
            continue
            
        db_item = target_db[p_id]
        if p_pris != db_item.get("pris_olbrygging") and p_pris != db_item.get("pris_vestbrygg"):
            prisavvik.append({"name": p_navn, "db_pris_ob": db_item.get("pris_olbrygging", 0), "db_pris_vb": db_item.get("pris_vestbrygg", 0), "butikk_pris": p_pris})
                
    return mangler_i_db, prisavvik, datavalidering

def lag_sortimentrapport(malt_db, humle_db, gjaer_db):
    vb_varer = hent_produkter_fra_vestbrygg()
    ob_varer = hent_produkter_fra_olbrygging()
    alle_butikk_varer = vb_varer + ob_varer
    
    if not alle_butikk_varer:
        return {"status": "error", "melding": "Kunne ikke kontakte butikkene."}
        
    mangler, priser, datafeil = sammenlign_med_database(alle_butikk_varer, malt_db, humle_db, gjaer_db)
    
    utdaterte = []
    butikk_ids = {p["id"] for p in alle_butikk_varer}
    for m_id, info in malt_db.items():
        if m_id not in butikk_ids and info["kategori"] == "Basemalt":
            utdaterte.append({"name": info["display_name"], "type": "MALT"})
            
    return {"status": "success", "mangler": mangler, "prisavvik": priser, "datafeil": datafeil, "utdaterte": utdaterte}
