# -*- coding: utf-8 -*-
"""DECKTOOLS pure Python calculation core (IronPython 2.7 compatible).
Dimensions in feet unless the variable ends with _in.
This is a drafting layout, NOT a manufacturer's installation design.
"""
import math

STOCK_WIDTH_IN = 5.5
THICKNESS_IN = 0.94
SIDE_GAP_IN = 3.0 / 16.0
BUTT_GAP_IN = 1.0 / 8.0
MAX_STOCK_FT = 20.0
KERF_IN = 1.0 / 8.0


def finite_number(value, label):
    """Reject NaN/infinity before loops, geometry, or quantity calculations."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError('{0} must be a finite number.'.format(label))
    if math.isnan(number) or math.isinf(number):
        raise ValueError('{0} must be a finite number.'.format(label))
    return number


def stock_length(value):
    length = finite_number(value, 'Stock length')
    if not 0.5 <= length <= MAX_STOCK_FT:
        raise ValueError('Stock length must be from 0.5 to 20 feet.')
    return length


def plan_rows(span_ft):
    """Return [(start_v_ft, end_v_ft, groove_mode), ...].
    Balanced symmetric perimeter rips, with factory grooves only on inside.
    """
    span_ft = finite_number(span_ft, 'Deck width')
    width_in = span_ft * 12.0
    if width_in < 6.0:
        raise ValueError('Deck width must be at least 6 inches.')
    n = int(math.ceil((width_in + SIDE_GAP_IN - 1.e-8) / (STOCK_WIDTH_IN + SIDE_GAP_IN)))
    n = max(1, n)
    if n == 1:
        if width_in > STOCK_WIDTH_IN + 1.e-6:
            raise ValueError('Internal width calculation error.')
        return [(0.0, span_ft, 'square')]
    edge = (width_in - (n - 2) * STOCK_WIDTH_IN - (n - 1) * SIDE_GAP_IN) / 2.0
    if edge < 0.5 or edge > STOCK_WIDTH_IN + 1.e-5:
        raise ValueError('Perimeter rip outside supported 1/2 to 5-1/2 inch range.')
    widths = [edge] + [STOCK_WIDTH_IN] * (n - 2) + [edge]
    rows = []
    cur = 0.0
    for i, width in enumerate(widths):
        mode = 'both'
        if width < STOCK_WIDTH_IN - 0.001:
            if i == 0:
                mode = 'right'  # factory groove inward
            elif i == n-1:
                mode = 'left'
        b = cur + width / 12.0
        rows.append((cur, b, mode))
        cur = b + SIDE_GAP_IN / 12.0
    if abs(rows[-1][1] - span_ft) > 1.e-6:
        raise ValueError('Row widths do not add up to deck boundary.')
    return rows


def estimated_stations(run_ft, spacing_in=16.0):
    """Schematic joist centres. 2-inch end insets are NOT framing validation."""
    run_ft = finite_number(run_ft, 'Deck run')
    spacing_in = finite_number(spacing_in, 'Joist spacing')
    if run_ft <= 0:
        raise ValueError('Deck run must be positive.')
    if not 4.0 <= spacing_in <= 36.0:
        raise ValueError('Joist spacing must be from 4 to 36 inches.')
    inset = 2.0 / 12.0
    if run_ft <= 2.0 * inset:
        return [run_ft / 2.0]
    ret = []
    x = inset
    step = spacing_in / 12.0
    while x <= run_ft - inset + 1.e-7:
        ret.append(x)
        x += step
    if ret and run_ft - inset - ret[-1] > step * 0.55:
        ret.append(run_ft - inset)
    return ret


def full_width_stations(segments, run_ft, span_ft, tolerance_ft=0.005):
    """Only full-width perpendicular joists can back a common straight seam.

    Partial or angled members may still receive clips at actual crossings,
    but their midpoint alone is not support for every board-row butt joint.
    """
    run_ft = finite_number(run_ft, 'Deck run')
    span_ft = finite_number(span_ft, 'Deck width')
    stations = []
    for segment in segments:
        s1, t1, s2, t2 = [finite_number(x, 'Joist coordinate') for x in segment]
        if abs(s2-s1) > tolerance_ft:
            continue
        if min(t1,t2) > tolerance_ft or max(t1,t2) < span_ft-tolerance_ft:
            continue
        position = (s1+s2)/2.0
        if 0.0 < position < run_ft:
            stations.append(round(position, 6))
    return sorted(set(stations))


def joint_positions(run_ft, stations, stock_length_ft=MAX_STOCK_FT):
    """Pick butt joints at joists, with no raw segment over stock length.

    Dynamic programming prevents a locally nearest joist from making a
    downstream segment too long. Slightly more segments may be used if the
    closest framing grid cannot produce a valid split.
    """
    run_ft = finite_number(run_ft, 'Deck run')
    maximum = stock_length(stock_length_ft)
    stations = [finite_number(x, 'Joist station') for x in stations]
    if run_ft <= 0:
        raise ValueError('Deck run must be positive.')
    if run_ft <= maximum + 1.e-8:
        return []
    candidates = sorted(set([round(x, 6) for x in stations
                             if x > 1.0 and x < run_ft-1.0]))
    if not candidates:
        raise ValueError('No joist centers available for butt joints on a run exceeding {0:g}ft.'.format(maximum))
    min_n = int(math.ceil(run_ft / maximum))
    for n in range(min_n, min_n + 4):
        # Entries: previous station -> (total penalty, path)
        layer = {0.0: (0.0, [])}
        for k in range(1, n):
            target = run_ft * k / float(n)
            nxt = {}
            for x in candidates:
                if x >= run_ft - (n-k):
                    continue
                options = []
                for prev,(penalty,path) in layer.items():
                    diff = x - prev
                    if 1.0 <= diff <= maximum + 1.e-7:
                        options.append((penalty + (x-target)*(x-target),path+[x]))
                if options:
                    nxt[x] = min(options,key=lambda tup:tup[0])
            layer = nxt
            if not layer: break
        feasible = [(penalty,path) for last,(penalty,path) in layer.items()
                    if len(path)==n-1 and 1.0<=run_ft-last<=maximum+1.e-7]
        if feasible:
            return min(feasible,key=lambda pair:pair[0])[1]
    raise ValueError('No valid joist-backed segments <={0:g}ft; add blocking/joists or revise deck direction.'.format(maximum))


def piece_spans(run_ft, joints, stock_length_ft=MAX_STOCK_FT):
    run_ft = finite_number(run_ft, 'Deck run')
    maximum = stock_length(stock_length_ft)
    joints = [finite_number(x, 'Butt joint') for x in joints]
    if run_ft <= 0 or any(x <= 0 or x >= run_ft for x in joints):
        raise ValueError('Butt joints must be inside a positive deck run.')
    if joints != sorted(set(joints)):
        raise ValueError('Butt joints must be unique and in increasing order.')
    bounds = [0.0] + joints + [run_ft]
    gap = BUTT_GAP_IN / 12.0
    pieces = []
    for i in range(len(bounds)-1):
        start = bounds[i] + (gap/2.0 if i else 0.0)
        end = bounds[i+1] - (gap/2.0 if i < len(bounds)-2 else 0.0)
        if end <= start or end-start > maximum + 1.e-7:
            raise ValueError('Invalid board cut or length greater than {0:g} feet.'.format(maximum))
        pieces.append((start, end))
    return pieces


def plan(run_ft, span_ft, stations, stock_length_ft=MAX_STOCK_FT):
    run_ft = finite_number(run_ft, 'Deck run')
    span_ft = finite_number(span_ft, 'Deck width')
    maximum = stock_length(stock_length_ft)
    if run_ft < 0.5 or span_ft < 0.5:
        raise ValueError('Rectangular deck must be at least 6 inches in each direction.')
    rows = plan_rows(span_ft)
    joints = joint_positions(run_ft, stations, maximum)
    segments = piece_spans(run_ft, joints, maximum)
    boards = []
    for r, (low, high, mode) in enumerate(rows):
        for p, (s, e) in enumerate(segments):
            boards.append({'row':r+1, 'piece':p+1,
                           'start':s, 'end':e,
                           'low':low, 'high':high,
                           'width_in':(high-low)*12.0, 'length_ft':e-s,
                           'edge_mode':mode})
    seams = [(rows[i][1] + rows[i+1][0])/2.0 for i in range(len(rows)-1)]
    return {'rows':rows,'boards':boards,'seams':seams,'joints':joints,
            'stock_length_ft':maximum}


def pack_stock(boards, stock_length_ft=MAX_STOCK_FT, kerf_in=KERF_IN,
               reserve_percent=0.0):
    """First-fit decreasing estimate with a traceable stock cutting schedule.

    Group by rip width/profile; do not assume opposite rips share raw stock.
    A shortened piece consumes one saw kerf, including the last trimmed piece.
    An exact remaining-length piece needs no cut; a kerf extending past the
    stock end consumes only the remaining material. Factory end trimming and
    longitudinal rip-saw loss are not modeled. Reserve boards are rounded up
    separately in each width/profile group and are not assigned installed cuts.
    """
    maximum = stock_length(stock_length_ft)
    kerf_in = finite_number(kerf_in, 'Saw kerf')
    reserve_percent = finite_number(reserve_percent, 'Spare-board allowance')
    if not 0.0 <= kerf_in <= 1.0:
        raise ValueError('Saw kerf must be from 0 to 1 inch.')
    if not 0.0 <= reserve_percent <= 100.0:
        raise ValueError('Spare-board allowance must be from 0 to 100 percent.')
    groups = {}
    for index, b in enumerate(boards):
        width = finite_number(b['width_in'], 'Board width')
        length = finite_number(b['length_ft'], 'Cut length')
        if not 0.5 <= width <= STOCK_WIDTH_IN + 1.e-7:
            raise ValueError('Board width must be from 0.5 to 5.5 inches.')
        if b['edge_mode'] not in ('both', 'left', 'right', 'square'):
            raise ValueError('Unknown board edge profile.')
        if length <= 0 or length > maximum + 1.e-7:
            raise ValueError('Every cut must be positive and fit the selected stock length.')
        key = (round(width, 4), b['edge_mode'])
        groups.setdefault(key, []).append((index, length))
    results = []
    kerf = kerf_in / 12.0
    next_stock = 1
    for key in sorted(groups):
        bins = []
        for index, length in sorted(groups[key], key=lambda x: (-x[1], x[0])):
            target = None
            for candidate in bins:
                if length <= maximum - candidate['used_ft'] + 1.e-7:
                    target = candidate
                    break
            if target is None:
                target = {'stock_id':'S{0:04d}'.format(next_stock),
                          'stock_length_ft':maximum, 'used_ft':0.0,
                          'kerf_ft':0.0, 'pieces':[]}
                next_stock += 1
                bins.append(target)
            remaining = maximum - target['used_ft']
            loss = min(kerf, max(0.0, remaining - length))
            target['pieces'].append({'board_index':index, 'length_ft':length,
                                     'kerf_ft':loss})
            target['used_ft'] += length + loss
            target['kerf_ft'] += loss
        for item in bins:
            item['unused_ft'] = max(0.0, maximum - item['used_ft'])
        spare = int(math.ceil(len(bins) * reserve_percent / 100.0))
        results.append({'width_in':key[0], 'edge_mode':key[1],
                        'stock':len(bins), 'reserve_stock':spare,
                        'purchase_stock':len(bins)+spare,
                        'stock_length_ft':maximum, 'kerf_in':kerf_in,
                        'reserve_percent':reserve_percent,
                        'cut_ft':sum(x[1] for x in groups[key]),
                        'kerf_ft':sum(b['kerf_ft'] for b in bins),
                        'unused_ft':sum(b['unused_ft'] for b in bins),
                        'bins':bins})
    return results


def pack_20ft_stock(boards):
    """Compatibility entry point for the original layout tests."""
    return pack_stock(boards)
