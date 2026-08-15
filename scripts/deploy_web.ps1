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

.PARAMETER DryRun
  Viser source, target, filantall og full filliste. Gjør ingen tilkobling og
  ingen endringer.

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

# ─── 2. Runtime-filliste (full sync, eksplisitt exclude-liste) ────────────
# Alt under web/ ER runtime bortsett fra disse to -- se web/README.md.
$ExcludeRelative = @("README.md", "CHANGELOG.md")

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

# ─── 6. Read-only produksjonsverifisering over HTTPS ───────────────────────
# Kjøres KUN hvis alle filene faktisk ble lastet opp uten feil over.
Write-Host ""
Write-Host "--- Verifiserer produksjon (HTTPS, read-only) ---"
$checks = @(
    "https://kvernhaugbrygghus.no/",
    "https://kvernhaugbrygghus.no/en/",
    "https://kvernhaugbrygghus.no/js/app.js",
    "https://kvernhaugbrygghus.no/js/preferences.js"
)
$verifyFailed = $false
foreach ($url in $checks) {
    try {
        $resp = Invoke-WebRequest -Uri $url -Method Get -UseBasicParsing -TimeoutSec 20
        $status = $resp.StatusCode
    }
    catch {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "FEIL" }
    }
    $ok = ($status -eq 200)
    if (-not $ok) { $verifyFailed = $true }
    $marker = if ($ok) { "OK  " } else { "FEIL" }
    Write-Host "  $marker $url ($status)"
}

Write-Host ""
if ($verifyFailed) {
    Write-Host "Verifisering fant minst én feil -- IKKE anta at deploy var vellykket før dette er rettet."
    exit 1
}
Write-Host "Verifisering OK -- produksjon svarer 200 på alle sjekkede URL-er."
exit 0
