# -*- coding: utf-8 -*-
"""
DECKTOOLS | Deck AutoLayout v0.4 (field test) - Revit 2025 / 2027 pyRevit.

Input: one RECTANGULAR, horizontal Floor as the deck footprint. May be rotated.
Output: one native Generic Model DirectShape per actual board cut; native
        Generic Model clip FamilyInstances (or DirectShape proxy fallback),
        tagged Comments/Mark fields, board cut-list, stock-cutting schedule,
        and material summary CSVs.

Boards: Trex-style 5.5 x 0.94 inches, 3/16 side gap, balanced edge rips,
        selected 12/16/20-ft stock, 1/8 butt joints at joist stations.
Clips: CAMO EDGECLIP 3/16 schematic, or an already-loaded point based Generic
        Model clip family; actual joist positions can be selected.

IMPORTANT: schematic clips/grooves, not manufacturer CAD. Estimated joists are
NOT a fastening design; does not cover perimeter starter clips, blocking,
engineering, picture framing, stairs, angle/curved decks, holes or obstacles.
"""
from __future__ import print_function
import os
import sys
import math
import time
import traceback

import clr
from System.Collections.Generic import List
from Autodesk.Revit import DB
from Autodesk.Revit.UI.Selection import ObjectType
from pyrevit import revit, forms, script

HERE = os.path.dirname(__file__)
if HERE not in sys.path: sys.path.insert(0,HERE)
import board_math as bm
import clip_family
import takeoff
# Reuse the exact cross-section math from the standalone board builder.
BOARDS_DIR=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'Boards.panel','TrexBoardBuilder.pushbutton')
if BOARDS_DIR not in sys.path: sys.path.insert(0,BOARDS_DIR)
import board_profile as profile

TITLE='DECKTOOLS | Deck AutoLayout v0.4'
output=script.get_output()
DOC=revit.doc
UIDOC=__revit__.ActiveUIDocument
APP=__revit__.Application


def alert(msg, warning=False):
    forms.alert(msg,title=TITLE,warn_icon=warning)


def confirm(msg):
    return forms.alert(msg,title=TITLE,yes=True,no=True)


def _param(e,bip):
    try: return e.get_Parameter(bip)
    except Exception: return None


def _set_param(e,bip,value):
    p=_param(e,bip)
    try:
        if p is not None and not p.IsReadOnly:
            # Preserve non-ASCII brand/type names under IronPython 2.7.
            p.Set(value if isinstance(value,(str,takeoff.text_type)) else str(value))
    except Exception: pass


def element_id_value(element_id):
    """Use the 64-bit ID API on current Revit, with an older API fallback."""
    try:
        return element_id.Value
    except AttributeError:
        return element_id.IntegerValue


def _key(floor):
    return 'DECKTOOLS|F{0}|'.format(element_id_value(floor.Id))


def _point(u,v,o,s,t,z=0.0):
    return o + u.Multiply(s) + v.Multiply(t) + DB.XYZ.BasisZ.Multiply(z)


def _uv(point,axis_u,axis_v):
    return (point.DotProduct(axis_u),point.DotProduct(axis_v))


