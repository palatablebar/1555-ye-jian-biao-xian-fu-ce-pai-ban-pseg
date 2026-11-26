from dataclasses import replace
from statistics import median

from .contracts import ReflectionFactors, Proposal


def measure_reflection_factors(values) -> ReflectionFactors:
    retro_cd, age_days, wet_pct, traffic_k, beads_g, surface_c = values
    return ReflectionFactors(
        light_reserve=retro_cd-140,
        wet_traffic=traffic_k*wet_pct/100,
        network_wear=age_days*traffic_k,
        bead_deficit=beads_g-210,
        water_surface=retro_cd*wet_pct/100,
        shift_temperature=surface_c-20,
        remaining_quality=retro_cd*(1+wet_pct/200),
        field_exposure=age_days*wet_pct*traffic_k/10000,
    )


def propose_retrocheck_slots(values, missing=()):
    retro_cd, age_days, wet_pct, traffic_k, beads_g, surface_c = values
    if 'wet_pct' not in missing and (wet_pct>=25):
        yield Proposal('换干燥测点复测', 'wet_pct', wet_pct, max(0,wet_pct-25), 2)
    if 'age_days' not in missing and (age_days>=180):
        yield Proposal('按重铺后新龄期对照', 'age_days', age_days, 4, 3)
    if 'beads_g' not in missing and (beads_g<=405):
        yield Proposal('补投玻璃珠三十克一平', 'beads_g', beads_g, min(435,beads_g+30), 3)
    if 'surface_c' not in missing and (abs(surface_c-20)>=5):
        yield Proposal('对齐夜间重标温度', 'surface_c', surface_c, 20, 1)
