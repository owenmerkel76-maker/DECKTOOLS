# Fast testing with Revit open

Your linked folder stays `C:\Users\owenm\Desktop\PY REVIT DECK TOOLS TEST`.
The tools do not change your pyRevit folder setting or your open project.

## One-time transition from the automatic updater

If the new buttons are already visible, go straight to Update & Reload.
Otherwise download the latest repository ZIP, extract it, and run
**Enable Fast Testing.cmd** with your existing Revit project open. Close any
DECKTOOLS dialog first. Press Enter for your linked folder, then click
**pyRevit → Reload** after the command says the update succeeded.
This uses the existing updater's installed-file baseline and disables its
scheduled task. It needs the automatic update setup you already completed.

Alternatively, let the existing automatic updater deliver these buttons once
while Revit is closed. You can then switch to the workflow below.

## Changes published by Codex

1. Wait until the change is committed and pushed to `codex/material-estimates`.
2. Between tool runs, click **DECKTOOLS → Studio → Update & Reload**.
3. Run the tool again. Rerun Deck Designer on the same footprint to regenerate
   its boards and clips with the new behavior.

Update & Reload downloads the latest extension, keeps a backup, and uses
pyRevit's native session reload. It keeps the Revit project open. The explicit
update disables **DECKTOOLS automatic updates** in Task Scheduler so background
replacement does not compete with development. Offline checks or locally
modified extension files stop the download workflow; no reload occurs on failure.
Check `%LOCALAPPDATA%\DECKTOOLS\AutoUpdate\updates.log` for the error.
No download or manual file replacement is needed for subsequent changes.

## Local editing or GitHub Desktop

After changing files in the linked extension folder, click **Reload Local
Changes**. It only reloads pyRevit; it does not download or replace any files.
If GitHub Desktop manages the checkout, select the `codex/material-estimates`
branch and **Fetch origin / Pull origin**, then click **Reload Local Changes**.
Your pyRevit Custom Extension Folders path must point at that checkout's folder
containing `DECKTOOLS.extension`. Signing into GitHub Desktop alone does not
connect the existing ZIP installation to Git. Do not register both installations.
Disable the background updater before switching to a Git checkout.

Most Python, XAML, ribbon, and tooltip changes can be tested this way. Changes
to compiled add-ins, pyRevit itself, or locked assemblies may require restarting
Revit. Reload does not retroactively change existing geometry, families, or
project materials; run the appropriate tool again to test the new behavior.
Run reloads between commands with DECKTOOLS dialogs closed.

The download/swap/rollback and reload dispatch are covered by cloud checks.
Native pyRevit ribbon reload still needs testing inside Windows Revit.
