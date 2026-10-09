# -*- coding: utf-8 -*-
import os
import webbrowser
import clr
from pyrevit import forms, revit, HOST_APP
from Autodesk.Revit import DB
from deck_settings import material_settings
from deck_materials import create_material

TREX_URL='https://www.trex.com/'


class MaterialWindow(forms.WPFWindow):
    def __init__(self,doc,app):
        forms.WPFWindow.__init__(self,os.path.join(os.path.dirname(__file__),'materials.xaml'))
        self.doc,self.app=doc,app
        self.sources=[('New material / standard Generic appearance',None)]
        for material in DB.FilteredElementCollector(doc).OfClass(DB.Material):
            self.sources.append((material.Name,material))
        self.sources[1:]=sorted(self.sources[1:],key=lambda x:x[0].lower())
        for name,material in self.sources: self.source.Items.Add(name)
        self.source.SelectedIndex=0

    def on_cancel(self,sender,args): self.Close()

    def on_color(self,sender,args):
        clr.AddReference('System.Windows.Forms')
        clr.AddReference('System.Drawing')
        from System.Windows.Forms import ColorDialog,DialogResult
        from System.Drawing import ColorTranslator
        dialog=ColorDialog()
        dialog.FullOpen=True
        try:
            try: dialog.Color=ColorTranslator.FromHtml(self.color.Text)
            except Exception: pass
            if dialog.ShowDialog()==DialogResult.OK:
                self.color.Text='#{0:02X}{1:02X}{2:02X}'.format(dialog.Color.R,dialog.Color.G,dialog.Color.B)
        finally: dialog.Dispose()

    def on_texture(self,sender,args):
        path=forms.pick_file(files_filter='Images|*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff',title='Choose downloaded color texture')
        if path: self.texture.Text=path

    def on_bump(self,sender,args):
        path=forms.pick_file(files_filter='Images|*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff',title='Choose grayscale height / bump map')
        if path: self.bump.Text=path

    def on_library(self,sender,args): webbrowser.open(TREX_URL)

    def on_create(self,sender,args):
        try:
            spec=material_settings(self.material_name.Text,self.color.Text,self.texture.Text,
                                   self.bump.Text,self.bump_amount.Text)
            spec['clear_maps']=bool(self.clear_maps.IsChecked)
            material=create_material(self.doc,self.app,spec,self.sources[self.source.SelectedIndex][1])
        except Exception as error:
            forms.alert(str(error),title='DECKTOOLS materials'); return
        forms.alert('Created material: '+material.Name+'\n\nChoose it for the field or border in Deck Designer. '
                    'Keep map files at their selected paths. Verify texture scale and orientation in '
                    'Revit Material Browser and a Realistic view.',title='DECKTOOLS materials')
        self.Close()


def show_material_tool():
    doc=revit.doc
    if doc is None or doc.IsFamilyDocument:
        forms.alert('Open a Revit project to create decking materials.'); return
    MaterialWindow(doc,HOST_APP.app).ShowDialog()
