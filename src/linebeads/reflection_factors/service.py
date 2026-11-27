from dataclasses import replace
from hashlib import sha256
from math import fsum, sqrt, isfinite
from statistics import median

from .measurement_bands import evaluate_shift
from .contracts import PreparedRuns, FeatureState, FeatureVector, Imputation, FEATURE_KEYS, FEATURE_RAW_INPUTS, RAW_KEYS

# 同区成熟记录少于此数时退用全班历史中位，并在审查中标记同区覆盖不足。
ZONE_FILL_MIN_RECORDS = 5


def derive(values):
    retro_cd, age_days, wet_pct, traffic_k, beads_g, surface_c = values
    retention = retro_cd/(1+age_days/140)
    wet_loss = wet_pct*traffic_k/100
    grain_coverage = beads_g/(1+wet_pct/70)
    traffic_exposure = age_days*traffic_k/1000
    thermal_mismatch = abs(surface_c-20)
    return retention, wet_loss, grain_coverage, traffic_exposure, thermal_mismatch


def spread(samples):
    if not samples:
        raise ValueError('量测列为空')
    mean = running_variance = 0.
    ordered = sorted(samples)
    clamp = len(ordered)//20
    lo,hi=ordered[clamp],ordered[-clamp-1]
    for counted, point in enumerate(ordered,start=1):
        clipped=min(hi,max(lo,point))
        delta=clipped-mean
        mean += delta/counted
        running_variance += delta*(clipped-mean)
    return mean,sqrt(running_variance / len(samples)) if running_variance > 1e-14 else 1.


def lookup_fills(complete):
    table = {}
    for name in RAW_KEYS:
        series = sorted(field for field in (getattr(item,name) for item in complete) if field is not None)
        if len(series)==0:
            raise ValueError(f'{name} 缺少可估计的历史中位数')
        table[name] = median(series)
    return tuple(table.values())


def zone_fills(records):
    """Freeze per-zone medians from mature history only.

    A zone column is usable only when at least ``ZONE_FILL_MIN_RECORDS`` mature
    records observed it; otherwise the ticket falls back to the pooled median.
    Coverage counts travel with the table so the review can explain the choice.
    """
    by_zone = {}
    for record in records:
        by_zone.setdefault(record.cohort, []).append(record)
    table = []
    for name in sorted(by_zone):
        rows = by_zone[name]
        values = []
        counts = []
        for key in RAW_KEYS:
            series = sorted(field for field in (getattr(row,key) for row in rows) if field is not None)
            counts.append(len(series))
            values.append(median(series) if len(series)>=ZONE_FILL_MIN_RECORDS else None)
        table.append((name, tuple(values), tuple(counts)))
    return tuple(table)


def fill_plan(record, fill, zones):
    """Select the fill basis for every missing field from frozen coverage.

    The basis is:
    * ``ZONE`` — same-zone mature median, chosen when the zone observed that
      field at least ``ZONE_FILL_MIN_RECORDS`` times;
    * ``COHORT`` — pooled historical median when same-zone coverage is thin.

    Fit and inference both call this with the frozen state, so the basis version
    cannot drift between training and serving.
    """
    picks = {}
    for slot, name in enumerate(RAW_KEYS):
        if getattr(record, name) is not None:
            continue
        zone_values, counts = zones.get(record.cohort, (None, (0,)*len(RAW_KEYS)))
        if zone_values is not None and zone_values[slot] is not None:
            picks[name] = (zone_values[slot], 'ZONE', counts[slot])
        else:
            picks[name] = (fill[slot], 'COHORT', counts[slot])
    return picks


def prepare_readings(row, fill, zones):
    sensor = {name:getattr(row,name) for name in RAW_KEYS}
    absent = tuple(name for name,reading in sensor.items() if reading is None)
    picks = fill_plan(row, fill, zones)
    values = tuple(sensor[name] if name not in picks else picks[name][0]
                   for name in RAW_KEYS)
    fills = tuple(Imputation(name, *picks[name]) for name in RAW_KEYS if name in picks)
    return values, absent, fills


def outside_envelope(index, amount, limits):
    delta = limits.scales[index]
    return amount < limits.floor[index]-.9*delta or amount > limits.ceil[index]+.9*delta


def adjudicate_fills(fills, values, reference):
    """Attach a dispatch-hold verdict to each fill from zone coverage and envelope.

    The basis is adjudicated, not the observed data:

    * a fill whose field lands a *consuming* feature outside the frozen training
      envelope is held as ``FILL_EXCEEDS_TRAINING_RANGE`` — the imputed value
      cannot be trusted, and dispatching on it could hide a low-reflectance
      segment behind a normal-looking estimate;
    * a fill that had to fall back to the pooled median is held as
      ``FILL_ZONE_COVERAGE_LOW``.

    Both checks depend only on the frozen state and the ticket's own observed
    fields, so the verdict is identical across reruns and batch groupings.
    """
    physical = derive(values)
    verdicts = []
    for fill in fills:
        if fill.basis == 'COHORT':
            verdicts.append(replace(fill, verdict='FILL_ZONE_COVERAGE_LOW'))
            continue
        pushed = any(
            fill.field in FEATURE_RAW_INPUTS[FEATURE_KEYS[index]] and outside_envelope(index, physical[index], reference)
            for index in range(len(FEATURE_KEYS))
        )
        verdicts.append(replace(fill, verdict='FILL_EXCEEDS_TRAINING_RANGE' if pushed else None))
    return tuple(verdicts)


