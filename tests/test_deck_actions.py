import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,MagicMock

LIB=Path(__file__).resolve().parents[1]/'DECKTOOLS.extension/lib'


class DeckActionsTests(unittest.TestCase):
    def setUp(self):
        self.floor=NS(Id=NS(Value=123))
        def element(identifier,comments):
            return NS(Id=identifier,get_Parameter=lambda name:NS(AsString=lambda:comments))
        self.items=[element(1,'DECKTOOLS|F123|BOARD|ROLE=FIELD'),
                    element(2,'DECKTOOLS|F123|BOARD|ROLE=FRAME'),
                    element(3,'DECKTOOLS|F123|CLIP|FAMILY_TYPE=Brand A'),
                    element(4,'DECKTOOLS|F456|BOARD|ROLE=FRAME'),
                    element(5,'DECKTOOLS|F1234|BOARD|ROLE=FIELD'),element(6,'ordinary model')]
        collector=NS(OfCategory=Mock())
        collector.OfCategory.return_value=NS(WhereElementIsNotElementType=Mock(return_value=self.items))
        self.doc=NS(Delete=Mock())
        self.scope={'DB':NS(FilteredElementCollector=Mock(return_value=collector),
                            BuiltInCategory=NS(OST_GenericModel='generic'),
                            BuiltInParameter=NS(ALL_MODEL_INSTANCE_COMMENTS='comments')),
                    'revit':NS(doc=self.doc,Transaction=MagicMock()),
                    'forms':NS(alert=Mock(return_value=True)),
                    'selected_floor':Mock(return_value=self.floor)}
        tree=ast.parse((LIB/'deck_actions.py').read_text())
        functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)
                   and n.name in ('generated_elements','inspect_deck','remove_deck')]
        exec(compile(ast.Module(body=functions,type_ignores=[]),'deck_actions.py','exec'),self.scope)

    def test_inspect_counts_field_frame_and_clips_for_only_one_floor(self):
        self.scope['inspect_deck']()
        report=self.scope['forms'].alert.call_args.args[0]
        self.assertIn('Field board cuts: 1',report)
        self.assertIn('Picture-frame cuts: 1',report)
        self.assertIn('Clip elements: 1',report)
        self.assertIn('Total generated elements: 3',report)

    def test_remove_targets_generated_elements_and_preserves_floor(self):
        self.scope['remove_deck']()
        self.assertEqual([call.args[0] for call in self.doc.Delete.call_args_list],[1,2,3])
        self.assertNotIn(self.floor.Id,self.doc.Delete.call_args_list)
        self.scope['revit'].Transaction.assert_called_once_with('DECKTOOLS | remove generated deck')

    def test_cancelled_remove_does_not_delete(self):
        self.scope['forms'].alert.return_value=False
        self.scope['remove_deck']()
        self.doc.Delete.assert_not_called()
        self.scope['revit'].Transaction.assert_not_called()


if __name__=='__main__': unittest.main()
