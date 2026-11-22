<#
.SYNOPSIS
    Uninstalls the exo engine from this machine (Windows). It does not touch projects:
    to remove it from a project, run `exo uninstall` inside that project.

.DESCRIPTION
    From the user PATH it removes only the entry that install.ps1 added, and only if
    that directory is empty (the uv one may hold other tools).

    Variables: EXO_DATA_DIR, EXO_INSTALL_NO_PATH=1, EXO_INSTALL_NO_UV=1 and
    EXO_INSTALL_ENV_SUBKEY (the same as install.ps1).

.EXAMPLE
    .\uninstall.ps1

.EXAMPLE
    irm https://raw.githubusercontent.com/julimonte03/exo-harness/main/uninstall.ps1 | iex
#>
[CmdletBinding()]
param([switch]$NoPath)

# En ASCII y sin BOM, y todo dentro de un bloque, por lo mismo que install.ps1:
# `irm | iex` corre en la sesion de quien lo invoca.
& {
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
        # del valor; solo escribe si cambio.
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
        Write-Host "Removed $Dir from the user PATH."
    }

    $uv = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $removed = $false
    if ($uv -and $env:EXO_INSTALL_NO_UV -ne '1') {
        $tools = Get-NativeOutput $uv.Source @('tool', 'list')
        if ($tools -match "(?m)^$([regex]::Escape($Dist))\b") {
            & $uv.Source tool uninstall $Dist
            if ($LASTEXITCODE -ne 0) { throw "uv tool uninstall $Dist failed" }
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
            Write-Host "Keeping $added on the PATH: it holds other tools."
        }
        Remove-Item -LiteralPath $PathMarker -Force
    }

    if ($removed) {
        Write-Host "Uninstalled $Dist. Project uninstall backups remain in $DataDir."
    } else {
        Write-Host "$Dist was not installed."
    }
}
