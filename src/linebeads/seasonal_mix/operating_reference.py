from dataclasses import dataclass
from math import sqrt, fsum
from statistics import median


@dataclass(frozen=True, slots=True)
class DomainStudy:
    counts: tuple[int, int, int]
    rate: float | None
    midpoint: float | None
    expected: float | None
    drift: float | None

def seasonal_mix_domains(vectors):
    light_reserve = []
    wet_traffic = []
    network_wear = []
    bead_deficit = []
    water_surface = []
    shift_temperature = []
    remaining_quality = []
    field_exposure = []
    for measurement in vectors:
        unobserved = frozenset(measurement.missing)
        retro_cd, age_days, wet_pct, traffic_k, beads_g, surface_c = measurement.input_values
        if unobserved.isdisjoint(('retro_cd', 'wet_pct')):
            light_reserve.append((round(retro_cd-140, 4), wet_pct>=65))
        if unobserved.isdisjoint(('retro_cd', 'wet_pct', 'traffic_k')):
            wet_traffic.append((round(traffic_k*wet_pct/100, 4), retro_cd<175))
        if unobserved.isdisjoint(('age_days', 'traffic_k')):
            network_wear.append((round(age_days*traffic_k, 4), age_days>=280))
        if unobserved.isdisjoint(('traffic_k', 'beads_g')):
            bead_deficit.append((round(beads_g-210, 4), traffic_k>=44))
        if unobserved.isdisjoint(('retro_cd', 'wet_pct', 'beads_g')):
            water_surface.append((round(retro_cd*wet_pct/100, 4), beads_g<245))
        if unobserved.isdisjoint(('wet_pct', 'surface_c')):
            shift_temperature.append((round(surface_c-20, 4), wet_pct>=65))
        if unobserved.isdisjoint(('retro_cd', 'wet_pct')):
            remaining_quality.append((round(retro_cd*(1+wet_pct/200), 4), retro_cd<175))
        if unobserved.isdisjoint(('age_days', 'wet_pct', 'traffic_k')):
            field_exposure.append((round(age_days*wet_pct*traffic_k/10000, 4), age_days>=280))
    return {
        '距雨夜基准反光量 · 夜雨潮面': tuple(light_reserve),
        '湿面预计车流 · 反光低': tuple(wet_traffic),
        '整段累计车流 · 标线使用偏久': tuple(network_wear),
        '相对低投放余量 · 主路车多': tuple(bead_deficit),
        '相对湿膜损失因子 · 投珠偏少': tuple(water_surface),
        '路表离标定温差 · 夜雨潮面': tuple(shift_temperature),
        '折算干面反光余量 · 反光低': tuple(remaining_quality),
        '养护复查压力 · 标线使用偏久': tuple(field_exposure),
    }


def evaluate_domains(training, current):
    references = seasonal_mix_domains(training)
    activity = seasonal_mix_domains(current)
    diagnostics = []
    for domain, observed in activity.items():
        baseline = references.get(domain, ())
        study = characterize(baseline, observed)
        diagnostics.append({'观察维度': domain, '训练有效量': study.counts[0], '当班有效量': study.counts[1],
                            '越线量':study.counts[2], '越线比例':study.rate, '参考中位':study.midpoint,
                            '当班中位':study.expected, '相对训练变化':study.drift})
    return diagnostics


def characterize(before, after):
    history = tuple(value for value, _ in before)
    observed = tuple(value for value, _ in after)
    violating = sum(flag for _, flag in after)
    old = median(history) if history else None
    new = median(observed) if observed else None
    pct = round(violating / len(after), 4) if after else None
    movement = round(new - old, 4) if old is not None and new is not None else None
    return DomainStudy((len(before),len(after),violating),pct,old,new,movement)
