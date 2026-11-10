<#
.SYNOPSIS
    Desinstala el motor exo de esta máquina (Windows). No toca los proyectos:
    para quitarlo de un proyecto, corré `exo uninstall` dentro de ese proyecto.

    Del PATH de usuario quita solo la entrada que agregó install.ps1, y solo si ese
    directorio quedó vacío (el de uv puede tener otras herramientas).

    Variables: EXO_DATA_DIR, EXO_INSTALL_NO_PATH=1, EXO_INSTALL_NO_UV=1 y
    EXO_INSTALL_ENV_SUBKEY (las mismas que install.ps1).
#>
[CmdletBinding()]
param([switch]$NoPath)

$ErrorActionPreference = 'Stop'
$Dist = 'exo-harness'
$NoPath = $NoPath -or ($env:EXO_INSTALL_NO_PATH -eq '1')
$DataDir = if ($env:EXO_DATA_DIR) { $env:EXO_DATA_DIR } else { Join-Path $env:LOCALAPPDATA $Dist }
$EnvSubKey = if ($env:EXO_INSTALL_ENV_SUBKEY) { $env:EXO_INSTALL_ENV_SUBKEY } else { 'Environment' }
$PathMarker = Join-Path $DataDir 'path-entry.txt'

function Get-NativeOutput {
    # Salida de un ejecutable sin cortar el script por lo que escriba en stderr
    # (en PowerShell 5.1, con 'Stop', `uv tool list` sin herramientas lo cortaba).
    param([string]$Exe, [string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        return (& $Exe @Arguments 2>$null) -join "`n"
    } catch {
        return ''
    } finally {
        $ErrorActionPreference = $previous
    }
}

function Test-SameDir {
    param([string]$Entry, [string]$Dir)
    $expanded = [Environment]::ExpandEnvironmentVariables($Entry).TrimEnd('\')
    return $expanded -ieq $Dir.TrimEnd('\')
}

function Remove-PathEntry {
    # Quita $Dir del PATH de usuario sin expandir las variables ni cambiar el tipo
    # del valor; solo escribe si cambió.
    param([string]$Dir)
    $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($EnvSubKey, $true)
    if (-not $key) { return }
    try {
        if ($key.GetValueNames() -notcontains 'Path') { return }
        $value = [string]$key.GetValue('Path', '', [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
        $kind = $key.GetValueKind('Path')
        $entries = @($value -split ';' | Where-Object { $_ })
        $kept = @($entries | Where-Object { -not (Test-SameDir $_ $Dir) })
        if ($kept.Count -eq $entries.Count) { return }
        $key.SetValue('Path', ($kept -join ';'), $kind)
    } finally {
        $key.Close()
    }
    if (-not $env:EXO_INSTALL_ENV_SUBKEY) {
        [Environment]::SetEnvironmentVariable('EXO_INSTALL_REFRESH', '1', 'User')
        [Environment]::SetEnvironmentVariable('EXO_INSTALL_REFRESH', $null, 'User')
    }
    Write-Host "Quité $Dir del PATH de usuario."
}

$uv = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
$removed = $false
if ($uv -and $env:EXO_INSTALL_NO_UV -ne '1') {
    $tools = Get-NativeOutput $uv.Source @('tool', 'list')
    if ($tools -match "(?m)^$([regex]::Escape($Dist))\b") {
        & $uv.Source tool uninstall $Dist
        if ($LASTEXITCODE -ne 0) { throw "uv tool uninstall $Dist falló" }
        $removed = $true
    }
}

$Venv = Join-Path $DataDir 'venv'
if (Test-Path $Venv) {
    Remove-Item -Recurse -Force $Venv
    $removed = $true
}

if (-not $NoPath -and (Test-Path -LiteralPath $PathMarker)) {
    $added = (Get-Content -LiteralPath $PathMarker -Raw).Trim()
    $leftovers = if (Test-Path -LiteralPath $added) { @(Get-ChildItem -LiteralPath $added -Force) } else { @() }
    if ($added -and $leftovers.Count -eq 0) {
        Remove-PathEntry $added
    } elseif ($added) {
        Write-Host "Dejo $added en el PATH: tiene otras herramientas."
    }
    Remove-Item -LiteralPath $PathMarker -Force
}

if ($removed) {
    Write-Host "Desinstalado $Dist. Los backups de desinstalación de proyectos quedan en $DataDir."
} else {
    Write-Host "$Dist no estaba instalado."
}