def floor_rectangle(floor, long_direction=True):
    """Find top horizontal rectangular planar face, including rotated decks.
    Fail safely for openings/slopes/curves/nonrectangular outlines.
    """
    opt=DB.Options()
    geom=floor.get_Geometry(opt)
    candidates=[]
    for g in geom:
        solids=[]
        if isinstance(g,DB.Solid): solids=[g]
        elif isinstance(g,DB.GeometryInstance):
            solids=[a for a in g.GetInstanceGeometry() if isinstance(a,DB.Solid)]
        for solid in solids:
            if solid is None or solid.Volume < 1.e-9: continue
            for face in solid.Faces:
                if isinstance(face,DB.PlanarFace) and face.FaceNormal.Z>0.99999:
                    candidates.append(face)
    if not candidates:
        raise ValueError('No upward planar face. Choose an ordinary flat rectangular Floor.')
    face=sorted(candidates,key=lambda f:(f.Origin.Z,f.Area),reverse=True)[0]
    loops=list(face.EdgeLoops)
    if len(loops)!=1:
        raise ValueError('Floor has openings/holes or multiple boundary loops. Not supported in v0.3.')
    edges=list(loops[0])
    if len(edges)!=4:
        raise ValueError('Floor must have exactly 4 straight outer edges; found {0}.'.format(len(edges)))
    vertices=[]
    for edge in edges:
        curve=edge.AsCurve()
        if not isinstance(curve,DB.Line):
            raise ValueError('Curved floor edges are not supported in v0.3.')
        for p in [curve.GetEndPoint(0),curve.GetEndPoint(1)]:
            if not any(q.DistanceTo(p)<0.001 for q in vertices): vertices.append(p)
    if len(vertices)!=4:
        raise ValueError('Could not recover four unique rectangle corners.')
    z=vertices[0].Z
    if any(abs(pt.Z-z)>0.001 for pt in vertices):
        raise ValueError('Sloping decks are not yet supported.')
    vectors=sorted([p-vertices[0] for p in vertices[1:]],key=lambda a:a.GetLength())
    a=vectors[0]; b=vectors[1]
    if abs(a.Normalize().DotProduct(b.Normalize()))>0.003:
        raise ValueError('Deck corners are not perpendicular. Use a 90-degree rectangle.')
    if long_direction:
        vec=b if b.GetLength()>=a.GetLength() else a
    else:
        vec=b if b.GetLength()<a.GetLength() else a
    u=DB.XYZ(vec.X,vec.Y,0).Normalize()
    v=DB.XYZ(-u.Y,u.X,0)
    uu=[p.DotProduct(u) for p in vertices]
    vv=[p.DotProduct(v) for p in vertices]
    lo_u,hi_u=min(uu),max(uu)
    lo_v,hi_v=min(vv),max(vv)
    run=hi_u-lo_u
    width=hi_v-lo_v
    if abs(face.Area-run*width)>max(0.01,face.Area*0.005):
        raise ValueError('Floor top is not a true four-corner rectangle.')
    origin=DB.XYZ(u.X*lo_u+v.X*lo_v,u.Y*lo_u+v.Y*lo_v,z)
    return {'origin':origin,'u':u,'v':v,'length':run,'width':width,'z':z}


def pick_floor():
    selected=[]
    for elid in UIDOC.Selection.GetElementIds():
        element=DOC.GetElement(elid)
        if isinstance(element,DB.Floor): selected.append(element)
    if len(selected)==1: return selected[0]
    try:
        ref=UIDOC.Selection.PickObject(ObjectType.Element,'Pick one rectangular Floor representing the deck footprint')
    except Exception:
        return None
    element=DOC.GetElement(ref.ElementId)
    if not isinstance(element,DB.Floor):
        raise ValueError('Selected element is not a Revit Floor.')
    return element


def actual_joists(coord):
    try:
        refs=UIDOC.Selection.PickObjects(ObjectType.Element,
                                        'Select structural-framing joists crossing the boards, then click Finish')
    except Exception:
        return None
    segments=[]
    for r in refs:
        e=DOC.GetElement(r.ElementId)
        location=e.Location
        if location is None or not isinstance(location,DB.LocationCurve): continue
        c=location.Curve
        if not isinstance(c,DB.Line): continue
        p1,p2=c.GetEndPoint(0),c.GetEndPoint(1)
        rel1=p1-coord['origin']; rel2=p2-coord['origin']
        s1=rel1.DotProduct(coord['u']); s2=rel2.DotProduct(coord['u'])
        t1=rel1.DotProduct(coord['v']); t2=rel2.DotProduct(coord['v'])
        # Only crossing or nearly perpendicular joists; reject beams along deck boards.
        if abs(t2-t1) < 0.5 or abs(t2-t1) < 2.0*abs(s2-s1): continue
        segments.append((s1,t1,s2,t2))
    if not segments:
        raise ValueError('No selected line-based joists run across the board direction.')
    return segments


def stations_for_joints(segments,coord):
    return bm.full_width_stations(segments,coord['length'],coord['width'])


