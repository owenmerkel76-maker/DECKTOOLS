# -*- coding: utf-8 -*-
"""Shared material summaries and CSV exports; no Revit dependency.

Compatible with IronPython 2.7 and CPython 3. Each export gets its own directory
so regenerating a floor cannot silently overwrite a previous cutting schedule.
"""
import csv
import os
import shutil
import sys
import tempfile

import board_math as bm

try:
    text_type = unicode
except NameError:
    text_type = str


def board_mark(floor_id, board):
    return 'DT-B-F{0}-R{1:03d}-P{2:02d}'.format(
        floor_id, board['row'], board['piece'])


def build_takeoff(plan, kerf_in=bm.KERF_IN, reserve_percent=0.0):
    groups = bm.pack_stock(plan['boards'],
                           plan.get('stock_length_ft', bm.MAX_STOCK_FT),
                           kerf_in, reserve_percent)
    assignments = {}
    for group in groups:
        for stock in group['bins']:
            for sequence, piece in enumerate(stock['pieces'], 1):
                assignments[piece['board_index']] = (stock['stock_id'], sequence)
    base_stock = sum(g['stock'] for g in groups)
    reserve_stock = sum(g['reserve_stock'] for g in groups)
    length = plan.get('stock_length_ft', bm.MAX_STOCK_FT)
    cut_ft = sum(g['cut_ft'] for g in groups)
    unused_ft = sum(g['unused_ft'] for g in groups)
    kerf_ft = sum(g['kerf_ft'] for g in groups)
    return {'groups':groups, 'assignments':assignments,
            'stock_length_ft':length, 'kerf_in':float(kerf_in),
            'reserve_percent':float(reserve_percent),
            'base_stock':base_stock, 'reserve_stock':reserve_stock,
            'purchase_stock':base_stock + reserve_stock,
            'cut_ft':cut_ft, 'unused_ft':unused_ft, 'kerf_ft':kerf_ft,
            'linear_loss_percent':(100.0 * (unused_ft + kerf_ft) /
                                   (base_stock * length) if base_stock else 0.0),
            'installed_face_sqft':sum(b['width_in'] / 12.0 * b['length_ft']
                                      for b in plan['boards'])}


