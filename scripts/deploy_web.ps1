<#
.SYNOPSIS
  Trygg, manuell én-kommando-deploy av web/-runtime til Domeneshop (FTPS).

.DESCRIPTION
  Laster opp HELE innholdet i repo_root\web\ (full sync, ikke delta) til
  ftp.domeneshop.no:/www over eksplisitt FTPS (AUTH TLS, samme sikkerhetsnivå
  som "Require explicit FTP over TLS" i FileZilla). README.md og CHANGELOG.md
  er utviklerdokumentasjon og ekskluderes -- alt annet under web/ er runtime
  og lastes opp uendret, med samme mappestruktur.

  Dette er IKKE automatisk CI/CD -- scriptet gjør ingenting uten at en
  bruker eksplisitt starter det og bekrefter opplastingen. Ingen FTP-passord
  lagres noe sted (ikke i repoet, ikke på disk, ikke i logg) -- det spørres
  interaktivt hver kjøring og holdes kun i en midlertidig curl-konfigfil som
  slettes umiddelbart etter bruk.

  Før noen fil lastes opp gjør scriptet én liten read-only preflight (list
  av target-mappen) for å bekrefte at innloggingen faktisk fungerer -- feiler
  den, stoppes hele deployen før noe som helst skrives. Under selve
  opplastingen stopper scriptet UMIDDELBART ved første feilede fil i stedet
  for å fortsette gjennom resten av listen (se Runde 22B.1).

  Kjenner IKKE remote-filer den ikke selv laster opp -- sletter aldri noe på
  serveren. Kun overskriving/opplasting av filene som faktisk finnes i
  web/ lokalt.

  GUARD (checkout må matche origin/master): en tidligere deploy ble kjørt
  fra en lokal checkout som var 52 commits bak origin/master og manglet
  hele PR #23 -- scriptet lastet stille opp gammelt innhold, rapporterte
  suksess, og den daværende HTTP-200-sjekken kunne ikke fange det (se
  issue #28). Scriptet nekter derfor nå å gjøre noe som helst dersom denne
  checkoutens HEAD ikke er nøyaktig identisk med origin/master (ahead,
  behind eller divergert stopper alle likt) -- kjør fra en fersk
  checkout/worktree av current origin/master i stedet.

  INNHOLDSVERIFISERING (ikke bare HTTP 200): etter opplasting lastes HVER
  ENESTE deployet fil ned igjen over HTTPS og sammenlignes byte-for-byte
  (SHA-256) mot den lokale kilden -- ikke et kuratert utvalg. HTTP 200
  beviser bare at siden svarer, ikke at innholdet er riktig.

  GUARD (rent web/-innhold i working tree/index): scriptet laster opp
  CURRENT WORKING-TREE-bytes, og INNHOLDSVERIFISERINGEN over sammenligner
  produksjon mot akkurat de samme lokale bytene den selv nettopp lastet
  opp -- den kan derfor aldri på egen hånd oppdage en ukommittert
  web/-endring (se issue #72). Scriptet nekter derfor å gjøre noe som
  helst dersom modifisert, staget, slettet, untracked ELLER gitignorert
  (f.eks. *.log/*.tmp) innhold finnes under web/ (README.md/CHANGELOG.md
  unntatt -- de deployes aldri). Gitignorerte filer under web/ må også
  fanges, siden fillistingen i steg 2 enumererer filsystemet direkte og
  laster opp ALT under web/ uansett .gitignore (Chief review, PR #73).
  Urelaterte urene filer utenfor web/ (f.eks. eierens egne lokale
  endringer andre steder i repoet) påvirkes ikke.

  DELTA-SJEKK OG BOLK-OPPLASTING (issue #213): en deploy av ALLE 85 filene
  traff et deterministisk FTPS-tilkoblingstak rundt fil #51 -- hver fil
  åpnet sin egen nye FTPS-innlogging/TLS-håndtrykk, og serveren stoppet å
  svare etter rundt 50 raske tilkoblinger. Scriptet gjør derfor nå to ting
  FØR selve FTPS-opplastingen: (1) en read-only HTTPS-delta-sjekk (samme
  mekanisme som INNHOLDSVERIFISERINGEN under, 0 FTPS-tilkoblinger, ingen
  credentials) som hopper over filer som allerede er byte-identiske med
  produksjon -- kun faktiske avvik/manglende filer sendes videre til
  opplasting; (2) filene som faktisk skal lastes opp samles i bolker og
  lastes opp med ÉN curl.exe-prosess per bolk (filene adskilt med --next
  i samme -K configfil, med credential-linjen OG --ssl-reqd gjentatt
  EKSPLISITT i hver enkelt blokk -- curl sin egen dokumentasjon sier at
  --next nullstiller alle ikke-globale opsjoner, så ingen av dem kan
  hvile på en antakelse om arv på tvers av blokker), som lar curl
  gjenbruke FTPS-tilkoblingen på tvers av filene i samme bolk i stedet
  for én ny tilkobling per fil. En bolk som feiler med en forbigående
  nettverksfeil (curl exit 56/55/18, f.eks. CURLE_RECV_ERROR) reverifiseres
  FØRST mot produksjon over HTTPS (samme read-only mekanisme som
  delta-sjekken) -- kun filer som fortsatt faktisk avviker/mangler/ikke
  kan verifiseres prøves på nytt, ÉN gang, etter en kort pause; hvis
  reverifiseringen viser at alle filene i bolken allerede kom frem (f.eks.
  exit 56 EFTER en ellers fullført overføring), regnes bolken som
  vellykket uten noe nytt curl-forsøk. Ekte feil (feil credentials,
  TLS-håndtrykk, manglende sti) stopper deployen umiddelbart akkurat som
  før, uten retry.

  OWNER-GATE TESTMODUS (issue #213, Chief-krav): normal deploy krever som
  før at HEAD er nøyaktig identisk med origin/master (guard 1b over) --
  det gjør det umulig å kjøre den ekte bolk-/retry-implementasjonen mot en
  eksakt PR-head FØR merge, selv om det nettopp er det en Chief-review av
  denne typen endring trenger å se bevist på ekte Windows/Domeneshop-FTPS.
  -OwnerGateTestSha <40-tegns SHA> åpner en SNEVER, eksplisitt unntaksvei:
  i stedet for HEAD == origin/master krever den at HEAD er NØYAKTIG den
  oppgitte SHA-en, OG (utenfor -DryRun) at origin/<eksplisitt oppgitt
  -OwnerGateTestBranch> -- hentet FERSK -- også er nøyaktig den samme
  SHA-en, slik at testkjøringen er bundet til akkurat den PR-branchens
  faktiske, pushede head og ikke en lokal commit som aldri ble reviewet.
  Enhver avvik (feil/manglende SHA, ufullstendig format, manglende
  -OwnerGateTestBranch, lokal HEAD som ikke matcher, eller origin-branchen
  som ikke matcher) stopper deployen umiddelbart -- fail-closed, ikke
  best-effort. Normal deploy (uten -OwnerGateTestSha) er HELT uendret og
  bruker fortsatt kun HEAD == origin/master.

  -OwnerGateTestBranch må oppgis EKSPLISITT (aldri utledet fra checkouten)
  fordi owner-gate-testen per konstruksjon kjøres fra en FRIKOBLET
  (detached HEAD) checkout/worktree på nøyaktig PR-branchens head-SHA --
  det er selve poenget, siden -OwnerGateTestSha binder testen til en
  eksakt commit, ikke en branch-tilstand. En frikoblet HEAD har ikke noe
  branch-navn: `git rev-parse --abbrev-ref HEAD` returnerer da bokstavelig
  strengen "HEAD", og `origin/HEAD` er git sin symbolske peker til
  origin-repoets STANDARD-branch (dvs. master), ikke PR-branchen -- en
  tidligere versjon av denne testmodusen utledet branch-navnet nettopp
  slik, og sammenlignet derfor stille master mot PR-SHA-en i stedet for
  PR-branchen selv, noe som fikk owner-gate-testen til å feile-lukket mot
  feil ref også når PR-branchen faktisk var oppdatert (Chief review, PR
  #216, runde 4). Med et eksplisitt -OwnerGateTestBranch-parameter gjøres
  aldri noe `--abbrev-ref`-kall i owner-gate-grenen -- checkoutens
  faktiske branch-tilstand (frikoblet eller ikke) er dermed irrelevant.

  Owner-gate-testmodus nekter i tillegg å target normal produksjon (/www,
  standardverdien for -RemoteRoot) uten et eksplisitt -OwnerGateAllowProductionTarget
  -- uten det må -RemoteRoot pekes til en isolert test-sti på Domeneshop,
  slik at en owner-gate-test aldri ved et uhell kan skrive PR-branchens
  ureviewede bytes til den faktiske live-siden. Credential-håndtering og
  --ssl-reqd-kravet er UENDRET i owner-gate-testmodus -- kun HVILKEN
  checkout-sammenligning guarden gjør, og HVOR opplastingen sendes, endres.

  DELTA-SJEKK OG VERIFISERING MOT DET ISOLERTE TESTMÅLET, IKKE PRODUKSJON
  (issue #213, Chief-krav, runde 5): den ekte bolk-/retry-OPPLASTINGEN er
  identisk uansett modus, men delta-sjekken (steg 2b) og produksjons-
  verifiseringen (steg 6) brukte tidligere begge $BaseUrl (hardkodet
  https://kvernhaugbrygghus.no, dvs. NORMAL PRODUKSJON) uansett hvilken
  -RemoteRoot som faktisk var target -- siden denne utvidelsen selv ikke
  endrer web/, ville produksjon allerede matche alle 85 filene, og
  delta-sjekken ville derfor stille hoppet over dem ALLE før én eneste
  FTPS-tilkobling til teststien i det hele tatt ble åpnet, og
  sluttverifiseringen ville "bekreftet" produksjonens bytes, ikke
  testmålets. Owner-gate testmodus gjør derfor nå to ting annerledes: (1)
  delta-sjekken hopper UBETINGET over -- ALLE filer sendes til
  FTPS-opplasting, uansett hva produksjon inneholder; (2) sluttverifiseringen
  (og en eventuell bolk-reverifisering før retry i steg 5c) laster i stedet
  ned hver fil på nytt over FTPS fra det faktiske -RemoteRoot-testmålet
  (bolkvis/--next-batchet for hele filsettet, samme tilkoblingsgjenbruks-
  prinsipp som selve opplastingen, for å unngå å reintrodusere
  tilkoblingstaket) -- ikke HTTPS mot produksjon. Smoke-sjekken (HTTP 200
  på produksjonens root/en) hoppes også over, siden den kun sier noe om
  normal produksjon. Normal deploy (uten -OwnerGateTestSha) er HELT
  uendret og bruker fortsatt utelukkende HTTPS mot $BaseUrl.

  KONFIG-LEVETID OG MODUSBEVISSTE MELDINGER (issue #213, Chief-krav, runde
  6): to gjenstående hull i owner-gate-verifiseringen over. (1)
  $curlConfigPath (credentials-configen fra steg 5) slettes i finally
  UMIDDELBART etter steg 5 -- FØR steg 6 i det hele tatt starter. Retry-
  passet i steg 6 (enkeltfil, ved ethvert avvik/ikke-verifiserbar fil i
  første FTPS-pass) pekte derfor deterministisk på en allerede slettet
  fil og kunne aldri lykkes. Steg 6 bygger derfor nå sin EGEN, ferske
  credentials-config ($ownerGateVerifyCurlConfigPath, fra samme
  in-memory $configContent-streng steg 5 selv brukte) FØR
  verifiseringen starter, og sletter den i sin egen finally -- uavhengig
  av $curlConfigPath sin egen levetid. (2) AVVIK-/KAN-IKKE-VERIFISERE-/
  OK-meldingene etter verifiseringen var hardkodet til "produksjon" i
  BEGGE moduser -- en vellykket sjekk av det isolerte owner-gate-
  testmålet kunne dermed leses som et bevis om normal produksjon, noe
  det aldri er. $verifiseringsMaalLabel/$verifiseringsProtokollLabel
  beregnes nå ÉN gang (owner-gate: eksplisitt $FtpHost$RemoteRoot +
  "FTPS"; normal: "produksjon" + "HTTPS", uendret ordlyd) og gjenbrukes
  av både per-fil-loggingen og sluttoppsummeringen.

  LOGIN-PREFLIGHT MOT FORELDER-MAPPEN FOR ET FERSKT TESTMÅL (issue #213,
  Chief-krav, runde 7): login-preflighten (steg 5b) listet tidligere ALLTID
  selve -RemoteRoot for å bekrefte innlogging -- curl må cd'e inn i mappen
  for å liste den, noe som krever at mappen allerede finnes. Et FERSKT
  isolert owner-gate-testmål (f.eks. /www-owner-gate-test) finnes derimot
  ikke før selve opplastingen oppretter det via --ftp-create-dirs, så
  preflighten feilet deterministisk med curl exit 9 ("Server denied you to
  change to the given directory") FØR noen opplasting fikk sjansen til å
  opprette mappen -- og dermed også før den ekte bolk-/retry-/
  verifiseringsflyten owner-gate-testen finnes for å bevise, i det hele
  tatt kunne kjøre. Owner-gate-modus lister derfor nå i stedet -RemoteRoot
  sin FORELDER-mappe (for standardeksempelet er det FTP-kontoens rot "/"),
  som alltid er tilgjengelig uavhengig av om selve testmålet finnes ennå
  (Get-OwnerGatePreflightSti). Dette endrer INGENTING ved hva som faktisk
  valideres for ugyldige credentials/tilgang -- samme curl-innlogging,
  samme feilkoder (f.eks. 530) -- kun HVILKEN mappe som listes. Normal
  deploy (uten -OwnerGateTestSha) er HELT uendret og lister fortsatt
  nøyaktig -RemoteRoot.

  DEGRADERENDE BOLKSTØRRELSE VED VEDVARENDE FORBIGÅENDE FEIL (issue #213,
  runde 8): login-preflight-fiksen (runde 7) løste "mappen finnes ikke
  ennå", men en reell owner-gate-kjøring mot Domeneshop på eksakt hode
  3bff6d2c... traff deretter et NYTT, ekte serverproblem -- "server did
  not report OK, got 426" (curl exit 18) på selve bolk-opplastingen, to
  bolker à 10 filer på rad, som IKKE ble løst av eksisterende
  reverifisering+ett bounded retry (steg 5c over). Scriptet stoppet derfor
  hele deployen ved fil 20/85. Steg 5c prøver nå IKKE lenger bare på nytt
  med samme bolkstørrelse -- filer som fortsatt avviker etter at en gitt
  bolkstørrelse har brukt opp sine bounded forsøk med en FORBIGÅENDE
  feilkode, degraderes i stedet til MINDRE bolker (10 -> 5 -> 2 -> 1, se
  Get-DegraderteBolkStorrelser) og forsøkes der på nytt med akkurat samme
  reverifiser-før-retry-logikk, helt ned til ÉN fil per curl.exe-prosess
  (ingen --next i det hele tatt) om nødvendig. Hypotesen -- ikke bekreftet
  empirisk i denne sandkassen, se tests/test_deploy_web_batch_upload.py --
  er at færre (til slutt null) --next-adskilte overføringer per
  kontrollforbindelse er mindre sårbart for hva enn som faktisk trigger 426
  mot akkurat denne serveren. En EKTE (ikke-forbigående) curl-feil
  degraderer ALDRI -- den stopper fortsatt deployen umiddelbart, uansett
  bolkstørrelse, akkurat som før. Kun når gulvstørrelsen (1 fil, ingen
  --next) OGSÅ har brukt opp sine bounded forsøk med en forbigående feil,
  stopper deployen -- det finnes ingen mindre bolkstørrelse å degradere
  videre til.

  Eksakt owner-PC-kommando for gaten (se .EXAMPLE under for full syntaks):
  fetch branchen, les dens faktiske head-SHA, og kjør scriptet med akkurat
  den SHA-en pluss en isolert -RemoteRoot.

.PARAMETER DryRun
  Viser source, target, filantall og full filliste. Gjør ingen FTP-/HTTPS-
  tilkobling og ingen endringer. Guardene over kjøres likevel (ren lokal
  git-sjekk, ingen `git fetch`) -- HEAD/origin-sammenligningen bruker da
  sist kjente origin/master; kjør uten -DryRun, eller `git fetch` manuelt
  her først, for en garantert fersk sammenligning. Den urene-web/-guarden
  gjør uansett aldri noen `git fetch` og er derfor alltid fersk.

.PARAMETER Force
  Hopper over ja/nei-bekreftelsen før opplasting. Bruk med varsomhet.

.PARAMETER FtpUser
  FTP-brukernavn. Spørres interaktivt dersom ikke oppgitt. Regnes ikke som
  hemmelig (samme prinsipp som å skrive det inn i FileZilla).

.PARAMETER FtpHost
  FTP-vertsnavn. Standard: ftp.domeneshop.no

.PARAMETER RemoteRoot
  Remote rotmappe. Standard: /www

.PARAMETER OwnerGateTestSha
  Aktiverer owner-gate testmodus (se .DESCRIPTION). Må være den fulle
  40-tegns commit-SHA-en til PR-branchens eksakte head som skal testes.
  Krever -OwnerGateTestBranch (se under). Utelatt (standard): scriptet
  oppfører seg helt som før, og krever HEAD == origin/master.

.PARAMETER OwnerGateTestBranch
  Kun relevant sammen med -OwnerGateTestSha -- MÅ oppgis eksplisitt når
  -OwnerGateTestSha er satt (fail-closed, ingen standardverdi/utledning).
  Det eksakte remote-branch-navnet (f.eks. "agent/issue-213") som
  -OwnerGateTestSha hentes fra og verifiseres FERSK mot etter
  `git fetch`. Utledes ALDRI fra checkoutens lokale branch-tilstand --
  owner-gate-testen kjøres typisk fra en frikoblet (detached HEAD)
  checkout/worktree, der det ikke finnes noe lokalt branch-navn å utlede
  (se .DESCRIPTION).

.PARAMETER OwnerGateAllowProductionTarget
  Kun relevant sammen med -OwnerGateTestSha. Bekrefter eksplisitt at
  owner-gate-testen bevisst skal target normal produksjon (-RemoteRoot
  fortsatt /www) i stedet for en isolert test-sti. Uten dette flagget
  nekter owner-gate-testmodus å kjøre mot standard -RemoteRoot.

.EXAMPLE
  .\scripts\deploy_web.ps1 -DryRun

.EXAMPLE
  .\scripts\deploy_web.ps1

.EXAMPLE
  # Owner-gate (issue #213): kjør den ekte bolk-/retry-implementasjonen mot
  # en isolert test-sti FØR merge, bundet til PR-branchens eksakte, pushede
  # head -- normal produksjon (/www) røres ikke. -OwnerGateTestBranch må
  # oppgis eksplisitt (fungerer også fra en frikoblet/detached-HEAD
  # test-worktree, se .DESCRIPTION).
  git fetch origin agent/issue-213
  $prHead = (git rev-parse origin/agent/issue-213).Trim()
  .\scripts\deploy_web.ps1 -OwnerGateTestSha $prHead -OwnerGateTestBranch "agent/issue-213" -RemoteRoot "/www-owner-gate-test"
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Force,
    [string]$FtpUser,
    [string]$FtpHost = "ftp.domeneshop.no",
    [string]$RemoteRoot = "/www",
    [string]$OwnerGateTestSha,
    [string]$OwnerGateTestBranch,
    [switch]$OwnerGateAllowProductionTarget
)

$ErrorActionPreference = "Stop"

# ─── Hjelpefunksjoner ───────────────────────────────────────────────────────

# curl sin -K configfil tolker BAKOVERSKRÅSTREK som escape-tegn inni en
# dobbeltfnutt-verdi: \\ -> \, \" -> ", og (dokumentert av curl selv) \t \n
# \r \v -> tab/linjeskift/vognretur/vertikal-tab. Et passord som INNEHOLDER
# en bakoverskråstrek -- f.eks. rett foran en 't'/'n'/'r'/'v' -- ville derfor
# blitt stille tolket om til et kontrolltegn eller på annen måte korrumpert
# hvis skråstreken ikke escapes FØRST. Rekkefølgen er kritisk: skråstrek MÅ
# escapes før fnutt, ellers ville fnutt-escapingens egen bakoverskråstrek bli
# dobbelt-escaped og selv korrumpere verdien. Bruker .Replace() (bokstavelig
# strengerstatning), ikke -replace (regex), for å unngå enda et lag med
# escaping-tvetydighet i selve fiksen.
function Get-CurlConfigEscaped {
    param([string]$Value)
    return $Value.Replace('\', '\\').Replace('"', '\"')
}

# Ren beslutningsfunksjon (issue #72) -- tar `git status --porcelain`-linjer
# (allerede pathspec-avgrenset til web/ av kalleren) pluss den samme
# repo-rot-relative eksklusjonslisten (README.md/CHANGELOG.md via
# $ExcludeRelative) og returnerer hvilke DEPLOYABLE stier under web/ som er
# urene -- modifisert/staget/slettet/untracked. Utpakket til egen funksjon
# (samme mønster som Get-CurlConfigEscaped/Get-CurlFeilmelding over) slik at
# selve avgjørelseslogikken er testbar uavhengig av git.exe/curl.exe-sjekken
# lenger ned, som gjør resten av scriptet Windows-only.
function Get-UrentWebInnhold {
    param(
        [string[]]$PorcelainLinjer,
        [string[]]$EkskluderteWebRelativeStier
    )
    $ekskludertAbsolutt = @($EkskluderteWebRelativeStier | ForEach-Object { "web/$_" })
    $urent = @()
    foreach ($line in $PorcelainLinjer) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        # Porcelain-linje: "XY <sti>", eller "XY <gammel sti> -> <ny sti>"
        # for en oppdaget staget rename. Kolonne 1-2 er statuskoder,
        # kolonne 4- er selve stien(e) -- Substring(3) er derfor en enklere
        # og mer robust utpakking enn å splitte på mellomrom (stier kan
        # selv inneholde mellomrom).
        $pathsPart = $line.Substring(3)
        if ($pathsPart -match '^"(.*)"$') { $pathsPart = $matches[1] }
        foreach ($p in ($pathsPart -split ' -> ')) {
            $p = $p.Trim().Trim('"')
            if ($ekskludertAbsolutt -notcontains $p) {
                $urent += $p
            }
        }
    }
    return @($urent | Sort-Object -Unique)
}

# Ren beslutningsfunksjon (issue #213, Chief-krav owner-gate) -- avgjør om
# owner-gate testmodus (-OwnerGateTestSha) får lov til å erstatte den
# vanlige HEAD==origin/master-guarden for DENNE kjøringen. Fail-closed by
# construction: enhver ugyldig SHA-form, tom verdi, HEAD-mismatch, eller
# (utenfor -DryRun) origin-branch-mismatch gir avslag -- aldri en stille
# aksept. $OriginBranchRefKjentFersk er $false kun under -DryRun (som per
# kontrakt aldri gjør `git fetch`, se .DESCRIPTION) -- da sammenlignes KUN
# mot HEAD, og meldingen sier eksplisitt at dette ikke er en garantert
# fersk sammenligning, samme prinsipp som den eksisterende HEAD-guarden
# allerede bruker for -DryRun.
function Test-OwnerGateForutsetninger {
    param(
        [Parameter(Mandatory)][string]$ExpectedSha,
        [Parameter(Mandatory)][string]$LocalHead,
        [string]$OriginBranchNavn,
        [string]$OriginBranchRef,
        [bool]$OriginBranchRefKjentFersk
    )
    if ($ExpectedSha -notmatch '^[0-9a-fA-F]{40}$') {
        return [PSCustomObject]@{ ok = $false; reason = "OwnerGateTestSha må være en full 40-tegns commit-SHA (fikk: '$ExpectedSha')." }
    }
    $expected = $ExpectedSha.ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($LocalHead)) {
        return [PSCustomObject]@{ ok = $false; reason = "Kunne ikke lese lokal HEAD -- kan ikke bekrefte owner-gate-forutsetningen." }
    }
    if ($LocalHead.ToLowerInvariant() -ne $expected) {
        return [PSCustomObject]@{ ok = $false; reason = "HEAD ($LocalHead) matcher ikke oppgitt OwnerGateTestSha ($ExpectedSha)." }
    }
    if (-not $OriginBranchRefKjentFersk) {
        return [PSCustomObject]@{ ok = $true; reason = "HEAD matcher OwnerGateTestSha (kun lokal sammenligning -- -DryRun henter aldri origin på nytt, se .DESCRIPTION)." }
    }
    if ([string]::IsNullOrWhiteSpace($OriginBranchRef)) {
        return [PSCustomObject]@{ ok = $false; reason = "Fant ikke origin/$OriginBranchNavn etter fersk fetch -- kan ikke bekrefte at HEAD samsvarer med PR-branchens faktiske, pushede head." }
    }
    if ($OriginBranchRef.ToLowerInvariant() -ne $expected) {
        return [PSCustomObject]@{ ok = $false; reason = "origin/$OriginBranchNavn ($OriginBranchRef) matcher ikke oppgitt OwnerGateTestSha ($ExpectedSha) -- push/fetch fersk branch-tilstand og prøv igjen." }
    }
    return [PSCustomObject]@{ ok = $true; reason = "HEAD OG origin/$OriginBranchNavn matcher OwnerGateTestSha." }
}

# Ren beslutningsfunksjon (issue #213, Chief-krav owner-gate, runde 7) --
# login-preflighten (steg 5b) validerte tidligere ALLTID mot selve
# $RemoteRoot (`ftp://...$RemoteRoot/`) -- curl cd'er inn i mappen for å
# liste den, noe som krever at mappen allerede finnes på serveren. Et
# FERSKT owner-gate-testmål (f.eks. "/www-owner-gate-test") finnes derimot
# ikke før selve opplastingen oppretter det via --ftp-create-dirs (se
# New-BolkOpplastingConfig) -- preflighten feilet derfor deterministisk med
# curl exit 9 ("Server denied you to change to the given directory") FØR
# noen opplasting fikk sjansen til å opprette mappen (owner-gate-kjøring
# observert av Chief på hode b71984a). Normal deploy ($RemoteRoot = "/www")
# er upåvirket -- den mappen eksisterer alltid. Fiksen: i owner-gate-modus
# valideres innlogging/tilgang i stedet mot $RemoteRoot sin FORELDER-mappe
# (for standardeksempelet "/www-owner-gate-test" er det FTP-kontoens rot
# "/"), som alltid er tilgjengelig uavhengig av om selve testmålet finnes
# ennå. Dette endrer INGENTING ved hva som faktisk valideres for ugyldige
# credentials/tilgang -- samme curl-innlogging, samme feilkoder (f.eks.
# 530) -- kun HVILKEN mappe som listes. Normal modus (-not $IsOwnerGateTest)
# returnerer $RemoteRoot uendret.
function Get-OwnerGatePreflightSti {
    param(
        [Parameter(Mandatory)][string]$RemoteRoot,
        [Parameter(Mandatory)][bool]$IsOwnerGateTest
    )
    if (-not $IsOwnerGateTest) {
        return $RemoteRoot
    }
    $trimmet = $RemoteRoot.TrimEnd('/')
    $sisteSkraastrek = $trimmet.LastIndexOf('/')
    if ($sisteSkraastrek -le 0) {
        return "/"
    }
    return $trimmet.Substring(0, $sisteSkraastrek)
}

# Ren beslutningsfunksjon (issue #213, Chief-krav owner-gate) -- nekter
# owner-gate testmodus å target normal produksjon (standard -RemoteRoot,
# /www) med en ureviewet PR-branch sine bytes, MED MINDRE eieren
# eksplisitt har bekreftet det med -OwnerGateAllowProductionTarget. Ren
# streng-/boolsk-sammenligning -- ingen fil-IO/nettverk, testbar isolert.
function Test-OwnerGateMaalErTrygt {
    param(
        [Parameter(Mandatory)][string]$RemoteRoot,
        [Parameter(Mandatory)][string]$StandardRemoteRoot,
        [Parameter(Mandatory)][bool]$AllowProductionTarget
    )
    if ($RemoteRoot -eq $StandardRemoteRoot -and -not $AllowProductionTarget) {
        return [PSCustomObject]@{ ok = $false; reason = "Owner-gate testmodus target standard produksjonssti ($StandardRemoteRoot) uten -OwnerGateAllowProductionTarget. Oppgi -RemoteRoot til en isolert test-sti på Domeneshop, eller bekreft bevisst med -OwnerGateAllowProductionTarget." }
    }
    return [PSCustomObject]@{ ok = $true; reason = "" }
}

# Ren beslutningsfunksjon (issue #213, Chief-krav owner-gate runde 5) --
# avgjør om delta-sjekken (steg 2b, HTTPS mot $BaseUrl = normal produksjon)
# får lov til å kjøre i det hele tatt. Chief-review (PR #216, runde 5)
# påviste at delta-sjekken -- uendret -- ville sammenlignet ALLE lokale
# filer mot LIVE PRODUKSJON selv når -RemoteRoot pekte til en isolert
# owner-gate-teststi: siden denne PR-en per konstruksjon ikke endrer web/,
# ville produksjon allerede matche alle 85 filene, og delta-sjekken ville
# derfor hoppet over dem ALLE -- FØR én eneste fil noensinne nådde den
# faktiske FTPS-bolk-/retry-koden testen er ment å bevise. Owner-gate
# testmodus hopper derfor over delta-sjekken UBETINGET (aldri basert på hva
# produksjon faktisk inneholder) -- ALLE filer sendes til FTPS-opplasting,
# uansett produksjonstilstand. Normal deploy (uten -OwnerGateTestSha) er
# uendret og bruker fortsatt delta-sjekken som før.
function Get-OwnerGateDeltaSjekkBeslutning {
    param([Parameter(Mandatory)][bool]$IsOwnerGateTest)
    if ($IsOwnerGateTest) {
        return [PSCustomObject]@{
            skipDelta = $true
            reason    = "Owner-gate testmodus: delta-sjekk mot produksjon hoppes UBETINGET over -- ALLE filer sendes til FTPS-bolk-opplasting uansett hva produksjon inneholder, slik at testen faktisk beviser den ekte bolk-/retry-implementasjonen mot det isolerte testmålet i stedet for å bli stille hoppet over fordi produksjon allerede matcher (Chief review, PR #216, runde 5)."
        }
    }
    return [PSCustomObject]@{ skipDelta = $false; reason = "" }
}

# curl exit code 67 = CURLE_LOGIN_DENIED -- serveren svarte FTP 530 på
# innlogging. Klassifiseres eksplisitt slik brukeren umiddelbart skjønner
# at dette er en autentiseringsfeil, ikke en tilfeldig nettverks-/filfeil.
function Get-CurlFeilmelding {
    param([int]$ExitCode)
    switch ($ExitCode) {
        67 { return "Innlogging avvist av FTP-serveren (FTP 530) -- feil brukernavn/passord, ELLER en credential-escaping/encoding-feil i scriptet. Se sluttrapporten for hvilket som er sannsynliggjort." }
        9 { return "Serveren nektet tilgang til stien (FTP 550-lignende)." }
        78 { return "Fjern-sti/-mappe finnes ikke på serveren." }
        35 { return "TLS/SSL-håndtrykk feilet." }
        default { return "Se 'curl --help' / curl sin dokumentasjon for exit code $ExitCode." }
    }
}

# Ren beslutningsfunksjon (issue #81) -- tar resultatene fra ETT
# verifiseringspass (allerede beregnet av kalleren -- ingen nettverk/fil-IO
# her) og returnerer hvilke relative stier som trenger et retry-forsøk: alt
# som ikke fikk status "ok" i det passet. Trukket ut til egen funksjon
# (samme mønster som Get-UrentWebInnhold over) slik at selve
# retry-utvelgelsen er testbar uavhengig av det faktiske HTTP-kallet.
function Get-VerifiseringsStierForRetry {
    param([Parameter(Mandatory)][object[]]$Resultater)
    return @($Resultater | Where-Object { -not $_.ok } | ForEach-Object { $_.rel })
}

# Ren beslutningsfunksjon (issue #81) -- slår sammen første passets
# resultater med retry-passets resultater til ett endelig resultatsett per
# fil. En sti som faktisk ble retried får sitt ENDELIGE utfall fra
# retry-resultatet (uansett retning); en sti som ikke trengte retry (var ok
# i pass 1) beholder sitt opprinnelige utfall uendret. Siden $Retry per
# konstruksjon kun inneholder stier Get-VerifiseringsStierForRetry plukket
# ut over (dvs. stier som IKKE var ok i pass 1), kan denne sammenslåingen
# aldri konvertere et uløst avvik til suksess med mindre retry-passets egne
# ferske bytes faktisk matcher -- den STILLER aldri om en fil pass 1 aldri
# rørte.
function Merge-VerifiseringsResultat {
    param(
        [Parameter(Mandatory)][object[]]$Forste,
        [object[]]$Retry = @()
    )
    $retryByRel = @{}
    foreach ($r in $Retry) { $retryByRel[$r.rel] = $r }
    $endelig = @()
    foreach ($f in $Forste) {
        if ($retryByRel.ContainsKey($f.rel)) {
            $endelig += $retryByRel[$f.rel]
        }
        else {
            $endelig += $f
        }
    }
    return @($endelig)
}

# Utfører ETT faktisk verifiseringsforsøk (fersk nedlasting + SHA-256-
# sammenligning) for én fil -- brukt av både første pass og retry-passet
# lenger ned, slik at et retry-forsøk garantert er en FERSK HTTP-hentning
# og aldri gjenbruk av forrige nedlastede fil (issue #81, krav 3). Dette er
# IKKE en ren funksjon (den gjør fil-IO og nettverkskall) -- selve
# beslutningslogikken som ER testbar uten nettverk/fil ligger i
# Get-VerifiseringsStierForRetry/Merge-VerifiseringsResultat over.
function Invoke-DeployFileVerifisering {
    param(
        [Parameter(Mandatory)][string]$Rel,
        [Parameter(Mandatory)][string]$LocalPath,
        [Parameter(Mandatory)][string]$BaseUrl,
        [Parameter(Mandatory)][string]$TempDir
    )
    $url = "$BaseUrl/$Rel"
    $tempFile = Join-Path $TempDir ("f" + [guid]::NewGuid().ToString("N"))
    try {
        Invoke-WebRequest -Uri $url -Method Get -UseBasicParsing -TimeoutSec 20 -OutFile $tempFile
        $localHash = (Get-FileHash -Path $LocalPath -Algorithm SHA256).Hash
        $remoteHash = (Get-FileHash -Path $tempFile -Algorithm SHA256).Hash
        if ($localHash -eq $remoteHash) {
            return [PSCustomObject]@{ rel = $Rel; ok = $true; reason = "ok"; localHash = $localHash; remoteHash = $remoteHash; error = $null }
        }
        return [PSCustomObject]@{ rel = $Rel; ok = $false; reason = "mismatch"; localHash = $localHash; remoteHash = $remoteHash; error = $null }
    }
    catch {
        return [PSCustomObject]@{ rel = $Rel; ok = $false; reason = "unverifiable"; localHash = $null; remoteHash = $null; error = $_.Exception.Message }
    }
    finally {
        if (Test-Path $tempFile) { Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue }
    }
}

# Ren beslutningsfunksjon (issue #213) -- klassifiserer om en curl-
# avslutningskode er FORBIGÅENDE (verdt ett bounded retry) eller en EKTE
# feil (skal stoppe deployen umiddelbart, akkurat som før). Bevisst
# selvstendig/uten ekstern konstant (i motsetning til f.eks. å referere en
# script-scope-variabel) -- testene dot-sourcer denne funksjonens tekst
# ALENE, samme mønster som de andre rene hjelpefunksjonene over, og en
# ekstern avhengighet ville da vært usynlig for testen.
#
# 56 (CURLE_RECV_ERROR) er nøyaktig feilen issue #213 observerte gjentatte
# ganger ved høy tilkoblingsrate (serveren sluttet å svare under mottak av
# responsen etter en ellers fullført opplasting). 55 (CURLE_SEND_ERROR) og
# 18 (CURLE_PARTIAL_FILE) er nært beslektede forbigående nettverksglipp av
# samme (sende/motta) karakter. BEVISST IKKE inkludert: 67 (feil
# credentials/FTP 530), 9 (tilgang nektet), 78 (mangler fjern-sti), 35
# (TLS-håndtrykk feilet) -- dette er ekte feil som aldri skal maskeres av
# et automatisk retry-forsøk.
function Test-ForbigaendeCurlFeil {
    param([Parameter(Mandatory)][int]$ExitCode)
    return @(55, 56, 18) -contains $ExitCode
}

# Ren funksjon (issue #213) -- deler en filliste inn i bolker av maks
# $BolkStorrelse filer hver (siste bolk kan være mindre). Brukt til å
# begrense antall FTPS-tilkoblinger per deploy: én curl.exe-prosess (og
# dermed én potensielt gjenbrukt FTPS-tilkobling for alle filene i den
# bolken) i stedet for én prosess/tilkobling per fil.
function Split-FilerIBolker {
    param(
        [Parameter(Mandatory)][object[]]$Filer,
        [Parameter(Mandatory)][int]$BolkStorrelse
    )
    $bolker = @()
    for ($idx = 0; $idx -lt $Filer.Count; $idx += $BolkStorrelse) {
        $slutt = [Math]::Min($idx + $BolkStorrelse, $Filer.Count) - 1
        $bolker += , @($Filer[$idx..$slutt])
    }
    return @($bolker)
}

# Ren funksjon (issue #213, Chief review PR #216, runde 8) -- en reell
# owner-gate-test mot Domeneshop (eksakt hode 3bff6d2c...) viste at SELV
# reverifisering+ett bounded retry (se hovedscriptets steg 5c) ikke alltid er
# nok: to bolker à 10 filer på rad traff vedvarende "server did not report
# OK, got 426" / curl exit 18 igjen etter retry, og scriptet stoppet HELE
# deployen ved fil 20/85 med ingen vei videre. Returnerer en DEGRADERENDE
# sekvens av bolkstørrelser fra $StartStorrelse (halvert for hvert steg,
# avrundet ned, gulv 1, ingen duplikater) -- f.eks. 10 -> [10, 5, 2, 1].
# Brukt av steg 5c til å falle tilbake til MINDRE bolker (til slutt ÉN fil
# per curl.exe-prosess -- helt uten --next) for KUN de filene som fortsatt
# ikke kom gjennom etter at en gitt bolkstørrelse har brukt opp sine bounded
# forsøk, i stedet for å stoppe hele deployen der. Hypotesen (kan IKKE
# bekreftes empirisk i denne sandkassen, se
# tests/test_deploy_web_batch_upload.py): en mindre bolk (færre
# --next-adskilte overføringer per kontrollforbindelse, til slutt INGEN
# --next i det hele tatt ved gulvstørrelse 1) er mindre sårbar for hva enn
# som faktisk trigger 426 på tvers av gjentatte overføringer i samme
# curl.exe-prosess mot akkurat denne serveren. Ekte (ikke-forbigående)
# curl-feil degraderer ALDRI -- de stopper fortsatt deployen umiddelbart,
# uansett bolkstørrelse, akkurat som før (se steg 5c).
function Get-DegraderteBolkStorrelser {
    param([Parameter(Mandatory)][int]$StartStorrelse)
    $storrelser = New-Object System.Collections.Generic.List[int]
    $s = $StartStorrelse
    while ($s -gt 1) {
        $storrelser.Add($s)
        $s = [Math]::Floor($s / 2)
    }
    $storrelser.Add(1)
    return @($storrelser)
}

# Bygger INNHOLDET til ÉN curl -K configfil som laster opp flere filer i
# samme curl.exe-prosess, adskilt med --next (issue #213) -- curl
# gjenbruker kontrollforbindelsen til samme FTPS-server på tvers av
# --next-adskilte overføringer i samme prosess der det er mulig, i stedet
# for å åpne en helt ny FTPS-innlogging/TLS-håndtrykk per fil (root cause
# for det observerte tilkoblingstaket rundt ~50 tilkoblinger). --ssl-reqd
# og --ftp-create-dirs gjentas EKSPLISITT for HVER fil i stedet for å
# stole på at de arves på tvers av --next -- --ssl-reqd er et
# obligatorisk FTPS-krav (se .DESCRIPTION), og skal derfor aldri hvile på
# en antakelse om curl sin arve-semantikk mellom --next-blokker.
# $BrukerLinje (`user = "..."`) gjentas AV SAMME GRUNN i HVER --next-blokk
# -- curl sin egen dokumentasjon sier eksplisitt at --next nullstiller
# alle ikke-globale opsjoner, og --user/-K sin `user = ...`-linje er IKKE
# global (https://curl.se/docs/manpage.html#--next). Uten denne
# repetisjonen ville kun overføring 1 i bolken faktisk fått eksplisitt
# FTPS-credentials -- overføring 2+ ville stolt på en antakelse om
# arve-semantikk curl selv sier ikke gjelder (Chief review, PR #216).
# Ren tekstbygging -- ingen fil-IO/nettverk her (testbar uten curl/nettverk,
# samme mønster som de andre rene hjelpefunksjonene over). Gjenbruker
# Get-CurlConfigEscaped (samme escaping som credential-linjen) for både
# lokal sti og fjern-URL, i stedet for å duplisere escaping-logikken.
function New-BolkOpplastingConfig {
    param(
        [Parameter(Mandatory)][string]$BrukerLinje,
        [Parameter(Mandatory)][object[]]$Filer,
        [Parameter(Mandatory)][string]$FtpHost,
        [Parameter(Mandatory)][string]$RemoteRoot
    )
    $blokker = @()
    foreach ($f in $Filer) {
        $escapedLocal = Get-CurlConfigEscaped $f.FullName
        $escapedUrl = Get-CurlConfigEscaped "ftp://$FtpHost$RemoteRoot/$($f.rel)"
        $blokker += @(
            $BrukerLinje
            "url = `"$escapedUrl`""
            "--ssl-reqd"
            "--ftp-create-dirs"
            "-T `"$escapedLocal`""
        ) -join "`n"
    }
    return (($blokker -join "`n--next`n") + "`n")
}

# Ren tekstbygging (issue #213, Chief-krav owner-gate runde 5) -- FTPS-
# nedlastingsmotstykket til New-BolkOpplastingConfig over: bygger INNHOLDET
# til ÉN curl -K configfil som laster NED flere filer (GET, ikke PUT/-T) i
# samme curl.exe-prosess, adskilt med --next, brukt KUN av
# Invoke-DeployBolkVerifiseringFtps under. Samme begrunnelse for repetisjon
# av credential-linjen og --ssl-reqd i HVER blokk som opplastings-
# motstykket (curl sin dokumentasjon: --next nullstiller alle ikke-globale
# opsjoner). Ingen fil-IO/nettverk her -- testbar isolert, samme mønster.
function New-BolkNedlastingConfig {
    param(
        [Parameter(Mandatory)][string]$BrukerLinje,
        [Parameter(Mandatory)][object[]]$Filer,
        [Parameter(Mandatory)][string]$FtpHost,
        [Parameter(Mandatory)][string]$RemoteRoot
    )
    $blokker = @()
    foreach ($f in $Filer) {
        $escapedUrl = Get-CurlConfigEscaped "ftp://$FtpHost$RemoteRoot/$($f.rel)"
        $escapedOut = Get-CurlConfigEscaped $f.TempFile
        $blokker += @(
            $BrukerLinje
            "url = `"$escapedUrl`""
            "--ssl-reqd"
            "-o `"$escapedOut`""
        ) -join "`n"
    }
    return (($blokker -join "`n--next`n") + "`n")
}

# Utfører ETT faktisk FTPS-verifiseringsforsøk (fersk nedlasting via
# curl.exe + SHA-256-sammenligning) for ÉN fil -- FTPS-motstykket til
# Invoke-DeployFileVerifisering over, brukt KUN i owner-gate testmodus
# (issue #213, Chief review, PR #216, runde 5). $BaseUrl (hardkodet
# https://kvernhaugbrygghus.no, dvs. normal produksjon/-www) beviser
# ingenting om en isolert -RemoteRoot-teststi -- en slik sti har ingen
# garantert HTTPS-adresse i det hele tatt. Laster i stedet ned filen over
# FTPS, fra nøyaktig $RemoteRoot (samme mål opplastingen skrev til) --
# beviser dermed bytene som FAKTISK ligger på det ekte testmålet, ikke
# produksjon. Brukt for enkeltfiler (bolk-reverifisering før retry i steg
# 5c, og retry-passet i steg 6) -- se Invoke-DeployBolkVerifiseringFtps for
# den bolkvise (--next-batchede) varianten som brukes for HELE filsettet i
# steg 6, slik at verifiseringen ikke selv åpner én FTPS-tilkobling per fil
# og dermed reintroduserer akkurat det tilkoblingstaket issue #213 fikset
# for opplastingen.
function Invoke-DeployFileVerifiseringFtps {
    param(
        [Parameter(Mandatory)][string]$Rel,
        [Parameter(Mandatory)][string]$LocalPath,
        [Parameter(Mandatory)][string]$CurlConfigPath,
        [Parameter(Mandatory)][string]$FtpHost,
        [Parameter(Mandatory)][string]$RemoteRoot,
        [Parameter(Mandatory)][string]$TempDir
    )
    $remoteUrl = "ftp://$FtpHost$RemoteRoot/$Rel"
    $tempFile = Join-Path $TempDir ("f" + [guid]::NewGuid().ToString("N"))
    try {
        & curl.exe -K $CurlConfigPath --ssl-reqd --silent --show-error -o $tempFile $remoteUrl
        $curlExit = $LASTEXITCODE
        if ($curlExit -ne 0 -or -not (Test-Path $tempFile)) {
            return [PSCustomObject]@{ rel = $Rel; ok = $false; reason = "unverifiable"; localHash = $null; remoteHash = $null; error = "curl exit code $curlExit ved FTPS-nedlasting av $remoteUrl" }
        }
        $localHash = (Get-FileHash -Path $LocalPath -Algorithm SHA256).Hash
        $remoteHash = (Get-FileHash -Path $tempFile -Algorithm SHA256).Hash
        if ($localHash -eq $remoteHash) {
            return [PSCustomObject]@{ rel = $Rel; ok = $true; reason = "ok"; localHash = $localHash; remoteHash = $remoteHash; error = $null }
        }
        return [PSCustomObject]@{ rel = $Rel; ok = $false; reason = "mismatch"; localHash = $localHash; remoteHash = $remoteHash; error = $null }
    }
    finally {
        if (Test-Path $tempFile) { Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue }
    }
}

# Bolkvis (batched) FTPS-nedlasting + SHA-256-sammenligning for et HELT
# filsett i bolker à maks $BolkStorrelse filer, ÉN curl.exe-prosess per
# bolk (issue #213, Chief review, PR #216, runde 5) -- brukt for
# førstepasset i owner-gate testmodus sin produksjonsverifisering (steg 6),
# der filsettet kan være alle 85 filene. Ett individuelt curl-kall per fil
# (slik Invoke-DeployFileVerifiseringFtps over gjør for det typisk små
# retry-settet) ville for HELE filsettet reintrodusert nøyaktig det FTPS-
# tilkoblingstaket denne saken opprinnelig fikset for selve opplastingen --
# samme bolk-/--next-gjenbruksmekanisme som New-BolkOpplastingConfig brukes
# derfor her også, for nedlasting. Returnerer samme resultatform som
# Invoke-DeployFileVerifisering/-Ftps (rel/ok/reason/localHash/remoteHash/
# error) slik at Get-VerifiseringsStierForRetry/Merge-VerifiseringsResultat
# kan gjenbrukes uendret for retry-utvelgelse og sammenslåing.
function Invoke-DeployBolkVerifiseringFtps {
    param(
        [Parameter(Mandatory)][object[]]$Filer,
        [Parameter(Mandatory)][string]$BrukerLinje,
        [Parameter(Mandatory)][string]$FtpHost,
        [Parameter(Mandatory)][string]$RemoteRoot,
        [Parameter(Mandatory)][int]$BolkStorrelse,
        [Parameter(Mandatory)][string]$TempDir
    )
    $resultater = @()
    $bolker = @(Split-FilerIBolker -Filer $Filer -BolkStorrelse $BolkStorrelse)
    foreach ($bolk in $bolker) {
        $bolkMedTemp = @($bolk | ForEach-Object {
            [PSCustomObject]@{ rel = $_.rel; FullName = $_.FullName; TempFile = (Join-Path $TempDir ("f" + [guid]::NewGuid().ToString("N"))) }
        })
        $bolkConfigInnhold = New-BolkNedlastingConfig -BrukerLinje $BrukerLinje -Filer $bolkMedTemp -FtpHost $FtpHost -RemoteRoot $RemoteRoot
        $bolkConfigPath = [System.IO.Path]::GetTempFileName()
        [System.IO.File]::WriteAllText($bolkConfigPath, $bolkConfigInnhold, (New-Object System.Text.UTF8Encoding($false)))
        try {
            & curl.exe -K $bolkConfigPath --silent --show-error
            $bolkExitCode = $LASTEXITCODE
        }
        finally {
            if (Test-Path $bolkConfigPath) { Remove-Item -Path $bolkConfigPath -Force -ErrorAction SilentlyContinue }
        }
        foreach ($f in $bolkMedTemp) {
            if (-not (Test-Path $f.TempFile)) {
                $resultater += [PSCustomObject]@{ rel = $f.rel; ok = $false; reason = "unverifiable"; localHash = $null; remoteHash = $null; error = "curl exit code $bolkExitCode ved bolkvis FTPS-nedlasting (fil ikke mottatt)." }
                continue
            }
            $localHash = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash
            $remoteHash = (Get-FileHash -Path $f.TempFile -Algorithm SHA256).Hash
            Remove-Item -Path $f.TempFile -Force -ErrorAction SilentlyContinue
            if ($localHash -eq $remoteHash) {
                $resultater += [PSCustomObject]@{ rel = $f.rel; ok = $true; reason = "ok"; localHash = $localHash; remoteHash = $remoteHash; error = $null }
            }
            else {
                $resultater += [PSCustomObject]@{ rel = $f.rel; ok = $false; reason = "mismatch"; localHash = $localHash; remoteHash = $remoteHash; error = $null }
            }
        }
    }
    return @($resultater)
}

# ─── 1. Finn repo-root/web robust ──────────────────────────────────────────
# Scriptet ligger alltid i <repo>\scripts\deploy_web.ps1 -- repo-roten er
# derfor alltid dens foreldre-mappe, uansett hvor brukeren selv står når
# scriptet startes. Ingen avhengighet av working directory.
$ScriptDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $ScriptDir
$WebRoot = Join-Path $RepoRoot "web"

if (-not (Test-Path $WebRoot)) {
    Write-Error "Fant ikke web/ under antatt repo-root ($WebRoot). Kjør scriptet som scripts\deploy_web.ps1 fra en normal klone av repoet."
    exit 1
}
if (-not (Test-Path (Join-Path $WebRoot "index.html"))) {
    Write-Error "web\index.html mangler under $WebRoot -- dette ser ikke ut som riktig web-runtime. Avbryter uten å gjøre noe."
    exit 1
}

# ─── 1a2. Guard: owner-gate testmodus kan ikke stille target produksjon ────
# Se .DESCRIPTION for bakgrunnen (issue #213, Chief-krav). Ren
# parameter-sjekk -- ingen git/nettverk -- kjøres derfor tidligst mulig,
# før noe som helst annet arbeid gjøres. Rører ingenting når
# -OwnerGateTestSha ikke er oppgitt (normal deploy, helt uendret).
$isOwnerGateTest = -not [string]::IsNullOrWhiteSpace($OwnerGateTestSha)
if ($isOwnerGateTest) {
    if ([string]::IsNullOrWhiteSpace($OwnerGateTestBranch)) {
        Write-Host ""
        Write-Host "STOPPER: -OwnerGateTestBranch må oppgis eksplisitt sammen med -OwnerGateTestSha."
        Write-Host "  Branchen kan ALDRI utledes fra checkouten selv -- owner-gate-testen kjøres"
        Write-Host "  typisk fra en frikoblet (detached HEAD) test-worktree, der det ikke finnes"
        Write-Host "  noe lokalt branch-navn å lese (se .DESCRIPTION)."
        Write-Host ""
        Write-Error "Ingen filer ble lastet opp -- -OwnerGateTestBranch mangler."
        exit 1
    }
    $maalSjekk = Test-OwnerGateMaalErTrygt -RemoteRoot $RemoteRoot -StandardRemoteRoot "/www" -AllowProductionTarget ([bool]$OwnerGateAllowProductionTarget)
    if (-not $maalSjekk.ok) {
        Write-Host ""
        Write-Host "STOPPER: $($maalSjekk.reason)"
        Write-Host ""
        Write-Error "Ingen filer ble lastet opp -- owner-gate mål-guard feilet."
        exit 1
    }
}

# ─── 1b. Guard: nekt å deploye fra en checkout som ikke matcher origin/master ──
# Se .DESCRIPTION for bakgrunnen (issue #28). Kjøres FØR filer i det hele
# tatt listes -- fail fast, ingen grunn til å bygge en filliste fra en
# checkout som uansett skal avvises. Owner-gate testmodus (issue #213,
# under) ERSTATTER denne sammenligningen med en snevrere, eksplisitt
# SHA-binding -- normal deploy (uten -OwnerGateTestSha) tar ALLTID else-
# grenen under, helt uendret fra før.
$gitCmd = Get-Command git.exe -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    Write-Error "git.exe ble ikke funnet i PATH. Kan ikke bekrefte at denne checkouten matcher origin/master -- avbryter uten å gjøre noe."
    exit 1
}

Push-Location $RepoRoot
try {
    if ($isOwnerGateTest) {
        # $OwnerGateTestBranch (eksplisitt parameter, validert over) -- ALDRI
        # utledet via `git rev-parse --abbrev-ref HEAD`. En tidligere versjon
        # gjorde nettopp det, som returnerer den literale strengen "HEAD" fra
        # en frikoblet (detached) checkout -- akkurat den tilstanden
        # owner-gate-testen typisk kjøres fra, siden -OwnerGateTestSha binder
        # testen til en eksakt commit, ikke en branch. `origin/HEAD` er
        # deretter git sin symbolske peker til origin-repoets STANDARD-branch
        # (master) -- ikke PR-branchen -- så guarden sammenlignet stille
        # master mot PR-SHA-en i stedet for PR-branchens faktiske head
        # (Chief review, PR #216, runde 4). Et rent strengparameter har ingen
        # slik avhengighet av lokal branch-tilstand.
        $localBranch = $OwnerGateTestBranch
        $localHead = (& git rev-parse HEAD).Trim()
        $originBranchRefKjentFersk = $false
        $originBranchRef = $null

        if (-not $DryRun) {
            # Fersk fetch KUN utenfor DryRun -- samme dokumenterte
            # 0-nettverkstilkoblinger-kontrakt som normalguarden under.
            Write-Host "--- Owner-gate: henter fersk origin/$localBranch for å bekrefte PR-head ---"
            & git fetch origin $localBranch --quiet
            if ($LASTEXITCODE -ne 0) {
                Write-Error "git fetch origin $localBranch feilet -- kan ikke bekrefte fersk PR-head. Avbryter uten å laste opp noe."
                exit 1
            }
            $originBranchRefKjentFersk = $true
            $originBranchRefRaw = & git rev-parse "origin/$localBranch" 2>$null
            if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($originBranchRefRaw)) {
                $originBranchRef = $originBranchRefRaw.Trim()
            }
        }

        $forutsetning = Test-OwnerGateForutsetninger -ExpectedSha $OwnerGateTestSha -LocalHead $localHead -OriginBranchNavn $localBranch -OriginBranchRef $originBranchRef -OriginBranchRefKjentFersk $originBranchRefKjentFersk

        if (-not $forutsetning.ok) {
            Write-Host ""
            Write-Host "STOPPER: owner-gate-forutsetning ikke oppfylt."
            Write-Host "  $($forutsetning.reason)"
            Write-Host ""
            Write-Error "Ingen filer ble lastet opp -- owner-gate SHA-verifisering feilet."
            exit 1
        }
        Write-Host "Owner-gate OK -- $($forutsetning.reason)"
        Write-Host "ADVARSEL: owner-gate testmodus er aktiv -- dette er IKKE en normal produksjonsdeploy."
        Write-Host ""
    }
    else {
        if (-not $DryRun) {
            # Fersk fetch KUN utenfor DryRun -- DryRun skal fortsatt gjøre 0
            # nettverkstilkoblinger (dets egen dokumenterte kontrakt). Den
            # faktiske FTP-deployen er der skaden faktisk kan skje, så DER skal
            # sammenligningen være garantert fersk, ikke avhengig av at brukeren
            # husket å `git fetch` manuelt på forhånd (nøyaktig det som gikk galt
            # forrige gang).
            Write-Host "--- Guard: henter fersk origin/master for å bekrefte checkouten ---"
            & git fetch origin master --quiet
            if ($LASTEXITCODE -ne 0) {
                Write-Error "git fetch origin master feilet -- kan ikke bekrefte at denne checkouten er oppdatert. Avbryter uten å laste opp noe."
                exit 1
            }
        }

        $localHead = (& git rev-parse HEAD).Trim()
        $originMasterRef = (& git rev-parse origin/master).Trim()

        if ([string]::IsNullOrWhiteSpace($localHead) -or [string]::IsNullOrWhiteSpace($originMasterRef)) {
            Write-Error "Kunne ikke lese HEAD og/eller origin/master fra git i $RepoRoot -- er dette faktisk en git-klone av kvernhaug-brygghus, med en 'origin'-remote? Avbryter uten å gjøre noe."
            exit 1
        }

        if ($localHead -ne $originMasterRef) {
            $counts = (& git rev-list --left-right --count "HEAD...origin/master").Trim()
            Write-Host ""
            Write-Host "STOPPER: denne checkouten matcher IKKE origin/master."
            Write-Host "  HEAD:          $localHead"
            Write-Host "  origin/master: $originMasterRef"
            Write-Host "  ahead/behind (HEAD...origin/master): $counts"
            Write-Host ""
            Write-Host "web/ under denne checkouten kan avvike fra hva som faktisk er merget og"
            Write-Host "godkjent -- en deploy herfra kan laste opp feil innhold til produksjon"
            Write-Host "(nøyaktig det som skjedde med issue #28). Kjør scriptet fra en"
            Write-Host "checkout/worktree hvis HEAD er identisk med origin/master."
            if ($DryRun) {
                Write-Host ""
                Write-Host "(DryRun sammenlignet mot sist kjente origin/master uten å hente på nytt --"
                Write-Host " kjør uten -DryRun, eller 'git fetch' manuelt her først, for en garantert"
                Write-Host " fersk sammenligning.)"
            }
            Write-Host ""
            Write-Error "Ingen filer ble lastet opp -- checkout matcher ikke origin/master."
            exit 1
        }
        Write-Host "Guard OK -- HEAD matcher origin/master ($localHead)."
        Write-Host ""
    }
}
finally {
    Pop-Location
}

# ─── 1c. Guard: nekt å deploye urent/ukommittert innhold under web/ ────────
# Se .DESCRIPTION for bakgrunnen (issue #72). Guarden over (1b) beviser kun
# at COMMITTED historikk (HEAD) matcher origin/master -- den sier ingenting
# om working tree/index. Scriptet laster likevel opp CURRENT WORKING-TREE-
# bytes, og INNHOLDSVERIFISERINGEN lenger ned sammenligner produksjon mot
# akkurat de samme lokale bytene den selv nettopp lastet opp -- den kan
# derfor aldri oppdage en ukommittert web/-endring på egen hånd. Denne
# guarden kjører derfor FØR filene i det hele tatt listes, dekker
# modifisert/staget/slettet/untracked i ett `git status --porcelain`-kall
# (dirtighet vises via OUTPUT, ikke exit code), og kjører også under
# -DryRun (ren lokal git-sjekk, ingen tilkobling) slik at DryRun faktisk
# reflekterer om en ekte deploy ville blitt avvist.
#
# --ignored=matching (Chief review, PR #73): reposet ignorerer *.log/*.tmp
# globalt (.gitignore), men fillistingen i steg 2 under (Get-ChildItem
# -Recurse -File) enumererer og laster opp ALT under web/ uansett
# .gitignore -- den kjenner ingen git-tilstand i det hele tatt. Uten dette
# flagget er en ignorert-men-deployable fil (f.eks. en lokal web/foo.log
# eller web/foo.tmp) usynlig for `git status --porcelain` (ignorerte filer
# vises kun via OUTPUT når --ignored eksplisitt er satt), så guarden ville
# sluppet den gjennom mens opplastingen likevel tar den med. --ignored=matching
# (fremfor default "traditional"-modus) sikrer at hver enkelt ignorert sti
# rapporteres eksplisitt i stedet for kollapset til et katalognavn der det
# er mulig, uten å endre hvordan modifisert/staget/slettet/untracked
# innhold allerede rapporteres.
#
# Samme deployable-fil-semantikk som eksklusjonslisten i steg 2 under
# ($ExcludeRelative, definert her og gjenbrukt der) -- web/README.md og
# web/CHANGELOG.md er utviklerdokumentasjon, aldri deployet, og skal derfor
# aldri i seg selv blokkere en deploy. Filer utenfor web/ (f.eks. eierens
# tiltenkte lokale endring i raw_data/unmatched_malt.json) berøres ikke i
# det hele tatt, siden git-kallet er pathspec-avgrenset til web/.
$ExcludeRelative = @("README.md", "CHANGELOG.md")

Push-Location $RepoRoot
try {
    $porcelain = & git status --porcelain --ignored=matching -- web/
    if ($LASTEXITCODE -ne 0) {
        Write-Error "git status --porcelain feilet for web/ -- kan ikke bekrefte at working tree/index er rent. Avbryter uten å gjøre noe."
        exit 1
    }
}
finally {
    Pop-Location
}

$dirtyDeployPaths = Get-UrentWebInnhold -PorcelainLinjer $porcelain -EkskluderteWebRelativeStier $ExcludeRelative

if ($dirtyDeployPaths.Count -gt 0) {
    Write-Host ""
    Write-Host "STOPPER: urent/ukommittert innhold funnet under web/ (deployable filer)."
    foreach ($p in $dirtyDeployPaths) { Write-Host "  $p" }
    Write-Host ""
    Write-Host "Scriptet laster opp CURRENT WORKING-TREE-bytes, og produksjonsverifiseringen"
    Write-Host "lenger ned sammenligner kun mot de samme lokale bytene -- den kan derfor IKKE"
    Write-Host "oppdage en ukommittert web/-endring den selv nettopp lastet opp."
    Write-Host "Commit, fjern fra staging (git restore --staged), eller rydd opp disse"
    Write-Host "filene, og prøv igjen."
    Write-Error "Ingen filer ble lastet opp -- urent web/-innhold (deployable filer)."
    exit 1
}
Write-Host "Guard OK -- web/ (deployable innhold) er rent i working tree/index."
Write-Host ""

# ─── 2. Runtime-filliste (full sync, eksplisitt exclude-liste) ────────────
# Alt under web/ ER runtime bortsett fra disse to -- se web/README.md.
$AllFiles = Get-ChildItem -Path $WebRoot -Recurse -File
$DeployFiles = @($AllFiles | Where-Object {
    $rel = $_.FullName.Substring($WebRoot.Length + 1) -replace '\\', '/'
    $ExcludeRelative -notcontains $rel
} | Sort-Object FullName)

if ($DeployFiles.Count -eq 0) {
    Write-Error "Fant 0 filer å deploye under $WebRoot. Noe er galt -- avbryter."
    exit 1
}

$TotalBytes = ($DeployFiles | Measure-Object -Property Length -Sum).Sum
$TotalMB = [math]::Round($TotalBytes / 1MB, 2)

Write-Host "SOURCE: $WebRoot"
Write-Host "TARGET: $FtpHost`:$RemoteRoot"
Write-Host "Filer:  $($DeployFiles.Count) stk, $TotalMB MB"
Write-Host "Ekskludert (utviklerdokumentasjon): $($ExcludeRelative -join ', ')"
Write-Host ""

if ($DryRun) {
    Write-Host "--- DRY RUN: ingen tilkobling gjøres, 0 endringer ---"
    foreach ($f in $DeployFiles) {
        $rel = $f.FullName.Substring($WebRoot.Length + 1) -replace '\\', '/'
        Write-Host "  $rel"
    }
    Write-Host ""
    Write-Host "$($DeployFiles.Count) filer ville blitt lastet opp til $FtpHost$RemoteRoot. 0 filer faktisk overført."
    exit 0
}

# ─── 2b. Delta-sjekk: hopp over filer som allerede matcher produksjon ──────
# Se .DESCRIPTION for bakgrunnen (issue #213). Kjøres FØR curl-
# avhengighetssjekken/bekreftelsen/credentials under -- bruker SAMME
# read-only HTTPS-mekanisme (Invoke-DeployFileVerifisering, samme funksjon
# INNHOLDSVERIFISERINGEN i steg 6 bruker) til å sammenligne hver lokal fil
# mot produksjon FØR noen FTPS-tilkobling i det hele tatt åpnes -- krever
# derfor ingen credentials. Kun filer som faktisk AVVIKER (eller ikke kan
# verifiseres, f.eks. en ny fil som ennå ikke finnes på produksjon) sendes
# videre til FTPS-opplastingen i steg 5c -- filer som allerede matcher
# produksjon rører aldri FTPS-tilkoblingen.
#
# Ligger bevisst ETTER DryRun sin "exit 0" over -- DryRuns dokumenterte
# kontrakt er 0 tilkoblinger, og denne seksjonen gjør ekte HTTPS-kall.
#
# Get-VerifiseringsStierForRetry gjenbrukes bevisst her (samme "resultat
# var ikke ok"-seleksjon som steg 6 bruker for retry-utvelgelse -- "trenger
# (første) opplasting" og "trenger et nytt forsøk" er samme beslutning på
# samme resultatform, ikke to parallelle implementasjoner).
$BaseUrl = "https://kvernhaugbrygghus.no"

$DeltaKandidatFiler = @($DeployFiles | ForEach-Object {
    $rel = $_.FullName.Substring($WebRoot.Length + 1) -replace '\\', '/'
    [PSCustomObject]@{ rel = $rel; FullName = $_.FullName }
})

$deltaBeslutning = Get-OwnerGateDeltaSjekkBeslutning -IsOwnerGateTest $isOwnerGateTest
if ($deltaBeslutning.skipDelta) {
    Write-Host "--- Delta-sjekk hoppet over (owner-gate testmodus) ---"
    Write-Host "  $($deltaBeslutning.reason)"
    $FilesToUpload = $DeltaKandidatFiler
    $SkippedCount = 0
}
else {
    Write-Host ("--- Delta-sjekk: sammenligner {0} lokale filer mot produksjon over HTTPS (0 FTPS-tilkoblinger) ---" -f $DeployFiles.Count)

    $deltaTempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("kbh_deploy_delta_" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $deltaTempDir | Out-Null
    try {
        $deltaResultater = @()
        foreach ($fc in $DeltaKandidatFiler) {
            $deltaResultater += Invoke-DeployFileVerifisering -Rel $fc.rel -LocalPath $fc.FullName -BaseUrl $BaseUrl -TempDir $deltaTempDir
        }
    }
    finally {
        Remove-Item -Path $deltaTempDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    $filesToUploadRels = @(Get-VerifiseringsStierForRetry -Resultater $deltaResultater)
    $FilesToUpload = @($DeltaKandidatFiler | Where-Object { $filesToUploadRels -contains $_.rel })
    $SkippedCount = $DeployFiles.Count - $FilesToUpload.Count
}

Write-Host ("Delta-sjekk OK -- {0} av {1} filer er allerede identisk med produksjon (hoppes over). {2} fil(er) skal lastes opp over FTPS." -f $SkippedCount, $DeployFiles.Count, $FilesToUpload.Count)
Write-Host ""

# ─── 3. Dependency-sjekk ────────────────────────────────────────────────────
$curlCmd = Get-Command curl.exe -ErrorAction SilentlyContinue
if (-not $curlCmd) {
    Write-Error "curl.exe ble ikke funnet i PATH. Dette scriptet krever curl med FTPS-støtte (bekreftet tilgjengelig: curl 8.21+ med Schannel/SSL på denne maskinen normalt)."
    exit 1
}

# ─── 4. Bekreftelse (default NO) ───────────────────────────────────────────
if (-not $Force) {
    if ($FilesToUpload.Count -lt $DeployFiles.Count) {
        $promptTekst = "Deploy $($FilesToUpload.Count) av $($DeployFiles.Count) fil(er) (resten er allerede identisk med produksjon) fra $WebRoot til ${FtpHost}:${RemoteRoot} ? [y/N]"
    }
    else {
        $promptTekst = "Deploy $($DeployFiles.Count) filer fra $WebRoot til ${FtpHost}:${RemoteRoot} ? [y/N]"
    }
    $answer = Read-Host $promptTekst
    if ($answer -ne "y" -and $answer -ne "Y") {
        Write-Host "Avbrutt -- ingen filer lastet opp."
        exit 0
    }
}

# ─── 5. Credentials (aldri lagret, aldri logget) ───────────────────────────
if (-not $FtpUser) {
    $FtpUser = Read-Host "FTP-brukernavn"
}
if ([string]::IsNullOrWhiteSpace($FtpUser)) {
    Write-Error "Ingen FTP-brukernavn oppgitt. Avbryter."
    exit 1
}

$securePass = Read-Host "FTP-passord" -AsSecureString
if ($securePass.Length -eq 0) {
    Write-Error "Ingen FTP-passord oppgitt. Avbryter."
    exit 1
}
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePass)
$plainPass = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

# curl sin -K configfil holder brukernavn/passord UTENFOR kommandolinjen
# (og dermed utenfor prosesslister/historikk) -- eneste sted credentials
# eksisterer på disk, og kun midlertidig, slettet i finally under uansett
# hvilken vei scriptet avslutter (suksess, preflight-feil, upload-feil).
$curlConfigPath = [System.IO.Path]::GetTempFileName()
$exitCode = 0

try {
    $escapedUser = Get-CurlConfigEscaped $FtpUser
    $escapedPass = Get-CurlConfigEscaped $plainPass
    $configContent = "user = `"$escapedUser`:$escapedPass`""
    # Skrives UTEN BOM med .NET direkte (ikke Set-Content -Encoding, som i
    # Windows PowerShell 5.1 kan prepende en UTF-8 BOM) -- curl sin
    # config-parser forventer ren tekst fra første byte; en BOM foran
    # "user = ..." kan hindre curl i å gjenkjenne linjen som gyldig i det
    # hele tatt, med samme sluttresultat (530) som en korrupt credential.
    [System.IO.File]::WriteAllText($curlConfigPath, $configContent, (New-Object System.Text.UTF8Encoding($false)))
    $plainPass = $null
    $escapedPass = $null

    # ─── 5b. Login-preflight -- 0 writes ────────────────────────────────
    # Én liten read-only listing av target-mappen for å bekrefte at
    # innloggingen faktisk fungerer FØR noen av de 50 filene røres. I
    # owner-gate-modus listes i stedet $RemoteRoot sin FORELDER-mappe (se
    # Get-OwnerGatePreflightSti) -- et FERSKT isolert testmål finnes ikke
    # ennå og opprettes først av selve opplastingen (--ftp-create-dirs).
    Write-Host ""
    Write-Host "--- Preflight: verifiserer FTP-innlogging (read-only, 0 writes) ---"
    $preflightSti = Get-OwnerGatePreflightSti -RemoteRoot $RemoteRoot -IsOwnerGateTest $isOwnerGateTest
    & curl.exe -K $curlConfigPath --ssl-reqd --silent --show-error -o "NUL" "ftp://$FtpHost$preflightSti/"
    $preflightExit = $LASTEXITCODE

    if ($preflightExit -ne 0) {
        Write-Host ""
        Write-Host "FTP-innlogging feilet. Ingen filer ble lastet opp."
        Write-Host ("curl exit code {0}: {1}" -f $preflightExit, (Get-CurlFeilmelding $preflightExit))
        $exitCode = 1
    }
    else {
        Write-Host "Preflight OK -- innlogging fungerer."
        Write-Host ""
        if ($FilesToUpload.Count -eq 0) {
            Write-Host ("--- Ingen filer å laste opp -- alle {0} filer er allerede identisk med produksjon (delta-sjekk, steg 2b) ---" -f $DeployFiles.Count)
        }
        else {
            # ─── 5c. Bolk-basert opplasting (issue #213) ───────────────────
            # Én curl.exe-prosess per bolk i stedet for én prosess/FTPS-
            # tilkobling per fil -- se .DESCRIPTION og New-BolkOpplastingConfig
            # for begrunnelsen. --fail-early: HELE bolk-invokeringen stopper
            # ved første feilede overføring i bolken (bevarer det eksisterende
            # "stopper umiddelbart ved første feil"-prinsippet, se Runde 22B.1
            # i .DESCRIPTION, nå på bolk- i stedet for fil-nivå).
            #
            # DEGRADERENDE BOLKSTØRRELSE (issue #213, Chief review PR #216,
            # runde 8): en reell owner-gate-test mot Domeneshop viste at
            # bolker à 10 filer kan treffe vedvarende curl 18 / FTP 426 selv
            # etter reverifisering+ett bounded retry -- se
            # Get-DegraderteBolkStorrelser over for hypotesen og
            # begrunnelsen. Filer som fortsatt ikke kom gjennom etter at en
            # gitt bolkstørrelse har brukt opp sine bounded forsøk prøves
            # derfor på nytt i MINDRE bolker (samme reverifiser-før-retry-
            # logikk, samme $MaxBolkOpplastingsForsok PER størrelse) i stedet
            # for at hele deployen stopper der -- til slutt ÉN fil per
            # curl.exe-prosess (ingen --next i det hele tatt) om nødvendig.
            # Ekte (ikke-forbigående) curl-feil degraderer ALDRI -- de
            # stopper fortsatt deployen umiddelbart, uansett bolkstørrelse,
            # akkurat som før.
            $UploadBolkStorrelse = 10
            $MaxBolkOpplastingsForsok = 2  # forste forsok + ETT bounded retry PER BOLKSTORRELSE ved forbigaende feil -- ikke en lokke.
            $BolkRetryPauseSekunder = 5
            $EnkeltfilPauseMillisekunder = 500  # kun ved gulvstorrelse 1 -- reduserer tilkoblingsraten pa tvers av enkeltfil-fallback-overforinger (samme "for mange raske tilkoblinger"-hypotese som issue #213 opprinnelig startet med).

            $BolkStorrelser = @(Get-DegraderteBolkStorrelser -StartStorrelse $UploadBolkStorrelse)

            Write-Host ("--- Laster opp {0} fil(er) i bolker à maks {1} (eksplisitt FTPS, {2} fil(er) allerede identisk med produksjon hoppet over) ---" -f $FilesToUpload.Count, $UploadBolkStorrelse, ($DeployFiles.Count - $FilesToUpload.Count))
            $stoppedEarly = $false
            $sisteExitCode = 0
            $vellykkedeRels = @{}
            $gjenstaendeForDenneStorrelsen = $FilesToUpload

            for ($storrelseIndeks = 0; $storrelseIndeks -lt $BolkStorrelser.Count; $storrelseIndeks++) {
                if ($gjenstaendeForDenneStorrelsen.Count -eq 0) { break }
                $storrelse = $BolkStorrelser[$storrelseIndeks]
                $erGulvStorrelse = ($storrelseIndeks -eq $BolkStorrelser.Count - 1)
                if ($storrelseIndeks -gt 0) {
                    Write-Host ""
                    Write-Host ("--- Degraderer til bolkstorrelse {0} for {1} fil(er) som ikke kom gjennom ved forrige (storre) bolkstorrelse etter reverifisering+bounded retry ---" -f $storrelse, $gjenstaendeForDenneStorrelsen.Count)
                }

                $bolker = @(Split-FilerIBolker -Filer $gjenstaendeForDenneStorrelsen -BolkStorrelse $storrelse)
                $totalBolker = $bolker.Count
                $bolkIndeks = 0
                $nesteStorrelseFiler = @()

                foreach ($bolk in $bolker) {
                    $bolkIndeks++
                    $forsteRel = $bolk[0].rel
                    $sisteRel = $bolk[$bolk.Count - 1].rel
                    Write-Host ("[storrelse {0}, bolk {1}/{2}] {3} fil(er) ({4} .. {5})" -f $storrelse, $bolkIndeks, $totalBolker, $bolk.Count, $forsteRel, $sisteRel)

                    $forsokTeller = 0
                    $bolkOk = $false
                    $sisteExitCode = 0
                    $gjenstaendeFiler = $bolk
                    do {
                        $forsokTeller++
                        $bolkConfigInnhold = New-BolkOpplastingConfig -BrukerLinje $configContent -Filer $gjenstaendeFiler -FtpHost $FtpHost -RemoteRoot $RemoteRoot
                        $bolkConfigPath = [System.IO.Path]::GetTempFileName()
                        [System.IO.File]::WriteAllText($bolkConfigPath, $bolkConfigInnhold, (New-Object System.Text.UTF8Encoding($false)))
                        try {
                            & curl.exe -K $bolkConfigPath --fail-early --silent --show-error
                            $sisteExitCode = $LASTEXITCODE
                        }
                        finally {
                            if (Test-Path $bolkConfigPath) { Remove-Item -Path $bolkConfigPath -Force -ErrorAction SilentlyContinue }
                        }

                        if ($sisteExitCode -eq 0) {
                            $bolkOk = $true
                            break
                        }
                        $erForbigaende = Test-ForbigaendeCurlFeil -ExitCode $sisteExitCode
                        if ((-not $erForbigaende) -or ($forsokTeller -ge $MaxBolkOpplastingsForsok)) {
                            break
                        }

                        # Reverifiser FØR retry (Chief review, PR #216): issue #213
                        # observerte curl exit 56 ETTER at filen faktisk hadde
                        # kommet frem -- et blindt retry av HELE bolken ville da
                        # lastet opp allerede-vellykkede filer på nytt. Samme
                        # read-only HTTPS-mekanisme som delta-sjekken (steg 2b) og
                        # produksjonsverifiseringen (steg 6) brukes til å
                        # reverifisere KUN filene i denne bolken mot produksjon --
                        # gjenstående retry-forsøk begrenses til filer som
                        # fortsatt avviker/mangler/ikke kan verifiseres. Hvis
                        # ingen gjenstår, regnes bolken som vellykket uten et
                        # faktisk nytt curl-forsøk.
                        if ($isOwnerGateTest) {
                            Write-Host ("  Forbigående feil (curl exit code {0}) -- reverifiserer {1} fil(er) i bolken over FTPS mot det ISOLERTE owner-gate-testmålet ($RemoteRoot) før et eventuelt retry-forsøk..." -f $sisteExitCode, $gjenstaendeFiler.Count)
                        }
                        else {
                            Write-Host ("  Forbigående feil (curl exit code {0}) -- reverifiserer {1} fil(er) i bolken mot produksjon før et eventuelt retry-forsøk..." -f $sisteExitCode, $gjenstaendeFiler.Count)
                        }
                        $bolkRetryTempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("kbh_deploy_bolkretry_" + [guid]::NewGuid().ToString("N"))
                        New-Item -ItemType Directory -Path $bolkRetryTempDir | Out-Null
                        try {
                            $bolkRetryResultater = @()
                            foreach ($f in $gjenstaendeFiler) {
                                if ($isOwnerGateTest) {
                                    $bolkRetryResultater += Invoke-DeployFileVerifiseringFtps -Rel $f.rel -LocalPath $f.FullName -CurlConfigPath $curlConfigPath -FtpHost $FtpHost -RemoteRoot $RemoteRoot -TempDir $bolkRetryTempDir
                                }
                                else {
                                    $bolkRetryResultater += Invoke-DeployFileVerifisering -Rel $f.rel -LocalPath $f.FullName -BaseUrl $BaseUrl -TempDir $bolkRetryTempDir
                                }
                            }
                        }
                        finally {
                            Remove-Item -Path $bolkRetryTempDir -Recurse -Force -ErrorAction SilentlyContinue
                        }
                        $gjenstaendeRels = @(Get-VerifiseringsStierForRetry -Resultater $bolkRetryResultater)
                        $gjenstaendeFiler = @($gjenstaendeFiler | Where-Object { $gjenstaendeRels -contains $_.rel })

                        if ($gjenstaendeFiler.Count -eq 0) {
                            Write-Host "  Reverifisering: alle filer i bolken er allerede identisk med produksjon -- bolken regnes som vellykket, ingen retry nødvendig."
                            $bolkOk = $true
                            break
                        }

                        Write-Host ("  Reverifisering: {0} fil(er) fortsatt avvikende/ikke-verifiserbare -- venter {1}s og prøver disse på nytt (forsøk {2}/{3})..." -f $gjenstaendeFiler.Count, $BolkRetryPauseSekunder, ($forsokTeller + 1), $MaxBolkOpplastingsForsok)
                        Start-Sleep -Seconds $BolkRetryPauseSekunder
                    } while ($true)

                    if ($bolkOk) {
                        # Uansett hvordan $bolkOk ble $true (direkte curl-suksess,
                        # ELLER reverifisering som viste at alle allerede matchet,
                        # ELLER et vellykket retry-forsøk på det reduserte settet)
                        # er HELE $bolk -- ikke bare det siste $gjenstaendeFiler --
                        # nå bekreftet oppe: filer som ikke lenger var i
                        # $gjenstaendeFiler ble allerede bekreftet av
                        # reverifiseringen over.
                        foreach ($f in $bolk) { $vellykkedeRels[$f.rel] = $true }
                        if ($erGulvStorrelse -and $bolkIndeks -lt $totalBolker) {
                            # Enkeltfil-fallback (gulvstorrelse 1): kort pause
                            # mellom PÅFØLGENDE enkeltfil-tilkoblinger for å
                            # redusere tilkoblingsraten -- samme hypotese som
                            # selve issue #213 (for mange raske tilkoblinger)
                            # startet med, nå anvendt kun på fallback-stien der
                            # --next-bolking uansett ikke lenger hjelper (1 fil
                            # = 0 --next-blokker).
                            Start-Sleep -Milliseconds $EnkeltfilPauseMillisekunder
                        }
                        continue
                    }

                    $erForbigaendeSisteFeil = Test-ForbigaendeCurlFeil -ExitCode $sisteExitCode
                    if ((-not $erForbigaendeSisteFeil) -or $erGulvStorrelse) {
                        Write-Host ""
                        Write-Host ("STOPPER: bolk {0}/{1} (bolkstorrelse {2}) feilet (curl exit code {3})" -f $bolkIndeks, $totalBolker, $storrelse, $sisteExitCode)
                        Write-Host (Get-CurlFeilmelding $sisteExitCode)
                        if ($gjenstaendeFiler.Count -lt $bolk.Count) {
                            Write-Host ("{0} av {1} fil(er) i denne bolken ble bekreftet allerede identisk med produksjon under reverifisering -- de resterende {2} fil(er) ble forsøkt på nytt som ÉN curl-økt, ingen garanti for nøyaktig hvilke av DISSE som kom gjennom før feilen." -f ($bolk.Count - $gjenstaendeFiler.Count), $bolk.Count, $gjenstaendeFiler.Count)
                        }
                        elseif ($erGulvStorrelse -and $erForbigaendeSisteFeil) {
                            Write-Host "Denne bolken er allerede på gulvstorrelse 1 (ingen --next, ÉN fil per curl.exe-prosess) -- ingen mindre bolkstorrelse å degradere videre til."
                        }
                        else {
                            Write-Host "Bolken lastes opp som ÉN curl-økt -- ingen garanti for nøyaktig hvilke enkeltfiler i akkurat denne bolken som faktisk kom gjennom før feilen. Kjør scriptet på nytt, eller verifiser produksjon manuelt, for et autoritativt svar per fil."
                        }
                        Write-Host ("Deploy er UFULLSTENDIG -- {0} av {1} fil(er) bekreftet lastet opp før feilen stoppet resten." -f $vellykkedeRels.Count, $FilesToUpload.Count)
                        Write-Host "Produksjonen skal IKKE regnes som oppdatert."
                        $stoppedEarly = $true
                        $exitCode = 1
                        break
                    }

                    Write-Host ("  Bolkstorrelse {0} brukte opp bounded forsøk for {1} gjenværende fil(er) (siste curl exit code {2}, forbigående) -- degraderer disse til mindre bolker i stedet for å stoppe deployen." -f $storrelse, $gjenstaendeFiler.Count, $sisteExitCode)
                    $nesteStorrelseFiler += $gjenstaendeFiler
                }
                if ($stoppedEarly) { break }
                $gjenstaendeForDenneStorrelsen = $nesteStorrelseFiler
            }
            if (-not $stoppedEarly) {
                Write-Host ""
                Write-Host ("Alle {0} fil(er) lastet opp (bolkstorrelser forsokt: {1}, {2} fil(er) hoppet over)." -f $FilesToUpload.Count, ($BolkStorrelser -join ", "), ($DeployFiles.Count - $FilesToUpload.Count))
            }
        }
    }
}
finally {
    if (Test-Path $curlConfigPath) {
        Remove-Item -Path $curlConfigPath -Force -ErrorAction SilentlyContinue
    }
}

if ($exitCode -ne 0) {
    exit $exitCode
}

# ─── 6. Produksjonsverifisering: FAKTISK FILINNHOLD, ikke bare HTTP 200 ────
# Kjøres KUN hvis alle filene faktisk ble lastet opp uten feil over.
#
# En tidligere deploy rapporterte "alle filer lastet opp" OG besto denne
# stegets forgjenger (HTTP-200 på fire faste URL-er) -- men innholdet som
# faktisk lå på produksjon var likevel FEIL, fordi HTTP 200 kun beviser at
# SIDEN SVARER, ikke at BYTENE er riktige (se issue #28 / guarden over).
# Denne versjonen laster derfor ned HVER ENESTE deployet fil på nytt og
# sammenligner SHA-256 mot den lokale kilden -- bevisst IKKE et kuratert
# utvalg "relevante" filer, siden nettopp et slikt utvalg-blindpunkt var
# årsaken til at forrige feil ikke ble oppdaget.
Write-Host ""
if ($isOwnerGateTest) {
    Write-Host "--- Owner-gate testmodus: hopper over smoke-sjekken mot normal produksjon (root/en) -- $RemoteRoot er et isolert testmål, ikke live-siden ---"
}
else {
    Write-Host "--- Verifiserer produksjon: rask HTTP-svar-sjekk (root/en) ---"
    $smokeChecks = @(
        "https://kvernhaugbrygghus.no/",
        "https://kvernhaugbrygghus.no/en/"
    )
    foreach ($url in $smokeChecks) {
        try {
            $resp = Invoke-WebRequest -Uri $url -Method Get -UseBasicParsing -TimeoutSec 20
            $status = $resp.StatusCode
        }
        catch {
            $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "FEIL" }
        }
        $marker = if ($status -eq 200) { "OK  " } else { "FEIL" }
        Write-Host "  $marker $url ($status)"
        if ($status -ne 200) {
            Write-Error "Produksjon svarer ikke 200 på $url -- stopper før innholdsverifisering. IKKE anta at deploy var vellykket."
            exit 1
        }
    }
}

# Kort, avgrenset pause (issue #81) -- ETT retry-forsøk, ikke en løkke --
# for at en forbigående nettverksglipp ikke skal rapporteres som et
# permanent avvik før den faktisk er bekreftet reproduserbar. Brukt av
# BEGGE grenene under (HTTPS-mot-produksjon og FTPS-mot-owner-gate-mål).
$RetryPauseSekunder = 5

# Ren tekstetikett (issue #213, Chief review, PR #216, runde 6) -- hvilket
# mål verifiseringsmeldingene under faktisk beskriver. Uten denne var
# AVVIK-/KAN-IKKE-VERIFISERE-/OK-meldingene hardkodet til "produksjon" selv
# i owner-gate testmodus -- en vellykket sjekk av det isolerte
# owner-gate-testmålet kunne dermed leses som et bevis om normal
# produksjon, noe det aldri er (owner-gate-modus skriver kun til
# $RemoteRoot, aldri til $BaseUrl). Beregnes ÉN gang her og gjenbrukes av
# BÅDE Write-VerifiseringsResultatLinje og sluttoppsummeringen lenger ned,
# slik at de to aldri kan komme i utakt med hverandre. Normal deploy (uten
# -OwnerGateTestSha) er uendret -- fortsatt "produksjon"/"HTTPS" i alle
# meldinger, akkurat som før denne endringen.
if ($isOwnerGateTest) {
    $verifiseringsMaalLabel = "det ISOLERTE owner-gate-testmålet ($FtpHost$RemoteRoot) -- IKKE produksjon"
    $verifiseringsProtokollLabel = "FTPS"
}
else {
    $verifiseringsMaalLabel = "produksjon"
    $verifiseringsProtokollLabel = "HTTPS"
}

function Write-VerifiseringsResultatLinje {
    param([string]$Prefiks, [object]$Resultat, [Parameter(Mandatory)][string]$MaalLabel)
    $label = switch ($Resultat.reason) {
        "ok" { "OK" }
        "mismatch" { "AVVIK" }
        default { "KAN IKKE VERIFISERE" }
    }
    Write-Host ("  [{0}] {1,-20} {2}" -f $Prefiks, $label, $Resultat.rel)
    if ($Resultat.reason -eq "mismatch") {
        Write-Host ("        forventet sjekksum (lokal kilde):  {0}" -f $Resultat.localHash)
        Write-Host ("        mottatt sjekksum ({0}):     {1}" -f $MaalLabel, $Resultat.remoteHash)
    }
    elseif ($Resultat.reason -eq "unverifiable") {
        Write-Host ("        feil: {0}" -f $Resultat.error)
    }
}

Write-Host ""
if ($isOwnerGateTest) {
    # Owner-gate testmodus (issue #213, Chief review, PR #216, runde 5):
    # $BaseUrl peker på normal produksjon og beviser ingenting om det
    # isolerte -RemoteRoot-testmålet -- verifiseringen må derfor kontrollere
    # BYTENE SOM FAKTISK BLE SKREVET TIL TESTMÅLET, over FTPS, ikke HTTPS
    # mot produksjon. Førstepasset er bolkvis (--next-batchet, maks 10 filer
    # per curl.exe-prosess, samme mekanisme som selve opplastingen) for å
    # unngå å åpne én FTPS-tilkobling per fil for et sett som kan være alle
    # 85 filene -- det ville reintrodusert akkurat det tilkoblingstaket
    # issue #213 fikset for opplastingen. Retry-passet (typisk et lite
    # restsett) bruker enkeltfil-varianten.
    Write-Host "--- Verifiserer owner-gate testmål ($RemoteRoot): FAKTISK INNHOLD over FTPS (SHA-256 per fil, bolkvis, $($DeployFiles.Count) filer) ---"
    $OwnerGateVerifyBolkStorrelse = 10
    $ownerGateVerifyTempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("kbh_deploy_ownergate_verify_" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $ownerGateVerifyTempDir | Out-Null
    # $curlConfigPath (steg 5) er allerede slettet på dette punktet -- finally-
    # blokken rundt steg 5 (preflight + bolk-opplasting) rydder den opp FØR
    # steg 6 i det hele tatt starter, uansett om opplastingen lyktes. Første
    # pass over ($OwnerGateVerifyBolkStorrelse-bolker) bygger sine egne
    # -K-configer fra $configContent (en in-memory-streng, aldri den slettede
    # filstien) og er derfor upåvirket -- men retry-passet under kaller
    # Invoke-DeployFileVerifiseringFtps med en EKSPLISITT -CurlConfigPath, og
    # trenger derfor sin EGEN, ferske credentials-config-fil (Chief review,
    # PR #216, runde 6: retry-passet pekte tidligere deterministisk på den
    # allerede slettede $curlConfigPath ved ethvert avvik/ikke-verifiserbar
    # fil i første pass, og kunne derfor aldri lykkes). Bygges FØR
    # try/finally slik at den er tilgjengelig uansett om retry faktisk
    # trengs -- slettes i samme finally som tempdir, uansett utfall.
    $ownerGateVerifyCurlConfigPath = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($ownerGateVerifyCurlConfigPath, $configContent, (New-Object System.Text.UTF8Encoding($false)))
    try {
        $forstePass = @(Invoke-DeployBolkVerifiseringFtps -Filer $DeltaKandidatFiler -BrukerLinje $configContent -FtpHost $FtpHost -RemoteRoot $RemoteRoot -BolkStorrelse $OwnerGateVerifyBolkStorrelse -TempDir $ownerGateVerifyTempDir)
        $i = 0
        foreach ($resultat in $forstePass) {
            $i++
            Write-VerifiseringsResultatLinje -Prefiks ("{0}/{1}" -f $i, $DeployFiles.Count) -Resultat $resultat -MaalLabel $verifiseringsMaalLabel
        }

        $relByPath = @{}
        foreach ($fc in $DeltaKandidatFiler) { $relByPath[$fc.rel] = $fc }

        $retryRels = @(Get-VerifiseringsStierForRetry -Resultater $forstePass)
        $retryPass = @()
        if ($retryRels.Count -gt 0) {
            Write-Host ""
            Write-Host ("--- {0} fil(er) feilet forste FTPS-pass -- venter {1}s og prover PA NYTT med fersk FTPS-nedlastning per fil ---" -f $retryRels.Count, $RetryPauseSekunder)
            Start-Sleep -Seconds $RetryPauseSekunder
            $j = 0
            foreach ($rel in $retryRels) {
                $j++
                $fc = $relByPath[$rel]
                $resultat = Invoke-DeployFileVerifiseringFtps -Rel $fc.rel -LocalPath $fc.FullName -CurlConfigPath $ownerGateVerifyCurlConfigPath -FtpHost $FtpHost -RemoteRoot $RemoteRoot -TempDir $ownerGateVerifyTempDir
                Write-VerifiseringsResultatLinje -Prefiks ("retry {0}/{1}" -f $j, $retryRels.Count) -Resultat $resultat -MaalLabel $verifiseringsMaalLabel
                $retryPass += $resultat
            }
        }

        $sluttResultat = @(Merge-VerifiseringsResultat -Forste $forstePass -Retry $retryPass)
    }
    finally {
        Remove-Item -Path $ownerGateVerifyTempDir -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path $ownerGateVerifyCurlConfigPath) { Remove-Item -Path $ownerGateVerifyCurlConfigPath -Force -ErrorAction SilentlyContinue }
    }
}
else {
    Write-Host "--- Verifiserer produksjon: FAKTISK INNHOLD (SHA-256 per fil, $($DeployFiles.Count) filer) ---"
    $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("kbh_deploy_verify_" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    # $BaseUrl er allerede satt i steg 2b (delta-sjekken, issue #213) -- samme
    # produksjons-URL, ikke duplisert her.
    try {
        $relByPath = @{}
        $i = 0
        $forstePass = @()
        foreach ($f in $DeployFiles) {
            $i++
            $rel = $f.FullName.Substring($WebRoot.Length + 1) -replace '\\', '/'
            $relByPath[$rel] = $f
            $resultat = Invoke-DeployFileVerifisering -Rel $rel -LocalPath $f.FullName -BaseUrl $BaseUrl -TempDir $tempDir
            Write-VerifiseringsResultatLinje -Prefiks ("{0}/{1}" -f $i, $DeployFiles.Count) -Resultat $resultat -MaalLabel $verifiseringsMaalLabel
            $forstePass += $resultat
        }

        $retryRels = @(Get-VerifiseringsStierForRetry -Resultater $forstePass)
        $retryPass = @()
        if ($retryRels.Count -gt 0) {
            Write-Host ""
            Write-Host ("--- {0} fil(er) feilet forste pass -- venter {1}s og prover PA NYTT med fersk HTTP-hentning per fil ---" -f $retryRels.Count, $RetryPauseSekunder)
            Start-Sleep -Seconds $RetryPauseSekunder
            $j = 0
            foreach ($rel in $retryRels) {
                $j++
                $f = $relByPath[$rel]
                $resultat = Invoke-DeployFileVerifisering -Rel $rel -LocalPath $f.FullName -BaseUrl $BaseUrl -TempDir $tempDir
                Write-VerifiseringsResultatLinje -Prefiks ("retry {0}/{1}" -f $j, $retryRels.Count) -Resultat $resultat -MaalLabel $verifiseringsMaalLabel
                $retryPass += $resultat
            }
        }

        $sluttResultat = @(Merge-VerifiseringsResultat -Forste $forstePass -Retry $retryPass)
    }
    finally {
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$mismatches = @($sluttResultat | Where-Object { $_.reason -eq "mismatch" })
$unverifiable = @($sluttResultat | Where-Object { $_.reason -eq "unverifiable" })

Write-Host ""
if ($mismatches.Count -gt 0 -or $unverifiable.Count -gt 0) {
    if ($mismatches.Count -gt 0) {
        Write-Host ("INNHOLDSAVVIK -- {0} svarer, men bytes matcher IKKE lokal kilde for $($mismatches.Count) fil(er) (uendret etter eventuelt retry):" -f $verifiseringsMaalLabel)
        foreach ($m in $mismatches) {
            Write-Host ("  - {0}" -f $m.rel)
            Write-Host ("      forventet sjekksum (lokal kilde):  {0}" -f $m.localHash)
            Write-Host ("      mottatt sjekksum ({0}):     {1}" -f $verifiseringsMaalLabel, $m.remoteHash)
        }
    }
    if ($unverifiable.Count -gt 0) {
        Write-Host ("KUNNE IKKE VERIFISERE $($unverifiable.Count) fil(er) (nettverksfeil/ikke tilgjengelig via {0}, uendret etter eventuelt retry):" -f $verifiseringsProtokollLabel)
        foreach ($u in $unverifiable) { Write-Host ("  - {0} ({1})" -f $u.rel, $u.error) }
    }
    Write-Host ""
    Write-Error "Innholdsverifisering feilet -- IKKE anta at deploy var vellykket før dette er undersøkt."
    exit 1
}

Write-Host ("Verifisering OK -- alle $($DeployFiles.Count) filer bekreftet byte-for-byte identiske mellom $WebRoot og {0}." -f $verifiseringsMaalLabel)
exit 0