def clip_points(plan,coord,segments,stations):
    """Return unique (s,t) positions. If actual joists given, use finite crossings."""
    pts=[]
    seen=set()
    for seam in plan['seams']:
        if segments is None:
            xs=stations
        else:
            xs=[]
            for s1,t1,s2,t2 in segments:
                if min(t1,t2)-0.005 <= seam <= max(t1,t2)+0.005:
                    frac=(seam-t1)/(t2-t1)
                    at=s1+(s2-s1)*frac
                    if 0.0 <= at <= coord['length']: xs.append(at)
        for s in xs:
            if 0.0<=s<=coord['length']:
                k=(int(round(s*1000.0)),int(round(seam*1000.0)))
                if k not in seen:
                    seen.add(k)
                    pts.append((s,seam))
    return pts


def curve_loop(points):
    loop=DB.CurveLoop()
    for i in range(len(points)):
        loop.Append(DB.Line.CreateBound(points[i],points[(i+1)%len(points)]))
    ls=List[DB.CurveLoop]()
    ls.Add(loop)
    return ls


def extrusion(pts,direction,dist,material_id=None):
    if material_id is None or material_id==DB.ElementId.InvalidElementId:
        return DB.GeometryCreationUtilities.CreateExtrusionGeometry(curve_loop(pts),direction,dist)
    try:
        so=DB.SolidOptions(material_id,DB.ElementId.InvalidElementId)
        return DB.GeometryCreationUtilities.CreateExtrusionGeometry(curve_loop(pts),direction,dist,so)
    except Exception:
        return DB.GeometryCreationUtilities.CreateExtrusionGeometry(curve_loop(pts),direction,dist)


def board_solid(b,coord,material_id):
    pts=profile.make_outline(float(b['width_in']),b['edge_mode'])
    row_center=(b['low']+b['high'])/2.0
    outline=[_point(coord['u'],coord['v'],coord['origin'],b['start'],
                    row_center+(y/12.0),z/12.0) for y,z in pts]
    return extrusion(outline,coord['u'],b['length_ft'],material_id)


def colored_material(name,RGB):
    mats=DB.FilteredElementCollector(DOC).OfClass(DB.Material)
    for m in mats:
        if m.Name==name: return m.Id
    mid=DB.Material.Create(DOC,name)
    mat=DOC.GetElement(mid)
    mat.Color=DB.Color(*RGB)
    return mid


def create_shape(solids,name,mark,comments):
    ds=DB.DirectShape.CreateElement(DOC,DB.ElementId(DB.BuiltInCategory.OST_GenericModel))
    ds.ApplicationId='DECKTOOLS-v0.3'
    ds.ApplicationDataId=mark
    try: ds.Name=name
    except Exception: pass  # DirectShape Name setter differs by Revit API version
    arr=List[DB.GeometryObject]()
    for s in solids: arr.Add(s)
    ds.SetShape(arr)
    _set_param(ds,DB.BuiltInParameter.ALL_MODEL_MARK,mark)
    _set_param(ds,DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS,comments)
    return ds


def clip_proxy_solid(s,t,coord,black_id,silver_id):
    """Native schematic clip proxy; gap 3/16, rest approximate. 3D solids."""
    def face_xy(xy,z):
        return [_point(coord['u'],coord['v'],coord['origin'],
                       s+x/12.0,t+y/12.0,z/12.0) for x,y in xy]
    def rect(xhalf,yhalf):
        return [(-xhalf,-yhalf),(xhalf,-yhalf),(xhalf,yhalf),(-xhalf,yhalf)]
    def octagon(radius):
        return [(radius*math.cos(i*math.pi/4.0),radius*math.sin(i*math.pi/4.0)) for i in range(8)]
    return [
        extrusion(face_xy(rect(0.34,0.09375),0.35),DB.XYZ.BasisZ,0.205/12.0,black_id),
        extrusion(face_xy(rect(0.27,0.36),0.425),DB.XYZ.BasisZ,0.037/12.0,silver_id),
        extrusion(face_xy(octagon(0.061),-1.20),DB.XYZ.BasisZ,1.75/12.0,silver_id),
        extrusion(face_xy(octagon(0.10),0.55),DB.XYZ.BasisZ,0.05/12.0,silver_id),
    ]


