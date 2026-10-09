from pathlib import Path
import random
import sys
import unittest
import ast
from types import SimpleNamespace
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
CORE=ROOT/'DECKTOOLS.extension/DECKTOOLS.tab/Layout.panel/DeckAutoLayout.pushbutton'
sys.path.insert(0,str(CORE))
import board_math as bm
import takeoff


class PictureFrameTests(unittest.TestCase):
    def make_plan(self,run=12,width=10,courses=1,stock=20):
        return bm.plan(run,width,bm.estimated_stations(run),stock,courses)

    def test_four_mitered_sides_and_recessed_field(self):
        plan=self.make_plan()
        frame=[b for b in plan['boards'] if b.get('role')=='FRAME']
        self.assertEqual(len(frame),4)
        self.assertEqual(set(b['frame_side'] for b in frame),{'TOP','BOTTOM','LEFT','RIGHT'})
        self.assertTrue(all(b['edge_mode']=='square' for b in frame))
        inset=(5.5+.1875)/12
        self.assertAlmostEqual(plan['field_bounds'][0],inset)
        for b in plan['boards']:
            if b.get('role')=='FIELD':
                self.assertGreaterEqual(b['start'],inset-1e-8)
                self.assertLessEqual(b['end'],12-inset+1e-8)
                self.assertGreaterEqual(b['low'],inset-1e-8)
                self.assertLessEqual(b['high'],10-inset+1e-8)
        self.assertEqual(len(set((b['row'],b['piece']) for b in plan['boards'])),len(plan['boards']))

    def test_two_and_three_courses_and_stock_splits(self):
        for courses in (1,2,3):
            plan=self.make_plan(30,20,courses,12)
            frames=[b for b in plan['boards'] if b.get('role')=='FRAME']
            self.assertEqual(set(b['frame_course'] for b in frames),set(range(1,courses+1)))
            self.assertGreater(plan['border_splits'],0)
            self.assertTrue(all(0<b['length_ft']<=12 for b in plan['boards']))
            estimate=takeoff.build_takeoff(plan,reserve_percent=10)
            self.assertEqual(len(estimate['assignments']),len(plan['boards']))
            self.assertAlmostEqual(estimate['base_stock']*12,
                                   estimate['cut_ft']+estimate['unused_ft']+estimate['kerf_ft'])

    def test_field_joints_retain_absolute_joist_positions(self):
        stations=bm.estimated_stations(35)
        plan=bm.plan(35,15,stations,12,2)
        self.assertTrue(plan['joints'])
        for joint in plan['joints']:
            self.assertLess(min(abs(joint-s) for s in stations),1e-6)

    def test_frame_area_uses_actual_polygons_not_rectangular_blanks(self):
        plan=self.make_plan()
        frame=[b for b in plan['boards'] if b.get('role')=='FRAME']
        for b in frame:
            self.assertAlmostEqual(b['face_area_sqft'],bm.polygon_area(b['polygon']))
            self.assertLess(b['face_area_sqft'],b['length_ft']*b['width_in']/12)
        expected=sum(b.get('face_area_sqft',b['length_ft']*b['width_in']/12) for b in plan['boards'])
        self.assertAlmostEqual(takeoff.build_takeoff(plan)['installed_face_sqft'],expected)

    def test_no_overlapping_board_interiors(self):
        plan=self.make_plan(courses=2)
        polygons=[]
        for b in plan['boards']:
            polygons.append(b.get('polygon',[(b['start'],b['low']),(b['end'],b['low']),
                                            (b['end'],b['high']),(b['start'],b['high'])]))
        def inside(poly,p):
            cross=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                cross.append((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
            return all(x>1e-8 for x in cross) or all(x< -1e-8 for x in cross)
        rng=random.Random(723)
        for _ in range(2000):
            p=(rng.uniform(0,12),rng.uniform(0,10))
            self.assertLessEqual(sum(inside(poly,p) for poly in polygons),1,p)

    def test_frame_reports_roles_sides_and_separate_stock_groups(self):
        plan=self.make_plan()
        estimate=takeoff.build_takeoff(plan)
        reports=takeoff.export_rows(1,plan,estimate,12,10,100,'estimated','proxy')
        cut=[dict(zip(reports['Cutlist.csv'][0],r)) for r in reports['Cutlist.csv'][1:]]
        self.assertEqual(sum(r['Role']=='FRAME' for r in cut),4)
        self.assertTrue(any(g['role']=='FRAME' for g in estimate['groups']))
        self.assertTrue(any('blocking' in str(cell) for row in reports['Materials.csv'] for cell in row))

    def test_zero_courses_matches_original(self):
        stations=bm.estimated_stations(12)
        self.assertEqual(bm.plan(12,10,stations),bm.plan(12,10,stations,20,0))

    def test_invalid_and_too_small_frames_fail(self):
        for courses,width in ((4,5.5),(-1,5.5),(1.5,5.5),(1,0),(1,6),(1,float('nan'))):
            with self.assertRaises(ValueError):
                bm.plan(12,10,[],20,courses,width)
        with self.assertRaisesRegex(ValueError,'less than 6 inches'):
            bm.plan(1,1,[],20,1)

    def test_frame_solid_uses_polygon_vertical_extrusion_and_selected_material(self):
        tree=ast.parse((CORE/'script.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='board_solid')
        extrude=Mock(return_value='solid')
        scope={'DB':SimpleNamespace(XYZ=SimpleNamespace(BasisZ='up')),'bm':bm,
               '_point':lambda u,v,o,x,y:(x,y),'extrusion':extrude}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'script.py','exec'),scope)
        board=next(b for b in self.make_plan()['boards'] if b.get('role')=='FRAME')
        self.assertEqual(scope['board_solid'](board,{'u':'u','v':'v','origin':'o'},22),'solid')
        extrude.assert_called_once_with(board['polygon'],'up',.94/12,22)


if __name__=='__main__': unittest.main()
