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
# eksisterer på disk, og kun midlertidig, slettet i finally under.
$curlConfigPath = [System.IO.Path]::GetTempFileName()
$failed = @()

try {
    $escapedUser = $FtpUser -replace '"', '\"'
    $escapedPass = $plainPass -replace '"', '\"'
    Set-Content -Path $curlConfigPath -Value "user = `"$escapedUser`:$escapedPass`"" -NoNewline -Encoding ascii
    $plainPass = $null

    Write-Host ""
    Write-Host "--- Laster opp $($DeployFiles.Count) filer (eksplisitt FTPS) ---"
    $i = 0
    foreach ($f in $DeployFiles) {
        $i++
        $rel = $f.FullName.Substring($WebRoot.Length + 1) -replace '\\', '/'
        $remoteUrl = "ftp://$FtpHost$RemoteRoot/$rel"
        Write-Host ("[{0}/{1}] {2}" -f $i, $DeployFiles.Count, $rel)
        # --ssl-reqd: krever AUTH TLS (eksplisitt FTPS) -- feiler i stedet for
        # å falle tilbake til klartekst. --ftp-create-dirs: oppretter manglende
        # mapper (css/js/assets/data/hjelp/en/en-hjelp) automatisk under
        # opplasting. Serversertifikat/hostname verifiseres normalt av curl --
        # ingen "-k"/"--insecure" her.
        & curl.exe -K $curlConfigPath --ssl-reqd --ftp-create-dirs --silent --show-error -T "$($f.FullName)" "$remoteUrl"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  FEILET (curl exit code $LASTEXITCODE)"
            $failed += $rel
        }
    }
}
finally {
    if (Test-Path $curlConfigPath) {
        Remove-Item -Path $curlConfigPath -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
if ($failed.Count -gt 0) {
    Write-Host "FEILET: $($failed.Count) av $($DeployFiles.Count) filer ble IKKE lastet opp:"
    foreach ($rel in $failed) { Write-Host "  $rel" }
    Write-Host ""
    Write-Host "Deploy er IKKE komplett. Rett feilen og kjør scriptet på nytt (curl skriver kun over/oppretter filer -- trygt å kjøre flere ganger)."
    exit 1
}
Write-Host "Alle $($DeployFiles.Count) filer lastet opp."

# ─── 6. Read-only produksjonsverifisering over HTTPS ───────────────────────
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
