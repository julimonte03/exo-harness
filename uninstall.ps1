<#
.SYNOPSIS
    Desinstala el motor exo de esta máquina (Windows). No toca los proyectos:
    para quitarlo de un proyecto, corré `exo uninstall` dentro de ese proyecto.

    Variables: EXO_DATA_DIR, EXO_INSTALL_NO_PATH=1, EXO_INSTALL_NO_UV=1 (las mismas
    que install.ps1).
#>
[CmdletBinding()]
param([switch]$NoPath)

$ErrorActionPreference = 'Stop'
$Dist = 'exo-harness'
$NoPath = $NoPath -or ($env:EXO_INSTALL_NO_PATH -eq '1')

$uv = Get-Command uv -ErrorAction SilentlyContinue
$removed = $false
if ($uv -and $env:EXO_INSTALL_NO_UV -ne '1') {
    $tools = (& $uv.Source tool list 2>$null) -join "`n"
    if ($tools -match "(?m)^$([regex]::Escape($Dist))\b") {
        & $uv.Source tool uninstall $Dist
        if ($LASTEXITCODE -ne 0) { throw "uv tool uninstall $Dist falló" }
        $removed = $true
    }
}

$DataDir = if ($env:EXO_DATA_DIR) { $env:EXO_DATA_DIR } else { Join-Path $env:LOCALAPPDATA $Dist }
$Venv = Join-Path $DataDir 'venv'
if (Test-Path $Venv) {
    Remove-Item -Recurse -Force $Venv
    $removed = $true
    if (-not $NoPath) {
        $BinDir = Join-Path $Venv 'Scripts'
        $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
        $parts = @($userPath -split ';' | Where-Object { $_ -and $_ -ne $BinDir })
        [Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User')
    }
}

if ($removed) {
    Write-Host "Desinstalado $Dist. Los backups de desinstalación de proyectos quedan en $DataDir."
} else {
    Write-Host "$Dist no estaba instalado."
}
