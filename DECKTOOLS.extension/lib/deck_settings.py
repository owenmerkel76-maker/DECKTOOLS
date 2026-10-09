# -*- coding: utf-8 -*-
"""Validated settings shared by the WPF UI and tests (IronPython compatible)."""
import math
import os
import re


def number(value,label,minimum,maximum):
    try: result=float(value)
    except (TypeError,ValueError,OverflowError): raise ValueError(label+' must be numeric.')
    if math.isnan(result) or math.isinf(result) or not minimum<=result<=maximum:
        raise ValueError('{0} must be from {1:g} to {2:g}.'.format(label,minimum,maximum))
    return result


def layout_settings(values):
    result=dict(values)
    result['stock_length']=number(values['stock_length'],'Stock length',12,20)
    if result['stock_length'] not in (12,16,20): raise ValueError('Choose 12-, 16-, or 20-foot stock.')
    result['spare_percent']=number(values['spare_percent'],'Spare allowance',0,100)
    result['kerf_in']=number(values['kerf_in'],'Saw kerf',0,1)
    result['spacing_in']=number(values['spacing_in'],'Joist spacing',4,36)
    result['frame_courses']=number(values['frame_courses'],'Frame courses',0,3)
    if result['frame_courses']!=int(result['frame_courses']): raise ValueError('Frame courses must be a whole number.')
    result['frame_courses']=int(result['frame_courses'])
    result['frame_width_in']=number(values['frame_width_in'],'Frame width',0.5,5.5)
    if values['joist_mode'] not in ('nominal','actual'): raise ValueError('Choose a joist source.')
    if values['clip_mode'] not in ('auto','proxy','loaded','browse'): raise ValueError('Choose a clip source.')
    return result


def material_settings(name,color,texture='',bump='',bump_amount='0.3'):
    name=name.strip()
    if not name: raise ValueError('Enter a new material name.')
    color=color.strip().lstrip('#')
    if not re.match(r'^[0-9a-fA-F]{6}$',color): raise ValueError('Color must be a six-digit hex value, e.g. #805F49.')
    files=[]
    for label,path in (('Texture',texture),('Bump map',bump)):
        path=path.strip()
        if path:
            if not os.path.isfile(path): raise ValueError(label+' file was not found.')
            if os.path.splitext(path)[1].lower() not in ('.png','.jpg','.jpeg','.bmp','.tif','.tiff'):
                raise ValueError(label+' must be PNG, JPEG, BMP, or TIFF.')
            path=os.path.abspath(path)
        files.append(path)
    return {'name':name,'rgb':tuple(int(color[i:i+2],16) for i in (0,2,4)),
            'texture':files[0],'bump':files[1],
            'bump_amount':number(bump_amount,'Bump strength',0,1)}
