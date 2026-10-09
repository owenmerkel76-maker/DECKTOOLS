@echo off
setlocal
echo DECKTOOLS automatic updates
echo Close Revit first. This preserves a backup and updates your linked folder.
echo Default folder: C:\Users\owenm\Desktop\PY REVIT DECK TOOLS TEST
set "decktools_parent="
set /p "decktools_parent=Press Enter to use this folder, or type another parent folder: "
if not defined decktools_parent set "decktools_parent=C:\Users\owenm\Desktop\PY REVIT DECK TOOLS TEST"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0DECKTOOLS.extension\lib\Update-DECKTOOLS.ps1" -Install -ExtensionParent "%decktools_parent%"
if errorlevel 1 echo Setup failed. Read the error above; no automatic updates have been confirmed.
pause
