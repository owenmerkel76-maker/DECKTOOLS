# -*- coding: utf-8 -*-
"""
Trex-style INDIVIDUAL BOARD native RFA generator - DECKTOOLS v0.2.
The button runs INSIDE Revit via pyRevit (IronPython compatible).
Native family geometry: Revit FamilyCreate.NewExtrusion (not imported CAD).
Board_Length is associated with the actual extrusion's end parameter.
Ripped width is chosen at GENERATION TIME (new separate family per width).
Do NOT edit Width_As_Built metadata expecting it to reshape geometry.
"""
from __future__ import print_function
import os
import sys
import re
import traceback

import clr
from pyrevit import DB, forms, revit, script
from Autodesk.Revit.DB import (XYZ, Line, Plane, SketchPlane, CurveArray,
                               CurveArrArray, Transaction, SaveAsOptions,
                               BuiltInParameter, GroupTypeId, SpecTypeId)

SCRIPT_DIR = os.path.dirname(__file__)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import board_profile as bp

TITLE = 'DECKTOOLS | Trex Board Builder v0.2'
OUT = script.get_output()


def inform(message):
    forms.alert(message, title=TITLE, warn_icon=False)


def fail(message):
    forms.alert(message, title=TITLE, warn_icon=True)


def read_in(text):
    """Read values in inches: 5.5, 5 1/2, 5-1/2, or 11/2."""
    s = str(text).strip().replace('"', '').replace('in', '').strip()
    s = s.replace('-', ' ')
    pieces = s.split()
    if not pieces:
        raise ValueError('Enter a width in inches.')
    if len(pieces) > 2:
        raise ValueError('Use a decimal or a mixed fraction, e.g. 4 1/4.')
    def parse_one(v):
        if '/' not in v:
            return float(v)
        num, den = v.split('/')
        return float(num) / float(den)
    if len(pieces) == 2:
        return parse_one(pieces[0]) + parse_one(pieces[1])
    return parse_one(pieces[0])


def get_template(app):
    path = ''
    try:
        path = app.FamilyTemplatePath or ''
    except Exception:
        pass
    bases = [path]
    try:
        year = app.VersionNumber
    except Exception:
        year = '2025'
    program_data = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
    for root in ('RVT ' + year, 'RVT ' + year + ' Release'):
        for name in ('English_I', 'English', 'US Imperial', 'English_M'):
            bases.append(os.path.join(program_data, 'Autodesk', root,
                                      'Family Templates', name))
    names = ('Generic Model.rft', 'Metric Generic Model.rft',
             'Generic Model - Line Based.rft')
    for base in bases:
        if not base:
            continue
        for name in names[:2]:
            candidate = os.path.join(base, name)
            if os.path.isfile(candidate):
                return candidate
        # Some installs place template in a subfolder of FamilyTemplatePath
        if os.path.isdir(base):
            try:
                for entry in os.listdir(base):
                    inner = os.path.join(base, entry)
                    if os.path.isdir(inner):
                        for name in names[:2]:
                            candidate = os.path.join(inner, name)
                            if os.path.isfile(candidate):
                                return candidate
            except Exception:
                pass
    return forms.pick_file(file_ext='rft',
                           files_filter='Revit Family Templates (*.rft)|*.rft',
                           title='Select a Generic Model.rft template')


def family_param(fm, name, group, spec, instance, value):
    p = fm.AddParameter(name, group, spec, instance)
    fm.Set(p, value)
    return p


def native_outline(doc, width_inches, mode, initial_length_feet):
    outline = bp.make_outline(width_inches, mode)
    profile = CurveArray()
    for i in range(len(outline)):
        y1, z1 = outline[i]
        y2, z2 = outline[(i + 1) % len(outline)]
        start = XYZ(0, y1 / 12.0, z1 / 12.0)
        end = XYZ(0, y2 / 12.0, z2 / 12.0)
        profile.Append(Line.CreateBound(start, end))
    profiles = CurveArrArray()
    profiles.Append(profile)
    sp = SketchPlane.Create(doc, Plane.CreateByNormalAndOrigin(XYZ.BasisX, XYZ.Zero))
    ext = doc.FamilyCreate.NewExtrusion(True, profiles, sp, initial_length_feet)
    if ext is None:
        raise RuntimeError('Revit failed to create the solid board extrusion.')
    return ext


