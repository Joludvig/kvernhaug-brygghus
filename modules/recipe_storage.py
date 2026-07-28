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
_LOGS_UNDERMAPPE = "_logs"

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


class LegacyLoggKandidatUkjent(Exception):
    """Reist når en fil i oppskriftsmappens rot, med akkurat det
    filnavnet en legacy-bryggelogg for oppskriften ville hatt
    ("<navn>_logg.json"), verken lar seg lese, parse som JSON, eller
    gjenkjennes entydig som EN AV DE TO kjente, trygge formene (en
    gyldig legacy-logg, eller en HELT ANNEN oppskrift som ved
    navnetilfeldighet har akkurat det filnavnet -- se
    _klassifiser_legacy_kandidat()). Reises FØR noen sideeffekt
    (arkivering/omdøping/backup) skjer på filen eller på oppskriften den
    ev. tilhørende operasjonen gjelder -- filen røres ALDRI. Kallestedet
    (ui/recipe_card.py) fanger denne og viser en tydelig feil uten å
    nullstille den valgte oppskriften."""
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


def _logs_mappe():
    """Undermappe hvor NYE bryggelogger skrives -- se _logg_filsti() /
    _legacy_logg_filsti() for bakgrunnen: oppskrifter og bryggelogger
    delte tidligere filnavnrom direkte i oppskriftsmappens rot (en
    oppskrift "Brygg Logg" og loggen til oppskriften "Brygg" kunne begge
    produsere filnavnet "brygg_logg.json"). En egen undermappe fjerner
    kollisjonen for alt som opprettes FREMOVER."""
    return os.path.join(_mappe(), _LOGS_UNDERMAPPE)


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


_LEGACY_KANDIDAT_INGEN = "ingen"
_LEGACY_KANDIDAT_LOGG = "logg"
_LEGACY_KANDIDAT_OPPSKRIFT = "oppskrift"


def _klassifiser_legacy_kandidat(sti):
    """Avgjør hva en fil på `sti` i oppskriftsmappens rot FAKTISK er, FØR
    den ev. behandles som en legacy-bryggelogg av
    _omdoep_logg_hvis_finnes()/_logg_maalsti()/slett_oppskrift_fil().

    Bakgrunn: en legacy-logg for oppskriften "X" bruker filnavnet
    "<generer_filnavn(X)>_logg.json" -- MEN en helt ANNEN, ubeslektet
    oppskrift kan (ved ren navnetilfeldighet, f.eks. "Brygg" og "Brygg
    Logg") ha AKKURAT det samme filnavnet som sin egen, ekte
    oppskriftfil. Uten denne klassifiseringen ville en operasjon på "X"
    (omdøping, sletting, ny loggoppføring) blindt anta at enhver
    eksisterende fil med det filnavnet var "X" sin legacy-logg, og
    dermed kunnet flytte, arkivere, sikkerhetskopiere eller overskrive
    den ANDRE oppskriften.

    Returnerer:
      - _LEGACY_KANDIDAT_INGEN: filen finnes ikke -- helt normalt.
      - _LEGACY_KANDIDAT_LOGG: filen er gyldig JSON, en liste der HVERT
        element er et objekt (inkl. en tom liste) -- en ekte
        legacy-logg, trygg å behandle som sådan.
      - _LEGACY_KANDIDAT_OPPSKRIFT: filen er gyldig JSON, et objekt med
        et "name"-felt -- en ANNEN oppskrift. Skal ALDRI flyttes,
        arkiveres, sikkerhetskopieres eller endres av en operasjon på
        "X"; skal behandles som om "X" ikke har noen legacy-logg.

    Reiser LegacyLoggKandidatUkjent (filen UENDRET, aldri rørt utover
    denne ene lesingen) hvis filen finnes, men verken er lesbar
    (rettighetsfeil, ugyldig tegnkoding), gyldig JSON, eller matcher
    noen av de to kjente, trygge formene over -- feil lukket, ingen
    gjetting om filen "sikkert nok" er den ene eller den andre."""
    if not os.path.exists(sti):
        return _LEGACY_KANDIDAT_INGEN
    try:
        with open(sti, "r", encoding="utf-8") as f:
            raw = f.read()
    except (OSError, UnicodeError) as e:
        raise LegacyLoggKandidatUkjent(
            f"Kunne ikke lese den mulige legacy-loggfilen {sti}: {e}. Filen ble IKKE endret."
        ) from e
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LegacyLoggKandidatUkjent(
            f"{sti} finnes, men inneholder ugyldig JSON og kan derfor ikke sikkert "
            f"klassifiseres som verken en legacy-logg eller en oppskrift ({e}). "
            "Filen ble IKKE endret."
        ) from e
    if isinstance(data, list) and all(isinstance(x, dict) for x in data):
        return _LEGACY_KANDIDAT_LOGG
    if isinstance(data, dict) and "name" in data:
        return _LEGACY_KANDIDAT_OPPSKRIFT
    raise LegacyLoggKandidatUkjent(
        f"{sti} finnes, men innholdet matcher verken en gyldig legacy-logg (en liste "
        "av objekter) eller en oppskrift (et objekt med et \"name\"-felt). "
        "Filen ble IKKE endret."
    )


