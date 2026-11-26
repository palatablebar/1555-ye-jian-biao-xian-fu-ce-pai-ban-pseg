from bisect import bisect_right
from collections import Counter, defaultdict
from statistics import median

from .contracts import ShiftReport, ReferenceProfile
from .operating_reference import evaluate_domains


def central_gap(earlier, this_shift):
    if not earlier or not this_shift:
        return 0.
    old = sorted(earlier)
    new = sorted(this_shift)
    checkpoints = set(old).union(new)
    return max(abs(bisect_right(old,cut)/len(old) - bisect_right(new,cut)/len(new)) for cut in checkpoints)


def zone_lookup(vectors):
    result = defaultdict(list)
    for sample in vectors:
        result[sample.cohort].append(sample)
    return result


def columns(points):
    return tuple(tuple(sorted(series)) for series in zip(*(point.values for point in points),strict=True))


def fit_baseline(features, signature):
    if not len(features):
        raise ValueError('校正基准无输入')
    typical = {plant:columns(shifts) for plant,shifts in zone_lookup(features).items() if len(shifts)>=5}
    return ReferenceProfile(signature, columns(features), typical, len(features))


def scan_current(reference, observed, signature):
    if signature != reference.signature:
        raise ValueError('工区版本发生变化，需重建基准')
    if not observed:
        return ShiftReport(0,(),(),(),'NO_CURRENT_RECORDS')
    groups = zone_lookup(observed)
    unknown = tuple(sorted(groups.keys()-reference.cohorts.keys()))
    accum = dict.fromkeys(('retention', 'wet_loss', 'grain_coverage', 'traffic_exposure', 'thermal_mismatch'),0.)
    for key, units in groups.items():
        previous = reference.cohorts.get(key,reference.bands)
        lines = zip(accum,previous,columns(units),strict=True)
        for name, history, current in lines:
            accum[name] += central_gap(history,current)*len(units)/len(observed)
    watch = sorted(ticket.key for ticket in observed if ticket.cohort in unknown or len(ticket.excursions)>=2 or len(ticket.missing)>=2)
    state = 'SHIFT_REVIEW' if unknown or max(accum.values())>.48 else 'STABLE'
    return ShiftReport(len(observed),tuple(sorted(accum.items(),key=lambda x:-x[1])),unknown,tuple(watch),state)



def coverage_by_group(calibration, validation):
    past = Counter(item.cohort for item in calibration)
    current = Counter(item.cohort for item in validation)
    return tuple((key,past[key],current[key]) for key in sorted(past.keys()|current.keys()))


def shift_evidence(current, coverage):
    names = dict(zip(('retention', 'wet_loss', 'grain_coverage', 'traffic_exposure', 'thermal_mismatch'),('龄期反光余量', '车流潮湿协变', '湿面等效玻璃珠', '累计车流暴露', '温度偏离'),strict=True))
    new = set(current.novel)
    table = [{'检测项':names.get(field,field), '分区累积分布差':round(evidence,4)} for field,evidence in current.signals]
    table.extend({'检测项':unit, '校准单数':old,'本班单数':seen,'现场': '未登记' if unit in new else '已登记'}
                 for unit,old,seen in coverage)
    return table


def shop_floor_shift(reference, current):
    measures = evaluate_domains(reference,current)
    return sorted(measures,key=lambda line:(-line['越线量'],line['观察维度']))
