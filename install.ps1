<#
.SYNOPSIS
    Instala el motor exo desde este clon (Windows).

.DESCRIPTION
    Verifica Python 3.10 o más. Con uv usa `uv tool install`; si no, crea un venv
    en %LOCALAPPDATA%\exo-harness\venv. Deja `exo` en el PATH de usuario (avisa si
    lo agrega y conserva el tipo del valor en el registro), corre `exo doctor` y,
    con -Init, adopta un proyecto. Re-ejecutarlo actualiza la instalación.

    Variables: EXO_DATA_DIR (carpeta de datos), EXO_INSTALL_NO_PATH=1 (no tocar el
    PATH), EXO_INSTALL_NO_UV=1 (no usar uv aunque esté instalado). Los tests usan
    EXO_INSTALL_ENV_SUBKEY para leer y escribir el PATH en otra clave de HKCU.

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
    # primero el lanzador py y saltea los alias de la Microsoft Store (WindowsApps),
    # que no son Python: abren la Store o fallan.
    foreach ($candidate in @(@('py', '-3'), @('python'), @('python3'))) {
        $exe = Get-Command $candidate[0] -CommandType Application -ErrorAction SilentlyContinue |
            Where-Object { $_.Source -notmatch '\\WindowsApps\\' } |
            Select-Object -First 1
        if (-not $exe) { continue }
        $prefix = @($candidate | Select-Object -Skip 1)
        $probe = $prefix + @('-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)')
        if (Test-Native $exe.Source $probe) {
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
    Write-Host "Instalando $Dist con uv tool..."
    Invoke-Checked $uv.Source @('tool', 'install', '--force', '--reinstall', $Spec)
    $BinDir = (& $uv.Source tool dir --bin).Trim()
} else {
    $Python = Find-Python
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
    $userPath = Get-UserPath
    $entries = @($userPath.Value -split ';' | Where-Object { $_ })
    if (-not ($entries | Where-Object { Test-SameDir $_ $BinDir })) {
        Set-UserPath (($entries + $BinDir) -join ';') $userPath.Kind
        New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
        Set-Content -LiteralPath $PathMarker -Value $BinDir -Encoding UTF8
        Write-Host "Agregué $BinDir al PATH de usuario. Abrí una terminal nueva para usar 'exo'."
    }
    if (-not (($env:Path -split ';') | Where-Object { $_ -and (Test-SameDir $_ $BinDir) })) {
        $env:Path = "$env:Path;$BinDir"
    }
}

& $Exe doctor
if ($LASTEXITCODE -ne 0) { throw 'exo doctor encontró errores; revisá la salida de arriba.' }

if ($Init) {
    & $Exe init --project $Init --yes
    if ($LASTEXITCODE -ne 0) { throw "exo init falló en $Init" }
}
Write-Host "Listo: $Exe"
