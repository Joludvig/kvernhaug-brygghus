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
  helst dersom modifisert, staget, slettet eller untracked innhold finnes
  under web/ (README.md/CHANGELOG.md unntatt -- de deployes aldri).
  Urelaterte urene filer utenfor web/ (f.eks. eierens egne lokale
  endringer andre steder i repoet) påvirkes ikke.

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
# Samme deployable-fil-semantikk som eksklusjonslisten i steg 2 under
# ($ExcludeRelative, definert her og gjenbrukt der) -- web/README.md og
# web/CHANGELOG.md er utviklerdokumentasjon, aldri deployet, og skal derfor
# aldri i seg selv blokkere en deploy. Filer utenfor web/ (f.eks. eierens
# tiltenkte lokale endring i raw_data/unmatched_malt.json) berøres ikke i
# det hele tatt, siden git-kallet er pathspec-avgrenset til web/.
$ExcludeRelative = @("README.md", "CHANGELOG.md")

Push-Location $RepoRoot
try {
    $porcelain = & git status --porcelain -- web/
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

# ─── 3. Dependency-sjekk ────────────────────────────────────────────────────
$curlCmd = Get-Command curl.exe -ErrorAction SilentlyContinue
if (-not $curlCmd) {
    Write-Error "curl.exe ble ikke funnet i PATH. Dette scriptet krever curl med FTPS-støtte (bekreftet tilgjengelig: curl 8.21+ med Schannel/SSL på denne maskinen normalt)."
    exit 1
}

# ─── 4. Bekreftelse (default NO) ───────────────────────────────────────────
if (-not $Force) {
    $answer = Read-Host "Deploy $($DeployFiles.Count) filer fra $WebRoot til ${FtpHost}:${RemoteRoot} ? [y/N]"
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
        Write-Host "--- Laster opp $($DeployFiles.Count) filer (eksplisitt FTPS) ---"
        $i = 0
        $stoppedEarly = $false
        foreach ($f in $DeployFiles) {
            $i++
            $rel = $f.FullName.Substring($WebRoot.Length + 1) -replace '\\', '/'
            $remoteUrl = "ftp://$FtpHost$RemoteRoot/$rel"
            Write-Host ("[{0}/{1}] {2}" -f $i, $DeployFiles.Count, $rel)
            # --ssl-reqd: krever AUTH TLS (eksplisitt FTPS) -- feiler i stedet
            # for å falle tilbake til klartekst. --ftp-create-dirs: oppretter
            # manglende mapper automatisk under opplasting. Serversertifikat/
            # hostname verifiseres normalt av curl -- ingen "-k"/"--insecure".
            & curl.exe -K $curlConfigPath --ssl-reqd --ftp-create-dirs --silent --show-error -T "$($f.FullName)" "$remoteUrl"
            if ($LASTEXITCODE -ne 0) {
                Write-Host ""
                Write-Host ("STOPPER: {0} feilet (curl exit code {1})" -f $rel, $LASTEXITCODE)
                Write-Host (Get-CurlFeilmelding $LASTEXITCODE)
                Write-Host ("Deploy er UFULLSTENDIG -- kun {0} av {1} filer ble lastet opp før feilen stoppet resten." -f ($i - 1), $DeployFiles.Count)
                Write-Host "Produksjonen skal IKKE regnes som oppdatert."
                $stoppedEarly = $true
                $exitCode = 1
                break
            }
        }
        if (-not $stoppedEarly) {
            Write-Host ""
            Write-Host "Alle $($DeployFiles.Count) filer lastet opp."
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
$mismatches = @()
$unverifiable = @()
try {
    $i = 0
    foreach ($f in $DeployFiles) {
        $i++
        $rel = $f.FullName.Substring($WebRoot.Length + 1) -replace '\\', '/'
        $url = "https://kvernhaugbrygghus.no/$rel"
        $tempFile = Join-Path $tempDir "f$i"
        try {
            Invoke-WebRequest -Uri $url -Method Get -UseBasicParsing -TimeoutSec 20 -OutFile $tempFile
            $localHash = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash
            $remoteHash = (Get-FileHash -Path $tempFile -Algorithm SHA256).Hash
            if ($localHash -ne $remoteHash) {
                Write-Host ("  [{0}/{1}] AVVIK                {2}" -f $i, $DeployFiles.Count, $rel)
                $mismatches += $rel
            }
            else {
                Write-Host ("  [{0}/{1}] OK                   {2}" -f $i, $DeployFiles.Count, $rel)
            }
        }
        catch {
            Write-Host ("  [{0}/{1}] KAN IKKE VERIFISERE  {2}  ({3})" -f $i, $DeployFiles.Count, $rel, $_.Exception.Message)
            $unverifiable += $rel
        }
    }
}
finally {
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
if ($mismatches.Count -gt 0 -or $unverifiable.Count -gt 0) {
    if ($mismatches.Count -gt 0) {
        Write-Host "INNHOLDSAVVIK -- produksjon svarer, men bytes matcher IKKE lokal kilde for $($mismatches.Count) fil(er):"
        foreach ($m in $mismatches) { Write-Host "  - $m" }
    }
    if ($unverifiable.Count -gt 0) {
        Write-Host "KUNNE IKKE VERIFISERE $($unverifiable.Count) fil(er) (nettverksfeil/ikke tilgjengelig via HTTPS):"
        foreach ($u in $unverifiable) { Write-Host "  - $u" }
    }
    Write-Host ""
    Write-Error "Innholdsverifisering feilet -- IKKE anta at deploy var vellykket før dette er undersøkt."
    exit 1
}

Write-Host "Verifisering OK -- alle $($DeployFiles.Count) filer bekreftet byte-for-byte identiske mellom $WebRoot og produksjon."
exit 0