def export_rows(floor_id, plan, estimate, run_ft, span_ft, clip_count,
                joist_source, clip_source):
    """Build all three reports from the same estimate used by the preview."""
    cuts = [['ID', 'Floor_ID', 'Row', 'Piece', 'Stock_ID', 'Cut_Sequence',
             'Cut_Length_ft', 'Cut_Length_in', 'Actual_Width_in',
             'Thickness_in', 'Edge_Profile', 'Stock_Length_ft',
             'Side_Gap_in', 'Butt_Gap_in', 'Start_ft', 'End_ft']]
    for index, b in enumerate(plan['boards']):
        stock_id, sequence = estimate['assignments'][index]
        cuts.append([board_mark(floor_id, b), floor_id, b['row'], b['piece'],
                     stock_id, sequence, '{:.6f}'.format(b['length_ft']),
                     '{:.6f}'.format(b['length_ft'] * 12.0),
                     '{:.6f}'.format(b['width_in']), bm.THICKNESS_IN,
                     b['edge_mode'], estimate['stock_length_ft'],
                     bm.SIDE_GAP_IN, bm.BUTT_GAP_IN,
                     '{:.6f}'.format(b['start']), '{:.6f}'.format(b['end'])])

    schedule = [['Stock_ID', 'Cut_Sequence', 'Board_ID', 'Row', 'Piece',
                 'Stock_Length_ft', 'Cut_Length_ft', 'Cut_Length_in',
                 'Actual_Width_in', 'Edge_Profile', 'Kerf_After_Cut_in',
                 'Remaining_After_Cut_ft']]
    for group in estimate['groups']:
        for stock in group['bins']:
            remaining = stock['stock_length_ft']
            for sequence, piece in enumerate(stock['pieces'], 1):
                b = plan['boards'][piece['board_index']]
                remaining -= piece['length_ft'] + piece['kerf_ft']
                schedule.append([stock['stock_id'], sequence,
                                 board_mark(floor_id, b), b['row'], b['piece'],
                                 stock['stock_length_ft'],
                                 '{:.6f}'.format(piece['length_ft']),
                                 '{:.6f}'.format(piece['length_ft'] * 12.0),
                                 '{:.6f}'.format(b['width_in']), b['edge_mode'],
                                 '{:.6f}'.format(piece['kerf_ft'] * 12.0),
                                 '{:.6f}'.format(max(0.0, remaining))])

    materials = [
        ['Category', 'Description', 'Quantity', 'Unit', 'Notes'],
        ['Deck', 'Rectangular footprint', '{:.3f}'.format(run_ft * span_ft),
         'square feet', 'Floor top footprint, including board gaps'],
        ['Deck', 'Board direction run', run_ft, 'feet', ''],
        ['Deck', 'Deck width', span_ft, 'feet', ''],
        ['Board', 'Installed cut pieces', len(plan['boards']), 'each',
         'Does not include spare stock'],
        ['Board', 'Installed rows', len(plan['rows']), 'rows',
         'Includes first and last perimeter rows'],
        ['Board', 'Perimeter ripped rows',
         sum(1 for r in plan['rows'] if (r[1]-r[0])*12.0 < 5.499), 'rows',
         'Factory groove retained on interior edge'],
        ['Board', 'Installed linear length', '{:.6f}'.format(estimate['cut_ft']),
         'feet', 'Sum of every installed cut'],
        ['Board', 'Installed face area',
         '{:.3f}'.format(estimate['installed_face_sqft']), 'square feet',
         'Actual cut widths and lengths; excludes gaps'],
        ['Clip', 'Board-gap/joist intersections', clip_count, 'each',
         'Excludes starter/finish fasteners and butt-joint blocking details'],
        ['Clip', 'Joist source', joist_source, '',
         'Nominal spacing is an estimate, not confirmed framing'],
        ['Clip', 'Geometry source', clip_source, '',
         'Built-in geometry is schematic'],
        ['Settings', 'Stock board length', estimate['stock_length_ft'], 'feet',
         'Assumes raw 5.5-inch-wide stock; rip width/profile groups kept separate'],
        ['Settings', 'Crosscut saw kerf', estimate['kerf_in'], 'inches',
         'No kerf for an exact remaining-length piece; no factory end trim'],
        ['Settings', 'Spare-board allowance', estimate['reserve_percent'], 'percent',
         'Rounded up in each width/profile group; extra whole boards'],
    ]
    for group in estimate['groups']:
        description = '{:g}ft stock | rip {:.4f}in | {}'.format(
            group['stock_length_ft'], group['width_in'], group['edge_mode'])
        materials.append(['Stock', description, group['purchase_stock'], 'boards',
                          '{} base + {} spare; {:.6f}ft offcut; {:.6f}ft crosscut kerf'.format(
                              group['stock'], group['reserve_stock'],
                              group['unused_ft'], group['kerf_ft'])])
    materials.extend([
        ['Stock', 'Base stock boards', estimate['base_stock'], 'boards',
         'First-fit estimate; not a guaranteed minimum'],
        ['Stock', 'Extra spare boards', estimate['reserve_stock'], 'boards',
         'Not assigned to installed cuts or the cutting schedule'],
        ['Stock', 'TOTAL boards to purchase', estimate['purchase_stock'], 'boards',
         'Base stock plus spare allowance'],
        ['Stock', 'TOTAL purchase linear length',
         '{:.6f}'.format(estimate['purchase_stock'] * estimate['stock_length_ft']),
         'feet', 'Includes whole spare boards'],
        ['Loss', 'Crosscut kerf loss', '{:.6f}'.format(estimate['kerf_ft']), 'feet',
         'Base stock only; excludes longitudinal ripping'],
        ['Offcut', 'Remaining offcut length', '{:.6f}'.format(estimate['unused_ft']),
         'feet', 'Base stock only; offcuts may be reusable'],
        ['Loss', 'Unused linear material including kerf',
         '{:.3f}'.format(estimate['linear_loss_percent']), 'percent',
         'Base stock only; excludes width removed by ripping and spare boards'],
        ['Exclusions', 'Picture frames, posts, stairs, blocking, starters, finish fasteners',
         '', '', 'Specify separately; no structural or fastening design'],
    ])
    return {'Cutlist.csv':cuts, 'StockCuts.csv':schedule, 'Materials.csv':materials}


def _write_csv(path, rows):
    if sys.version_info[0] >= 3:
        with open(path, 'w', newline='', encoding='utf-8-sig') as stream:
            csv.writer(stream).writerows(rows)
    else:
        with open(path, 'wb') as stream:
            stream.write(b'\xef\xbb\xbf')
            writer = csv.writer(stream)
            for row in rows:
                writer.writerow([value.encode('utf-8') if isinstance(value, text_type)
                                 else value for value in row])


def write_exports(folder, prefix, rows):
    """Write a unique export set. Remove only this set if a write fails."""
    if not os.path.isdir(folder):
        os.makedirs(folder)
    destination = tempfile.mkdtemp(prefix=prefix + '_', dir=folder)
    paths = {}
    try:
        for name in ('Cutlist.csv', 'StockCuts.csv', 'Materials.csv'):
            paths[name] = os.path.join(destination, name)
            _write_csv(paths[name], rows[name])
    except Exception:
        shutil.rmtree(destination)
        raise
    return paths
