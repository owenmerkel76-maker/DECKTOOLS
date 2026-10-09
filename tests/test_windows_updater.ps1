# Dependency-free regression tests: pwsh -NoProfile -File tests/test_windows_updater.ps1
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/../tools/windows/Update-DECKTOOLS.ps1" -FunctionsOnly
$sandbox = Join-Path ([IO.Path]::GetTempPath()) ('decktools-tests-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $sandbox | Out-Null
$script:Checks = 0
function Assert-True($Condition, $Message) {
    if (-not $Condition) { throw "FAIL: $Message" }
    $script:Checks++
}
function Assert-Throws($Action, $Pattern) {
    $caught = $null
    try { & $Action } catch { $caught = $_.Exception.Message }
    Assert-True ($caught -and $caught -match $Pattern) "Expected error matching '$Pattern'; got '$caught'"
}
function Test-RevitRunning {
    $script:ProcessChecks++
    return ($script:Running -or ($script:OpenDuringDownload -and $script:ProcessChecks -gt 1))
}
function Invoke-WebRequest($Uri, $OutFile, [switch]$UseBasicParsing, $TimeoutSec) {
    $script:Downloads++
    if ($script:FailDownload) { throw 'Network unavailable' }
    Copy-Item -LiteralPath $script:Fixture -Destination $OutFile
}
function Move-Item($LiteralPath, $Destination) {
    if ($script:FailSwap -and $LiteralPath -match 'unpacked') { throw 'Simulated locked folder' }
    Microsoft.PowerShell.Management\Move-Item -LiteralPath $LiteralPath -Destination $Destination
}
function Set-Content {
    param($LiteralPath, [Parameter(ValueFromPipeline=$true)]$Value, $Encoding)
    process {
        if ($script:FailManifest -and $LiteralPath -match 'installed-manifest\.json\..*\.tmp$') {
            throw 'Simulated metadata write failure'
        }
        if ($Encoding) { Microsoft.PowerShell.Management\Set-Content -LiteralPath $LiteralPath -Value $Value -Encoding $Encoding }
        else { Microsoft.PowerShell.Management\Set-Content -LiteralPath $LiteralPath -Value $Value }
    }
}
try {
    $ExtensionParent = Join-Path $sandbox 'linked folder with spaces'
    $StateFolder = Join-Path $sandbox 'state'
    $Target = Join-Path $ExtensionParent 'DECKTOOLS.extension'
    New-Item -ItemType Directory -Path $Target, $StateFolder | Out-Null
    Set-Content -LiteralPath (Join-Path $Target 'old-tool.py') -Value 'old version'
    $original = Get-ExtensionManifest $Target
    $source = Join-Path $sandbox 'source/repository/DECKTOOLS.extension'
    New-Item -ItemType Directory -Path (Join-Path $source 'lib'), (Join-Path $source 'DECKTOOLS.tab') -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $source 'lib/menu.xaml') -Value '<Window />'
    Set-Content -LiteralPath (Join-Path $source 'lib/deck_menu.py') -Value '# new menu'
    Set-Content -LiteralPath (Join-Path $source 'DECKTOOLS.tab/bundle.yaml') -Value 'title: DECKTOOLS'
    $script:Fixture = Join-Path $sandbox 'fixture.zip'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::CreateFromDirectory((Join-Path $sandbox 'source'), $script:Fixture)
    $Install = $true
    $script:ProcessChecks = 0
    Invoke-ExtensionUpdate
    Assert-True (Test-SameManifest (Get-ExtensionManifest $Target) (Get-ExtensionManifest $source)) 'New extension installed'
    $backups = @(Get-ChildItem -LiteralPath $StateFolder -Directory -Filter 'backup-*')
    Assert-True ($backups.Count -eq 1) 'Original installation backed up once'
    Assert-True (Test-SameManifest $original (Get-ExtensionManifest $backups[0].FullName)) 'Complete backup preserves original files'
    $Install = $false
    Invoke-ExtensionUpdate
    Assert-True (@(Get-ChildItem -LiteralPath $StateFolder -Directory -Filter 'backup-*').Count -eq 1) 'Unchanged version does not create extra backups'
    New-Item -ItemType Directory -Path (Join-Path $Target '__pycache__') | Out-Null
    Set-Content -LiteralPath (Join-Path $Target '__pycache__/menu.pyc') -Value 'cache'
    Invoke-ExtensionUpdate
    Assert-True (Test-SameManifest (Get-ExtensionManifest $Target) (Get-ExtensionManifest $source)) 'Python caches ignored'
    $edited = Join-Path $Target 'lib/deck_menu.py'
    Set-Content -LiteralPath $edited -Value '# user edits'
    Assert-Throws { Invoke-ExtensionUpdate } 'Local extension files changed'
    Assert-True ((Get-Content -LiteralPath $edited -Raw) -match 'user edits') 'Local edits preserved'
    Copy-Item -LiteralPath (Join-Path $source 'lib/deck_menu.py') -Destination $edited -Force
    $extra = Join-Path $Target 'my-custom-family.rfa'
    Set-Content -LiteralPath $extra -Value 'user family'
    Assert-Throws { Invoke-ExtensionUpdate } 'Local extension files changed'
    Remove-Item -LiteralPath $extra
    Remove-Item -LiteralPath $edited
    Assert-Throws { Invoke-ExtensionUpdate } 'Local extension files changed'
    Copy-Item -LiteralPath (Join-Path $source 'lib/deck_menu.py') -Destination $edited
    $script:FailDownload = $true
    Assert-Throws { Invoke-ExtensionUpdate } 'Network unavailable'
    Assert-True (Test-SameManifest (Get-ExtensionManifest $Target) (Get-ExtensionManifest $source)) 'Failed download leaves installation intact'
    $script:FailDownload = $false
    $script:Running = $true
    $beforeDownloads = $script:Downloads
    Invoke-ExtensionUpdate
    Assert-True ($beforeDownloads -eq $script:Downloads) 'No download or mutation while Revit is running'
    $script:Running = $false
    # Publish a changed version for rollback and process-race tests.
    Set-Content -LiteralPath (Join-Path $source 'lib/deck_menu.py') -Value '# updated menu'
    Remove-Item -LiteralPath $script:Fixture
    [IO.Compression.ZipFile]::CreateFromDirectory((Join-Path $sandbox 'source'), $script:Fixture)
    $beforeUpdate = Get-ExtensionManifest $Target
    $script:OpenDuringDownload = $true
    $script:ProcessChecks = 0
    Invoke-ExtensionUpdate
    Assert-True (Test-SameManifest $beforeUpdate (Get-ExtensionManifest $Target)) 'Revit opening during download postpones update'
    $script:OpenDuringDownload = $false
    $script:FailSwap = $true
    Assert-Throws { Invoke-ExtensionUpdate } 'Simulated locked folder'
    Assert-True (Test-SameManifest $beforeUpdate (Get-ExtensionManifest $Target)) 'Failed swap restores complete prior installation'
    $script:FailSwap = $false
    # A failed metadata write must restore files and preserve the old baseline.
    $manifestBefore = Get-Content -LiteralPath (Join-Path $StateFolder 'installed-manifest.json') -Raw
    $script:FailManifest = $true
    Assert-Throws { Invoke-ExtensionUpdate } 'Simulated metadata write failure'
    Assert-True (Test-SameManifest $beforeUpdate (Get-ExtensionManifest $Target)) 'Failed metadata write rolls back installation'
    Assert-True ($manifestBefore -eq (Get-Content -LiteralPath (Join-Path $StateFolder 'installed-manifest.json') -Raw)) 'Failed metadata write preserves baseline'
    $script:FailManifest = $false
    Invoke-ExtensionUpdate
    Assert-True (Test-SameManifest (Get-ExtensionManifest $Target) (Get-ExtensionManifest $source)) 'Retry after failed swap succeeds'
    Assert-True (@(Get-ChildItem -LiteralPath $ExtensionParent -Directory -Filter '.decktools-update-*').Count -eq 0) 'Temporary downloads cleaned up'
    # Verify archive path traversal is rejected before extraction.
    $evil = Join-Path $sandbox 'unsafe.zip'
    $zip = [IO.Compression.ZipFile]::Open($evil, [IO.Compression.ZipArchiveMode]::Create)
    $zip.CreateEntry('../escaped.txt') | Out-Null
    $zip.Dispose()
    Assert-Throws { Expand-VerifiedArchive $evil (Join-Path $sandbox 'unsafe') } 'unsafe path'
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $sandbox 'escaped.txt'))) 'Archive cannot write outside extraction directory'
    Write-Host "$script:Checks updater checks passed. Windows scheduler/process integration not exercised."
} finally {
    Remove-Item -LiteralPath $sandbox -Recurse -Force
}
