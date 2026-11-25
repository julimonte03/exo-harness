<#
.SYNOPSIS
    Installs the exo engine on Windows: from this clone, or from GitHub when piped.

.DESCRIPTION
    Run from a clone, it installs that clone. Piped (irm ... | iex), it installs from
    GitHub: the latest release, or the tag, branch or commit in EXO_REF. With uv it
    runs `uv tool install` from git (needs git). Without uv it creates a venv in
    %LOCALAPPDATA%\exo-harness\venv and installs the release wheel after checking it
    against the SHA256SUMS of the release (a branch or a commit installs from git;
    a release whose SHA256SUMS cannot be downloaded installs nothing); that needs
    Python 3.10 or later.

    It puts `exo` on the user PATH (says so when it adds it and keeps the registry
    value type), runs `exo doctor` and, with -Init, adopts a project. Running it
    again updates the installation.

    Variables: EXO_REF (tag, branch or commit to install when piped; default: the
    latest release, or main if there is none), EXO_REPO_URL (repository to install
    from when piped; default: https://github.com/julimonte03/exo-harness),
    EXO_DATA_DIR (data folder), EXO_INSTALL_NO_PATH=1 (leave the PATH alone),
    EXO_INSTALL_NO_UV=1 (do not use uv even if it is installed). The tests use
    EXO_INSTALL_ENV_SUBKEY to read and write the PATH under another HKCU key.

    To read it before running it:
        irm https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.ps1 -OutFile install.ps1
        notepad install.ps1
        powershell -ExecutionPolicy Bypass -File install.ps1

.EXAMPLE
    irm https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.ps1 | iex

.EXAMPLE
    $env:EXO_REF = 'v1.0.0'; irm https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.ps1 | iex

.EXAMPLE
    & ([scriptblock]::Create((irm https://raw.githubusercontent.com/julimonte03/exo-harness/main/install.ps1))) -Init C:\code\my-project

.EXAMPLE
    .\install.ps1 -Init C:\code\my-project -WithVector
#>
[CmdletBinding()]
param(
    [string]$Init,
    [switch]$WithVector,
    [switch]$NoPath
)

# Este archivo va en ASCII y sin BOM: `irm | iex` no tolera el BOM, y PowerShell 5.1
# lee un archivo sin BOM con la pagina de codigos ANSI. Por pipe corre en la sesion
# de quien lo invoca: todo va dentro de este bloque para no dejarle variables,
# funciones ni $ErrorActionPreference cambiadas. Termina con throw, nunca con exit,
# que cerraria esa sesion.
& {
    # Repo del motor (ADR-0017). EXO_REPO_URL lo cambia para probar contra un remoto
    # simulado o para instalar desde un espejo.
    $RepoUrl = if ($env:EXO_REPO_URL) { $env:EXO_REPO_URL.TrimEnd('/') } else { 'https://github.com/julimonte03/exo-harness' }

    $ErrorActionPreference = 'Stop'
    $Dist = 'exo-harness'
    $NoPath = $NoPath -or ($env:EXO_INSTALL_NO_PATH -eq '1')
    $Extras = if ($WithVector) { '[vector]' } else { '' }
    $DataDir = if ($env:EXO_DATA_DIR) { $env:EXO_DATA_DIR } else { Join-Path $env:LOCALAPPDATA $Dist }
    $EnvSubKey = if ($env:EXO_INSTALL_ENV_SUBKEY) { $env:EXO_INSTALL_ENV_SUBKEY } else { 'Environment' }
    # Lo que este instalador agrego al PATH, para que uninstall.ps1 quite solo eso.
    $PathMarker = Join-Path $DataDir 'path-entry.txt'

    function Test-Native {
        # Corre un ejecutable para sondearlo. En PowerShell 5.1, con 'Stop', cualquier
        # salida por stderr de un ejecutable redirigido corta el script: aca no importa.
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
        # con error al recibir argumentos, asi que la sonda lo descarta sola.
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
        # Corre un ejecutable y manda su codigo de salida. Con la salida redirigida
        # (`*> install.log`), PowerShell 5.1 convierte su stderr (el progreso de uv o de
        # pip) en errores, y con 'Stop' cortaria una instalacion que salio bien.
        param([string]$Exe, [string[]]$Arguments, [string]$Failure = '')
        $previous = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            & $Exe @Arguments
        } finally {
            $ErrorActionPreference = $previous
        }
        if ($LASTEXITCODE -ne 0) {
            if ($Failure) { throw $Failure }
            throw "Failed: $Exe $($Arguments -join ' ')"
        }
    }

    function Get-UserPath {
        # Lee el PATH de usuario sin expandir las variables (%USERPROFILE%...) y con su
        # tipo: [Environment]::SetEnvironmentVariable lo reescribiria expandido y como
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
            # si (WM_SETTINGCHANGE): una variable de paso alcanza para disparar el aviso.
            [Environment]::SetEnvironmentVariable('EXO_INSTALL_REFRESH', '1', 'User')
            [Environment]::SetEnvironmentVariable('EXO_INSTALL_REFRESH', $null, 'User')
        }
    }

    function Test-SameDir {
        param([string]$Entry, [string]$Dir)
        $expanded = [Environment]::ExpandEnvironmentVariables($Entry).TrimEnd('\')
        return $expanded -ieq $Dir.TrimEnd('\')
    }

    function Get-RepoScheme {
        # Solo https. file:// y http a 127.0.0.1 o localhost no salen de la maquina:
        # sirven para un espejo local y para los tests. Sin @ (credenciales o un host
        # disfrazado), ni ? o # que cambien la URL. Devuelve el protocolo permitido
        # para bajar.
        param([string]$Url)
        if ($Url -match '[^A-Za-z0-9._~:/%+-]') { throw "EXO_REPO_URL has characters that are not allowed: $Url" }
        if ($Url -match '^https://.') { return 'https' }
        if ($Url -match '^file:///.') { return 'file' }
        if ($Url -match '^http://(127\.0\.0\.1|localhost)(:[0-9]+)?/.') { return 'http' }
        throw "EXO_REPO_URL must be an https:// URL (got: $Url)."
    }

    function Assert-Ref {
        # Un tag, rama o commit que no cambie la URL ni el requisito de pip: sin
        # espacios, comillas, @, # ni '..'.
        param([string]$Ref)
        if (-not $Ref -or $Ref.StartsWith('-') -or $Ref.Contains('..') -or $Ref -match '[^A-Za-z0-9._/+-]') {
            throw "Not a valid tag, branch or commit: '$Ref'. Set EXO_REF to a release tag such as v1.0.0, or to a branch."
        }
    }

    function Save-Url {
        # Baja $Url a $Path solo por el protocolo de EXO_REPO_URL, tambien en cada
        # redireccion. .NET las sigue a cualquier protocolo y la URI final no muestra
        # los saltos del medio (https, http, https): se siguen a mano, de a una, y la
        # que cambia de protocolo se rechaza antes de pedirla. HttpWebRequest anda
        # igual en PowerShell 5.1 y 7, y File.Create toma la ruta tal cual.
        param([string]$Url, [string]$Path)
        $current = $Url
        for ($hops = 0; $hops -le 10; $hops++) {
            $request = [System.Net.WebRequest]::Create($current)
            # Con file:// no hay redirecciones: FileWebRequest no tiene AllowAutoRedirect.
            if ($request -is [System.Net.HttpWebRequest]) { $request.AllowAutoRedirect = $false }
            $response = $request.GetResponse()
            try {
                $status = if ($response -is [System.Net.HttpWebResponse]) { [int]$response.StatusCode } else { 200 }
                if ($status -lt 300) {
                    $out = [System.IO.File]::Create($Path)
                    try { $response.GetResponseStream().CopyTo($out) } finally { $out.Dispose() }
                    return
                }
                $location = $response.Headers['Location']
                if (-not $location) { throw "$current answered $status without a Location." }
                $next = New-Object System.Uri -ArgumentList ([System.Uri]$current), $location
            } finally {
                $response.Close()
            }
            if ($next.Scheme -ne $Scheme) {
                throw "$current redirected to $($next.AbsoluteUri), which is not $Scheme; refusing it."
            }
            $current = $next.AbsoluteUri
        }
        throw "Too many redirects from $Url."
    }

    function Get-Redirect {
        # Adonde redirige $Url, sin seguir la redireccion. HttpWebRequest anda igual en
        # PowerShell 5.1 y 7; Invoke-WebRequest -MaximumRedirection 0 no.
        param([string]$Url)
        $request = [System.Net.WebRequest]::Create($Url)
        $request.AllowAutoRedirect = $false
        $response = $request.GetResponse()
        try {
            $location = $response.Headers['Location']
            if (-not $location) { return '' }
            return (New-Object System.Uri -ArgumentList ([System.Uri]$Url), $location).AbsoluteUri
        } finally {
            $response.Close()
        }
    }

    function Get-LatestRef {
        # El tag del ultimo release, sin API ni token: <repo>/releases/latest redirige
        # a <repo>/releases/tag/<tag>, o a <repo>/releases si todavia no hay ninguno.
        try {
            $location = Get-Redirect "$RepoUrl/releases/latest"
        } catch {
            throw "Could not reach $RepoUrl to find the latest release ($($_.Exception.Message)). Check the connection, or set EXO_REF to a tag or a branch."
        }
        if ($location -match '/releases/tag/([^/]+)$') { return [System.Uri]::UnescapeDataString($Matches[1]) }
        if ($location -match '/releases/?$') {
            Write-Host "$RepoUrl has no releases yet: installing the main branch."
            return 'main'
        }
        throw "Unexpected answer from $RepoUrl/releases/latest. Set EXO_REF to a tag or a branch."
    }

    function Get-VerifiedWheel {
        # Baja el wheel del release $Ref a $Dir y lo verifica contra el SHA256SUMS del
        # mismo release. Devuelve su ruta, o nada si $Ref no tiene SHA256SUMS (es una
        # rama o un commit, no un release). Si no coincide, no instala nada. Un release
        # (v y un digito, como los tags que publica release.yml) no pasa a git si su
        # SHA256SUMS no baja: seria instalar sin checksum lo que se pidio verificado.
        param([string]$Ref, [string]$Dir)
        $base = "$RepoUrl/releases/download/$Ref"
        $sums = Join-Path $Dir 'SHA256SUMS'
        try {
            Save-Url "$base/SHA256SUMS" $sums
        } catch {
            if ($Ref -cmatch '^v[0-9]') {
                throw "Cannot verify release ${Ref}: could not download $base/SHA256SUMS ($($_.Exception.Message)). Nothing was installed. Check the connection and that the release exists in $RepoUrl/releases, then retry."
            }
            return $null
        }
        $lines = @(Get-Content -LiteralPath $sums | Where-Object { $_ -match '^[0-9A-Fa-f]{64} [ *][A-Za-z0-9._+-]+\.whl$' })
        if ($lines.Count -ne 1) {
            throw "The SHA256SUMS of release $Ref should list exactly one wheel; it lists $($lines.Count)."
        }
        $expected = $lines[0].Substring(0, 64).ToLowerInvariant()
        $name = $lines[0].Substring(66)
        Write-Host "Downloading $name from release $Ref..."
        $wheel = Join-Path $Dir $name
        try {
            Save-Url "$base/$name" $wheel
        } catch {
            throw "Could not download $base/${name}: $($_.Exception.Message)"
        }
        # Con .NET y no con Get-FileHash: lanzado desde pwsh, Windows PowerShell 5.1 hereda
        # el PSModulePath de PowerShell 7 y puede no encontrar esa funcion.
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $stream = [System.IO.File]::OpenRead($wheel)
        try { $digest = $sha.ComputeHash($stream) } finally { $stream.Dispose(); $sha.Dispose() }
        $actual = -join ($digest | ForEach-Object { $_.ToString('x2') })
        if ($actual -ne $expected) {
            throw "Checksum mismatch for ${name}: SHA256SUMS says $expected, the download is $actual. Nothing was installed; retry, and report it if it happens again."
        }
        Write-Host "Verified $name against SHA256SUMS."
        return $wheel
    }

    $uv = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $UseUv = [bool]($uv -and $env:EXO_INSTALL_NO_UV -ne '1')
    $Downloads = $null
    $FromGit = $false
    try {
        # Un clon tiene el motor al lado del script. Por pipe no hay script en disco
        # ($PSScriptRoot vacio), y un install.ps1 bajado suelto no tiene el clon al lado.
        if ($PSScriptRoot -and (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'pyproject.toml')) -and
            (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'src\exo\_meta.py'))) {
            if ($env:EXO_REF) { Write-Host "EXO_REF is ignored: installing the clone in $PSScriptRoot." }
            $Spec = $PSScriptRoot + $Extras
        } else {
            $Scheme = Get-RepoScheme $RepoUrl
            # PowerShell 5.1 en Windows viejos no ofrece TLS 1.2, que GitHub exige.
            [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
            $Ref = if ($env:EXO_REF) { $env:EXO_REF } else { Get-LatestRef }
            Assert-Ref $Ref
            $Spec = $null
            # Sin uv, el wheel del release, verificado. Una rama o un commit no tienen
            # SHA256SUMS en releases/download: se instalan desde git.
            if (-not $UseUv) {
                $Downloads = Join-Path ([System.IO.Path]::GetTempPath()) "$Dist-$([guid]::NewGuid().ToString('N'))"
                New-Item -ItemType Directory -Path $Downloads | Out-Null
                $wheel = Get-VerifiedWheel $Ref $Downloads
                if ($wheel) { $Spec = $wheel + $Extras }
            }
            if (-not $Spec) {
                if (-not (Get-Command git -CommandType Application -ErrorAction SilentlyContinue)) {
                    if ($UseUv) {
                        throw "git is required to install $Ref with uv. Install git, or set EXO_INSTALL_NO_UV=1 to install the release wheel with pip."
                    }
                    throw "git is required to install $Ref, which is not a release. Install git, or set EXO_REF to a release tag."
                }
                Write-Host "Installing $Dist from $RepoUrl at $Ref..."
                # uv no acepta file:///C:/...@ref (lee el ':' de la unidad como usuario y
                # clave); con la unidad codificada lo aceptan uv, pip y git.
                $gitUrl = $RepoUrl -replace '^file:///([A-Za-z]):', 'file:///$1%3A'
                $Spec = "$Dist$Extras @ git+$gitUrl@$Ref"
                $FromGit = $true
            }
        }

        if ($UseUv) {
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
            $pipArgs = @('-m', 'pip', 'install', '--upgrade', '--quiet', '--disable-pip-version-check')
            # Una rama o un commit traen la misma version que lo instalado: sin
            # --force-reinstall, pip lo da por instalado y no trae el commit nuevo.
            if ($FromGit) { $pipArgs += '--force-reinstall' }
            Invoke-Checked (Join-Path $Venv 'Scripts\python.exe') ($pipArgs + @($Spec))
            $BinDir = Join-Path $Venv 'Scripts'
        }
    } finally {
        if ($Downloads) { Remove-Item -LiteralPath $Downloads -Recurse -Force -ErrorAction SilentlyContinue }
    }

    # -LiteralPath: con -Path, un [, ] o * de EXO_DATA_DIR se lee como comodin.
    $Exe = Join-Path $BinDir 'exo.exe'
    if (-not (Test-Path -LiteralPath $Exe)) { throw "The installation did not produce $Exe" }

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

    Invoke-Checked $Exe @('doctor') 'exo doctor found errors; check the output above.'

    if ($Init) {
        Invoke-Checked $Exe @('init', '--project', $Init, '--yes') "exo init failed in $Init"
    }
    Write-Host "Done: $Exe"
}
