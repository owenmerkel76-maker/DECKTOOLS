#!/usr/bin/env python3
"""Preview a rectangular-deck takeoff using the same math as the Revit button."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'DECKTOOLS.extension' / 'DECKTOOLS.tab' / 'Layout.panel' / 'DeckAutoLayout.pushbutton'
sys.path.insert(0, str(CORE))

import board_math as bm
import takeoff


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=float,
                        help='Deck dimension along the boards, in feet')
    parser.add_argument('--width', required=True, type=float,
                        help='Deck dimension across the boards, in feet')
    parser.add_argument('--stock', type=int, choices=(12, 16, 20), default=20,
                        help='Stock board length in feet (default: 20)')
    parser.add_argument('--spacing', type=float, default=16.0,
                        help='Estimated joist spacing in inches (default: 16)')
    parser.add_argument('--kerf', type=float, default=bm.KERF_IN,
                        help='Crosscut saw kerf in inches (default: 0.125)')
    parser.add_argument('--spare-percent', type=float, default=10.0,
                        help='Whole spare boards, rounded up per group (default: 10)')
    parser.add_argument('--output', type=Path, default=ROOT / 'DECKTOOLS_Exports',
                        help='Parent directory for the three CSV reports')
    args = parser.parse_args(argv)
    try:
        bm.pack_stock([], args.stock, args.kerf, args.spare_percent)
        stations = bm.estimated_stations(args.run, args.spacing)
        plan = bm.plan(args.run, args.width, stations, args.stock)
        estimate = takeoff.build_takeoff(plan, args.kerf, args.spare_percent)
        clips = len(plan['seams']) * len(stations)
        rows = takeoff.export_rows(
            0, plan, estimate, args.run, args.width, clips,
            'Assumed {:g}in O.C.'.format(args.spacing), 'No model generated (CLI estimate)')
        paths = takeoff.write_exports(str(args.output), 'Estimate', rows)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print('{} installed pieces across {} rows'.format(len(plan['boards']), len(plan['rows'])))
    print('{} base + {} spare = {} {}ft stock boards to purchase'.format(
        estimate['base_stock'], estimate['reserve_stock'],
        estimate['purchase_stock'], args.stock))
    print('{:.3f}ft crosscut kerf loss; {:.3f}ft remaining offcuts'.format(
        estimate['kerf_ft'], estimate['unused_ft']))
    print('{} estimated clip positions; nominal framing only'.format(clips))
    for name in ('Cutlist.csv', 'StockCuts.csv', 'Materials.csv'):
        print('{}: {}'.format(name, paths[name]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
