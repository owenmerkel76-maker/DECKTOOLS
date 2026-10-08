import csv
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'DECKTOOLS.extension' / 'DECKTOOLS.tab' / 'Layout.panel' / 'DeckAutoLayout.pushbutton'
sys.path.insert(0, str(CORE))

import board_math as bm
import takeoff


def board(length, width=5.5, mode='both'):
    return {'length_ft':length, 'width_in':width, 'edge_mode':mode}


class StockPackingTests(unittest.TestCase):
    def test_trimmed_single_piece_consumes_kerf(self):
        group = bm.pack_stock([board(8)])[0]
        self.assertAlmostEqual(group['kerf_ft'], 0.125 / 12)
        self.assertAlmostEqual(group['unused_ft'], 12 - 0.125 / 12)

    def test_full_length_piece_needs_no_crosscut(self):
        group = bm.pack_stock([board(20)])[0]
        self.assertEqual(group['kerf_ft'], 0)
        self.assertEqual(group['unused_ft'], 0)

    def test_two_ten_foot_cuts_do_not_fit_twenty_foot_stock(self):
        group = bm.pack_stock([board(10), board(10)])[0]
        self.assertEqual(group['stock'], 2)

    def test_exact_remaining_piece_avoids_extra_kerf(self):
        remaining = 20 - 10 - bm.KERF_IN / 12
        group = bm.pack_stock([board(10), board(remaining)])[0]
        self.assertEqual(group['stock'], 1)
        self.assertAlmostEqual(group['kerf_ft'], bm.KERF_IN / 12)
        self.assertAlmostEqual(group['unused_ft'], 0)

    def test_saw_overhang_only_consumes_stock_remaining(self):
        group = bm.pack_stock([board(20 - 0.001)])[0]
        self.assertAlmostEqual(group['kerf_ft'], 0.001)
        self.assertAlmostEqual(group['unused_ft'], 0)

    def test_custom_kerf_and_stock_length(self):
        group = bm.pack_stock([board(5), board(5)], 12, 0.25)[0]
        self.assertEqual(group['stock'], 1)
        self.assertAlmostEqual(group['kerf_ft'], 0.5 / 12)
        self.assertAlmostEqual(group['unused_ft'], 2 - 0.5 / 12)

    def test_zero_kerf_allows_two_halves(self):
        group = bm.pack_stock([board(10), board(10)], kerf_in=0)[0]
        self.assertEqual(group['stock'], 1)
        self.assertEqual(group['unused_ft'], 0)

    def test_spares_rounded_up_per_width_and_profile_group(self):
        groups = bm.pack_stock([board(8, 4, 'left'), board(8, 4, 'right'),
                                board(8), board(8)], reserve_percent=10)
        self.assertEqual(len(groups), 3)
        self.assertEqual(sum(g['stock'] for g in groups), 3)
        self.assertEqual(sum(g['reserve_stock'] for g in groups), 3)
        self.assertEqual(sum(g['purchase_stock'] for g in groups), 6)

    def test_zero_spares_preserves_base_quantity(self):
        group = bm.pack_stock([board(8)], reserve_percent=0)[0]
        self.assertEqual(group['reserve_stock'], 0)
        self.assertEqual(group['purchase_stock'], group['stock'])

    def test_empty_takeoff_has_zero_totals(self):
        estimate = takeoff.build_takeoff({'boards':[], 'stock_length_ft':12})
        self.assertEqual(estimate['purchase_stock'], 0)
        self.assertEqual(estimate['linear_loss_percent'], 0)

    def test_deterministic_and_no_input_mutation(self):
        boards = [board(4), board(6), board(6)]
        original = [dict(b) for b in boards]
        self.assertEqual(bm.pack_stock(boards), bm.pack_stock(boards))
        self.assertEqual(boards, original)

    def test_invalid_stock_settings_rejected(self):
        for kwargs in ({'stock_length_ft':0}, {'stock_length_ft':21},
                       {'kerf_in':-1}, {'kerf_in':1.1},
                       {'reserve_percent':-1}, {'reserve_percent':101},
                       {'kerf_in':float('nan')}, {'reserve_percent':float('inf')},
                       {'stock_length_ft':float('inf')}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                bm.pack_stock([board(4)], **kwargs)

    def test_invalid_cuts_and_profiles_rejected(self):
        for b in (board(21), board(0), board(-1), board(float('nan')),
                  board(float('inf')), board(4, 6), board(4, 0.4),
                  board(4, float('nan')), board(4, mode='unknown')):
            with self.subTest(board=b), self.assertRaises(ValueError):
                bm.pack_stock([b])

    def test_every_random_cut_assigned_once_and_material_conserved(self):
        rng = random.Random(415)
        for stock_length in (12, 16, 20):
            boards = [board(rng.uniform(0.5, stock_length),
                            rng.choice([3, 5.5]), rng.choice(['left', 'right', 'both']))
                      for _ in range(100)]
            groups = bm.pack_stock(boards, stock_length, 0.125, 10)
            assigned = []
            stock_ids = []
            for group in groups:
                self.assertAlmostEqual(group['stock'] * stock_length,
                                       group['cut_ft'] + group['kerf_ft'] + group['unused_ft'])
                self.assertEqual(group['reserve_stock'], int(math.ceil(group['stock'] * 0.1)))
                for stock in group['bins']:
                    stock_ids.append(stock['stock_id'])
                    self.assertGreaterEqual(stock['unused_ft'], 0)
                    self.assertLessEqual(stock['used_ft'], stock_length + 1e-7)
                    self.assertAlmostEqual(stock_length, sum(
                        p['length_ft'] + p['kerf_ft'] for p in stock['pieces']) + stock['unused_ft'])
                    assigned.extend(p['board_index'] for p in stock['pieces'])
            self.assertEqual(sorted(assigned), list(range(len(boards))))
            self.assertEqual(len(stock_ids), len(set(stock_ids)))


class LayoutTests(unittest.TestCase):
    def test_twelve_and_sixteen_foot_stock_changes_long_run_joints(self):
        stations = bm.estimated_stations(25)
        for maximum in (12, 16, 20):
            plan = bm.plan(25, 10, stations, maximum)
            self.assertEqual(plan['stock_length_ft'], maximum)
            self.assertTrue(all(b['length_ft'] <= maximum for b in plan['boards']))
            self.assertTrue(all(any(abs(j - s) <= 1e-6 for s in stations)
                                for j in plan['joints']))
        short = bm.plan(25, 10, stations, 12)
        long = bm.plan(25, 10, stations, 20)
        self.assertGreater(len(short['boards']), len(long['boards']))

    def test_exact_stock_run_needs_no_joints(self):
        for maximum in (12, 16, 20):
            plan = bm.plan(maximum, 10, bm.estimated_stations(maximum), maximum)
            self.assertEqual(plan['joints'], [])

    def test_random_layouts_support_all_stock_lengths_and_generate_valid_profiles(self):
        profile_dir = (ROOT / 'DECKTOOLS.extension' / 'DECKTOOLS.tab' /
                       'Boards.panel' / 'TrexBoardBuilder.pushbutton')
        sys.path.insert(0, str(profile_dir))
        import board_profile
        rng = random.Random(6244)
        for stock_length in (12, 16, 20):
            for _ in range(80):
                run = rng.uniform(1, 45)
                width = rng.uniform(0.5, 40)
                stations = bm.estimated_stations(run, rng.choice([12, 16, 24]))
                plan = bm.plan(run, width, stations, stock_length)
                estimate = takeoff.build_takeoff(plan, reserve_percent=10)
                self.assertEqual(len(estimate['assignments']), len(plan['boards']))
                self.assertAlmostEqual(plan['rows'][0][0], 0)
                self.assertAlmostEqual(plan['rows'][-1][1], width)
                for b in plan['boards']:
                    self.assertLessEqual(b['length_ft'], stock_length)
                    points = board_profile.make_outline(b['width_in'], b['edge_mode'])
                    self.assertGreater(board_profile.section_area_in2(points), 0)

    def test_actual_joists_must_span_full_width_and_be_perpendicular(self):
        segments = [(10, -1, 10, 11), (5, 0, 6, 10),
                    (8, 4, 8, 6), (25, 10, 25, 0),
                    (40, 0, 40, 10), (10, 11, 10, -1)]
        self.assertEqual(bm.full_width_stations(segments, 30, 10), [10, 25])

    def test_no_joint_support_fails_for_selected_length(self):
        with self.assertRaisesRegex(ValueError, '12ft'):
            bm.plan(13, 10, [], 12)

    def test_invalid_dimensions_rejected(self):
        for value in (float('nan'), float('inf'), -1, 0):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    bm.plan(value, 10, [])
                with self.assertRaises(ValueError):
                    bm.plan(10, value, [])
                with self.assertRaises(ValueError):
                    bm.estimated_stations(value)

    def test_invalid_joints_rejected(self):
        for joints in ([10, 5], [5, 5], [-1], [20], [float('nan')]):
            with self.subTest(joints=joints), self.assertRaises(ValueError):
                bm.piece_spans(20, joints)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.plan = bm.plan(25, 10, bm.estimated_stations(25), 16)
        self.estimate = takeoff.build_takeoff(self.plan, reserve_percent=10)
        self.rows = takeoff.export_rows(123, self.plan, self.estimate,
                                        25, 10, 100, 'Actual joists', 'Schematic clip')

    def test_cutlist_and_stock_schedule_match_exactly(self):
        cuts = [dict(zip(self.rows['Cutlist.csv'][0], row)) for row in self.rows['Cutlist.csv'][1:]]
        schedule = [dict(zip(self.rows['StockCuts.csv'][0], row)) for row in self.rows['StockCuts.csv'][1:]]
        self.assertEqual(len(cuts), len(self.plan['boards']))
        self.assertEqual(len(schedule), len(cuts))
        by_id = {row['Board_ID']:row for row in schedule}
        self.assertEqual(len(by_id), len(cuts))
        for cut in cuts:
            assigned = by_id[cut['ID']]
            self.assertEqual(cut['Stock_ID'], assigned['Stock_ID'])
            self.assertEqual(cut['Cut_Sequence'], assigned['Cut_Sequence'])
            self.assertEqual(cut['Cut_Length_ft'], assigned['Cut_Length_ft'])
            self.assertEqual(cut['Stock_Length_ft'], 16)
            self.assertAlmostEqual(float(cut['Cut_Length_in']), float(cut['Cut_Length_ft']) * 12, places=4)

    def test_material_summary_matches_purchase_and_losses(self):
        data = {row[1]:row[2] for row in self.rows['Materials.csv'][1:]}
        self.assertEqual(data['TOTAL boards to purchase'], self.estimate['purchase_stock'])
        self.assertEqual(data['Extra spare boards'], self.estimate['reserve_stock'])
        self.assertAlmostEqual(float(data['Crosscut kerf loss']), self.estimate['kerf_ft'], places=5)
        self.assertLess(self.estimate['installed_face_sqft'], 250)

    def test_stock_schedule_conserves_length_after_each_cut(self):
        remaining = {}
        for data in self.rows['StockCuts.csv'][1:]:
            row = dict(zip(self.rows['StockCuts.csv'][0], data))
            previous = remaining.get(row['Stock_ID'], row['Stock_Length_ft'])
            after = float(row['Remaining_After_Cut_ft'])
            self.assertAlmostEqual(previous - float(row['Cut_Length_ft']) -
                                   float(row['Kerf_After_Cut_in']) / 12, after, places=5)
            self.assertGreaterEqual(after, 0)
            remaining[row['Stock_ID']] = after

    def test_repeated_exports_preserve_both_and_support_unicode(self):
        self.rows['Materials.csv'].append(['Note', 'Clip caf\u00e9', 1, '', ''])
        with tempfile.TemporaryDirectory() as folder:
            first = takeoff.write_exports(folder, 'Deck_F123', self.rows)
            second = takeoff.write_exports(folder, 'Deck_F123', self.rows)
            self.assertNotEqual(first['Cutlist.csv'], second['Cutlist.csv'])
            for paths in (first, second):
                for name, path in paths.items():
                    with open(path, encoding='utf-8-sig', newline='') as stream:
                        rows = list(csv.reader(stream))
                    self.assertEqual(len(rows), len(self.rows[name]))
                    self.assertEqual(rows[0], self.rows[name][0])
            self.assertIn('caf\u00e9', Path(first['Materials.csv']).read_text(encoding='utf-8-sig'))

    def test_failed_export_removes_its_incomplete_set(self):
        rows = dict(self.rows)
        del rows['Materials.csv']
        with tempfile.TemporaryDirectory() as folder:
            keep = Path(folder) / 'keep.txt'
            keep.write_text('existing file')
            with self.assertRaises(KeyError):
                takeoff.write_exports(folder, 'Deck_F123', rows)
            self.assertEqual(list(Path(folder).iterdir()), [keep])


class CommandLineTests(unittest.TestCase):
    def test_cli_creates_three_consistent_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'estimate_deck.py'),
                                     '--run', '12', '--width', '10', '--stock', '12',
                                     '--spare-percent', '10', '--output', folder],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('22 installed pieces', result.stdout)
            self.assertIn('22 base + 4 spare = 26 12ft stock boards', result.stdout)
            self.assertEqual(len(list(Path(folder).rglob('*.csv'))), 3)

    def test_invalid_cli_input_writes_no_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'estimate_deck.py'),
                                     '--run', 'nan', '--width', '10', '--output', folder],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('finite number', result.stderr)
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
