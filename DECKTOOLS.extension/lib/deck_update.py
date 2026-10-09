# -*- coding: utf-8 -*-
"""Explicit development updates, followed by pyRevit's native session reload."""
import os
from pyrevit import forms
from pyrevit.loader import sessionmgr
from System.Diagnostics import Process, ProcessStartInfo


def updater_arguments(script, parent):
    for value in (script, parent):
        if any(character in value for character in ('"', '\r', '\n')):
            raise ValueError('Unsupported character in extension path.')
    return '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -Live -ExtensionParent "{1}"'.format(script, parent)


def reload_tools():
    """Reload local edits without downloading or changing any files."""
    sessionmgr.reload_pyrevit()


def update_and_reload():
    extension = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(extension, 'lib', 'Update-DECKTOOLS.ps1')
    parent = os.path.dirname(extension)
    executable = os.path.join(os.environ['SYSTEMROOT'], 'System32',
                              'WindowsPowerShell', 'v1.0', 'powershell.exe')
    start = ProcessStartInfo()
    start.FileName = executable
    start.Arguments = updater_arguments(script, parent)
    start.UseShellExecute = False
    start.CreateNoWindow = True
    process = Process.Start(start)
    try:
        # PowerShell records errors in updates.log; no redirected pipes can block.
        process.WaitForExit()
        exit_code = process.ExitCode
    finally:
        process.Dispose()
    if exit_code != 0:
        forms.alert('Update stopped. Your current tools have not been reloaded.\n\n'
                    'Read the last error in:\n%LOCALAPPDATA%\\DECKTOOLS\\AutoUpdate\\updates.log\n\n'
                    'Local edits are preserved. If you use a Git checkout, pull in '
                    'GitHub Desktop and use Reload Local Changes instead.',
                    title='DECKTOOLS | Update & Reload')
        return
    # Use pyRevit's supported reload, outside any Revit transaction or open dialog.
    reload_tools()
