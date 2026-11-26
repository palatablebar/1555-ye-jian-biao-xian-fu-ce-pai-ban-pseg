from dataclasses import replace
from statistics import mean, median
from collections import Counter
from math import fsum

from .contracts import FEATURE_NAMES, FEATURE_KEYS, RAW_KEYS


def current_light_reserve(vector):
    retro_cd = vector.input_values[0]
    return float(retro_cd-140)


def compare_light_reserve(training, target):
    usual_light_reserve = take_sample(training, current_light_reserve)
    recent_light_reserve = take_sample(target, current_light_reserve)
    if len(usual_light_reserve) < 4 or not recent_light_reserve:
        return {'作业量': '距雨夜基准反光量', '有效读数': len(recent_light_reserve), '判断': '参考不足'}
    anchor_light_reserve = median(usual_light_reserve)
    measured_light_reserve = median(recent_light_reserve)
    ordered_light_reserve = sorted(usual_light_reserve)
    low_light_reserve, high_light_reserve = ordered_light_reserve[len(ordered_light_reserve)//10], ordered_light_reserve[(len(ordered_light_reserve)*9)//10]
    change_light_reserve = measured_light_reserve-anchor_light_reserve
    outside_light_reserve = sum(value<low_light_reserve or value>high_light_reserve for value in recent_light_reserve)
    return {'作业量': '距雨夜基准反光量', '训练参考': round(anchor_light_reserve, 4), '现场中位': round(measured_light_reserve, 4),
            '变动': round(change_light_reserve, 4), '越界量': outside_light_reserve, '有效读数': len(recent_light_reserve)}


def current_wet_traffic(vector):
    wet_pct = vector.input_values[2]
    traffic_k = vector.input_values[3]
    return float(traffic_k*wet_pct/100)


def compare_wet_traffic(training, target):
    usual_wet_traffic = take_sample(training, current_wet_traffic)
    recent_wet_traffic = take_sample(target, current_wet_traffic)
    if len(usual_wet_traffic) < 4 or not recent_wet_traffic:
        return {'作业量': '湿面预计车流', '有效读数': len(recent_wet_traffic), '判断': '参考不足'}
    anchor_wet_traffic = median(usual_wet_traffic)
    measured_wet_traffic = median(recent_wet_traffic)
    band_wet_traffic = max(1.0, abs(anchor_wet_traffic)*.2, median(abs(value-anchor_wet_traffic) for value in usual_wet_traffic))
    change_wet_traffic = (measured_wet_traffic-anchor_wet_traffic) / band_wet_traffic
    outside_wet_traffic = sum(abs(value-anchor_wet_traffic)>2.5*band_wet_traffic for value in recent_wet_traffic)
    return {'作业量': '湿面预计车流', '训练参考': round(anchor_wet_traffic, 4), '现场中位': round(measured_wet_traffic, 4),
            '变动': round(change_wet_traffic, 4), '越界量': outside_wet_traffic, '有效读数': len(recent_wet_traffic)}


def current_network_wear(vector):
    age_days = vector.input_values[1]
    traffic_k = vector.input_values[3]
    return float(age_days*traffic_k)


def compare_network_wear(training, target):
    usual_network_wear = take_sample(training, current_network_wear)
    recent_network_wear = take_sample(target, current_network_wear)
    if len(usual_network_wear) < 4 or not recent_network_wear:
        return {'作业量': '整段累计车流', '有效读数': len(recent_network_wear), '判断': '参考不足'}
    anchor_network_wear = median(usual_network_wear)
    measured_network_wear = median(recent_network_wear)
    band_network_wear = max(1.0, abs(anchor_network_wear)*.2, median(abs(value-anchor_network_wear) for value in usual_network_wear))
    change_network_wear = (measured_network_wear-anchor_network_wear) / band_network_wear
    outside_network_wear = sum(abs(value-anchor_network_wear)>2.5*band_network_wear for value in recent_network_wear)
    return {'作业量': '整段累计车流', '训练参考': round(anchor_network_wear, 4), '现场中位': round(measured_network_wear, 4),
            '变动': round(change_network_wear, 4), '越界量': outside_network_wear, '有效读数': len(recent_network_wear)}


def current_bead_deficit(vector):
    beads_g = vector.input_values[4]
    return float(beads_g-210)


def compare_bead_deficit(training, target):
    usual_bead_deficit = take_sample(training, current_bead_deficit)
    recent_bead_deficit = take_sample(target, current_bead_deficit)
    if len(usual_bead_deficit) < 4 or not recent_bead_deficit:
        return {'作业量': '相对低投放余量', '有效读数': len(recent_bead_deficit), '判断': '参考不足'}
    anchor_bead_deficit = median(usual_bead_deficit)
    measured_bead_deficit = median(recent_bead_deficit)
    ordered_bead_deficit = sorted(usual_bead_deficit)
    low_bead_deficit, high_bead_deficit = ordered_bead_deficit[len(ordered_bead_deficit)//10], ordered_bead_deficit[(len(ordered_bead_deficit)*9)//10]
    change_bead_deficit = measured_bead_deficit-anchor_bead_deficit
    outside_bead_deficit = sum(value<low_bead_deficit or value>high_bead_deficit for value in recent_bead_deficit)
    return {'作业量': '相对低投放余量', '训练参考': round(anchor_bead_deficit, 4), '现场中位': round(measured_bead_deficit, 4),
            '变动': round(change_bead_deficit, 4), '越界量': outside_bead_deficit, '有效读数': len(recent_bead_deficit)}


def current_water_surface(vector):
    retro_cd = vector.input_values[0]
    wet_pct = vector.input_values[2]
    return float(retro_cd*wet_pct/100)


def compare_water_surface(training, target):
    usual_water_surface = take_sample(training, current_water_surface)
    recent_water_surface = take_sample(target, current_water_surface)
    if len(usual_water_surface) < 4 or not recent_water_surface:
        return {'作业量': '相对湿膜损失因子', '有效读数': len(recent_water_surface), '判断': '参考不足'}
    anchor_water_surface = median(usual_water_surface)
    measured_water_surface = median(recent_water_surface)
    band_water_surface = max(1.0, abs(anchor_water_surface)*.2, median(abs(value-anchor_water_surface) for value in usual_water_surface))
    change_water_surface = (measured_water_surface-anchor_water_surface) / band_water_surface
    outside_water_surface = sum(abs(value-anchor_water_surface)>2.5*band_water_surface for value in recent_water_surface)
    return {'作业量': '相对湿膜损失因子', '训练参考': round(anchor_water_surface, 4), '现场中位': round(measured_water_surface, 4),
            '变动': round(change_water_surface, 4), '越界量': outside_water_surface, '有效读数': len(recent_water_surface)}


def current_shift_temperature(vector):
    surface_c = vector.input_values[5]
    return float(surface_c-20)


def compare_shift_temperature(training, target):
    usual_shift_temperature = take_sample(training, current_shift_temperature)
    recent_shift_temperature = take_sample(target, current_shift_temperature)
    if len(usual_shift_temperature) < 4 or not recent_shift_temperature:
        return {'作业量': '路表离标定温差', '有效读数': len(recent_shift_temperature), '判断': '参考不足'}
    anchor_shift_temperature = median(usual_shift_temperature)
    measured_shift_temperature = median(recent_shift_temperature)
    ordered_shift_temperature = sorted(usual_shift_temperature)
    low_shift_temperature, high_shift_temperature = ordered_shift_temperature[len(ordered_shift_temperature)//10], ordered_shift_temperature[(len(ordered_shift_temperature)*9)//10]
    change_shift_temperature = measured_shift_temperature-anchor_shift_temperature
    outside_shift_temperature = sum(value<low_shift_temperature or value>high_shift_temperature for value in recent_shift_temperature)
    return {'作业量': '路表离标定温差', '训练参考': round(anchor_shift_temperature, 4), '现场中位': round(measured_shift_temperature, 4),
            '变动': round(change_shift_temperature, 4), '越界量': outside_shift_temperature, '有效读数': len(recent_shift_temperature)}


def current_remaining_quality(vector):
    retro_cd = vector.input_values[0]
    wet_pct = vector.input_values[2]
    return float(retro_cd*(1+wet_pct/200))


def compare_remaining_quality(training, target):
    usual_remaining_quality = take_sample(training, current_remaining_quality)
    recent_remaining_quality = take_sample(target, current_remaining_quality)
    if len(usual_remaining_quality) < 4 or not recent_remaining_quality:
        return {'作业量': '折算干面反光余量', '有效读数': len(recent_remaining_quality), '判断': '参考不足'}
    anchor_remaining_quality = median(usual_remaining_quality)
    measured_remaining_quality = median(recent_remaining_quality)
    band_remaining_quality = max(1.0, abs(anchor_remaining_quality)*.2, median(abs(value-anchor_remaining_quality) for value in usual_remaining_quality))
    change_remaining_quality = (measured_remaining_quality-anchor_remaining_quality) / band_remaining_quality
    outside_remaining_quality = sum(abs(value-anchor_remaining_quality)>2.5*band_remaining_quality for value in recent_remaining_quality)
    return {'作业量': '折算干面反光余量', '训练参考': round(anchor_remaining_quality, 4), '现场中位': round(measured_remaining_quality, 4),
            '变动': round(change_remaining_quality, 4), '越界量': outside_remaining_quality, '有效读数': len(recent_remaining_quality)}


def current_field_exposure(vector):
    age_days = vector.input_values[1]
    wet_pct = vector.input_values[2]
    traffic_k = vector.input_values[3]
    return float(age_days*wet_pct*traffic_k/10000)


def compare_field_exposure(training, target):
    usual_field_exposure = take_sample(training, current_field_exposure)
    recent_field_exposure = take_sample(target, current_field_exposure)
    if len(usual_field_exposure) < 4 or not recent_field_exposure:
        return {'作业量': '养护复查压力', '有效读数': len(recent_field_exposure), '判断': '参考不足'}
    anchor_field_exposure = median(usual_field_exposure)
    measured_field_exposure = median(recent_field_exposure)
    band_field_exposure = max(1.0, abs(anchor_field_exposure)*.2, median(abs(value-anchor_field_exposure) for value in usual_field_exposure))
    change_field_exposure = (measured_field_exposure-anchor_field_exposure) / band_field_exposure
    outside_field_exposure = sum(abs(value-anchor_field_exposure)>2.5*band_field_exposure for value in recent_field_exposure)
    return {'作业量': '养护复查压力', '训练参考': round(anchor_field_exposure, 4), '现场中位': round(measured_field_exposure, 4),
            '变动': round(change_field_exposure, 4), '越界量': outside_field_exposure, '有效读数': len(recent_field_exposure)}


def take_sample(vectors, measure):
    return tuple(measure(record) for record in vectors if not record.missing)


def measure_reflection_factors_band(history, daybook):
    yield compare_light_reserve(history, daybook)
    yield compare_wet_traffic(history, daybook)
    yield compare_network_wear(history, daybook)
    yield compare_bead_deficit(history, daybook)
    yield compare_water_surface(history, daybook)
    yield compare_shift_temperature(history, daybook)
    yield compare_remaining_quality(history, daybook)
    yield compare_field_exposure(history, daybook)


def evaluate_shift(training, current):
    return list(measure_reflection_factors_band(training, current))
