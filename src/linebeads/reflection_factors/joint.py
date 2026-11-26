from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JointAction:
    case: str
    work_units: int
    notes: str
    changes: dict[str, tuple[float, float]]

    def evidence(self, old_value, new_value, extrapolates):
        return {'联动推演':self.case, '用量':self.work_units, '先决条件':self.notes,
                '原预测':round(old_value,4), '替换预测':round(new_value,4),
                '变化':round(new_value-old_value,4), '超训练域':bool(extrapolates),
                '联动量测':{item:{'原值':before,'替换值':after} for item,(before,after) in self.changes.items()}}


def simulate_dry_segment_rescan(readings, invalid):
    retro_cd, wet_pct = readings[0], readings[2]
    if invalid.intersection(('retro_cd', 'wet_pct')):
        return None
    if not (wet_pct>=27 and retro_cd<=480):
        return None
    wet_pct_adjusted = wet_pct-25
    retro_cd_adjusted = retro_cd+30
    inspected = {
        'wet_pct': (wet_pct, wet_pct_adjusted),
        'retro_cd': (retro_cd, retro_cd_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('干面同线复测', 2, '同参照点避开积水边缘', inspected)
    return None


def simulate_replace_worn_patch(readings, invalid):
    age_days, beads_g = readings[1], readings[4]
    if invalid.intersection(('age_days', 'beads_g')):
        return None
    if not (age_days>=180 and beads_g<=401):
        return None
    age_days_adjusted = 4
    beads_g_adjusted = beads_g+30
    inspected = {
        'age_days': (age_days, age_days_adjusted),
        'beads_g': (beads_g, beads_g_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('复铺加玻璃珠', 3, '新修段进入复测队', inspected)
    return None


def simulate_move_lane_sample(readings, invalid):
    wet_pct, traffic_k = readings[2], readings[3]
    if invalid.intersection(('wet_pct', 'traffic_k')):
        return None
    if not (traffic_k>=25 and wet_pct>=21):
        return None
    traffic_k_adjusted = traffic_k-16
    wet_pct_adjusted = wet_pct-18
    inspected = {
        'traffic_k': (traffic_k, traffic_k_adjusted),
        'wet_pct': (wet_pct, wet_pct_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('换低车流测位', 2, '将差异测点挪出积水轮迹', inspected)
    return None


def simulate_realign_night_sensor(readings, invalid):
    wet_pct, surface_c = readings[2], readings[5]
    if invalid.intersection(('wet_pct', 'surface_c')):
        return None
    if not (abs(surface_c-20)>=5 and wet_pct>=20):
        return None
    surface_c_adjusted = 20
    wet_pct_adjusted = wet_pct-17
    inspected = {
        'surface_c': (surface_c, surface_c_adjusted),
        'wet_pct': (wet_pct, wet_pct_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('温差和潮面复标', 2, '核对温度校准与反光采样位置', inspected)
    return None


def simulate_bead_extra_recheck(readings, invalid):
    retro_cd, beads_g = readings[0], readings[4]
    if invalid.intersection(('retro_cd', 'beads_g')):
        return None
    if not (beads_g<=377 and retro_cd<=465):
        return None
    beads_g_adjusted = beads_g+47
    retro_cd_adjusted = retro_cd+38
    inspected = {
        'beads_g': (beads_g, beads_g_adjusted),
        'retro_cd': (retro_cd, retro_cd_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('低反光点补投', 3, '补前补后记下颗粒班次', inspected)
    return None


def options(values, missing):
    measurements=tuple(values)
    unobserved=frozenset(missing)
    cases=(
        simulate_dry_segment_rescan(measurements, unobserved),
        simulate_replace_worn_patch(measurements, unobserved),
        simulate_move_lane_sample(measurements, unobserved),
        simulate_realign_night_sensor(measurements, unobserved),
        simulate_bead_extra_recheck(measurements, unobserved),
    )
    return tuple(action for action in cases if action is not None)
