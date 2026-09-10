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

.EXAMPLE
  .\scripts\deploy_web.ps1 -DryRun

.EXAMPLE
  .\scripts\deploy_web.ps1
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Force,
    [string]$FtpUser,
    [string]$FtpHost = "ftp.domeneshop.no",
    [string]$RemoteRoot = "/www"
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

# ─── 1b. Guard: nekt å deploye fra en checkout som ikke matcher origin/master ──
# Se .DESCRIPTION for bakgrunnen (issue #28). Kjøres FØR filer i det hele
# tatt listes -- fail fast, ingen grunn til å bygge en filliste fra en
# checkout som uansett skal avvises.
$gitCmd = Get-Command git.exe -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    Write-Error "git.exe ble ikke funnet i PATH. Kan ikke bekrefte at denne checkouten matcher origin/master -- avbryter uten å gjøre noe."
    exit 1
}

Push-Location $RepoRoot
try {
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

Write-Host ("--- Delta-sjekk: sammenligner {0} lokale filer mot produksjon over HTTPS (0 FTPS-tilkoblinger) ---" -f $DeployFiles.Count)
$DeltaKandidatFiler = @($DeployFiles | ForEach-Object {
    $rel = $_.FullName.Substring($WebRoot.Length + 1) -replace '\\', '/'
    [PSCustomObject]@{ rel = $rel; FullName = $_.FullName }
})

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
    # innloggingen faktisk fungerer FØR noen av de 50 filene røres.
    Write-Host ""
    Write-Host "--- Preflight: verifiserer FTP-innlogging (read-only, 0 writes) ---"
    & curl.exe -K $curlConfigPath --ssl-reqd --silent --show-error -o "NUL" "ftp://$FtpHost$RemoteRoot/"
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
            $UploadBolkStorrelse = 10
            $MaxBolkOpplastingsForsok = 2  # forste forsok + ETT bounded retry ved forbigaende feil -- ikke en lokke.
            $BolkRetryPauseSekunder = 5

            Write-Host ("--- Laster opp {0} fil(er) i bolker à maks {1} (eksplisitt FTPS, {2} fil(er) allerede identisk med produksjon hoppet over) ---" -f $FilesToUpload.Count, $UploadBolkStorrelse, ($DeployFiles.Count - $FilesToUpload.Count))
            $i = 0
            $stoppedEarly = $false
            $bolker = @(Split-FilerIBolker -Filer $FilesToUpload -BolkStorrelse $UploadBolkStorrelse)
            $totalBolker = $bolker.Count
            $bolkIndeks = 0
            foreach ($bolk in $bolker) {
                $bolkIndeks++
                $forsteRel = $bolk[0].rel
                $sisteRel = $bolk[$bolk.Count - 1].rel
                Write-Host ("[bolk {0}/{1}] {2} fil(er) ({3} .. {4})" -f $bolkIndeks, $totalBolker, $bolk.Count, $forsteRel, $sisteRel)

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
                    Write-Host ("  Forbigående feil (curl exit code {0}) -- reverifiserer {1} fil(er) i bolken mot produksjon før et eventuelt retry-forsøk..." -f $sisteExitCode, $gjenstaendeFiler.Count)
                    $bolkRetryTempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("kbh_deploy_bolkretry_" + [guid]::NewGuid().ToString("N"))
                    New-Item -ItemType Directory -Path $bolkRetryTempDir | Out-Null
                    try {
                        $bolkRetryResultater = @()
                        foreach ($f in $gjenstaendeFiler) {
                            $bolkRetryResultater += Invoke-DeployFileVerifisering -Rel $f.rel -LocalPath $f.FullName -BaseUrl $BaseUrl -TempDir $bolkRetryTempDir
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

                $i += $bolk.Count
                if (-not $bolkOk) {
                    Write-Host ""
                    Write-Host ("STOPPER: bolk {0}/{1} feilet (curl exit code {2})" -f $bolkIndeks, $totalBolker, $sisteExitCode)
                    Write-Host (Get-CurlFeilmelding $sisteExitCode)
                    if ($gjenstaendeFiler.Count -lt $bolk.Count) {
                        Write-Host ("{0} av {1} fil(er) i denne bolken ble bekreftet allerede identisk med produksjon under reverifisering -- de resterende {2} fil(er) ble forsøkt på nytt som ÉN curl-økt, ingen garanti for nøyaktig hvilke av DISSE som kom gjennom før feilen." -f ($bolk.Count - $gjenstaendeFiler.Count), $bolk.Count, $gjenstaendeFiler.Count)
                    }
                    else {
                        Write-Host "Bolken lastes opp som ÉN curl-økt -- ingen garanti for nøyaktig hvilke enkeltfiler i akkurat denne bolken som faktisk kom gjennom før feilen. Kjør scriptet på nytt, eller verifiser produksjon manuelt, for et autoritativt svar per fil."
                    }
                    Write-Host ("Deploy er UFULLSTENDIG -- {0} av {1} fil(er) var i bolker forsøkt lastet opp (inkludert den feilede bolken) før feilen stoppet resten." -f $i, $FilesToUpload.Count)
                    Write-Host "Produksjonen skal IKKE regnes som oppdatert."
                    $stoppedEarly = $true
                    $exitCode = 1
                    break
                }
            }
            if (-not $stoppedEarly) {
                Write-Host ""
                Write-Host ("Alle {0} fil(er) lastet opp ({1} bolk(er), {2} fil(er) hoppet over)." -f $FilesToUpload.Count, $totalBolker, ($DeployFiles.Count - $FilesToUpload.Count))
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

Write-Host ""
Write-Host "--- Verifiserer produksjon: FAKTISK INNHOLD (SHA-256 per fil, $($DeployFiles.Count) filer) ---"
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("kbh_deploy_verify_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir | Out-Null
# $BaseUrl er allerede satt i steg 2b (delta-sjekken, issue #213) -- samme
# produksjons-URL, ikke duplisert her.
# Kort, avgrenset pause (issue #81) -- ETT retry-forsøk, ikke en løkke --
# for at en forbigående nettverksglipp ikke skal rapporteres som et
# permanent avvik før den faktisk er bekreftet reproduserbar.
$RetryPauseSekunder = 5

function Write-VerifiseringsResultatLinje {
    param([string]$Prefiks, [object]$Resultat)
    $label = switch ($Resultat.reason) {
        "ok" { "OK" }
        "mismatch" { "AVVIK" }
        default { "KAN IKKE VERIFISERE" }
    }
    Write-Host ("  [{0}] {1,-20} {2}" -f $Prefiks, $label, $Resultat.rel)
    if ($Resultat.reason -eq "mismatch") {
        Write-Host ("        forventet sjekksum (lokal kilde):  {0}" -f $Resultat.localHash)
        Write-Host ("        mottatt sjekksum (produksjon):     {0}" -f $Resultat.remoteHash)
    }
    elseif ($Resultat.reason -eq "unverifiable") {
        Write-Host ("        feil: {0}" -f $Resultat.error)
    }
}

try {
    $relByPath = @{}
    $i = 0
    $forstePass = @()
    foreach ($f in $DeployFiles) {
        $i++
        $rel = $f.FullName.Substring($WebRoot.Length + 1) -replace '\\', '/'
        $relByPath[$rel] = $f
        $resultat = Invoke-DeployFileVerifisering -Rel $rel -LocalPath $f.FullName -BaseUrl $BaseUrl -TempDir $tempDir
        Write-VerifiseringsResultatLinje -Prefiks ("{0}/{1}" -f $i, $DeployFiles.Count) -Resultat $resultat
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
            Write-VerifiseringsResultatLinje -Prefiks ("retry {0}/{1}" -f $j, $retryRels.Count) -Resultat $resultat
            $retryPass += $resultat
        }
    }

    $sluttResultat = @(Merge-VerifiseringsResultat -Forste $forstePass -Retry $retryPass)
}
finally {
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

$mismatches = @($sluttResultat | Where-Object { $_.reason -eq "mismatch" })
$unverifiable = @($sluttResultat | Where-Object { $_.reason -eq "unverifiable" })

Write-Host ""
if ($mismatches.Count -gt 0 -or $unverifiable.Count -gt 0) {
    if ($mismatches.Count -gt 0) {
        Write-Host "INNHOLDSAVVIK -- produksjon svarer, men bytes matcher IKKE lokal kilde for $($mismatches.Count) fil(er) (uendret etter eventuelt retry):"
        foreach ($m in $mismatches) {
            Write-Host ("  - {0}" -f $m.rel)
            Write-Host ("      forventet sjekksum (lokal kilde):  {0}" -f $m.localHash)
            Write-Host ("      mottatt sjekksum (produksjon):     {0}" -f $m.remoteHash)
        }
    }
    if ($unverifiable.Count -gt 0) {
        Write-Host "KUNNE IKKE VERIFISERE $($unverifiable.Count) fil(er) (nettverksfeil/ikke tilgjengelig via HTTPS, uendret etter eventuelt retry):"
        foreach ($u in $unverifiable) { Write-Host ("  - {0} ({1})" -f $u.rel, $u.error) }
    }
    Write-Host ""
    Write-Error "Innholdsverifisering feilet -- IKKE anta at deploy var vellykket før dette er undersøkt."
    exit 1
}

Write-Host "Verifisering OK -- alle $($DeployFiles.Count) filer bekreftet byte-for-byte identiske mellom $WebRoot og produksjon."
exit 0
