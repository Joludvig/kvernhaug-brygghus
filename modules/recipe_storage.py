# modules/recipe_storage.py
import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from config import DEMO_MODE

_log = logging.getLogger(__name__)

_ARCHIVE_UNDERMAPPE = "_archive"
_BACKUP_UNDERMAPPE = "_backup"

# Standard antall backupfiler som beholdes PER kildefil (se
# _backup_eksisterende_fil()/_rydd_gamle_recipe_backupfiler()). Samme
# mønster/terskel som modules/pantry.py::PANTRY_BACKUP_MAKS_ANTALL.
RECIPE_BACKUP_MAKS_ANTALL = 20


class OppskriftNavnKollisjon(Exception):
    """Reist når en lagring ville overskrevet en ANNEN eksisterende
    oppskrift stille -- samme genererte filnavn, men en annen kildefil
    (eller ingen kjent kildefil i det hele tatt, som ved «Lagre som ny
    kopi»). Kallestedet (ui/recipe_card.py) fanger denne og viser en
    tydelig feilmelding i stedet for å overskrive."""
    pass


class UgyldigKildefilnavn(Exception):
    """Reist når et oppgitt kildefilnavn ikke er et trygt, rent filnavn
    som ligger DIREKTE i den aktive oppskriftsmappen -- f.eks. et
    path-traversal-forsøk ("../pantry.json"), en absolutt sti, eller en
    sti inn i en undermappe. Kallestedet (ui/recipe_card.py) fanger denne
    og viser en tydelig feilmelding i stedet for å arkivere feil fil."""
    pass


class LoggKorruptError(Exception):
    """Reist når en brygglogg-fil FINNES men ikke er gyldig JSON. Filen
    røres ALDRI når dette oppstår -- verken lest som tom liste og siden
    stille overskrevet (som ville erstattet HELE historikken med kun én
    ny oppføring ved neste lagre_logg_entry()-kall) eller reparert
    automatisk. Samme etablerte mønster som
    modules/pantry.py::PantryCorruptError/last_pantry(). Kallestedet
    (ui/recipe_card.py) fanger dette og viser en tydelig feil i UI-et,
    med henvisning til recipes/_backup/ for manuell gjenoppretting."""
    pass


def _mappe():
    """Aktiv oppskriftsmappe — lest FRISKT ved hvert kall, aldri frosset
    ved modul-import.

    KVERNHAUG_RECIPES_DIR finnes KUN for testisolasjon. En tidligere
    variant leste miljøvariabelen inn i en modulnivå-konstant (`MAPPE =
    os.getenv(...)`) — det virker bare hvis testen setter miljøvariabelen
    FØR modulen importeres FØRSTE gang i hele prosessen. Siden andre
    testmoduler (f.eks. tests/test_process_profiles.py) importerer denne
    modulen ved modul-nivå, kan den ha blitt importert (og MAPPE dermed
    frosset til "recipes") lenge før en senere test rakk å sette
    miljøvariabelen — med det resultat at "isolerte" ende-til-ende-tester
    stille skrev ekte testoppskrifter til den virkelige recipes/-mappen.
    Løsningen er å ALDRI fryse verdien — les os.environ på nytt hver
    gang funksjonene under faktisk trenger stien."""
    return os.getenv("KVERNHAUG_RECIPES_DIR", "recipes")


def sikre_mappe():
    """Sørger for at recipes-mappen eksisterer på harddisken."""
    if not os.path.exists(_mappe()):
        os.makedirs(_mappe())


def _archive_mappe():
    return os.path.join(_mappe(), _ARCHIVE_UNDERMAPPE)


def _backup_mappe():
    return os.path.join(_mappe(), _BACKUP_UNDERMAPPE)


def _sikre_undermappe(sti):
    if not os.path.exists(sti):
        os.makedirs(sti)


def _tidsstempel_suffiks():
    # Mikrosekund-presisjon + kort tilfeldig hex-suffiks (samme mønster
    # som modules/pantry.py::lag_pantry_backup) -- garanterer unike
    # filnavn selv ved flere raske, påfølgende kall.
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_" + uuid.uuid4().hex[:6]


def _unik_arkivsti(arkiv_mappe, filnavn):
    """Returnerer en garantert ledig sti i arkivmappen — legger til et
    tidsstempel-suffiks hvis filnavnet allerede finnes der fra en
    tidligere arkivering (f.eks. samme oppskrift omdøpt eller slettet
    flere ganger over tid)."""
    kandidat = os.path.join(arkiv_mappe, filnavn)
    if not os.path.exists(kandidat):
        return kandidat
    navn, ext = os.path.splitext(filnavn)
    return os.path.join(arkiv_mappe, f"{navn}.{_tidsstempel_suffiks()}{ext}")


