# -*- coding: utf-8 -*-
"""Native Revit material creation with independent appearance assets.

Generic appearance schema only; unsupported schemas fail without leaving a
partial material. Texture/bump files remain external Revit rendering resources.
"""
from Autodesk.Revit import DB


def connect_bitmap(property,path):
    if property is None: raise ValueError('Appearance asset lacks the requested texture/bump property.')
    asset=property.GetSingleConnectedAsset()
    if asset is None:
        property.AddConnectedAsset('UnifiedBitmap')
        asset=property.GetSingleConnectedAsset()
    bitmap=asset.FindByName('unifiedbitmap_Bitmap') if asset is not None else None
    if bitmap is None: raise ValueError('The appearance connection is not a supported bitmap asset.')
    bitmap.Value=path


def create_material(doc,app,spec,source=None):
    """Create a new project material; never edit a shared source appearance."""
    for existing in DB.FilteredElementCollector(doc).OfClass(DB.Material):
        if existing.Name.lower()==spec['name'].lower():
            raise ValueError('A material with this name exists. Choose a new name.')
    tx=DB.Transaction(doc,'DECKTOOLS | create decking material')
    tx.Start()
    try:
        material_id=DB.Material.Create(doc,spec['name'])
        material=doc.GetElement(material_id)
        material.Color=DB.Color(*spec['rgb'])
        # Duplication prevents changes from propagating to other materials.
        source_asset=doc.GetElement(source.AppearanceAssetId) if source is not None else None
        appearance=None
        if source_asset is not None:
            appearance=source_asset.Duplicate(spec['name']+' appearance')
        else:
            for asset in app.GetAssets(DB.Visual.AssetType.Appearance):
                if asset.FindByName('generic_diffuse') is not None:
                    appearance=DB.AppearanceAssetElement.Create(doc,spec['name']+' appearance',asset)
                    break
            if appearance is None and (spec['texture'] or spec['bump']):
                raise ValueError('No Generic appearance template is available. Import a Generic '
                                 'material with Revit Material Browser and use it as the source.')
        if appearance is not None:
            material.AppearanceAssetId=appearance.Id
            scope=DB.Visual.AppearanceAssetEditScope(doc)
            try:
                editable=scope.Start(appearance.Id)
                diffuse=editable.FindByName('generic_diffuse')
                if diffuse is None:
                    raise ValueError('This source uses an unsupported appearance schema. '
                                     'Choose a Generic appearance material or edit it in Revit Material Browser.')
                diffuse.SetValueAsColor(DB.Color(*spec['rgb']))
                # Remove inherited color maps when the user wants a solid color.
                if spec['texture']:
                    connect_bitmap(diffuse,spec['texture'])
                elif (source is None or spec.get('clear_maps',False)) and diffuse.NumberOfConnectedProperties:
                    diffuse.RemoveConnectedAsset()
                bump=editable.FindByName('generic_bump_map')
                if spec['bump']:
                    connect_bitmap(bump,spec['bump'])
                    amount=editable.FindByName('generic_bump_amount')
                    if amount is None: raise ValueError('Generic appearance asset lacks bump strength.')
                    amount.Value=spec['bump_amount']
                elif (source is None or spec.get('clear_maps',False)) and bump is not None and bump.NumberOfConnectedProperties:
                    bump.RemoveConnectedAsset()
                scope.Commit(True)
            finally:
                scope.Dispose()
        if tx.Commit()!=DB.TransactionStatus.Committed:
            raise RuntimeError('Revit did not commit the new material.')
        return material
    except Exception:
        if tx.GetStatus()==DB.TransactionStatus.Started: tx.RollBack()
        raise
