from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import ast

LIB=Path(__file__).resolve().parents[1]/'DECKTOOLS.extension/lib'
sys.path.insert(0,str(LIB))
from deck_settings import layout_settings,material_settings


class SettingsTests(unittest.TestCase):
    def values(self):
        return {'stock_length':20,'spare_percent':'10','kerf_in':'.125','spacing_in':16,
                'frame_courses':2,'frame_width_in':5.5,'joist_mode':'nominal','clip_mode':'auto'}

    def test_settings_normalize_and_preserve_materials(self):
        values=self.values();values['frame_material_id']=22
        result=layout_settings(values)
        self.assertEqual(result['frame_courses'],2)
        self.assertEqual(result['spare_percent'],10.0)
        self.assertEqual(result['frame_material_id'],22)
        self.assertEqual(values['spare_percent'],'10')

    def test_invalid_settings_fail(self):
        for key,value in [('kerf_in','nan'),('spacing_in',0),('stock_length',15),
                          ('frame_courses',1.5),('frame_width_in',6),('joist_mode','x'),('clip_mode','x')]:
            values=self.values();values[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): layout_settings(values)

    def test_color_and_map_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            texture=Path(folder)/'wood.png';texture.write_bytes(b'test fixture')
            bump=Path(folder)/'height.jpg';bump.write_bytes(b'test fixture')
            result=material_settings('Brand wood','#805F49',str(texture),str(bump),'0.5')
            self.assertEqual(result['rgb'],(128,95,73))
            self.assertEqual(result['texture'],str(texture))
            self.assertEqual(result['bump_amount'],.5)

    def test_missing_maps_and_invalid_colors_fail(self):
        for args in [('', '#805F49'),('A','#GG0000'),('A','#fff'),
                     ('A','#805F49','/does-not-exist.png'),('A','#805F49','','','nan')]:
            with self.subTest(args=args),self.assertRaises(ValueError): material_settings(*args)

    def test_xaml_events_reference_real_handlers(self):
        pairs=[('layout.xaml','deck_ui.py','LayoutWindow'),
               ('materials.xaml','material_ui.py','MaterialWindow'),
               ('menu.xaml','deck_menu.py','DeckMenu')]
        for xaml,module,cls in pairs:
            tree=ET.parse(LIB/xaml)
            parsed=ast.parse((LIB/module).read_text(encoding='utf-8'))
            klass=next(n for n in parsed.body if isinstance(n,ast.ClassDef) and n.name==cls)
            methods={n.name for n in klass.body if isinstance(n,ast.FunctionDef)}
            for node in tree.iter():
                if 'Click' in node.attrib: self.assertIn(node.attrib['Click'],methods)
            names=[node.attrib.get('{http://schemas.microsoft.com/winfx/2006/xaml}Name') for node in tree.iter()]
            names=[n for n in names if n]
            self.assertEqual(len(names),len(set(names)))


if __name__=='__main__': unittest.main()
