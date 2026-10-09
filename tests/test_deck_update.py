import ast
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import Mock
import os

LIB = Path(__file__).resolve().parents[1] / 'DECKTOOLS.extension/lib'


class UpdateTests(TestCase):
    def setUp(self):
        self.process = NS(WaitForExit=Mock(), Dispose=Mock(), ExitCode=0)
        self.start = NS()
        self.session = NS(reload_pyrevit=Mock())
        self.scope = {'os': NS(path=os.path, environ={'SYSTEMROOT': r'C:\Windows'}),
                      '__file__': str(LIB / 'deck_update.py'),
                      'forms': NS(alert=Mock()), 'sessionmgr': self.session,
                      'ProcessStartInfo': Mock(return_value=self.start),
                      'Process': NS(Start=Mock(return_value=self.process))}
        tree = ast.parse((LIB / 'deck_update.py').read_text())
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'deck_update.py', 'exec'), self.scope)

    def test_successful_update_reloads_only_after_process_finishes(self):
        events = []
        self.process.WaitForExit.side_effect = lambda: events.append('wait')
        self.process.Dispose.side_effect = lambda: events.append('dispose')
        self.session.reload_pyrevit.side_effect = lambda: events.append('reload')
        self.scope['update_and_reload']()
        self.assertEqual(events, ['wait', 'dispose', 'reload'])
        self.assertIn('-Live', self.start.Arguments)
        self.assertFalse(self.start.UseShellExecute)
        self.assertTrue(self.start.CreateNoWindow)

    def test_failed_update_does_not_reload(self):
        self.process.ExitCode = 1
        self.scope['update_and_reload']()
        self.session.reload_pyrevit.assert_not_called()
        self.process.Dispose.assert_called_once()
        self.assertIn('updates.log', self.scope['forms'].alert.call_args.args[0])

    def test_local_reload_does_not_start_updater(self):
        self.scope['reload_tools']()
        self.session.reload_pyrevit.assert_called_once()
        self.scope['Process'].Start.assert_not_called()

    def test_spaces_are_quoted_and_command_injection_is_rejected(self):
        arguments = self.scope['updater_arguments']('C:\\folder with spaces\\updater.ps1',
                                                     'C:\\PY REVIT DECK TOOLS TEST')
        self.assertIn('-ExtensionParent "C:\\PY REVIT DECK TOOLS TEST"', arguments)
        for value in ['bad"path', 'bad\npath', 'bad\rpath']:
            with self.assertRaises(ValueError):
                self.scope['updater_arguments'](value, 'C:\\tools')
