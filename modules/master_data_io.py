# modules/master_data_io.py
"""
Delt, herdet lese-/skrivehjelper for masterdatabasene (master_malt.json,
master_humle_v2.json, master_gjaer_v2.json) -- brukt av
modules/store_matcher.py (skanning/matching mot butikkdata) og
ui/review_panel.py (manuell review-godkjenning). Dette er de eneste to
stedene i appen som skriver til masterdata.

All skriving går via skriv_master_json_atomisk(): atomisk (midlertidig
fil + os.replace, aldri en direkte overskriving som kan etterlate en
halvskrevet/korrupt masterfil ved et krasj midtveis) og med en
automatisk, tidsstemplet backup av forrige versjon FØR den overskrives --
samme mønster som modules/pantry.py::lagre_pantry() og
modules/recipe_storage.py::lagre_oppskrift(). Backupfilene
(<fil>.backup_<tidsstempel>) ligger i SAMME mappe som originalen (data/)
og er gitignoret (se .gitignore: "data/*.json.backup_*") -- masterfilene
selv er versjonskontrollerte, så git-historikk er allerede det primære
sikkerhetsnettet; disse lokale backupene dekker uncommittede endringer
gjort via appens Import/Review-UI mellom to commits.
"""
import json
import os
import shutil
import uuid
from datetime import datetime

# Antall backupfiler som beholdes PER masterfil (se
# backup_master_fil()/_rydd_gamle_backupfiler()). Samme terskel som
# modules/pantry.py::PANTRY_BACKUP_MAKS_ANTALL og
# modules/recipe_storage.py::RECIPE_BACKUP_MAKS_ANTALL.
MASTER_BACKUP_MAKS_ANTALL = 20


def _tidsstempel_suffiks():
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_" + uuid.uuid4().hex[:6]


def _rydd_gamle_backupfiler(filsti, maks_antall=MASTER_BACKUP_MAKS_ANTALL):
    if not maks_antall or maks_antall <= 0:
        return
    mappe = os.path.dirname(filsti) or "."
    if not os.path.isdir(mappe):
        return
    prefiks = f"{os.path.basename(filsti)}.backup_"
    stier = sorted(
        os.path.join(mappe, f) for f in os.listdir(mappe) if f.startswith(prefiks)
    )
    for gammel_sti in stier[:-maks_antall]:
        try:
            os.remove(gammel_sti)
        except OSError:
            pass  # en mislykket opprydding er ikke kritisk -- filen er lagret uansett


def backup_master_fil(filsti):
    """Kopierer en eksisterende masterdatafil til en tidsstemplet
    `<filsti>.backup_<tidsstempel>`-fil i samme mappe, FØR den
    overskrives. No-op (returnerer None) hvis filen ikke finnes ennå --
    ingenting å miste ved en aller første skriving."""
    if not os.path.exists(filsti):
        return None
    mal = f"{filsti}.backup_{_tidsstempel_suffiks()}"
    shutil.copy2(filsti, mal)
    _rydd_gamle_backupfiler(filsti)
    return mal


def les_master_json(filsti):
    with open(filsti, "r", encoding="utf-8") as f:
        return json.load(f)


def skriv_master_json_atomisk(filsti, data):
    """Tar automatisk en backup av en eksisterende fil (se
    backup_master_fil), og skriver deretter NY data atomisk: midlertidig
    fil + os.replace (atomisk på både Windows og POSIX)."""
    if os.path.exists(filsti):
        backup_master_fil(filsti)
    tmp_sti = filsti + f".tmp_{uuid.uuid4().hex[:8]}"
    with open(tmp_sti, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_sti, filsti)
