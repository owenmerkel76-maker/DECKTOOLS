from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'DECKTOOLS.extension' / 'DECKTOOLS.tab' / 'Boards.panel' / 'TrexBoardBuilder.pushbutton'
sys.path.insert(0, str(CORE))

import board_profile as bp


class BoardProfileTests(unittest.TestCase):
    def test_half_inch_rip_retains_one_groove(self):
        for mode in ('left', 'right'):
            points = bp.make_outline(0.5, mode)
            self.assertEqual(len(points), 8)
            self.assertAlmostEqual(bp.section_area_in2(points), 0.5 * 0.94 - 0.25 * 0.2)

    def test_half_inch_opposed_grooves_rejected(self):
        with self.assertRaises(ValueError):
            bp.make_outline(0.5, 'both')

    def test_square_half_inch_rip_has_full_section(self):
        points = bp.make_outline(0.5, 'square')
        self.assertEqual(len(points), 4)
        self.assertAlmostEqual(bp.section_area_in2(points), 0.5 * 0.94)

    def test_standard_board_area_excludes_both_grooves(self):
        self.assertAlmostEqual(bp.section_area_in2(bp.make_outline(5.5)),
                               5.5 * 0.94 - 2 * 0.25 * 0.2)

    def test_invalid_dimensions_and_mode_rejected(self):
        for width in (0.4, 6, float('nan'), float('inf')):
            with self.subTest(width=width), self.assertRaises(ValueError):
                bp.make_outline(width)
        with self.assertRaises(ValueError):
            bp.make_outline(5.5, 'unknown')


if __name__ == '__main__':
    unittest.main()
