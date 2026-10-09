"""Exercise the button's prompt/estimate flow with mocked Revit boundaries.

This executes the actual main function but does not validate Autodesk geometry.
"""
import ast
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'DECKTOOLS.extension' / 'DECKTOOLS.tab' / 'Layout.panel' / 'DeckAutoLayout.pushbutton'
sys.path.insert(0, str(CORE))

import board_math as bm
import takeoff


class LayoutWorkflowTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((CORE / 'script.py').read_text(encoding='utf-8'))
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name in ('main', 'element_id_value', 'symbol_label', 'choose_clip_type', 'clip_points')]
        code = compile(ast.Module(body=functions, type_ignores=[]), str(CORE / 'script.py'), 'exec')
        forms = SimpleNamespace(
            CommandSwitchWindow=SimpleNamespace(show=Mock(side_effect=[
                'Along LONG edge of deck (default)', '12-foot stock',
                'Use nominal joists at 16in O.C. (test estimate)',
                'Use generic placeholder solids (no family)'])),
            ask_for_string=Mock(side_effect=['10', '0.125', '16']),
            SelectFromList=SimpleNamespace(show=Mock()))
        self.settings={'along_long':True,'stock_length':12,'spare_percent':10,'kerf_in':.125,
                       'spacing_in':16,'frame_courses':0,'frame_width_in':5.5,
                       'joist_mode':'nominal','clip_mode':'proxy'}
        floor = SimpleNamespace(Id=SimpleNamespace(Value=123))
        self.scope = {
            'DOC':SimpleNamespace(IsFamilyDocument=False),
            'APP':SimpleNamespace(VersionNumber='2025'),
            'TITLE':'DECKTOOLS', 'forms':forms, 'bm':bm, 'takeoff':takeoff, 'os':os,
            'pick_floor':Mock(return_value=floor),
            'collect_layout_settings':Mock(return_value=self.settings),
            'floor_rectangle':Mock(return_value={'length':12.0, 'width':10.0}),
            'clip_points':lambda plan, coord, segments, stations:
                          [(s, t) for s in stations for t in plan['seams']],
            'existing_symbols':Mock(return_value=[]),
            'old_elements':Mock(return_value=[]),
            'confirm':Mock(return_value=True),
            'place':Mock(side_effect=lambda plan, coord, floor, clips, sym, old, **kwargs:
                         (plan['boards'], clips)),
            'exports':Mock(return_value={'Cutlist.csv':'/reports/Cutlist.csv',
                                        'StockCuts.csv':'/reports/StockCuts.csv',
                                        'Materials.csv':'/reports/Materials.csv'}),
            'output':SimpleNamespace(print_md=Mock()), 'alert':Mock(),
        }
        exec(code, self.scope)

    def test_preview_model_and_export_share_selected_stock_and_spares(self):
        with redirect_stdout(io.StringIO()):
            self.scope['main']()
        preview = self.scope['confirm'].call_args.args[0]
        self.assertIn('12ft stock: 22 base + 4 spare = 26 boards to purchase', preview)
        model_plan = self.scope['place'].call_args.args[0]
        export_args = self.scope['exports'].call_args.args
        self.assertIs(export_args[1], model_plan)
        self.assertEqual(model_plan['stock_length_ft'], 12)
        self.assertEqual(len(model_plan['boards']), 22)
        self.assertEqual(export_args[-1]['purchase_stock'], 26)
        self.assertIn('26 estimated 12ft boards to purchase', self.scope['alert'].call_args.args[0])

    def test_cancelled_preview_does_not_place_or_export(self):
        self.scope['confirm'].return_value = False
        self.scope['main']()
        self.scope['place'].assert_not_called()
        self.scope['exports'].assert_not_called()

    def test_invalid_settings_do_not_place_or_export(self):
        self.settings['spare_percent']=float('nan')
        with self.assertRaises(ValueError):
            self.scope['main']()
        self.scope['place'].assert_not_called()
        self.scope['exports'].assert_not_called()
        self.scope['confirm'].assert_not_called()

    def test_modern_element_id_does_not_truncate_large_values(self):
        self.assertEqual(self.scope['element_id_value'](SimpleNamespace(Value=2**40)), 2**40)
        self.assertEqual(self.scope['element_id_value'](SimpleNamespace(IntegerValue=123)), 123)

    def test_cancelled_settings_does_not_modify_model(self):
        self.scope['collect_layout_settings'].return_value=None
        self.scope['main']()
        self.scope['place'].assert_not_called()

    def test_frame_geometry_and_materials_reach_model_and_reports(self):
        self.settings.update({'frame_courses':1,'field_material_id':11,'frame_material_id':22,
                              'field_material_name':'Warm wood','frame_material_name':'Dark border'})
        with redirect_stdout(io.StringIO()): self.scope['main']()
        plan=self.scope['place'].call_args.args[0]
        self.assertEqual(sum(b.get('role')=='FRAME' for b in plan['boards']),4)
        self.assertEqual(plan['frame_material'],'Dark border')
        self.assertEqual(self.scope['place'].call_args.kwargs,
                         {'field_material_id':11,'frame_material_id':22})
        clips=self.scope['place'].call_args.args[3]
        self.assertTrue(all(plan['field_bounds'][0]<=s<=plan['field_bounds'][1] for s,t in clips))
        self.assertIs(self.scope['exports'].call_args.args[1],plan)

    def test_loaded_brand_family_is_used_and_reported_by_type(self):
        symbol=SimpleNamespace(Family=SimpleNamespace(Name='OtherBrand'), Name='Fastener A')
        label='OtherBrand : Fastener A'
        self.scope['existing_symbols'].return_value=[(label,symbol)]
        self.scope['forms'].SelectFromList.show.return_value=label
        self.settings['clip_mode']='loaded'
        with redirect_stdout(io.StringIO()):
            self.scope['main']()
        self.assertIs(self.scope['place'].call_args.args[4],symbol)
        self.assertEqual(self.scope['exports'].call_args.args[5],label)
        self.assertIn('Clip family/type: '+label,self.scope['confirm'].call_args.args[0])

    def test_browsed_family_is_used(self):
        symbol=SimpleNamespace(Family=SimpleNamespace(Name='Brand B'), Name='Hidden Fastener')
        self.scope['load_clip_family']=Mock(return_value=symbol)
        self.settings['clip_mode']='browse'
        with redirect_stdout(io.StringIO()):
            self.scope['main']()
        self.scope['load_clip_family'].assert_called_once_with()
        self.assertIs(self.scope['place'].call_args.args[4],symbol)
        self.assertEqual(self.scope['exports'].call_args.args[5],'Brand B : Hidden Fastener')

    def test_cancelled_family_browse_does_not_generate_deck(self):
        self.scope['load_clip_family']=Mock(return_value=None)
        self.settings['clip_mode']='browse'
        self.scope['main']()
        self.scope['place'].assert_not_called()
        self.scope['exports'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
