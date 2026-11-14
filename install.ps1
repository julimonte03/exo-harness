<#
.SYNOPSIS
    Installs the exo engine from this clone (Windows).

.DESCRIPTION
    Requires Python 3.10 or later. With uv it uses `uv tool install`; otherwise it
    creates a venv in %LOCALAPPDATA%\exo-harness\venv. Puts `exo` on the user PATH
    (says so when it adds it and keeps the registry value type), runs `exo doctor`
    and, with -Init, adopts a project. Running it again updates the installation.

    Variables: EXO_DATA_DIR (data folder), EXO_INSTALL_NO_PATH=1 (leave the PATH
    alone), EXO_INSTALL_NO_UV=1 (do not use uv even if it is installed). The tests
    use EXO_INSTALL_ENV_SUBKEY to read and write the PATH under another HKCU key.

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Init C:\code\my-project
    .\install.ps1 -WithVector
#>
[CmdletBinding()]
param(
    [string]$Init,
    [switch]$WithVector,
    [switch]$NoPath
)

$ErrorActionPreference = 'Stop'
$Repo = $PSScriptRoot
$Dist = 'exo-harness'
$NoPath = $NoPath -or ($env:EXO_INSTALL_NO_PATH -eq '1')
$Spec = if ($WithVector) { "$Repo[vector]" } else { $Repo }
$DataDir = if ($env:EXO_DATA_DIR) { $env:EXO_DATA_DIR } else { Join-Path $env:LOCALAPPDATA $Dist }
$EnvSubKey = if ($env:EXO_INSTALL_ENV_SUBKEY) { $env:EXO_INSTALL_ENV_SUBKEY } else { 'Environment' }
# Lo que este instalador agregó al PATH, para que uninstall.ps1 quite solo eso.
$PathMarker = Join-Path $DataDir 'path-entry.txt'

function Test-Native {
    # Corre un ejecutable para sondearlo. En PowerShell 5.1, con 'Stop', cualquier
    # salida por stderr de un ejecutable redirigido corta el script: acá no importa.
    param([string]$Exe, [string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Exe @Arguments 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $previous
    }
}

function Find-Python {
    # Devuelve el ejecutable y sus argumentos previos (por ejemplo py -3). Prueba
    # primero el lanzador py. El alias de la Microsoft Store que no es Python sale
    # con error al recibir argumentos, así que la sonda lo descarta sola.
    foreach ($candidate in @(@('py', '-3'), @('python'), @('python3'))) {
        $exe = Get-Command $candidate[0] -CommandType Application -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if (-not $exe) { continue }
        $prefix = @($candidate | Select-Object -Skip 1)
        $probe = $prefix + @('-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)')
        if (Test-Native $exe.Source $probe) {
            $found = @($exe.Source) + $prefix
            return , $found
        }
    }
    throw 'Python 3.10 or later not found. Install it from https://www.python.org or with winget, then run this script again.'
}

function Invoke-Checked {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Failed: $Exe $($Arguments -join ' ')" }
}

function Get-UserPath {
    # Lee el PATH de usuario sin expandir las variables (%USERPROFILE%...) y con su
    # tipo: [Environment]::SetEnvironmentVariable lo reescribiría expandido y como
    # REG_SZ.
    $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($EnvSubKey)
    $value = ''
    $kind = [Microsoft.Win32.RegistryValueKind]::ExpandString
    if ($key) {
        try {
            if ($key.GetValueNames() -contains 'Path') {
                $value = [string]$key.GetValue('Path', '', [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
                $kind = $key.GetValueKind('Path')
            }
        } finally {
            $key.Close()
        }
    }
    return [pscustomobject]@{ Value = $value; Kind = $kind }
}

function Set-UserPath {
    param([string]$Value, [Microsoft.Win32.RegistryValueKind]$Kind)
    $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($EnvSubKey)
    try { $key.SetValue('Path', $Value, $Kind) } finally { $key.Close() }
    if (-not $env:EXO_INSTALL_ENV_SUBKEY) {
        # Escribir el registro no avisa a las ventanas abiertas; SetEnvironmentVariable
        # sí (WM_SETTINGCHANGE): una variable de paso alcanza para disparar el aviso.
        [Environment]::SetEnvironmentVariable('EXO_INSTALL_REFRESH', '1', 'User')
        [Environment]::SetEnvironmentVariable('EXO_INSTALL_REFRESH', $null, 'User')
    }
}

function Test-SameDir {
    param([string]$Entry, [string]$Dir)
    $expanded = [Environment]::ExpandEnvironmentVariables($Entry).TrimEnd('\')
    return $expanded -ieq $Dir.TrimEnd('\')
}

$uv = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($uv -and $env:EXO_INSTALL_NO_UV -ne '1') {
    Write-Host "Installing $Dist with uv tool..."
    # Sin --force: si ya hay otro exo en el directorio de uv, uv no lo pisa (ADR-0001).
    Invoke-Checked $uv.Source @('tool', 'install', '--reinstall', $Spec)
    $BinDir = (& $uv.Source tool dir --bin).Trim()
} else {
    $Python = Find-Python
    $Venv = Join-Path $DataDir 'venv'
    Write-Host "Installing $Dist into $Venv..."
    $pyArgs = @($Python | Select-Object -Skip 1) + @('-m', 'venv', $Venv)
    Invoke-Checked $Python[0] $pyArgs
    Invoke-Checked (Join-Path $Venv 'Scripts\python.exe') @('-m', 'pip', 'install', '--upgrade', '--quiet', '--disable-pip-version-check', $Spec)
    $BinDir = Join-Path $Venv 'Scripts'
}

$Exe = Join-Path $BinDir 'exo.exe'
if (-not (Test-Path $Exe)) { throw "The installation did not produce $Exe" }

if (-not $NoPath) {
    $userPath = Get-UserPath
    $entries = @($userPath.Value -split ';' | Where-Object { $_ })
    if (-not ($entries | Where-Object { Test-SameDir $_ $BinDir })) {
        Set-UserPath (($entries + $BinDir) -join ';') $userPath.Kind
        New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
        Set-Content -LiteralPath $PathMarker -Value $BinDir -Encoding UTF8
        Write-Host "Added $BinDir to the user PATH. Open a new terminal to use 'exo'."
    }
    if (-not (($env:Path -split ';') | Where-Object { $_ -and (Test-SameDir $_ $BinDir) })) {
        $env:Path = "$env:Path;$BinDir"
    }
}

& $Exe doctor
if ($LASTEXITCODE -ne 0) { throw 'exo doctor found errors; check the output above.' }

if ($Init) {
    & $Exe init --project $Init --yes
    if ($LASTEXITCODE -ne 0) { throw "exo init failed in $Init" }
}
Write-Host "Done: $Exe"