def existing_symbols():
    """Offer every compatible point-based Generic Model, regardless of brand/name."""
    items=[]
    for f in DB.FilteredElementCollector(DOC).OfClass(DB.FamilySymbol):
        try:
            category=f.Category
            if category is None or element_id_value(category.Id)!=int(DB.BuiltInCategory.OST_GenericModel): continue
            if f.Family.FamilyPlacementType!=DB.FamilyPlacementType.OneLevelBased: continue
            try:
                type_name=f.Name
            except AttributeError:
                type_name=DB.Element.Name.GetValue(f)
            name=f.Family.Name + ' : ' + type_name
            items.append((name,f))
        except Exception: continue
    return sorted(items,key=lambda item:item[0].lower())


def symbol_label(symbol):
    try:
        type_name=symbol.Name
    except AttributeError:
        type_name=DB.Element.Name.GetValue(symbol)
    return symbol.Family.Name + ' : ' + type_name


def choose_clip_type(items):
    """Searchable list avoids a button for every Generic Model type in a project."""
    choice=forms.SelectFromList.show([name for name,s in items],
        title='Choose clip family / type (3/16-inch gap)',
        multiselect=False,button_name='Use clip type')
    if not choice: return None
    selected=next((s for name,s in items if name==choice),None)
    if selected is None:
        raise ValueError('The chosen family type was not found.')
    return selected


def load_clip_family():
    """Load a new RFA and choose its type; roll back incompatible/cancelled loads.

    No family overwrite options are supplied. Already loaded families should be
    chosen from the loaded-family list instead of replacing their definitions.
    """
    filepath=forms.pick_file(file_ext='rfa',
        files_filter='Revit Families (*.rfa)|*.rfa',
        title='Choose a clip family (point-based Generic Model, any brand)')
    if not filepath: return None
    if not os.path.isfile(filepath) or not filepath.lower().endswith('.rfa'):
        raise ValueError('Choose an existing Revit family (.rfa) file.')
    before=set(element_id_value(s.Id) for _,s in existing_symbols())
    tr=DB.Transaction(DOC,'DECKTOOLS | load selected clip family')
    tr.Start()
    try:
        result=DOC.LoadFamily(filepath)
        # The out-family overload can return a tuple under Python/.NET bindings.
        success=result[0] if isinstance(result,tuple) else result
        if not success:
            raise ValueError('Revit did not load this family. If it is already loaded, '
                             'choose it from the loaded clip list; existing definitions are preserved.')
        items=[(name,s) for name,s in existing_symbols()
               if element_id_value(s.Id) not in before]
        if not items:
            raise ValueError('This family has no supported clip types. Use an unhosted, '
                             'point-based Generic Model family; hosted, face-based, '
                             'work-plane-based, line-based, and adaptive families are unsupported.')
        selected=choose_clip_type(items)
        if selected is None:
            tr.RollBack()
            return None
        status=tr.Commit()
        if status!=DB.TransactionStatus.Committed:
            raise RuntimeError('Revit did not commit the clip family load (status: {0}).'.format(status))
        return selected
    except Exception:
        if tr.GetStatus()==DB.TransactionStatus.Started: tr.RollBack()
        raise


def get_template():
    base=APP.FamilyTemplatePath or ''
    choices=[base]
    for year in [str(APP.VersionNumber),'2025','2027']:
        root=os.path.join(os.environ.get('PROGRAMDATA','C:\\ProgramData'),
                          'Autodesk','RVT '+year,'Family Templates')
        for lang in ['English_I','English','US Imperial','English_M']:
            choices.append(os.path.join(root,lang))
    for loc in choices:
        if not os.path.isdir(loc): continue
        for rt in [loc]+[os.path.join(loc,d) for d in os.listdir(loc)
                         if os.path.isdir(os.path.join(loc,d))]:
            for title in ['Generic Model.rft','Metric Generic Model.rft']:
                path=os.path.join(rt,title)
                if os.path.isfile(path): return path
    return None


