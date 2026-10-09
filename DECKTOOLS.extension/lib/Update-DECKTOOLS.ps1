# Works with Windows PowerShell 5.1; no Git or administrator access required.
[CmdletBinding()]
param(
    [string]$ExtensionParent = 'C:\Users\owenm\Desktop\PY REVIT DECK TOOLS TEST',
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Live,
    [switch]$FunctionsOnly
)

$ErrorActionPreference = 'Stop'
$TaskName = 'DECKTOOLS automatic updates'

function Get-ExtensionManifest([string]$Folder) {
    $result = @{}
    if (Test-Path -LiteralPath $Folder) {
        foreach ($directory in Get-ChildItem -LiteralPath $Folder -Directory -Recurse -Force) {
            if ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked directories cannot be auto-updated.' }
        }
        foreach ($file in Get-ChildItem -LiteralPath $Folder -File -Recurse -Force) {
            $relative = $file.FullName.Substring($Folder.TrimEnd('\', '/').Length + 1).Replace('\', '/')
            if ($relative -match '(^|/)__pycache__/|\.py[co]$') { continue }
            if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked files cannot be auto-updated.' }
            $result[$relative] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        }
    }
    return $result
}

function Test-SameManifest($Left, $Right) {
    if ($Left.Count -ne $Right.Count) { return $false }
    foreach ($key in $Left.Keys) {
        if (-not $Right.ContainsKey($key) -or $Left[$key] -ne $Right[$key]) { return $false }
    }
    return $true
}

function Test-RevitRunning {
    return [bool](Get-Process -Name Revit -ErrorAction SilentlyContinue)
}

function Save-ExtensionManifest($Manifest, [string]$Path) {
    $temporary = $Path + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
    try {
        $Manifest | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding UTF8
        if (Test-Path -LiteralPath $Path) { [IO.File]::Replace($temporary, $Path, [NullString]::Value) }
        else { [IO.File]::Move($temporary, $Path) }
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
}

function Write-UpdateLog([string]$Message) {
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath (Join-Path $StateFolder 'updates.log') -Value $line
    Write-Host $line
}

function Expand-VerifiedArchive([string]$Archive, [string]$Destination) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($Archive)
    try {
        $prefix = [IO.Path]::GetFullPath($Destination) + [IO.Path]::DirectorySeparatorChar
        foreach ($entry in $zip.Entries) {
            $path = [IO.Path]::GetFullPath((Join-Path $Destination $entry.FullName.Replace('\', '/')))
            if (-not $path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Archive contains an unsafe path.'
            }
        }
    } finally { $zip.Dispose() }
    [IO.Compression.ZipFile]::ExtractToDirectory($Archive, $Destination)
    $roots = @(Get-ChildItem -LiteralPath $Destination -Directory)
    if ($roots.Count -ne 1) { throw 'Unexpected repository archive structure.' }
    $extension = Join-Path $roots[0].FullName 'DECKTOOLS.extension'
    foreach ($required in @('lib/menu.xaml', 'DECKTOOLS.tab/bundle.yaml', 'lib/deck_menu.py')) {
        if (-not (Test-Path -LiteralPath (Join-Path $extension $required) -PathType Leaf)) {
            throw "Downloaded extension is incomplete: $required"
        }
    }
    return $extension
}

function Invoke-ExtensionUpdate {
    if (-not $Live -and (Test-RevitRunning)) { Write-UpdateLog 'Waiting: Revit is open. No files changed.'; return }
    if ((Test-Path -LiteralPath (Join-Path $Target '.git')) -or
        (Test-Path -LiteralPath (Join-Path $ExtensionParent '.git'))) {
        throw 'This folder is Git-managed. Use Git to update it instead.'
    }
    $current = Get-ExtensionManifest $Target
    $manifestPath = Join-Path $StateFolder 'installed-manifest.json'
    if (Test-Path -LiteralPath $manifestPath) {
        $saved = @{}
        $json = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        foreach ($property in $json.PSObject.Properties) { $saved[$property.Name] = $property.Value }
        if (-not (Test-SameManifest $current $saved)) {
            throw 'Local extension files changed. Automatic update paused to preserve your edits. See docs/AUTO_UPDATES.md.'
        }
    } elseif (-not $Install) {
        throw 'Run Setup Auto Updates.cmd once before automatic updates.'
    }
    $work = Join-Path $ExtensionParent ('.decktools-update-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $work | Out-Null
    try {
        $archive = Join-Path $work 'download.zip'
        # Keep this on the branch where the current DECKTOOLS improvements are published.
        $url = 'https://github.com/owenmerkel76-maker/DECKTOOLS/archive/refs/heads/codex/material-estimates.zip'
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing -TimeoutSec 90
        $incoming = Expand-VerifiedArchive $archive (Join-Path $work 'unpacked')
        $next = Get-ExtensionManifest $incoming
        if (Test-SameManifest $current $next) {
            if (-not (Test-Path -LiteralPath $manifestPath)) {
                Save-ExtensionManifest $next $manifestPath
            }
            Write-UpdateLog 'Already up to date.'
            return
        }
        if (-not $Live -and (Test-RevitRunning)) { Write-UpdateLog 'Waiting: Revit opened during download. No files changed.'; return }
        # Recheck for edits made while downloading; never overwrite those edits.
        if (-not (Test-SameManifest $current (Get-ExtensionManifest $Target))) {
            throw 'Extension changed during download. No files changed.'
        }
        $backup = Join-Path $StateFolder ('backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N'))
        $previous = Join-Path $work 'previous'
        $hadPrevious = Test-Path -LiteralPath $Target
        if ($hadPrevious) {
            # Copy the old version to durable storage BEFORE swapping the live directory.
            Copy-Item -LiteralPath $Target -Destination $backup -Recurse
            Move-Item -LiteralPath $Target -Destination $previous
        }
        try {
            Move-Item -LiteralPath $incoming -Destination $Target
            Save-ExtensionManifest $next $manifestPath
        } catch {
            if (Test-Path -LiteralPath $Target) { Remove-Item -LiteralPath $Target -Recurse -Force }
            if ($hadPrevious) { Move-Item -LiteralPath $previous -Destination $Target }
            throw
        }
        if ($hadPrevious) { Write-UpdateLog "Updated. Previous version backed up at $backup. Reload pyRevit to load the new version." }
        else { Write-UpdateLog 'Installed. Open Revit to load the new version.' }
    } finally {
        if (Test-Path -LiteralPath $work) { Remove-Item -LiteralPath $work -Recurse -Force }
    }
}

if ($FunctionsOnly) { return }
if ($env:OS -ne 'Windows_NT') { throw 'Run this setup on the Windows computer where Revit is installed.' }
$ExtensionParent = [IO.Path]::GetFullPath($ExtensionParent.Trim().Trim('"')).TrimEnd('\')
if ([IO.Path]::GetFileName($ExtensionParent) -eq 'DECKTOOLS.extension') {
    throw 'Enter the parent folder containing DECKTOOLS.extension, not the extension itself.'
}
$Target = Join-Path $ExtensionParent 'DECKTOOLS.extension'
$StateFolder = Join-Path $env:LOCALAPPDATA 'DECKTOOLS\AutoUpdate'
New-Item -ItemType Directory -Path $StateFolder -Force | Out-Null
$configPath = Join-Path $StateFolder 'folder.txt'
if ((Test-Path -LiteralPath $configPath) -and
    (Get-Content -LiteralPath $configPath -Raw).Trim() -ne $ExtensionParent) {
    throw 'Auto-updates are already configured for a different folder. Uninstall before changing folders.'
}
if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    # Preserve extension, logs, and backups; remove only configuration and baseline.
    Remove-Item -LiteralPath $configPath, (Join-Path $StateFolder 'installed-manifest.json') -Force -ErrorAction SilentlyContinue
    Write-Host 'Automatic updates disabled. Your extension and backups are preserved.'
    return
}
if ($Live) {
    # Live updates are explicit commands, never unattended replacements during use.
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) { $task | Disable-ScheduledTask | Out-Null }
    Write-UpdateLog 'Development mode: background task disabled. Use Update & Reload in DECKTOOLS.'
}
if (-not (Test-Path -LiteralPath $ExtensionParent -PathType Container)) {
    throw "Folder does not exist: $ExtensionParent"
}
if ((Get-Item -LiteralPath $ExtensionParent).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Choose a regular local folder, not a directory link.'
}
if ((Test-Path -LiteralPath $Target) -and
    ((Get-Item -LiteralPath $Target).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'The extension folder is a directory link. Choose a regular local folder.'
}
$mutex = New-Object Threading.Mutex($false, 'Local\DECKTOOLSAutoUpdate')
$locked = $false
try {
    try { $locked = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) { throw 'Another DECKTOOLS update is running. Try again in a few seconds.' }
    if ($Install -and (Test-RevitRunning)) { throw 'Close Revit, then run setup again.' }
    Invoke-ExtensionUpdate
    if ($Install) {
        if (-not (Test-Path -LiteralPath (Join-Path $StateFolder 'installed-manifest.json'))) {
            throw 'Setup was postponed because Revit opened. Close Revit and run setup again.'
        }
        $runner = Join-Path $StateFolder 'Update-DECKTOOLS.ps1'
        if ($PSCommandPath -ne $runner) { Copy-Item -LiteralPath $PSCommandPath -Destination $runner -Force }
        $ExtensionParent | Set-Content -LiteralPath $configPath -Encoding UTF8
        $powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        $arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" -ExtensionParent "{1}"' -f $runner, $ExtensionParent
        $action = New-ScheduledTaskAction -Execute $powershell -Argument $arguments
        $logon = New-ScheduledTaskTrigger -AtLogOn -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
        $interval = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15)
        $principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($logon, $interval) -Principal $principal -Settings $settings -Force | Out-Null
        Write-UpdateLog "Automatic updates enabled for $Target. Checks at sign-in and every 15 minutes while signed in; waits while Revit is open."
    }
} catch {
    Write-UpdateLog ('ERROR: ' + $_.Exception.Message)
    throw
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
