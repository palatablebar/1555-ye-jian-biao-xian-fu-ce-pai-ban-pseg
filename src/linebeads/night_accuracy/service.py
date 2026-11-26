from math import ceil, isfinite, fsum, sqrt
from statistics import median

from .contracts import Verification, Assessment, ModelReport
from .slices import replay_slices


def physical_residual_scale(point):
    return max(2., 1.+point.input_values[2]/18)


def ranked_error(samples, coverage):
    if not 0 < coverage < 1:
        raise ValueError('区间比例必须处于开区间 (0,1)')
    catalogue = sorted(samples,reverse=True)
    last = len(catalogue)
    position = max(0,last-ceil((last+1)*coverage))
    return catalogue[position] if last else None


def gauge_reference(observations, coverage):
    expected = []
    potential = []
    for instrument in observations:
        if not instrument.observed or instrument.outcome is None:
            continue
        reading, book = instrument.score, instrument.outcome
        if not isfinite(reading) or not isfinite(book):
            raise ValueError('仪表复测必须有有限误差')
        scale = physical_residual_scale(instrument)
        divergence = (reading-book)/scale
        expected.append(max(0.,divergence))
        potential.append(max(0.,-divergence))
    if not expected:
        return Verification('sparse-interval',(),0,None)
    outer_calibration = ranked_error(potential,max(coverage,.92))
    inner_calibration = ranked_error(expected,max(coverage,.80))
    return Verification('night_wetness_bounds',(inner_calibration,outer_calibration),len(expected),None)


def prepare_verification(pairs, *, coverage=.85):
    return gauge_reference(pairs,coverage)


def check_point(scored, bounds):
    if scored.score < 0 or not isfinite(scored.score):
        raise ValueError('仪表预测须为有限非负读数')
    if bounds.size == 0:
        return Assessment(scored,scored.score,None,None,True)
    inner,outer = bounds.parameters
    scale = physical_residual_scale(scored)
    limits = max(0.,scored.score-inner*scale), scored.score+outer*scale
    return Assessment(scored,scored.score,*limits,False)


def validate_predictions(scored, prepared):
    measured = []
    for readings in scored:
        measured.append(check_point(readings,prepared))
    return tuple(measured)


def performance(assessments):
    count = 0
    agrees = 0
    banded = 0
    residuals = []
    for batch in assessments:
        truth = batch.raw.outcome
        if truth is None or not batch.raw.observed:
            continue
        count += 1
        residuals.append(batch.estimate-truth)
        if batch.upper is not None:
            banded += 1
            agrees += batch.lower <= truth <= batch.upper
    if count == 0:
        return ModelReport('NO_MATURE_RESULT',0,None,None,(),None)
    squared_error = fsum(residual*residual for residual in residuals)
    covered = agrees/banded if banded else None
    return ModelReport('READY',count,fsum(map(abs,residuals))/count,sqrt(squared_error/count),(),covered)


def calibration_evidence(report):
    return [{'核验':report.status,'复测实绩':report.count,'测量绝对误差':report.mae,
             '残差均方根':report.error,'复测区间通过率':report.auxiliary}]


def sector_replay(checked, line):
    return replay_slices(checked,line)


def boundary_diagnostics(checks, threshold):
    under = []
    over = []
    actual_cases = 0
    predicted_cases = 0
    for judgement in checks:
        reference = judgement.raw.outcome
        if not judgement.raw.observed or reference is None:
            continue
        actual_cases += reference>=threshold
        predicted_cases += judgement.estimate>=threshold
        if judgement.estimate < threshold <= reference:
            under.append(reference-judgement.estimate)
        if reference < threshold <= judgement.estimate:
            over.append(judgement.estimate-reference)
    return {'临界判断':'反光衰减','实绩超线':actual_cases,'估计超线':predicted_cases,
            '额外复测':len(over),'漏查':len(under),'漏查偏差中位':median(under) if under else None,
            '额外复测偏差中位':median(over) if over else None}