def find_or_generate_schematic_family():
    """Use existing schematic RFA if available; otherwise make one natively."""
    for _,sym in existing_symbols():
        if sym.Family.Name==clip_family.FAMILY_NAME: return sym
    template=get_template()
    if not template:
        print('Clip RFA: no family template found; using native DirectShape proxies.')
        return None
    folder=os.path.join(os.environ.get('USERPROFILE',os.path.expanduser('~')),
                        'Documents','DECKTOOLS_Families')
    if not os.path.isdir(folder): os.makedirs(folder)
    filepath=os.path.join(folder,clip_family.FAMILY_NAME+'.rfa')
    try:
        if not os.path.isfile(filepath):
            clip_family.generate(APP,template,filepath)
        tr=DB.Transaction(DOC,'Load schematic CAMO clip family')
        tr.Start()
        try:
            DOC.LoadFamily(filepath)
            tr.Commit()
        except Exception:
            if tr.GetStatus()==DB.TransactionStatus.Started: tr.RollBack()
            raise
        for _,sym in existing_symbols():
            if sym.Family.Name==clip_family.FAMILY_NAME: return sym
        print('Generated clip RFA but could not find its type. Using proxy solids.')
    except Exception as exc:
        print('Clip RFA generation/loading warning: {0}. Using native DirectShape clip proxies.'.format(exc))
    return None


