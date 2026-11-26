from hashlib import sha256
from math import isfinite
from statistics import median

from .contracts import MODEL_NAME, Fit, Prediction
from .baseline import baseline_review
from .diagnostics import explain_bead_kernel
from .radius_model import fit_kernel, score_kernel


def reference_book(points):
    arrivals = sorted(points,key=lambda record:(record.day,record.key))
    indexed = {record.key:record for record in arrivals}
    if len(arrivals) != len(indexed):
        raise ValueError('邻域样本使用唯一单号')
    for record in arrivals:
        target_number = record.outcome
        numbers = (target_number,*record.values)
        if any(number is None or not isfinite(number) for number in numbers):
            raise ValueError('邻域向量需要有限实数')
    return arrivals


def fit_model(history, feature_stamp):
    book = reference_book(history)
    if not feature_stamp or len(book)<8:
        raise ValueError('无法为少于八条单据的参考域拟合')
    parameters, evidence = fit_kernel(book)
    centers = tuple(median(column) for column in zip(*(row.values for row in book),strict=True))
    source = [(note.key,note.cohort,note.values,note.outcome,note.observed) for note in book]
    payload = (MODEL_NAME,feature_stamp,source)
    stamp = sha256(repr(payload).encode()).hexdigest()[:16]
    axis_metadata = tuple((f'参考轴{i+1}中位',centre) for i,centre in enumerate(centers))
    return Fit(MODEL_NAME,feature_stamp,stamp,parameters,(*evidence,*axis_metadata,('参考域记录',len(book))))


def predict_one(fit, observation):
    estimated, differences = score_kernel(fit.parameters,observation)
    differences = tuple(differences)
    if not isfinite(estimated) or estimated<0 or not all(map(isfinite,differences)):
        raise ArithmeticError('距离或贡献无法比较')
    return Prediction(key=observation.key,cohort=observation.cohort,day=observation.day,
                      score=estimated,contributions=differences,missing=observation.missing,
                      excursions=observation.excursions,outcome=observation.outcome,observed=observation.observed,
                      input_values=observation.input_values)


def predict(fit, observations, feature_stamp):
    if feature_stamp != fit.feature:
        raise ValueError('邻域计算拒绝不匹配的坐标版本')
    matched = []
    for inspected in observations:
        matched.append(predict_one(fit,inspected))
    return tuple(matched)


def compare_batches(fit, groups, feature_stamp):
    separate = tuple(prediction for group in groups for prediction in predict(fit, group, feature_stamp))
    return separate == predict(fit, (row for group in groups for row in group), feature_stamp)


def inspection_rows(fit, sections):
    """Return model-specific evidence for the current run without retraining."""
    return (explain_bead_kernel(fit, sections.calibration, sections.replay, sections.live)
            + baseline_review(fit, sections.train, sections.replay))
