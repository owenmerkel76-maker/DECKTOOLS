# -*- coding: utf-8 -*-
import os
import runpy
from pyrevit import forms,HOST_APP
import deck_actions
from material_ui import show_material_tool

EXTENSION=os.path.dirname(os.path.dirname(__file__))


class DeckMenu(forms.WPFWindow):
    def __init__(self):
        forms.WPFWindow.__init__(self,os.path.join(os.path.dirname(__file__),'menu.xaml'))
        self.action=None
    def on_action(self,sender,args):
        self.action=str(sender.Tag)
        self.Close()


def launch_script(relative):
    runpy.run_path(os.path.join(EXTENSION,relative),
                  init_globals={'__revit__':HOST_APP.uiapp},run_name='__main__')


def show_menu():
    menu=DeckMenu()
    menu.ShowDialog()
    actions={
        'layout':lambda:launch_script('DECKTOOLS.tab/Layout.panel/DeckAutoLayout.pushbutton/script.py'),
        'board':lambda:launch_script('DECKTOOLS.tab/Boards.panel/TrexBoardBuilder.pushbutton/script.py'),
        'materials':show_material_tool,'inspect':deck_actions.inspect_deck,
        'select':deck_actions.select_deck,'remove':deck_actions.remove_deck,
        'reports':deck_actions.open_reports,'library':deck_actions.manufacturer_library}
    if menu.action in actions:
        try: actions[menu.action]()
        except Exception as error:
            import traceback
            print(traceback.format_exc())
            forms.alert(str(error),title='DECKTOOLS')
