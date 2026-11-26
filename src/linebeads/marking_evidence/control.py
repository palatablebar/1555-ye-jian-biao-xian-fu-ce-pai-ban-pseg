from collections import Counter
from math import isfinite


def accountable_plan(rows, actual_balance, starting_capacity):
    seen = set()
    counts = Counter()
    total = 0
    for row in rows:
        if row['key'] in seen:
            raise ArithmeticError('复核凭证的关联单号不唯一')
        key = row['key']
        seen.add(key)
        state = row['state']
        counts[state] += 1
        if state == '已分派':
            total += row['cost']
        if not isfinite(row['estimate']):
            raise ArithmeticError('非有限估计不能签发')
    if total + actual_balance != starting_capacity:
        raise ArithmeticError('处置清册与工位余额不符')
    return counts, total


def register_marking_evidence(measurements, estimate):
    retro_cd = measurements['retro_cd']
    age_days = measurements['age_days']
    wet_pct = measurements['wet_pct']
    traffic_k = measurements['traffic_k']
    beads_g = measurements['beads_g']
    surface_c = measurements['surface_c']
    return {
        '距雨夜基准反光量': round(retro_cd-140, 3),
        '整段累计车流': round(age_days*traffic_k, 3),
        '折算干面反光余量': round(retro_cd*(1+wet_pct/200), 3),
        '养护复查压力': round(age_days*wet_pct*traffic_k/10000, 3),
        '复核代价指标': round(max(0,180-retro_cd)/55 + wet_pct/80 + traffic_k/110, 4),
    }


def document_control(rows):
    register = []
    for row in rows:
        if row['state'] not in {'已分派', '暂停', '人工判读'}:
            continue
        note = register_marking_evidence(row['measurements'], row['estimate'])
        register.append({'单号': row['key'], '区段': row['zone'], '处置': row['state'], **note})
    return register