def old_elements(floor):
    prefix=_key(floor)
    out=[]
    for e in DB.FilteredElementCollector(DOC).OfCategory(DB.BuiltInCategory.OST_GenericModel).WhereElementIsNotElementType():
        p=_param(e,DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p is not None and p.AsString() and p.AsString().startswith(prefix):
            out.append(e)
            continue
        # DirectShape element identity is a second, stable regeneration marker.
        if isinstance(e,DB.DirectShape):
            try:
                if e.ApplicationId=='DECKTOOLS-v0.3' and e.ApplicationDataId.startswith('DT-'):
                    if ('-F{0}-'.format(element_id_value(floor.Id))) in e.ApplicationDataId:
                        out.append(e)
            except Exception: pass
    return out


def place(plan,coord,floor,clips,chosen_symbol,old):
    boards=plan['boards']
    if len(boards)>1200 or len(clips)>4000:
        raise ValueError('Limit: 1,200 board cuts or 4,000 clips per test layout. Split the deck.')
    pref=_key(floor)
    created_board=[]; created_clip=[]
    tr=DB.Transaction(DOC,'DECKTOOLS | regenerate deck and clips')
    tr.Start()
    try:
        for e in old: DOC.Delete(e.Id)
        board_id=colored_material('DT Trex-Style Composite (approx)',(128,95,73))
        black_id=colored_material('DT CAMO-style Nylon Proxy',(38,39,40))
        silver_id=colored_material('DT CAMO-style Stainless Proxy',(159,168,174))
        if chosen_symbol is not None and not chosen_symbol.IsActive:
            chosen_symbol.Activate()
            DOC.Regenerate()
        angle=math.atan2(coord['u'].Y,coord['u'].X)
        clip_description=(symbol_label(chosen_symbol) if chosen_symbol is not None
                          else 'Generic CAMO-style schematic placeholder')
        for b in boards:
            mark=takeoff.board_mark(element_id_value(floor.Id),b)
            meta=pref+'BOARD|L={0:.4f}ft|W={1:.4f}in|PROFILE={2}'.format(
                b['length_ft'],b['width_in'],b['edge_mode'])
            model=create_shape([board_solid(b,coord,board_id)],
                'DT Trex-Style Board',mark,meta)
            created_board.append(model)
        for i,(s,t) in enumerate(clips):
            mark='DT-C-F{0}-{1:05d}'.format(element_id_value(floor.Id),i+1)
            meta=pref+'CLIP|FAMILY_TYPE={0}|GAP=0.1875in'.format(clip_description)
            if chosen_symbol is not None:
                position=_point(coord['u'],coord['v'],coord['origin'],s,t)
                clip=DOC.Create.NewFamilyInstance(position,chosen_symbol,
                                                  DB.Structure.StructuralType.NonStructural)
                if abs(angle)>1.e-7:
                    DB.ElementTransformUtils.RotateElement(DOC,clip.Id,
                        DB.Line.CreateBound(position,position+DB.XYZ.BasisZ),angle)
                _set_param(clip,DB.BuiltInParameter.ALL_MODEL_MARK,mark)
                _set_param(clip,DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS,meta)
            else:
                solids=clip_proxy_solid(s,t,coord,black_id,silver_id)
                clip=create_shape(solids,'DT CAMO EDGECLIP Schematic Proxy',mark,meta)
            created_clip.append(clip)
        status=tr.Commit()
        if status!=DB.TransactionStatus.Committed:
            raise RuntimeError('Revit did not commit the deck layout (status: {0}).'.format(status))
    except Exception:
        if tr.GetStatus()==DB.TransactionStatus.Started: tr.RollBack()
        raise
    return (created_board,created_clip)


def exports(floor,plan,clips,coord,mode,symbol,estimate):
    folder=os.path.join(os.environ.get('USERPROFILE',os.path.expanduser('~')),
                        'Documents','DECKTOOLS_Exports')
    date=time.strftime('%Y%m%d_%H%M%S')
    prefix='Deck_F{0}_{1}'.format(element_id_value(floor.Id),date)
    rows=takeoff.export_rows(element_id_value(floor.Id),plan,estimate,
                            coord['length'],coord['width'],len(clips),mode,
                            symbol or 'schematic built-in proxy')
    return takeoff.write_exports(folder,prefix,rows)


def main():
    if DOC is None or DOC.IsFamilyDocument:
        alert('Open a Revit project (not a family editor), then run the tool.',True); return
    if int(APP.VersionNumber)<2025:
        alert('Supports Revit 2025 and newer.',True); return
    floor=pick_floor()
    if floor is None: return
    orient=forms.CommandSwitchWindow.show(
        ['Along LONG edge of deck (default)','Along SHORT edge of deck'],
        message='How should the decking boards run?')
    if not orient: return
    along_long=orient.startswith('Along LONG')
    coord=floor_rectangle(floor,along_long)

    stock_choice=forms.CommandSwitchWindow.show(
        ['20-foot stock (original default)','16-foot stock','12-foot stock'],
        message='Which stock board length will you purchase?')
    if not stock_choice: return
    stock_length=float(stock_choice.split('-')[0])
    spare_answer=forms.ask_for_string(default='10',title=TITLE,
        prompt='Extra spare boards (% from 0 to 100; rounded up per width/profile group):')
    if spare_answer is None: return
    spare_percent=bm.finite_number(spare_answer,'Spare-board allowance')
    kerf_answer=forms.ask_for_string(default='0.125',title=TITLE,
        prompt='Crosscut saw kerf in INCHES (0 to 1; 0.125 = 1/8 inch):')
    if kerf_answer is None: return
    kerf_in=bm.finite_number(kerf_answer,'Saw kerf')
    # Validate settings before asking for joist selection or changing the model.
    bm.pack_stock([],stock_length,kerf_in,spare_percent)

    joist_choice=forms.CommandSwitchWindow.show(
        ['Use nominal joists at 16in O.C. (test estimate)',
         'Select actual modeled joists (line-based framing)'],
        message='Clip positions: where are the joists?')
    if not joist_choice: return
    segments=None; nominal=None
    if joist_choice.startswith('Use nominal'):
        answer=forms.ask_for_string(default='16',title=TITLE,
                prompt='Assumed joist spacing in INCHES. Clip placement is estimated:')
        if answer is None: return
        try: nominal=float(answer)
        except Exception: raise ValueError('Enter numeric joist spacing such as 16.')
        stations=bm.estimated_stations(coord['length'],nominal)
        joist_label='Assumed {0:g}in O.C.'.format(nominal)
    else:
        segments=actual_joists(coord)
        if segments is None: return
        stations=stations_for_joints(segments,coord)
        joist_label='Selected actual joists (total {0})'.format(len(segments))
        if not stations and coord['length']>stock_length:
            raise ValueError('No selected perpendicular joist spans the full deck width. '
                             'A common butt-joint seam needs full-width support; add/select framing or revise direction.')
    plan=bm.plan(coord['length'],coord['width'],stations,stock_length)
    clips=clip_points(plan,coord,segments,stations)
    estimate=takeoff.build_takeoff(plan,kerf_in,spare_percent)
    if len(plan['boards'])>1200 or len(clips)>4000:
        raise ValueError('Large deck: exceeds first-test safety limit of 1,200 boards or 4,000 clips.')

    existing=existing_symbols()
    opts=['Auto-create generic clip placeholder (CAMO-style schematic)']
    if existing:
        opts.append('Choose a loaded clip family/type')
    opts.append('Load a different clip family (.rfa)')
    opts.append('Use generic placeholder solids (no family)')
    use=forms.CommandSwitchWindow.show(opts,message='Choose clip geometry for the 3/16-inch board gap (any brand)')
    if not use: return
    sym=None
    if use=='Choose a loaded clip family/type':
        sym=choose_clip_type(existing)
        if sym is None: return
    elif use=='Load a different clip family (.rfa)':
        sym=load_clip_family()
        if sym is None: return
    want_auto=use.startswith('Auto-create')
    clip_label=(symbol_label(sym) if sym is not None else
                'Generic CAMO-style schematic family' if want_auto else
                'Generic schematic placeholder solids')
    old=old_elements(floor)
    detail=('Floor ID: {0}\nDeck run: {1:.2f} ft | width: {2:.2f} ft\n'
            'Board rows: {3} | installed pieces: {4}\n'
            'Perimeter rips: {5:.3f} in each\n'
            'Clip positions (3/16-in gap): {6} | joists: {7}\n'
            'Clip family/type: {17}\n'
            '{10:g}ft stock: {8} base + {11} spare = {12} boards to purchase\n'
            'Spare allowance: {13:g}% | crosscut kerf: {14:g} in\n'
            'Remaining offcuts: {15:.2f} ft | crosscut kerf loss: {16:.2f} ft\n'
            'Previously generated elements to replace: {9}\n\n'
            'Board grooves and built-in placeholder clips are SCHEMATIC.\n'
            'No starter clips, edge fastening, blocking, picture frames, stair or code detailing.\n\n'
            'Generate model elements and takeoff CSV files?').format(
            element_id_value(floor.Id),coord['length'],coord['width'],len(plan['rows']),
            len(plan['boards']), (plan['rows'][0][1]-plan['rows'][0][0])*12.0,
            len(clips),joist_label,estimate['base_stock'],len(old),stock_length,
            estimate['reserve_stock'],estimate['purchase_stock'],spare_percent,
            kerf_in,estimate['unused_ft'],estimate['kerf_ft'],clip_label)
    if not confirm(detail): return
    if want_auto:
        sym=find_or_generate_schematic_family()
    created=place(plan,coord,floor,clips,sym,old)
    output.print_md('## DECKTOOLS v0.4 — Layout completed')
    print('Floor {0}: {1} boards, {2} clip elements'.format(
          element_id_value(floor.Id),len(created[0]),len(created[1])))
    try:
        paths=exports(floor,plan,clips,coord,joist_label,
             symbol_label(sym) if sym is not None else None,estimate)
        print('Cut list: '+paths['Cutlist.csv'])
        print('Stock cutting schedule: '+paths['StockCuts.csv'])
        print('Materials takeoff: '+paths['Materials.csv'])
        report='CSV folder: '+os.path.dirname(paths['Cutlist.csv'])
    except Exception as exp:
        print('CSV WARNING: model created, but CSV export failed: {0}'.format(exp))
        report='CSV export failed; see pyRevit output panel.'
    alert('Deck created successfully.\n\n{0} individual board cuts\n{1} clip elements\n'
          '{2} estimated {4:g}ft boards to purchase ({5} base + {6} spare)\n\n{3}\n\n'
          'Board grooves and built-in clips are schematic; verify selected clip compatibility.'.format(
              len(created[0]),len(created[1]),estimate['purchase_stock'],report,
              stock_length,estimate['base_stock'],estimate['reserve_stock']))


if __name__=='__main__':
    try: main()
    except Exception as error:
        print(traceback.format_exc())
        alert('Deck AutoLayout failed. Revit transaction was rolled back if modeling started.\n'
              'See the pyRevit output panel.\n\n{0}'.format(error),True)