def _skriv_json_atomisk(filsti, data):
    """Skriver JSON til en midlertidig fil og erstatter deretter
    målfilen med os.replace (atomisk på både Windows og POSIX), slik at
    et krasj midtveis i skrivingen aldri kan etterlate en halvskrevet
    eller korrupt oppskrift-/loggfil. Samme mønster som
    modules/pantry.py::lagre_pantry().

    Feiler enten selve serialiseringen (f.eks. et ikke-JSON-serialiserbart
    felt i `data`) eller selve os.replace()-kallet, ryddes den
    midlertidige filen bort før unntaket kastes videre uendret -- en
    mislykket lagring skal ALDRI etterlate en lekket .tmp_*-fil i
    oppskriftsmappen."""
    tmp_sti = filsti + f".tmp_{uuid.uuid4().hex[:8]}"
    try:
        with open(tmp_sti, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_sti, filsti)
    except Exception:
        try:
            os.remove(tmp_sti)
        except OSError:
            pass
        raise


def _backup_eksisterende_fil(filsti):
    """Kopierer en eksisterende oppskriftsfil til recipes/_backup/ FØR den
    overskrives. No-op hvis filen ikke finnes ennå (første lagring —
    ingenting å miste). Beholder kun de RECIPE_BACKUP_MAKS_ANTALL nyeste
    backupene PER kildefilnavn."""
    if not os.path.exists(filsti):
        return None
    backup_mappe = _backup_mappe()
    _sikre_undermappe(backup_mappe)
    filnavn = os.path.basename(filsti)
    mal = os.path.join(backup_mappe, f"{filnavn}.backup_{_tidsstempel_suffiks()}")
    shutil.copy2(filsti, mal)
    _rydd_gamle_recipe_backupfiler(filnavn)
    return mal


def _rydd_gamle_recipe_backupfiler(filnavn, maks_antall=RECIPE_BACKUP_MAKS_ANTALL):
    if not maks_antall or maks_antall <= 0:
        return
    backup_mappe = _backup_mappe()
    if not os.path.isdir(backup_mappe):
        return
    prefiks = f"{filnavn}.backup_"
    stier = sorted(
        os.path.join(backup_mappe, f) for f in os.listdir(backup_mappe) if f.startswith(prefiks)
    )
    for gammel_sti in stier[:-maks_antall]:
        try:
            os.remove(gammel_sti)
        except OSError:
            pass  # en mislykket opprydding er ikke kritisk -- filen er lagret uansett


def _arkiver_fil(kilde_sti):
    """Flytter en fil til recipes/_archive/ (aldri permanent sletting).
    No-op hvis filen ikke finnes."""
    if not os.path.exists(kilde_sti):
        return None
    arkiv_mappe = _archive_mappe()
    _sikre_undermappe(arkiv_mappe)
    maal_sti = _unik_arkivsti(arkiv_mappe, os.path.basename(kilde_sti))
    shutil.move(kilde_sti, maal_sti)
    return maal_sti


def _arkiver_kildefil_etter_omdoeping(gammelt_filnavn, nytt_filnavn):
    """Kalles ETTER at den nye oppskriftsfilen allerede er skrevet: flytter
    den gamle kildefilen til recipes/_archive/ og migrerer en eventuell
    tilhørende _logg.json til det NYE filnavnet, slik at bryggeloggen
    følger oppskriften videre under det nye navnet i stedet for å bli
    stående igjen, orphan, under det gamle."""
    mappe = _mappe()
    gammel_sti = os.path.join(mappe, gammelt_filnavn)
    _arkiver_fil(gammel_sti)

    gammel_logg = os.path.join(mappe, gammelt_filnavn.replace(".json", "_logg.json"))
    ny_logg = os.path.join(mappe, nytt_filnavn.replace(".json", "_logg.json"))
    if os.path.exists(gammel_logg):
        if os.path.exists(ny_logg):
            # Målet har (uvanlig nok) allerede sin egen logg -- arkiver
            # den gamle loggen i stedet for å overskrive en annen
            # oppskrifts historikk stille.
            _arkiver_fil(gammel_logg)
        else:
            shutil.move(gammel_logg, ny_logg)