def _omdoep_logg_hvis_finnes(logg_basisnavn_gammel, logg_basisnavn_ny, logg_mappe, klassifiser=False):
    """Flytter én loggfil (hvis den finnes) fra det gamle til det nye
    NAVNET, uten å bytte MAPPE -- kalles separat for den nye
    loggplasseringen (_logs_mappe()) og for den gamle, legacy-
    plasseringen (oppskriftsmappens rot), slik at en logg ALDRI
    implisitt migreres fra den ene navnerom-mappen til den andre bare
    fordi oppskriften den tilhører ble omdøpt.

    `klassifiser=True` (brukt for legacy-roten, der filnavnet kan være
    tvetydig -- se _klassifiser_legacy_kandidat()) sjekker at kandidaten
    faktisk ER en legacy-logg før den røres i det hele tatt: en ANNEN
    oppskrift med samme filnavn (_LEGACY_KANDIDAT_OPPSKRIFT) eller en
    ukjent/korrupt kandidat blir stående helt urørt (sistnevnte har
    allerede stoppet hele omdøpingen tidligere, se
    _forhaandsvalider_omdoeping_av_logg() -- dette er kun det faktiske
    flytte-steget). `klassifiser=False` (brukt for den ALDRI tvetydige
    _logs_mappe()) beholder den enkle eksistens-sjekken."""
    gammel_logg = os.path.join(logg_mappe, logg_basisnavn_gammel)
    if klassifiser:
        if _klassifiser_legacy_kandidat(gammel_logg) != _LEGACY_KANDIDAT_LOGG:
            return
    elif not os.path.exists(gammel_logg):
        return
    ny_logg = os.path.join(logg_mappe, logg_basisnavn_ny)
    if os.path.exists(ny_logg):
        # Målet har (uvanlig nok) allerede sin egen logg -- arkiver den
        # gamle loggen i stedet for å overskrive en annen oppskrifts
        # historikk stille.
        _arkiver_fil(gammel_logg)
    else:
        shutil.move(gammel_logg, ny_logg)


def _forhaandsvalider_omdoeping_av_logg(gammelt_filnavn):
    """Klassifiserer en EVENTUELL legacy-loggkandidat for
    `gammelt_filnavn` i oppskriftsmappens rot FØR lagre_oppskrift() gjør
    NOEN som helst skriving (ny fil, backup, arkivering). Reiser
    LegacyLoggKandidatUkjent tidlig, uendret fil, dersom kandidaten
    finnes men ikke lar seg klassifisere -- slik at en omdøping ALDRI
    kan bli halvveis gjennomført (ny fil skrevet, men gammel fil/logg
    ikke arkivert fordi et sent, uventet unntak stoppet prosessen)."""
    gammel_logg_basis = gammelt_filnavn.replace(".json", "_logg.json")
    _klassifiser_legacy_kandidat(os.path.join(_mappe(), gammel_logg_basis))


