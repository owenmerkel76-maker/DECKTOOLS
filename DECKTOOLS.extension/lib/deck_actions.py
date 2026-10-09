# -*- coding: utf-8 -*-
import os
import webbrowser
from pyrevit import forms,revit,HOST_APP
from Autodesk.Revit import DB
from Autodesk.Revit.UI.Selection import ObjectType
from System.Collections.Generic import List


def selected_floor():
    doc=revit.doc
    if doc is None or doc.IsFamilyDocument:
        forms.alert('Open a project with a deck Floor.'); return None
    floors=[doc.GetElement(i) for i in HOST_APP.uidoc.Selection.GetElementIds()
            if isinstance(doc.GetElement(i),DB.Floor)]
    if len(floors)==1: return floors[0]
    try: ref=HOST_APP.uidoc.Selection.PickObject(ObjectType.Element,'Select the deck footprint Floor')
    except Exception: return None
    floor=doc.GetElement(ref.ElementId)
    if not isinstance(floor,DB.Floor):
        forms.alert('Select a Floor used as the deck footprint.'); return None
    return floor


def generated_elements(floor):
    identifier=floor.Id.Value
    prefix='DECKTOOLS|F{0}|'.format(identifier)
    items=[]
    for element in DB.FilteredElementCollector(revit.doc).OfCategory(
            DB.BuiltInCategory.OST_GenericModel).WhereElementIsNotElementType():
        comments=element.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        text=comments.AsString() if comments is not None else ''
        if text and text.startswith(prefix): items.append((element,text))
    return items


def inspect_deck():
    floor=selected_floor()
    if floor is None: return
    items=generated_elements(floor)
    boards=[text for element,text in items if '|BOARD|' in text]
    frame=sum('|ROLE=FRAME' in text for text in boards)
    clips=sum('|CLIP|' in text for element,text in items)
    forms.alert('Floor {0}\n\nField board cuts: {1}\nPicture-frame cuts: {2}\nClip elements: {3}\n'
                'Total generated elements: {4}'.format(floor.Id.Value,len(boards)-frame,frame,clips,len(items)),
                title='DECKTOOLS | Inspect deck')


def select_deck():
    floor=selected_floor()
    if floor is None: return
    items=generated_elements(floor)
    if not items: forms.alert('No DECKTOOLS elements were found for this Floor.'); return
    ids=List[DB.ElementId]()
    for element,text in items: ids.Add(element.Id)
    HOST_APP.uidoc.Selection.SetElementIds(ids)


def remove_deck():
    floor=selected_floor()
    if floor is None: return
    items=generated_elements(floor)
    if not items: forms.alert('No DECKTOOLS elements were found for this Floor.'); return
    if not forms.alert('Remove {0} generated boards/clips for Floor {1}?\n'
                       'The footprint Floor stays.'.format(len(items),floor.Id.Value),
                       yes=True,no=True,title='DECKTOOLS | Remove generated deck'): return
    with revit.Transaction('DECKTOOLS | remove generated deck'):
        for element,text in items: revit.doc.Delete(element.Id)


def open_reports():
    path=os.path.join(os.environ.get('USERPROFILE',os.path.expanduser('~')),'Documents','DECKTOOLS_Exports')
    if not os.path.isdir(path):
        forms.alert('No export folder yet. Generate a deck to create reports.'); return
    os.startfile(path)


def manufacturer_library():
    webbrowser.open('https://www.trex.com/')
    forms.alert('Use Trex professional/BIM resources to download supplied materials or image maps.\n\n'
                'Import .adsklib materials through Revit Material Browser, or choose downloaded texture '
                'and grayscale bump images in DECKTOOLS Materials. No automatic catalog sync is performed.',
                title='DECKTOOLS | Manufacturer resources')
