@echo off
setlocal
echo DECKTOOLS fast development setup - Revit can stay open.
echo Close any DECKTOOLS dialog before continuing.
set "decktools_parent="
set /p "decktools_parent=Press Enter for your PY REVIT DECK TOOLS TEST folder, or type another parent folder: "
if not defined decktools_parent set "decktools_parent=C:\Users\owenm\Desktop\PY REVIT DECK TOOLS TEST"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0DECKTOOLS.extension\lib\Update-DECKTOOLS.ps1" -Live -ExtensionParent "%decktools_parent%"
if errorlevel 1 goto failed
echo Updated. Click pyRevit Reload once to see the new Update and Reload buttons.
goto done
:failed
echo Setup stopped. Read the last error in %%LOCALAPPDATA%%\DECKTOOLS\AutoUpdate\updates.log
:done
pause
