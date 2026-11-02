<#
.SYNOPSIS
    Instala el motor exo desde este clon (Windows).

.DESCRIPTION
    Verifica Python 3.10 o más. Con uv usa `uv tool install`; si no, crea un venv
    en %LOCALAPPDATA%\exo-harness\venv. Deja `exo` en el PATH de usuario (avisa si
    lo agrega), corre `exo doctor` y, con -Init, adopta un proyecto. Re-ejecutarlo
    actualiza la instalación.

    Variables: EXO_DATA_DIR (carpeta de datos), EXO_INSTALL_NO_PATH=1 (no tocar el
    PATH), EXO_INSTALL_NO_UV=1 (no usar uv aunque esté instalado).

.EXAMPLE
    .\install.ps1
    .\install.ps1 -Init C:\code\mi-proyecto
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

function Find-Python {
    # Devuelve el ejecutable y sus argumentos previos (por ejemplo py -3).
    foreach ($candidate in @(@('python'), @('py', '-3'), @('python3'))) {
        $exe = Get-Command $candidate[0] -ErrorAction SilentlyContinue
        if (-not $exe) { continue }
        $prefix = @($candidate | Select-Object -Skip 1)
        $probe = $prefix + @('-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)')
        & $exe.Source @probe 2>$null
        if ($LASTEXITCODE -eq 0) {
            $found = @($exe.Source) + $prefix
            return , $found
        }
    }
    throw 'No encontré Python 3.10 o más. Instalalo desde https://www.python.org o con winget, y volvé a correr este script.'
}

function Invoke-Checked {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Falló: $Exe $($Arguments -join ' ')" }
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv -and $env:EXO_INSTALL_NO_UV -ne '1') {
    Write-Host "Instalando $Dist con uv tool..."
    Invoke-Checked $uv.Source @('tool', 'install', '--force', '--reinstall', $Spec)
    $BinDir = (& $uv.Source tool dir --bin).Trim()
} else {
    $Python = Find-Python
    $DataDir = if ($env:EXO_DATA_DIR) { $env:EXO_DATA_DIR } else { Join-Path $env:LOCALAPPDATA $Dist }
    $Venv = Join-Path $DataDir 'venv'
    Write-Host "Instalando $Dist en $Venv..."
    $pyArgs = @($Python | Select-Object -Skip 1) + @('-m', 'venv', $Venv)
    Invoke-Checked $Python[0] $pyArgs
    Invoke-Checked (Join-Path $Venv 'Scripts\python.exe') @('-m', 'pip', 'install', '--upgrade', '--quiet', '--disable-pip-version-check', $Spec)
    $BinDir = Join-Path $Venv 'Scripts'
}

$Exe = Join-Path $BinDir 'exo.exe'
if (-not (Test-Path $Exe)) { throw "La instalación no dejó $Exe" }

if (-not $NoPath) {
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $parts = @($userPath -split ';' | Where-Object { $_ })
    if ($parts -notcontains $BinDir) {
        [Environment]::SetEnvironmentVariable('Path', (($parts + $BinDir) -join ';'), 'User')
        Write-Host "Agregué $BinDir al PATH de usuario. Abrí una terminal nueva para usar 'exo'."
    }
    if (($env:Path -split ';') -notcontains $BinDir) { $env:Path = "$env:Path;$BinDir" }
}

& $Exe doctor
if ($LASTEXITCODE -ne 0) { throw 'exo doctor encontró errores; revisá la salida de arriba.' }

if ($Init) {
    & $Exe init --project $Init --yes
    if ($LASTEXITCODE -ne 0) { throw "exo init falló en $Init" }
}
Write-Host "Listo: $Exe"
