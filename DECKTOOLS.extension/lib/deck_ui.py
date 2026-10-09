# -*- coding: utf-8 -*-
import os
from pyrevit import forms
from Autodesk.Revit import DB
from deck_settings import layout_settings


class LayoutWindow(forms.WPFWindow):
    def __init__(self,doc):
        forms.WPFWindow.__init__(self,os.path.join(os.path.dirname(__file__),'layout.xaml'))
        self.result=None
        self.materials=[('Default composite',None)]
        for material in DB.FilteredElementCollector(doc).OfClass(DB.Material):
            self.materials.append((material.Name,material.Id))
        self.materials[1:]=sorted(self.materials[1:],key=lambda x:x[0].lower())
        for name,identifier in self.materials:
            self.field_material.Items.Add(name)
            self.frame_material.Items.Add(name)
        self.field_material.SelectedIndex=0
        self.frame_material.SelectedIndex=0

    def on_cancel(self,sender,args): self.Close()

    def on_accept(self,sender,args):
        try:
            self.result=layout_settings({
                'along_long':self.direction.SelectedIndex==0,
                'stock_length':(20,16,12)[self.stock.SelectedIndex],
                'spare_percent':self.spares.Text,'kerf_in':self.kerf.Text,
                'spacing_in':self.spacing.Text,
                'frame_courses':self.courses.SelectedIndex,'frame_width_in':self.frame_width.Text,
                'joist_mode':('nominal','actual')[self.joists.SelectedIndex],
                'clip_mode':('auto','proxy','loaded','browse')[self.clips.SelectedIndex],
                'field_material_id':self.materials[self.field_material.SelectedIndex][1],
                'frame_material_id':self.materials[self.frame_material.SelectedIndex][1],
                'field_material_name':self.materials[self.field_material.SelectedIndex][0],
                'frame_material_name':self.materials[self.frame_material.SelectedIndex][0]})
        except (ValueError,IndexError) as error:
            forms.alert(str(error),title='DECKTOOLS settings'); return
        self.Close()


def collect_layout_settings(doc):
    window=LayoutWindow(doc)
    window.ShowDialog()
    return window.result
