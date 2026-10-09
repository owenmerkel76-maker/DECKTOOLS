# Compatibility entry point; the updater ships inside the extension for live updates.
try {
    & "$PSScriptRoot/../../DECKTOOLS.extension/lib/Update-DECKTOOLS.ps1" @args
    exit 0
} catch {
    Write-Error $_
    exit 1
}