def build_family(app, template, outpath, width_in, length_ft, mode):
    family_doc = None
    step = 'Create native family document'
    try:
        family_doc = app.NewFamilyDocument(template)
        if family_doc is None or not family_doc.IsFamilyDocument:
            raise RuntimeError('Could not create a native Revit family document.')
        step = 'Start family editing transaction'
        tx = Transaction(family_doc, 'Create native Trex-style board')
        tx.Start()
        try:
            step = 'Create family type'
            fm = family_doc.FamilyManager
            type_name = '{0:0.3f}in {1} {2:g}ft'.format(width_in, mode, length_ft)
            famtype = fm.NewType(type_name)
            fm.CurrentType = famtype

            # Native extrusion with actual grooved side profile.
            step = 'Create native board solid'
            ext = native_outline(family_doc, width_in, mode, length_ft)
            family_doc.Regenerate()

            # Revit 2025+: GroupTypeId.Geometry (Dimensions is NOT a valid API member).
            # The extrusion END is directly driven by the instance parameter.
            step = 'Add Board_Length family parameter'
            board_len = fm.AddParameter('Board_Length', GroupTypeId.Geometry,
                                        SpecTypeId.Length, True)
            step = 'Connect Board_Length to extrusion end'
            ext_end = ext.get_Parameter(BuiltInParameter.EXTRUSION_END_PARAM)
            if ext_end is None:
                raise RuntimeError('Extrusion End parameter unavailable.')
            # Signature accepts ONE element Parameter only, not the family param.
            if not fm.CanElementParameterBeAssociated(ext_end):
                raise RuntimeError('Revit cannot associate Board_Length to extrusion end.')
            fm.AssociateElementParameterToFamilyParameter(ext_end, board_len)
            fm.Set(board_len, float(length_ft))

            # Scheduling / descriptive parameters; WIDTH DOES NOT FLEX GEOMETRY.
            # Generate another family from this button to obtain a different rip.
            step = 'Create scheduling parameters'
            family_param(fm, 'Width_As_Built', GroupTypeId.Geometry,
                         SpecTypeId.Length, False, width_in / 12.0)
            family_param(fm, 'Thickness_As_Built', GroupTypeId.Geometry,
                         SpecTypeId.Length, False, bp.THICKNESS_IN / 12.0)
            family_param(fm, 'Recommended_Board_Gap', GroupTypeId.Geometry,
                         SpecTypeId.Length, False, bp.GAP_IN / 12.0)
            family_param(fm, 'Max_Stock_Length', GroupTypeId.Geometry,
                         SpecTypeId.Length, False, bp.MAX_STOCK_FT)
            family_param(fm, 'Section_Area', GroupTypeId.Geometry,
                         SpecTypeId.Area, False,
                         bp.section_area_in2(bp.make_outline(width_in, mode)) / 144.0)
            family_param(fm, 'Edge_Profile', GroupTypeId.IdentityData,
                         SpecTypeId.String.Text, False, mode)
            family_param(fm, 'Geometry_Accuracy', GroupTypeId.IdentityData,
                         SpecTypeId.String.Text, False,
                         'Overall Trex dimensions; groove approximate')
            family_param(fm, 'Width_Control', GroupTypeId.IdentityData,
                         SpecTypeId.String.Text, False,
                         'Width fixed by created profile; use builder for rip')

            # Give the board a distinct appearance in 3D, not a linked CAD object.
            try:
                material_id = DB.Material.Create(family_doc, 'Composite Decking - Trex Style')
                material = family_doc.GetElement(material_id)
                material.Color = DB.Color(135, 103, 77)
                material.Shininess = 18
                pm = ext.get_Parameter(BuiltInParameter.MATERIAL_ID_PARAM)
                if pm is not None and not pm.IsReadOnly:
                    pm.Set(material_id)
            except Exception as appearance_exc:
                print('Noncritical material appearance warning: {0}'.format(appearance_exc))

            step = 'Regenerate and validate board geometry'
            family_doc.Regenerate()
            if abs(ext.EndOffset - float(length_ft)) > 1e-5:
                raise RuntimeError('Geometry length does not match the requested cut length.')
            tx.Commit()
        except Exception:
            if tx.GetStatus() == DB.TransactionStatus.Started:
                tx.RollBack()
            raise

        step = 'Save generated RFA'
        opts = SaveAsOptions()
        opts.OverwriteExistingFile = False
        family_doc.SaveAs(outpath, opts)
        return outpath
    except Exception as exc:
        raise RuntimeError('{0}: {1}'.format(step, exc))
    finally:
        if family_doc is not None:
            try:
                family_doc.Close(False)
            except Exception:
                pass


