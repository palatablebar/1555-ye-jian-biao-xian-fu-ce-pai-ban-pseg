from dataclasses import replace
from hashlib import sha256
from math import fsum, sqrt, isfinite
from statistics import median

from .measurement_bands import evaluate_shift
from .contracts import PreparedRuns, FeatureState, FeatureVector, FEATURE_KEYS, RAW_KEYS


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


def prepare_readings(row, fixes):
    sensor = {name:getattr(row,name) for name in RAW_KEYS}
    absent = tuple(name for name,reading in sensor.items() if reading is None)
    values = tuple(sensor[name] if name not in absent else fixes[slot] for slot,name in enumerate(RAW_KEYS))
    return values,absent


def fit_features(training):
    records=tuple(sorted(training,key=lambda item:(item.cohort,item.day,item.key)))
    calibration=lookup_fills(records)
    processed=(derive(prepare_readings(note,calibration)[0]) for note in records)
    labels=tuple(zip(*processed,strict=True))
    centers,scales=zip(*(spread(column) for column in labels),strict=True)
    ranges=tuple((min(column),max(column)) for column in labels)
    key_data='\n'.join(repr(sample.signature()) for sample in records)
    digest=sha256((repr((RAW_KEYS,FEATURE_KEYS,centers,scales,ranges))+key_data).encode()).hexdigest()
    return FeatureState(calibration,centers,scales,tuple(low for low,_ in ranges),tuple(high for _,high in ranges),digest[:16])


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
    fixed, absent=prepare_readings(record,reference.fill)
    normalized, physical, attention=numeric_fields(fixed,reference)
    return FeatureVector(record.key,record.cohort,record.day,normalized,physical,absent,attention,record.outcome,record.observed,fixed)


def transform_all(observations, reference):
    return tuple(map(lambda row:transform(row,reference),observations))


def transform_windows(windows, reference):
    return PreparedRuns(*(transform_all(records, reference) for _, records in windows.partitions()))


def feature_evidence(reference):
    return [{'特征': name,'中心':round(center,3),'尺度':round(scale,3),'训练最小':round(low,3),'训练最大':round(high,3)}
            for name,center,scale,low,high in zip(FEATURE_KEYS,reference.offsets,reference.scales,reference.floor,reference.ceil,strict=True)]


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