def _valider_kildefilnavn(kilde_filnavn):
    """Validerer at `kilde_filnavn` er et RENT filnavn -- ingen
    mappekomponenter, ingen ".."-traversal, ingen absolutt sti -- som
    ligger DIREKTE i den aktive oppskriftsmappen. Reiser
    UgyldigKildefilnavn ved ethvert brudd. Returnerer den fulle,
    validerte filstien.

    `os.path.basename(kilde_filnavn) != kilde_filnavn` fanger i praksis
    alle traversal-varianter i ett steg: en sti med "/" eller "\\" i seg
    (uansett OS), en "../"-prefiks, eller en absolutt sti får ALLTID et
    kortere resultat fra basename() enn originalen. Det andre steget
    (normalisert absoluttbane må ha oppskriftsmappen som DIREKTE
    foreldre) er et uavhengig sikkerhetsnett i tillegg, ikke en
    erstatning for det første."""
    if not kilde_filnavn or not isinstance(kilde_filnavn, str):
        raise UgyldigKildefilnavn(f"Mangler eller ugyldig kildefilnavn: {kilde_filnavn!r}")
    if kilde_filnavn in (".", ".."):
        raise UgyldigKildefilnavn(f"Ugyldig kildefilnavn: {kilde_filnavn!r}")
    if os.path.basename(kilde_filnavn) != kilde_filnavn:
        raise UgyldigKildefilnavn(
            f"Kildefilnavnet må være et rent filnavn uten mappekomponenter: {kilde_filnavn!r}"
        )
    if not kilde_filnavn.endswith(".json"):
        raise UgyldigKildefilnavn(f"Kildefilnavnet må ende på .json: {kilde_filnavn!r}")

    mappe = os.path.abspath(_mappe())
    kandidat_sti = os.path.abspath(os.path.join(mappe, kilde_filnavn))
    if os.path.dirname(kandidat_sti) != mappe:
        raise UgyldigKildefilnavn(
            f"Kildefilnavnet peker utenfor den aktive oppskriftsmappen: {kilde_filnavn!r}"
        )
    return kandidat_sti


_TRANSLITERATION = {
    ord('æ'): 'ae', ord('Æ'): 'Ae',
    ord('ø'): 'o',  ord('Ø'): 'O',
    ord('å'): 'a',  ord('Å'): 'A',
    ord('ð'): 'd',  ord('Ð'): 'D',
}

def generer_filnavn(oppskrift_navn):
    """Lager et trygt, standardisert filnavn basert på oppskriftens navn."""
    translittert = oppskrift_navn.translate(_TRANSLITERATION)
    trygg_tittel = "".join([c for c in translittert if c.isalnum() or c in (" ", "_", "-")]).rstrip()
    trygg_tittel = trygg_tittel.replace(" ", "_").lower()
    return f"{trygg_tittel}.json"

def lagre_oppskrift(recipe, kilde_filnavn=None, bloker_ved_navnekollisjon=False):
    """Lagrer eller oppdaterer et Recipe Object som en JSON-fil.

    Atomisk (midlertidig fil + os.replace, se _skriv_json_atomisk) og tar
    automatisk en tidsstemplet backup av en eksisterende fil rett før den
    overskrives (se _backup_eksisterende_fil).

    `kilde_filnavn` er filnavnet oppskriften FAKTISK ble lastet fra (se
    ui/sidebar.py sin `_last_loaded_recipe_file`) -- ikke bare navnet slik
    det står nå. `None` betyr "ingen kjent tidligere kildefil" -- enten en
    helt ny oppskrift, eller et direkte kall utenfor UI-et (f.eks. en
    test/et skript) som bare vil opprette-eller-oppdatere ved navn, uten
    at det er en bevisst "lagre som ny kopi"-handling.

    Oppførsel:
      - Uendret navn (nytt filnavn == kilde_filnavn): vanlig
        stedfortredende oppdatering av samme fil.
      - Endret navn (nytt filnavn != kilde_filnavn, og kilde_filnavn ikke
        er None, dvs. en omdøping av en KJENT eksisterende oppskrift):
        skriver den NYE filen først, og arkiverer deretter den gamle
        kildefilen til recipes/_archive/ (aldri permanent sletting) samt
        migrerer en eventuell tilhørende _logg.json til det nye navnet.
        Kolliderer det nye navnet med en ANNEN eksisterende fil, reises
        OppskriftNavnKollisjon uten at noe skrives.
      - `kilde_filnavn=None` og `bloker_ved_navnekollisjon=True` (brukt av
        ui/recipe_card.py sin «Lagre som ny kopi»-knapp): hvis det
        genererte filnavnet allerede finnes på disk, reiser dette
        OppskriftNavnKollisjon i stedet for å overskrive stille -- en ny
        kopi skal ALDRI overskrive en annen eksisterende oppskrift.
        Standard er False, slik at et vanlig, direkte
        lagre_oppskrift(recipe)-kall (uten kjent kildefil-sporing) beholder
        sin opprinnelige opprett-eller-oppdater-ved-navn-oppførsel.

    Returnerer det nye filnavnet (eller None i DEMO_MODE)."""
    if DEMO_MODE:
        return None
    sikre_mappe()
    nytt_filnavn = generer_filnavn(recipe["name"])
    filsti = os.path.join(_mappe(), nytt_filnavn)

    navn_endret = kilde_filnavn is not None and kilde_filnavn != nytt_filnavn
    kollisjon_mot_annen_fil = os.path.exists(filsti) and (
        navn_endret or (kilde_filnavn is None and bloker_ved_navnekollisjon)
    )
    if kollisjon_mot_annen_fil:
        raise OppskriftNavnKollisjon(
            f"En annen oppskrift bruker allerede navnet \"{recipe['name']}\" "
            f"(filen {nytt_filnavn}). Velg et annet navn før lagring."
        )

    if os.path.exists(filsti):
        _backup_eksisterende_fil(filsti)

    _skriv_json_atomisk(filsti, recipe)

    if navn_endret:
        _arkiver_kildefil_etter_omdoeping(kilde_filnavn, nytt_filnavn)

    return nytt_filnavn

