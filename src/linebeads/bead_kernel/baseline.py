from collections import defaultdict
from math import fabs, fsum
from statistics import mean, median

from .radius_model import score_kernel


def street_reference(history):
    buffer=defaultdict(list)
    for sample in history:
        source=(sample.cohort,sample.input_values[2]>=43)
        buffer[source].append(sample.outcome)
    return {key:median(samples) for key,samples in buffer.items()},median(point.outcome for point in history)


def wet_dry_median(store,inspection):
    archive, usual=store
    weather=inspection.input_values[2]>=43
    return archive.get((inspection.cohort,weather),usual)


def baseline_review(fit, training, replay):
    convention = street_reference(training)
    production = defaultdict(list)
    for sample in replay:
        if not sample.observed or sample.outcome is None:
            continue
        estimate, _ = score_kernel(fit.parameters,sample)
        baseline = wet_dry_median(convention, sample)
        actual = sample.outcome
        loss, prior = abs(actual-estimate),abs(actual-baseline)
        production[sample.cohort].append((loss,prior,estimate-actual,baseline-actual))
    reports = []
    for sector, comparison in sorted(production.items()):
        model_loss, base_loss, error, original = zip(*comparison,strict=True)
        paired = tuple(old-new for old,new in zip(base_loss,model_loss,strict=True))
        n = len(comparison)
        reports.append({'回放组':sector,'实绩数':n,'基线':'按路段历史反光衰减中位','估计代价':round(mean(model_loss),4),
                        '业务基线代价':round(mean(base_loss),4),'模型偏误中位':round(median(error),4),
                        '参照偏误中位':round(median(original),4),'同单误差减少中位':round(median(paired),4),
                        '改善单数':sum(delta>0 for delta in paired),'恶化单数':sum(delta<0 for delta in paired)})
    return reports