def _arkiver_kildefil_etter_omdoeping(gammelt_filnavn, nytt_filnavn):
    """Kalles ETTER at den nye oppskriftsfilen allerede er skrevet: flytter
    den gamle kildefilen til recipes/_archive/ og migrerer en eventuell
    tilhørende bryggelogg til det NYE filnavnet, slik at loggen følger
    oppskriften videre under det nye navnet i stedet for å bli stående
    igjen, orphan, under det gamle.

    En logg kan i dag ligge på to steder (se _logg_filsti() /
    _legacy_logg_filsti()): den nye plasseringen (recipes/_logs/) for
    logger opprettet etter denne endringen, eller direkte i
    oppskriftsmappens rot for eldre, legacy-logger. Omdøpingen sjekker
    og omdøper i BEGGE navnerom uavhengig av hverandre -- en logg som
    ligger i _logs/ blir værende i _logs/ under det nye navnet, en
    legacy-logg i roten blir værende i roten under det nye navnet.
    Ingen av dem flyttes på tvers av navnerom her -- det ville vært en
    implisitt migrering av eksisterende data, ikke bare en omdøping.

    Legacy-roten klassifiseres FØR den røres (se
    _omdoep_logg_hvis_finnes(..., klassifiser=True)) -- selve
    forhåndsvalideringen (som ville stoppet HELE omdøpingen ved en
    ukjent/korrupt kandidat) har allerede skjedd i
    _forhaandsvalider_omdoeping_av_logg(), kalt av lagre_oppskrift() FØR
    noe som helst ble skrevet."""
    mappe = _mappe()
    gammel_sti = os.path.join(mappe, gammelt_filnavn)
    _arkiver_fil(gammel_sti)

    gammel_logg_basis = gammelt_filnavn.replace(".json", "_logg.json")
    ny_logg_basis = nytt_filnavn.replace(".json", "_logg.json")
    _omdoep_logg_hvis_finnes(gammel_logg_basis, ny_logg_basis, _logs_mappe())
    _omdoep_logg_hvis_finnes(gammel_logg_basis, ny_logg_basis, mappe, klassifiser=True)


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

    Returnerer det nye filnavnet (eller None i DEMO_MODE).

    `kilde_filnavn` valideres via _valider_kildefilnavn() FØR noe annet
    -- før kollisjonssjekk, backup, skriving av den nye filen, eller
    arkivering av den gamle. Et ugyldig kildefilnavn (path traversal,
    absolutt sti, mappekomponent, ".", "..", tom streng der en kildefil
    er oppgitt) skal ALDRI kunne føre til at koden senere prøver å
    arkivere/flytte noe utenfor (eller feil sted i) den aktive
    oppskriftsmappen -- se _arkiver_kildefil_etter_omdoeping(). `None`
    er unntaket: det betyr eksplisitt "ingen kjent tidligere kildefil"
    (ny oppskrift, eller "lagre som ny kopi") og krever ingen
    validering, siden det aldri brukes til å peke på en fil i det hele
    tatt."""
    if DEMO_MODE:
        return None
    if kilde_filnavn is not None:
        _valider_kildefilnavn(kilde_filnavn)
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

    if navn_endret:
        # Klassifiser en EVENTUELL legacy-loggkandidat FØR noe som helst
        # skrives -- se _forhaandsvalider_omdoeping_av_logg(). En
        # ukjent/korrupt kandidat skal stoppe HELE omdøpingen her, ikke
        # etterlate en halvveis gjennomført tilstand (ny fil skrevet,
        # gammel fil arkivert, men loggflyttingen feilet et sted).
        _forhaandsvalider_omdoeping_av_logg(kilde_filnavn)

    if os.path.exists(filsti):
        _backup_eksisterende_fil(filsti)

    _skriv_json_atomisk(filsti, recipe)

    if navn_endret:
        _arkiver_kildefil_etter_omdoeping(kilde_filnavn, nytt_filnavn)

    return nytt_filnavn

def _logg_filsti(oppskrift_navn):
    """NY plassering for bryggelogger: recipes/_logs/<generert
    filnavn>_logg.json -- en EGEN undermappe, adskilt fra selve
    oppskriftsfilenes navnerom i mappe-roten (se _logs_mappe())."""
    base = generer_filnavn(oppskrift_navn).replace(".json", "_logg.json")
    return os.path.join(_logs_mappe(), base)

def _legacy_logg_filsti(oppskrift_navn):
    """Den GAMLE loggplasseringen (direkte i oppskriftsmappens rot) --
    brukt KUN for LESETILGANG til logger som ble opprettet FØR denne
    endringen (se _logg_maalsti()). Nye logger skrives ALDRI hit, og en
    eksisterende legacy-logg flyttes/migreres ALDRI automatisk til den
    nye plasseringen som del av vanlig bruk -- kun en fremtidig,
    eksplisitt brukerhandling skal kunne gjøre det (atomisk, med backup,
    uten historikktap)."""
    base = generer_filnavn(oppskrift_navn).replace(".json", "_logg.json")
    return os.path.join(_mappe(), base)

def _logg_maalsti(oppskrift_navn):
    """Stien EN SKRIVING (lagre_logg_entry) skal bruke: hvis loggen
    allerede finnes på den NYE plasseringen, fortsett å skrive der. Hvis
    den GAMLE, legacy-plasseringen i stedet inneholder en EKTE legacy-
    logg (klassifisert -- se _klassifiser_legacy_kandidat()), fortsett å
    skrive DER, for å unngå at en helt vanlig "legg til brygg"-handling
    implisitt migrerer en eksisterende legacy-logg til et nytt sted. Er
    legacy-kandidaten i stedet en HELT ANNEN oppskrift (samme filnavn
    ved ren tilfeldighet, se _klassifiser_legacy_kandidat()) eller
    finnes ingen kandidat i det hele tatt, går en helt NY logg til den
    nye plasseringen -- den andre oppskriften røres aldri.

    Kan reise LegacyLoggKandidatUkjent hvis en eksisterende legacy-
    kandidat ikke lar seg klassifisere (korrupt/uleselig/ukjent schema)
    -- kallestedet (lagre_logg_entry) fanger dette."""
    ny_sti = _logg_filsti(oppskrift_navn)
    if os.path.exists(ny_sti):
        return ny_sti
    legacy_sti = _legacy_logg_filsti(oppskrift_navn)
    if _klassifiser_legacy_kandidat(legacy_sti) == _LEGACY_KANDIDAT_LOGG:
        return legacy_sti
    return ny_sti

def lagre_logg_entry(oppskrift_navn, entry):
    """Legger til én loggoppføring i oppskriftens loggfil.

    Tar automatisk en tidsstemplet backup av en EKSISTERENDE loggfil rett
    før den overskrives (samme rullerende backup-prinsipp og terskel som
    lagre_oppskrift() bruker for selve oppskriftsfilen -- se
    _backup_eksisterende_fil/RECIPE_BACKUP_MAKS_ANTALL).

    Leser eksisterende logg via hent_logg() FØR den nye oppføringen
    legges til: er loggfilen korrupt eller har feil schema, forplanter
    det seg som LoggKorruptError HERFRA, uten at noe skrives -- i stedet
    for at denne ene, nye oppføringen stille erstatter hele den (ellers
    tapte) historikken. En ukjent/korrupt legacy-loggKANDIDAT (se
    _logg_maalsti()/_klassifiser_legacy_kandidat()) blokkerer på samme
    måte, som LoggKorruptError -- fra kallerens ståsted er "kan ikke
    avgjøre om det finnes en eksisterende logg" den samme typen feil som
    "loggen finnes, men er korrupt", og UI-et (ui/recipe_card.py) fanger
    allerede LoggKorruptError rundt nøyaktig dette kallet."""
    if DEMO_MODE:
        return
    sikre_mappe()
    try:
        filsti = _logg_maalsti(oppskrift_navn)
    except LegacyLoggKandidatUkjent as e:
        raise LoggKorruptError(str(e)) from e
    _sikre_undermappe(os.path.dirname(filsti))
    logg = hent_logg(oppskrift_navn)
    logg.append(entry)
    if os.path.exists(filsti):
        _backup_eksisterende_fil(filsti)
    _skriv_json_atomisk(filsti, logg)

def hent_logg(oppskrift_navn):
    """Henter alle loggoppføringer for en oppskrift.

    Ser først etter loggen på den NYE plasseringen (recipes/_logs/),
    deretter -- kun for lesetilgang, og kun hvis den faktisk klassifiseres
    som en EKTE legacy-logg (se _klassifiser_legacy_kandidat()) -- på den
    gamle, legacy-plasseringen direkte i oppskriftsmappens rot. En annen
    oppskrift som ved navnetilfeldighet har samme filnavn behandles som
    om "X" ikke har noen legacy-logg i det hele tatt (tom liste), og
    røres ALDRI. Returnerer tom liste hvis loggen ikke finnes NOE sted --
    helt normalt for en oppskrift uten registrerte brygg. Kaster
    LoggKorruptError (uten å røre filen) hvis den FINNES men ikke er
    gyldig JSON, eller hvis en legacy-kandidat ikke lar seg klassifisere
    -- ALDRI stille tom, som tidligere kunne få lagre_logg_entry() til å
    overskrive hele historikken med bare den ene, nye oppføringen. Samme
    etablerte mønster som modules/pantry.py::last_pantry()/
    PantryCorruptError."""
    filsti = _logg_filsti(oppskrift_navn)
    if not os.path.exists(filsti):
        legacy_sti = _legacy_logg_filsti(oppskrift_navn)
        try:
            klassifisering = _klassifiser_legacy_kandidat(legacy_sti)
        except LegacyLoggKandidatUkjent as e:
            raise LoggKorruptError(str(e)) from e
        if klassifisering != _LEGACY_KANDIDAT_LOGG:
            # _LEGACY_KANDIDAT_INGEN (finnes ikke) eller
            # _LEGACY_KANDIDAT_OPPSKRIFT (en ANNEN oppskrift, samme
            # filnavn ved tilfeldighet) -- begge betyr "ingen legacy-logg
            # for DENNE oppskriften".
            return []
        filsti = legacy_sti
    with open(filsti, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LoggKorruptError(
            f"{filsti} inneholder ugyldig JSON og ble IKKE overskrevet ({e}). "
            f"Rett filen manuelt, eller gjenopprett fra en backup i {_backup_mappe()}, "
            "før nye loggoppføringer kan lagres."
        ) from e

    # Gyldig JSON er IKKE det samme som et gyldig loggschema -- {}, "en
    # streng", 42, null, eller en liste med ikke-objekt-elementer er alle
    # gyldig JSON, men ville fått lagre_logg_entry() til å krasje på
    # logg.append(entry) (en dict) eller stille produsert en liste med
    # oppføringer appen ikke kan vise. Roten MÅ være en liste, og hver
    # EKSISTERENDE oppføring MÅ være et objekt/dict (ui/recipe_card.py
    # leser alltid oppføringer via entry.get(...), aldri indeksering uten
    # en forutgående .get()-vakt -- se _render_brewday_result_panel()).
    if not isinstance(data, list):
        raise LoggKorruptError(
            f"{filsti} inneholder gyldig JSON, men av feil type "
            f"({type(data).__name__} i stedet for en liste med loggoppføringer). Filen ble IKKE endret."
        )
    for i, oppforing in enumerate(data):
        if not isinstance(oppforing, dict):
            raise LoggKorruptError(
                f"{filsti} inneholder en ugyldig loggoppføring på indeks {i} "
                f"({type(oppforing).__name__} i stedet for et objekt). Filen ble IKKE endret."
            )
    return data


def _skann_oppskriftsfiler(mappe):
    """Leser og parser alle .json-filer direkte i en gitt mappe (aldri
    undermapper som _archive/_backup/_logs — os.listdir() er ikke
    rekursiv). Returnerer en liste av (filnavn, data)-par for filer som
    lot seg lese OG som er et JSON-objekt med et "name"-felt;
    korrupte/ufullstendige filer logges og hoppes over. Delt
    lesehjelper for hent_alle_oppskrifter(), hent_oppskrift_filnavn_kart()
    og finn_duplikate_oppskrift_navn() — én skanning å holde konsistent.

    MERK: filtrerer IKKE lenger bort filnavn som ender på "_logg.json" --
    en oppskrift kan hete f.eks. "Brygg Logg" (kanonisk filnavn
    "brygg_logg.json") og skal kunne lagres/lastes/vises helt normalt.
    Nye bryggelogger skrives uansett til en egen undermappe (se
    _logg_filsti()/_logs_mappe()) og havner derfor aldri her i det hele
    tatt. En eventuell GAMMEL, legacy-loggfil som fortsatt ligger i
    mappe-roten (et JSON-array, ikke et objekt) blir naturlig hoppet
    over av "name"-sjekken under uansett, uten noe eget filnavn-filter."""
    filer = [f for f in os.listdir(mappe) if f.endswith(".json")]
    resultat = []
    for f in filer:
        filsti = os.path.join(mappe, f)
        try:
            with open(filsti, "r", encoding="utf-8") as file_content:
                data = json.load(file_content)
            if not isinstance(data, dict) or "name" not in data:
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
    aktive oppskriftsmappen, eller LegacyLoggKandidatUkjent (se
    _klassifiser_legacy_kandidat()) hvis en mulig legacy-loggkandidat i
    mapperoten ikke lar seg klassifisere -- i BEGGE tilfeller FØR
    oppskriftsfilen arkiveres, slik at en avvist sletting aldri kan bli
    halvveis gjennomført. Kallestedet (ui/recipe_card.py) eier selve
    bekreftelsesdialogen FØR dette kalles og fanger alle tre
    unntakstypene for å vise en tydelig feil i UI-et uten å nullstille
    noe. Returnerer True hvis oppskriftsfilen fantes og ble arkivert,
    False hvis den ikke fantes."""
    if DEMO_MODE:
        return False
    filsti = _valider_kildefilnavn(kilde_filnavn)
    if not os.path.exists(filsti):
        return False

    logg_basis = kilde_filnavn.replace(".json", "_logg.json")
    # Klassifiser en EVENTUELL legacy-loggkandidat i mapperoten FØR noe
    # arkiveres -- filnavnet kan (ved ren tilfeldighet) tilhøre en HELT
    # ANNEN oppskrift i stedet for en legacy-logg for DENNE (se
    # _klassifiser_legacy_kandidat()). Kandidaten i recipes/_logs/ er
    # derimot ALDRI tvetydig -- enhver fil der er per konstruksjon en
    # ekte logg.
    legacy_logg_sti = os.path.join(_mappe(), logg_basis)
    legacy_klassifisering = _klassifiser_legacy_kandidat(legacy_logg_sti)

    _arkiver_fil(filsti)
    _arkiver_fil(os.path.join(_logs_mappe(), logg_basis))
    if legacy_klassifisering == _LEGACY_KANDIDAT_LOGG:
        _arkiver_fil(legacy_logg_sti)
    return True