def _logg_filsti(oppskrift_navn):
    base = generer_filnavn(oppskrift_navn).replace(".json", "_logg.json")
    return os.path.join(_mappe(), base)

def lagre_logg_entry(oppskrift_navn, entry):
    """Legger til én loggoppføring i oppskriftens loggfil.

    Tar automatisk en tidsstemplet backup av en EKSISTERENDE loggfil rett
    før den overskrives (samme rullerende backup-prinsipp og terskel som
    lagre_oppskrift() bruker for selve oppskriftsfilen -- se
    _backup_eksisterende_fil/RECIPE_BACKUP_MAKS_ANTALL).

    Leser eksisterende logg via hent_logg() FØR den nye oppføringen
    legges til: er loggfilen korrupt, forplanter det seg som
    LoggKorruptError HERFRA, uten at noe skrives -- i stedet for at denne
    ene, nye oppføringen stille erstatter hele den (ellers tapte)
    historikken."""
    if DEMO_MODE:
        return
    sikre_mappe()
    filsti = _logg_filsti(oppskrift_navn)
    logg = hent_logg(oppskrift_navn)
    logg.append(entry)
    if os.path.exists(filsti):
        _backup_eksisterende_fil(filsti)
    _skriv_json_atomisk(filsti, logg)

def hent_logg(oppskrift_navn):
    """Henter alle loggoppføringer for en oppskrift.

    Returnerer tom liste hvis loggfilen ikke finnes ennå -- helt normalt
    for en oppskrift uten registrerte brygg. Kaster LoggKorruptError
    (uten å røre filen) hvis den FINNES men ikke er gyldig JSON -- ALDRI
    stille tom, som tidligere kunne få lagre_logg_entry() til å overskrive
    hele historikken med bare den ene, nye oppføringen. Samme etablerte
    mønster som modules/pantry.py::last_pantry()/PantryCorruptError."""
    filsti = _logg_filsti(oppskrift_navn)
    if not os.path.exists(filsti):
        return []
    with open(filsti, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise LoggKorruptError(
            f"{filsti} inneholder ugyldig JSON og ble IKKE overskrevet ({e}). "
            f"Rett filen manuelt, eller gjenopprett fra en backup i {_backup_mappe()}, "
            "før nye loggoppføringer kan lagres."
        ) from e


def _skann_oppskriftsfiler(mappe):
    """Leser og parser alle oppskriftsfiler (unntatt _logg.json) direkte i
    en gitt mappe (aldri undermapper som _archive/_backup — os.listdir()
    er ikke rekursiv). Returnerer en liste av (filnavn, data)-par for
    filer som lot seg lese OG som har et "name"-felt; korrupte/ufullstendige
    filer logges og hoppes over. Delt lesehjelper for
    hent_alle_oppskrifter(), hent_oppskrift_filnavn_kart() og
    finn_duplikate_oppskrift_navn() — én skanning å holde konsistent."""
    filer = [f for f in os.listdir(mappe) if f.endswith(".json") and not f.endswith("_logg.json")]
    resultat = []
    for f in filer:
        filsti = os.path.join(mappe, f)
        try:
            with open(filsti, "r", encoding="utf-8") as file_content:
                data = json.load(file_content)
            if "name" not in data:
                raise KeyError("name")
            resultat.append((f, data))
        except (json.JSONDecodeError, OSError, KeyError) as e:
            _log.warning("Kunne ikke lese oppskriftsfil %s: %s", f, e)
    return resultat


def hent_alle_oppskrifter(mappe=None):
    """Henter alle lagrede oppskrifter fra harddisken og returnerer et kart.

    `mappe=None` (standard) betyr "den aktive oppskriftsmappen" — løst
    friskt via _mappe() ved KALLET, ikke ved funksjonsdefinisjonen (Python
    evaluerer default-argumentverdier ÉN gang, ved modul-import — akkurat
    samme felle som den gamle MAPPE-konstanten).

    MERK (kjent, lav prioritet teknisk gjeld): to filer med samme "name"
    kollapses stille til én her, siden navnet brukes som nøkkel. Bruk
    finn_duplikate_oppskrift_navn() for å oppdage og varsle om en slik
    kollisjon før den skjer."""
    if mappe is None:
        mappe = _mappe()
        sikre_mappe()
    elif not os.path.exists(mappe):
        return {}
    return {data["name"]: data for _, data in _skann_oppskriftsfiler(mappe)}


def hent_oppskrift_filnavn_kart(mappe=None):
    """Kart fra oppskriftsnavn -> faktisk filnavn på disk (den EKTE
    kildefilen, ikke et navn gjettet/regenerert fra teksten i "name").
    Brukes av ui/sidebar.py til å huske hvilken fil en lastet oppskrift
    faktisk kom fra, slik at lagre_oppskrift(..., kilde_filnavn=...) vet
    nøyaktig hvilken fil som ev. skal arkiveres ved en omdøping."""
    if mappe is None:
        mappe = _mappe()
        sikre_mappe()
    elif not os.path.exists(mappe):
        return {}
    return {data["name"]: f for f, data in _skann_oppskriftsfiler(mappe)}


def finn_duplikate_oppskrift_navn(mappe=None):
    """Skanner den aktive oppskriftsmappen og returnerer en liste over
    duplikate "name"-verdier på tvers av filer:
    [{"navn": ..., "filer": [...]}, ...]. Skriver og endrer ingenting —
    ren deteksjon til bruk i et UI-varsel (se ui/sidebar.py), siden
    hent_alle_oppskrifter() ellers ville kollapset dem stille til én
    oppføring (se docs/PROJECT_STATUS_JULI_2026.md, kjent teknisk gjeld)."""
    if mappe is None:
        mappe = _mappe()
        if not os.path.exists(mappe):
            return []
    elif not os.path.exists(mappe):
        return []
    navn_til_filer = {}
    for f, data in _skann_oppskriftsfiler(mappe):
        navn_til_filer.setdefault(data["name"], []).append(f)
    return [
        {"navn": navn, "filer": sorted(flist)}
        for navn, flist in navn_til_filer.items()
        if len(flist) > 1
    ]

def slett_oppskrift_fil(kilde_filnavn):
    """Arkiverer oppskriftsfilen (og en eventuell tilhørende loggfil) --
    flytter dem til recipes/_archive/ i stedet for å slette dem permanent.

    `kilde_filnavn` MÅ være det faktiske filnavnet oppskriften ble lastet
    fra (se ui/sidebar.py sin `_last_loaded_recipe_file`, satt fra
    hent_oppskrift_filnavn_kart() -- den EKTE filen på disk, aldri
    gjettet på nytt fra oppskriftens redigerbare "name"-felt via
    generer_filnavn()). To grunner til at navnebasert gjetting er
    utrygt: (1) et filnavn på disk kan avvike fra det oppskriften
    nettopp ble omdøpt til i UI-et før brukeren har lagret, og (2) hvis
    en ANNEN, ubeslektet fil tilfeldigvis allerede har det "kanoniske"
    filnavnet generer_filnavn(navn) ville produsert, ville en
    navnebasert sletting arkivert FEIL fil.

    Reiser UgyldigKildefilnavn (se _valider_kildefilnavn) hvis
    kilde_filnavn ikke er et rent, traversal-fritt filnavn direkte i den
    aktive oppskriftsmappen. Kallestedet (ui/recipe_card.py) eier selve
    bekreftelsesdialogen FØR dette kalles og fanger begge unntakstypene
    for å vise en tydelig feil i UI-et uten å nullstille noe. Returnerer
    True hvis oppskriftsfilen fantes og ble arkivert, False hvis den
    ikke fantes."""
    if DEMO_MODE:
        return False
    filsti = _valider_kildefilnavn(kilde_filnavn)
    if not os.path.exists(filsti):
        return False
    _arkiver_fil(filsti)

    logg_sti = os.path.join(_mappe(), kilde_filnavn.replace(".json", "_logg.json"))
    if os.path.exists(logg_sti):
        _arkiver_fil(logg_sti)
    return True
