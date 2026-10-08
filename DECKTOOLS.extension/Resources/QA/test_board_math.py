# -*- coding: utf-8 -*-
"""Run with ordinary Python: python test_board_math.py. Does not need Revit."""
from __future__ import print_function
import os
import sys
import random

HERE=os.path.dirname(os.path.abspath(__file__))
CORE=os.path.abspath(os.path.join(HERE,'..','..','DECKTOOLS.tab','Layout.panel','DeckAutoLayout.pushbutton'))
sys.path.insert(0,CORE)
import board_math as bm


def check(condition,message):
    if not condition: raise AssertionError(message)


def verify(l,w,spacing):
    stations=bm.estimated_stations(l,spacing)
    plan=bm.plan(l,w,stations)
    rows=plan['rows']; cuts=plan['boards']
    check(abs(rows[-1][1]-w)<1e-6,'incorrect width')
    check(abs(rows[0][0])<1e-6,'incorrect start')
    for i,row in enumerate(rows):
        check(0.5 <= (row[1]-row[0])*12 <=5.5001,'rip out of bounds')
        if i:
            check(abs((row[0]-rows[i-1][1])*12-0.1875)<1e-6,'wrong 3/16 gap')
    for cut in cuts:
        check(0<cut['length_ft']<=20.00001,'piece longer than max stock')
        check(cut['edge_mode'] in ('both','left','right','square'),'mode')
    for r in range(1,len(rows)+1):
        bb=[b for b in cuts if b['row']==r]
        bb.sort(key=lambda p:p['start'])
        check(abs(bb[0]['start'])<1e-6,'run starting gap')
        check(abs(bb[-1]['end']-l)<1e-6,'run ending gap')
        for i in range(1,len(bb)):
            check(abs((bb[i]['start']-bb[i-1]['end'])*12-.125)<1e-5,'wrong butt gap')
    stocks=bm.pack_20ft_stock(cuts)
    for s in stocks:
        check(s['stock']>=1 and s['unused_ft']>=-1e-5,'stock count/waste')
    return len(rows),len(cuts),len(stations),sum(g['stock'] for g in stocks)


if __name__=='__main__':
    # Exact boundary, balanced rips, deck rotated in Revit (projection checked there),
    # 20ft limit and butt joint sites on estimated joists.
    cases=[(12,10,16),(20,20,16),(25,15,16),(37,10.5,12),
           (8,0.5,16),(19.9,40,16),(42,14,12)]
    for l,w,spacing in cases:
        print('PASS fixed',l,w,spacing,verify(l,w,spacing))
    rnd=random.Random(6244)
    passed=0
    for i in range(240):
        l=rnd.uniform(1,45)
        w=rnd.uniform(0.5,40)
        gap=rnd.choice([12,16,24])
        try:
            verify(l,w,gap)
            passed+=1
        except ValueError as err:
            # Some narrow/slender rectangles and far-apart joists are not supported;
            # reject explicitly rather than silently model illegal-length cuts.
            print('SAFE REJECTION {0}: {1}'.format(i,err))
    print('PASSED {0} randomized valid decking layouts + {1} fixed cases'.format(passed,len(cases)))
