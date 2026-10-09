"""Appearance edit control flow; Autodesk runtime calls are mocked."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

LIB=Path(__file__).resolve().parents[1]/'DECKTOOLS.extension/lib'


class MaterialAssetTests(unittest.TestCase):
    def setUp(self):
        self.bitmap=NS(Value='original.png')
        self.image=NS(FindByName=Mock(return_value=self.bitmap))
        def property():
            p=NS(GetSingleConnectedAsset=Mock(return_value=None),
                 NumberOfConnectedProperties=0,RemoveConnectedAsset=Mock(),
                 SetValueAsColor=Mock())
            def connect(schema): p.GetSingleConnectedAsset.return_value=self.image
            p.AddConnectedAsset=Mock(side_effect=connect)
            return p
        self.diffuse,self.bump=property(),property()
        self.amount=NS(Value=0)
        self.properties={'generic_diffuse':self.diffuse,'generic_bump_map':self.bump,
                         'generic_bump_amount':self.amount}
        self.asset=NS(FindByName=lambda name:self.properties.get(name))
        self.appearance=NS(Id=101)
        self.material=NS(Name='DT wood')
        self.source_asset=NS(Duplicate=Mock(return_value=self.appearance))
        self.doc=NS(GetElement=lambda identifier:self.material if identifier==1 else self.source_asset)
        self.tx=Mock();self.tx.GetStatus.return_value='started';self.tx.Commit.return_value='committed'
        self.edit=Mock();self.edit.Start.return_value=self.asset
        collector=NS(OfClass=Mock(return_value=[]))
        db=NS(FilteredElementCollector=Mock(return_value=collector),
              Material=NS(Create=Mock(return_value=1)),Transaction=Mock(return_value=self.tx),
              TransactionStatus=NS(Started='started',Committed='committed'),
              Color=lambda *rgb:rgb,
              AppearanceAssetElement=NS(Create=Mock(return_value=self.appearance)),
              Visual=NS(AssetType=NS(Appearance='appearance'),AppearanceAssetEditScope=Mock(return_value=self.edit)))
        self.scope={'DB':db}
        tree=ast.parse((LIB/'deck_materials.py').read_text())
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        exec(compile(ast.Module(body=funcs,type_ignores=[]),'deck_materials.py','exec'),self.scope)
        self.app=NS(GetAssets=Mock(return_value=[self.asset]))
        self.spec={'name':'DT wood','rgb':(128,95,73),'texture':'wood.png',
                   'bump':'height.png','bump_amount':.5}

    def test_creates_native_color_texture_and_bump(self):
        self.assertIs(self.scope['create_material'](self.doc,self.app,self.spec),self.material)
        self.assertEqual(self.material.Color,(128,95,73))
        self.assertEqual(self.material.AppearanceAssetId,101)
        self.diffuse.AddConnectedAsset.assert_called_once_with('UnifiedBitmap')
        self.bump.AddConnectedAsset.assert_called_once_with('UnifiedBitmap')
        self.assertEqual(self.amount.Value,.5)
        self.edit.Commit.assert_called_once_with(True)
        self.tx.Commit.assert_called_once_with()

    def test_source_appearance_is_duplicated(self):
        self.scope['create_material'](self.doc,self.app,self.spec,NS(AppearanceAssetId=99))
        self.source_asset.Duplicate.assert_called_once_with('DT wood appearance')
        self.app.GetAssets.assert_not_called()

    def test_unsupported_schema_rolls_back_and_disposes(self):
        del self.properties['generic_diffuse']
        with self.assertRaisesRegex(ValueError,'unsupported appearance'):
            self.scope['create_material'](self.doc,self.app,self.spec,NS(AppearanceAssetId=99))
        self.tx.RollBack.assert_called_once_with()
        self.edit.Dispose.assert_called_once_with()
        self.tx.Commit.assert_not_called()

    def test_absent_generic_template_blocks_maps(self):
        self.app.GetAssets.return_value=[]
        with self.assertRaisesRegex(ValueError,'Generic appearance template'):
            self.scope['create_material'](self.doc,self.app,self.spec)
        self.tx.RollBack.assert_called_once_with()

    def test_source_maps_are_preserved_unless_explicitly_cleared(self):
        self.spec.update(texture='',bump='')
        self.diffuse.NumberOfConnectedProperties=self.bump.NumberOfConnectedProperties=1
        self.scope['create_material'](self.doc,self.app,self.spec,NS(AppearanceAssetId=99))
        self.diffuse.RemoveConnectedAsset.assert_not_called()
        self.bump.RemoveConnectedAsset.assert_not_called()
        self.spec['clear_maps']=True
        self.scope['create_material'](self.doc,self.app,self.spec,NS(AppearanceAssetId=99))
        self.diffuse.RemoveConnectedAsset.assert_called_once_with()
        self.bump.RemoveConnectedAsset.assert_called_once_with()

    def test_missing_bump_property_rolls_back(self):
        del self.properties['generic_bump_map']
        with self.assertRaisesRegex(ValueError,'texture/bump property'):
            self.scope['create_material'](self.doc,self.app,self.spec)
        self.tx.RollBack.assert_called_once_with()


if __name__=='__main__': unittest.main()
