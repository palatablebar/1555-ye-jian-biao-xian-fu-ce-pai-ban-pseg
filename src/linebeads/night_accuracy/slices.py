from bisect import bisect_left
from collections import defaultdict
from statistics import median


def groups_for_night_accuracy(raw):
    retro_cd, age_days, wet_pct, traffic_k, beads_g, surface_c = raw
    if wet_pct>=65:
        yield '夜雨潮面'
    if retro_cd<175:
        yield '反光低'
    if age_days>=280:
        yield '标线使用偏久'
    if traffic_k>=44:
        yield '主路车多'
    if beads_g<245:
        yield '投珠偏少'

def shift_residue(assessment, limit):
    readback = assessment.raw.outcome
    if readback is None or not assessment.raw.observed:
        return None
    error = assessment.estimate - readback
    decision_gap = readback >= limit and assessment.estimate < limit
    rushed_gauge = readback < limit and assessment.estimate >= limit
    spread = None if assessment.lower is None else assessment.upper-assessment.lower
    return abs(error), decision_gap, rushed_gauge, spread


def frequency_quantile(samples, share):
    # Nearest-rank used for the small workpiece batches on the shop floor.
    ordered = sorted(samples)
    counts = range(1,len(ordered)+1)
    select = bisect_left(counts,len(ordered)*share)
    return ordered[min(select,len(ordered)-1)]


def replay_slices(points, threshold, *, risk_model=False):
    records = defaultdict(list)
    for sample in points:
        differences = shift_residue(sample,threshold)
        if differences is None:
            continue
        lot_groups = groups_for_night_accuracy(sample.raw.input_values)
        for group in lot_groups:
            records[group].append(differences)
    report = []
    for tooling in ('夜雨潮面', '反光低', '标线使用偏久', '主路车多', '投珠偏少'):
        findings = records[tooling]
        if findings:
            magnitudes, missed, extra, widths = zip(*findings,strict=True)
            known = [width for width in widths if width is not None]
            report.append({'难点':tooling,'实绩数':len(magnitudes),'90% 绝对残差':round(frequency_quantile(magnitudes,.9),4),
                           '误放信号':sum(missed),'追加复测信号':sum(extra),'残差区间宽度中位':round(median(known),3) if known else None})
        else:
            report.append({'难点':tooling,'实绩数':0,'状态':'等待现场返读'})
    return report