def main():
    app = __revit__.Application
    version = int(app.VersionNumber)
    if version < 2025:
        fail('Designed for Revit 2025 and Revit 2027.')
        return

    mode_titles = [
        'Grooved BOTH sides - standard stock board',
        'Rip RIGHT side - factory groove kept on LEFT',
        'Rip LEFT side - factory groove kept on RIGHT',
        'Square edges - no clip grooves',
    ]
    choice = forms.CommandSwitchWindow.show(mode_titles,
                                             message='Choose actual manufactured edge profile')
    if not choice:
        return
    modes = dict(zip(mode_titles, ('both', 'left', 'right', 'square')))
    mode = modes[choice]

    width_s = forms.ask_for_string(default='5.5',
                      prompt='Actual board width in inches (5.5 stock; smaller for ripped boards):',
                      title=TITLE)
    if width_s is None:
        return
    length_s = forms.ask_for_string(default='20',
                      prompt='Initial cut length in FEET (0.5 through 20). '
                             'The placed board length can be changed by Board_Length:',
                      title=TITLE)
    if length_s is None:
        return
    try:
        width_in = read_in(width_s)
        length_ft = bp.validate_length_ft(float(str(length_s).replace("'", '').strip()))
        bp.make_outline(width_in, mode)
        if width_in < 5.5 and mode == 'both':
            if not forms.alert('A ripped board usually loses one factory groove. '
                         'Generate both grooves anyway?', yes=True, no=True,
                         title=TITLE):
                return
    except Exception as err:
        fail('Invalid board dimensions: {0}'.format(err))
        return

    template = get_template(app)
    if not template:
        fail('Please select an installed Generic Model.rft template.')
        return

    nominal = '{0:0.3f}'.format(width_in).replace('.', 'p')
    default_name = 'DECKTOOLS_TrexStyle_{0}in_{1}_{2:g}ft.rfa'.format(nominal, mode, length_ft)
    filepath = forms.save_file(file_ext='rfa', default_name=default_name,
                               title='Save native Revit board family (.rfa)')
    if not filepath:
        return
    filepath = os.path.abspath(filepath)
    if not filepath.lower().endswith('.rfa'):
        filepath += '.rfa'
    if os.path.exists(filepath):
        fail('File already exists. Choose a different filename to avoid overwriting.')
        return

    try:
        build_family(app, template, filepath, width_in, length_ft, mode)
    except Exception as err:
        print(traceback.format_exc())
        fail('Could not create board RFA. See the pyRevit output panel for details.\n\n{0}'.format(err))
        return

    # Optional load: keep creation and existing project modifications separate.
    msg = ('Native RFA saved:\n{0}\n\n{1:g}" wide x {2:g} ft long x 0.94" thick\n'
           'Edge profile: {3}\n\nBoard_Length flexes geometry. '
           'Width_As_Built is scheduling metadata; rerun builder for another rip width.\n\n'
           'Load family into active project now?').format(filepath, width_in, length_ft, mode)
    if not forms.alert(msg, yes=True, no=True, title=TITLE):
        return
    project = revit.doc
    if project is None or project.IsFamilyDocument:
        inform('RFA saved. Open a project document to load it.')
        return
    load_tx = Transaction(project, 'Load generated Trex-style board')
    try:
        load_tx.Start()
        # Revit 2025 and 2027 API: the simpler LoadFamily(filename) overload
        # returns a bool in IronPython; leave placement to the user.
        result = project.LoadFamily(filepath)
        load_tx.Commit()
        inform('RFA saved and family load requested.\nUse Component to place a board, '
               'then edit Board_Length in the instance Properties.\n\n{0}'.format(filepath))
    except Exception as exc:
        if load_tx.GetStatus() == DB.TransactionStatus.Started:
            load_tx.RollBack()
        fail('RFA SAVED successfully, but loading into the project failed. '
             'Use Insert > Load Family manually.\n\n{0}'.format(exc))


if __name__ == '__main__':
    main()
