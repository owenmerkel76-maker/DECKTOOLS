"""Test family selection/load control flow with mocked Autodesk boundaries."""
import ast
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / 'DECKTOOLS.extension' / 'DECKTOOLS.tab' / 'Layout.panel' /
          'DeckAutoLayout.pushbutton' / 'script.py')


def load_functions(scope, names):
    tree=ast.parse(SCRIPT.read_text(encoding='utf-8'))
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(SCRIPT),'exec'),scope)


def symbol(name, identifier, placement='point', category=-2000151):
    return SimpleNamespace(Name='Type A',Id=SimpleNamespace(Value=identifier),
                           Category=SimpleNamespace(Id=SimpleNamespace(Value=category)),
                           Family=SimpleNamespace(Name=name,FamilyPlacementType=placement))


class ClipSelectionTests(unittest.TestCase):
    def test_any_brand_name_is_supported_and_hosted_types_are_filtered(self):
        supported=symbol('Brand Z Fastener',1)
        placeholder=symbol('DT_CAMO_EDGECLIP_3-16_SCHEMATIC',2)
        hosted=[symbol('Clip',3,'hosted'),symbol('Clip',4,'face'),
                symbol('Clip',5,'line'),symbol('Clip',6,'adaptive'),
                symbol('Clip',7,'workplane'),symbol('Clip',8,category=999)]
        collector=SimpleNamespace(OfClass=Mock(return_value=[supported,placeholder]+hosted))
        db=SimpleNamespace(FilteredElementCollector=Mock(return_value=collector),
                           FamilySymbol=object,
                           BuiltInCategory=SimpleNamespace(OST_GenericModel=-2000151),
                           FamilyPlacementType=SimpleNamespace(OneLevelBased='point'))
        scope={'DB':db,'DOC':object()}
        load_functions(scope,('element_id_value','existing_symbols'))
        items=scope['existing_symbols']()
        self.assertEqual(len(items),2)
        self.assertIs(items[0][1],supported)
        self.assertIn('Brand Z Fastener : Type A',[name for name,s in items])

    def test_non_ascii_clip_metadata_is_preserved(self):
        parameter=SimpleNamespace(IsReadOnly=False,Set=Mock())
        scope={'_param':Mock(return_value=parameter),
               'takeoff':SimpleNamespace(text_type=str)}
        load_functions(scope,('_set_param',))
        scope['_set_param'](object(),object(),'CLIP|FAMILY_TYPE=Marqu\u00e9 : Mod\u00e8le A')
        parameter.Set.assert_called_once_with('CLIP|FAMILY_TYPE=Marqu\u00e9 : Mod\u00e8le A')


class ClipLoadingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path=Path(self.temp.name)/'OtherBrand.rfa'
        path.write_bytes(b'fixture; Autodesk load is mocked')
        self.selected=symbol('OtherBrand',2)
        self.old=symbol('Existing Clip',1)
        self.transaction=Mock()
        self.transaction.GetStatus.return_value='started'
        self.transaction.Commit.return_value='committed'
        self.scope={
            'os':os,
            'DOC':SimpleNamespace(LoadFamily=Mock(return_value=True)),
            'DB':SimpleNamespace(Transaction=Mock(return_value=self.transaction),
                                 TransactionStatus=SimpleNamespace(Started='started',Committed='committed')),
            'forms':SimpleNamespace(pick_file=Mock(return_value=str(path)),
                                    SelectFromList=SimpleNamespace(
                                        show=Mock(return_value='OtherBrand : Type A'))),
            'existing_symbols':Mock(side_effect=[
                [('Existing Clip : Type A',self.old)],
                [('Existing Clip : Type A',self.old),('OtherBrand : Type A',self.selected)]])}
        load_functions(self.scope,('element_id_value','choose_clip_type','load_clip_family'))

    def test_load_selects_only_new_family_types(self):
        result=self.scope['load_clip_family']()
        self.assertIs(result,self.selected)
        choices=self.scope['forms'].SelectFromList.show.call_args.args[0]
        self.assertEqual(choices,['OtherBrand : Type A'])
        self.transaction.Commit.assert_called_once_with()
        self.transaction.RollBack.assert_not_called()

    def test_tuple_return_from_dotnet_load_is_supported(self):
        self.scope['DOC'].LoadFamily.return_value=(True,object())
        self.assertIs(self.scope['load_clip_family'](),self.selected)

    def test_cancelled_file_picker_does_not_load(self):
        self.scope['forms'].pick_file.return_value=None
        self.assertIsNone(self.scope['load_clip_family']())
        self.scope['DOC'].LoadFamily.assert_not_called()
        self.scope['DB'].Transaction.assert_not_called()

    def test_cancelled_type_selection_rolls_back_loaded_family(self):
        self.scope['forms'].SelectFromList.show.return_value=None
        self.assertIsNone(self.scope['load_clip_family']())
        self.transaction.RollBack.assert_called_once_with()
        self.transaction.Commit.assert_not_called()

    def test_incompatible_family_rolls_back(self):
        self.scope['existing_symbols'].side_effect=[
            [('Existing Clip : Type A',self.old)],
            [('Existing Clip : Type A',self.old)]]
        with self.assertRaisesRegex(ValueError,'point-based Generic Model'):
            self.scope['load_clip_family']()
        self.transaction.RollBack.assert_called_once_with()
        self.transaction.Commit.assert_not_called()

    def test_already_loaded_family_is_not_overwritten(self):
        self.scope['DOC'].LoadFamily.return_value=(False,None)
        with self.assertRaisesRegex(ValueError,'already loaded'):
            self.scope['load_clip_family']()
        self.transaction.RollBack.assert_called_once_with()
        self.transaction.Commit.assert_not_called()

    def test_load_error_rolls_back(self):
        self.scope['DOC'].LoadFamily.side_effect=RuntimeError('Revit version mismatch')
        with self.assertRaisesRegex(RuntimeError,'version mismatch'):
            self.scope['load_clip_family']()
        self.transaction.RollBack.assert_called_once_with()

    def test_failed_commit_is_not_reported_as_loaded(self):
        self.transaction.Commit.return_value='rolledback'
        self.transaction.GetStatus.return_value='rolledback'
        with self.assertRaisesRegex(RuntimeError,'did not commit'):
            self.scope['load_clip_family']()


if __name__ == '__main__':
    unittest.main()
