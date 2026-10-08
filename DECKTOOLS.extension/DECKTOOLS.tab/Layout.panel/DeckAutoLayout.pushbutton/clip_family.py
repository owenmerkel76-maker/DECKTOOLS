# -*- coding: utf-8 -*-
"""Schematic CAMO-style 3/16-in clip native Revit Generic Model family.
Not a CAMO engineering CAD model. Origin = gap center at BOARD UNDERSIDE.
X across joist, Y across deck-board gap, Z vertical.
"""
import os
import math
from Autodesk.Revit import DB

FAMILY_NAME = 'DT_CAMO_EDGECLIP_3-16_SCHEMATIC'


def _prism(doc, points_xy_in, z0_in, height_in):
    profile = DB.CurveArray()
    for i in range(len(points_xy_in)):
        ax, ay = points_xy_in[i]
        bx, by = points_xy_in[(i+1) % len(points_xy_in)]
        profile.Append(DB.Line.CreateBound(
            DB.XYZ(ax/12.0,ay/12.0,z0_in/12.0),
            DB.XYZ(bx/12.0,by/12.0,z0_in/12.0)))
    curves = DB.CurveArrArray()
    curves.Append(profile)
    plane = DB.Plane.CreateByNormalAndOrigin(DB.XYZ.BasisZ, DB.XYZ(0,0,z0_in/12.0))
    sp = DB.SketchPlane.Create(doc,plane)
    return doc.FamilyCreate.NewExtrusion(True,curves,sp,height_in/12.0)


def _rect(half_x,half_y):
    return [(-half_x,-half_y),(half_x,-half_y),(half_x,half_y),(-half_x,half_y)]


def _octagon(radius):
    return [(radius*math.cos(i*2.0*math.pi/8.0), radius*math.sin(i*2.0*math.pi/8.0)) for i in range(8)]


def generate(app, template, filepath):
    fdoc = None
    try:
        fdoc = app.NewFamilyDocument(template)
        if fdoc is None or not fdoc.IsFamilyDocument:
            raise RuntimeError('Could not open Generic Model family template.')
        tr = DB.Transaction(fdoc,'Create schematic CAMO EDGECLIP solids')
        tr.Start()
        try:
            fm = fdoc.FamilyManager
            try:
                ft = fm.NewType('3-16in Gap - Schematic')
                fm.CurrentType = ft
            except Exception:
                pass
            # Confirmed gap is 3/16 inch. All other plastic/wing sizes below are approximate.
            # Nylon spacer; 0.1875 wide through the board gap.
            plastic = _prism(fdoc,_rect(0.34,0.09375),0.35,0.205)
            # Stainless wings slide into the opposed grooves (rough visual envelope).
            wings = _prism(fdoc,_rect(0.27,0.36),0.425,0.037)
            # Approximate single screw, 1-3/4 inch total shank projection.
            screw = _prism(fdoc,_octagon(0.061),-1.20,1.75)
            head = _prism(fdoc,_octagon(0.10),0.55,0.05)
            # Slight legs/feet gripping top of joist, schematic only.
            foot1 = _prism(fdoc,[(-0.31,-0.18),(-0.23,-0.18),(-0.23,-0.12),(-0.31,-0.12)],0.13,0.26)
            foot2 = _prism(fdoc,[(-0.31,0.12),(-0.23,0.12),(-0.23,0.18),(-0.31,0.18)],0.13,0.26)
            try:
                black_id = DB.Material.Create(fdoc,'DT_Clip_Nylon_Black')
                silver_id = DB.Material.Create(fdoc,'DT_Clip_Stainless')
                blk=fdoc.GetElement(black_id); blk.Color=DB.Color(32,35,41)
                slv=fdoc.GetElement(silver_id); slv.Color=DB.Color(164,172,177)
                for ext, mid in [(plastic,black_id),(foot1,black_id),(foot2,black_id),
                                 (wings,silver_id),(screw,silver_id),(head,silver_id)]:
                    pm=ext.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)
                    if pm is not None and not pm.IsReadOnly: pm.Set(mid)
            except Exception:
                pass
            fdoc.Regenerate()
            tr.Commit()
        except Exception:
            if tr.GetStatus()==DB.TransactionStatus.Started: tr.RollBack()
            raise
        opts=DB.SaveAsOptions(); opts.OverwriteExistingFile=False
        fdoc.SaveAs(filepath,opts)
        return filepath
    finally:
        if fdoc is not None:
            try: fdoc.Close(False)
            except Exception: pass
