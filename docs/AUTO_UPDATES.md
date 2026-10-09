# Automatic updates on your Revit computer

Run **Setup Auto Updates.cmd** from the extracted repository once, with Revit
closed. Press Enter to use `C:\Users\owenm\Desktop\PY REVIT DECK TOOLS TEST`,
or enter the parent folder containing your existing `DECKTOOLS.extension`.
Keep your existing pyRevit Custom Extension Folders setting pointing there.
No Git, Python, or administrator access is needed.

Setup downloads the current extension and registers **DECKTOOLS automatic
updates** in Windows Task Scheduler for your Windows account. The task checks
at sign-in and every 15 minutes while you are signed in. It only changes files
while Revit is closed. Open Revit after an update to load the new version.
An offline computer keeps its current extension; the next scheduled check retries.
Windows must allow PowerShell and per-user scheduled tasks; workplace policies
may prevent setup. Never enable automatic updates on a shared multi-user folder.

Updates come from the `codex/material-estimates` branch of
`owenmerkel76-maker/DECKTOOLS`, where the current improvements are published.
Only committed and pushed changes are available. Changes on other branches
do not update this installation. The repository must remain publicly
downloadable from your Windows computer. The task updates the extension, not
its own copied updater script; rerun setup to install future updater changes.

Setup backs up an existing folder before replacing it. Subsequent
updates stop if you have edited, added, or removed extension files locally
(Python caches are ignored). Reports in Documents and materials/families saved
outside the extension folder are unaffected. Keep custom files outside the
managed extension directory. Backups are kept indefinitely; delete older ones
manually when you no longer need them.

## Status, backup, and manual check

Open `%LOCALAPPDATA%\DECKTOOLS\AutoUpdate` in File Explorer:

- `updates.log` records updates, waits, and errors.
- `backup-*` directories contain previous extension versions.
- `folder.txt` records the linked parent folder.

For a check immediately, open Task Scheduler, select **DECKTOOLS automatic
updates**, and choose **Run**, with Revit closed.

To disable the task, right-click it and choose **Disable**. To remove its
registration, run this in PowerShell (use your own parent folder if different):

```powershell
& "$env:LOCALAPPDATA\DECKTOOLS\AutoUpdate\Update-DECKTOOLS.ps1" -Uninstall -ExtensionParent 'C:\Users\owenm\Desktop\PY REVIT DECK TOOLS TEST'
```

If local edits have paused updates, save your edited folder elsewhere first.
Then uninstall using the command above and rerun setup to adopt the repository
version; setup will also back up the edited folder. To restore a previous
version, disable the task, close Revit, move the current extension aside, and
copy a backup directory into the linked parent as `DECKTOOLS.extension`.
Reopen Revit. Leave updates disabled until you choose to adopt newer code.

Cloud tests exercise downloads, file comparisons, backup/swap, failure rollback,
and local-edit protection. Windows Task Scheduler registration and Revit process
detection still require checking on the Windows computer.