def fit_features(training):
    records=tuple(sorted(training,key=lambda item:(item.cohort,item.day,item.key)))
    calibration=lookup_fills(records)
    table=zone_fills(records)
    zones={name:(values,counts) for name,values,counts in table}
    processed=(derive(prepare_readings(note,calibration,zones)[0]) for note in records)
    labels=tuple(zip(*processed,strict=True))
    centers,scales=zip(*(spread(column) for column in labels),strict=True)
    ranges=tuple((min(column),max(column)) for column in labels)
    fill_version=sha256(repr((RAW_KEYS,calibration,table)).encode()).hexdigest()[:12]
    key_data='\n'.join(repr(sample.signature()) for sample in records)
    digest=sha256((repr((RAW_KEYS,FEATURE_KEYS,centers,scales,ranges,fill_version,table))+key_data).encode()).hexdigest()
    return FeatureState(calibration,table,centers,scales,tuple(low for low,_ in ranges),tuple(high for _,high in ranges),fill_version,digest[:16])


def numeric_fields(values, limits):
    measured=derive(values)
    envelope={}
    features=[]
    for i, amount in enumerate(measured):
        delta=limits.scales[i]
        value=(amount-limits.offsets[i])/delta
        if not isfinite(value):
            raise ValueError('截尾标准值无效')
        envelope[FEATURE_KEYS[i]] = amount < limits.floor[i]-.9*delta or amount > limits.ceil[i]+.9*delta
        features.append(min(12.,max(-12.,value)))
    return tuple(features),measured,tuple(field for field,triggered in envelope.items() if triggered)


def transform(record, reference):
    zones={name:(values,counts) for name,values,counts in reference.zone_fill}
    fixed, absent, fills=prepare_readings(record,reference.fill,zones)
    normalized, physical, attention=numeric_fields(fixed,reference)
    verdicts=adjudicate_fills(fills,fixed,reference)
    return FeatureVector(record.key,record.cohort,record.day,normalized,physical,absent,attention,record.outcome,record.observed,fixed,verdicts)


def transform_all(observations, reference):
    return tuple(map(lambda row:transform(row,reference),observations))


def transform_windows(windows, reference):
    return PreparedRuns(*(transform_all(records, reference) for _, records in windows.partitions()))


def feature_evidence(reference):
    return [{'特征': name,'中心':round(center,3),'尺度':round(scale,3),'训练最小':round(low,3),'训练最大':round(high,3)}
            for name,center,scale,low,high in zip(FEATURE_KEYS,reference.offsets,reference.scales,reference.floor,reference.ceil,strict=True)]


def fill_basis_evidence(reference):
    """Frozen imputation basis: pooled medians plus per-zone coverage counts."""
    rows = [{'补值依据': '全班历史中位', '分区': '全部', '字段': name, '中位': round(value, 4), '成熟记录': None}
            for name, value in zip(RAW_KEYS, reference.fill, strict=True)]
    for zone, values, counts in reference.zone_fill:
        for name, value, count in zip(RAW_KEYS, values, counts, strict=True):
            adopted = '同区中位' if value is not None else '覆盖不足，沿用全班中位'
            rows.append({'补值依据': adopted, '分区': zone, '字段': name,
                         '中位': None if value is None else round(value, 4), '成熟记录': count})
    return rows


def fill_review_evidence(features):
    """Per-fill imputation verdict for the current live shift."""
    rows = []
    for point in features.live:
        for fill in point.fills:
            rows.append({'单号': point.key, '作业区': point.cohort, '缺测字段': '、'.join(point.missing),
                         **fill.evidence()})
    return rows


def render_interventions(vector, reference, score):
    from .interventions import propose_retrocheck_slots

    records = []
    estimate = score(vector)
    for adjustment in propose_retrocheck_slots(vector.input_values, vector.missing):
        position=RAW_KEYS.index(adjustment.field)
        modified=tuple(adjustment.after if position==slot else part for slot,part in enumerate(vector.input_values))
        values, factors, flags = numeric_fields(modified,reference)
        alternative=replace(vector,values=values,factors=factors,input_values=modified,excursions=flags)
        revised=score(alternative)
        records.append({**adjustment.evidence(),'原预测':round(estimate,4),'替换预测':round(revised,4),
                        '预测变化':round(revised-estimate,4),'超训练域':bool(flags)})
    return records


def business_factors(vector):
    from .interventions import measure_reflection_factors

    return measure_reflection_factors(vector.input_values).explain()


def measure_review(features):
    return evaluate_shift(features.train, features.live)


def render_joint_experiments(vector, reference, score):
    from .joint import options

    raw = vector.input_values
    base = score(vector)
    replies=[]
    for action in options(raw,vector.missing):
        adjusted = tuple(action.changes[key][1] if key in action.changes else value for key,value in zip(RAW_KEYS,raw,strict=True))
        normalized, measured, signals=numeric_fields(adjusted,reference)
        scenario=replace(vector,values=normalized,input_values=adjusted,factors=measured,excursions=signals)
        replies.append(action.evidence(base,score(scenario),signals))
    return replies
