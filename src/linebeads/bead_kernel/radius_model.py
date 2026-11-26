from math import exp, fsum
from statistics import median


def fit_kernel(rows):
    records = tuple((item.key, item.cohort, item.values, item.outcome) for item in rows)
    small = []
    for key, _, vector, _ in records:
        distance = min(fsum((x - y) ** 2 for x,y in zip(vector, ref, strict=True))
                       for ref_key, _, ref, _ in records if ref_key != key)
        small.append(distance)
    bandwidth = max(.12, median(small) * 3.1)
    return (records, bandwidth), (('历史测点', len(records)), ('核半径平方', bandwidth),
                                 ('全站中位衰减', median(item[-1] for item in records)))


def score_kernel(neighborhood, sample):
    records, bandwidth = neighborhood
    comparisons = []
    for key, section, ref, target in records:
        difference = tuple(abs(actual - past) for actual,past in zip(sample.values,ref,strict=True))
        squared = fsum(value ** 2 for value in difference) + (.32 if section != sample.cohort else 0.)
        comparisons.append((squared, key, target, difference))
    subset = sorted(comparisons)[:22]
    nearest = subset[0][0]
    weights = tuple(exp(-(distance - nearest) / bandwidth) for distance, *_ in subset)
    denominator = fsum(weights)
    prediction = fsum(weight * item[2] for weight,item in zip(weights,subset,strict=True)) / denominator
    gaps = tuple(fsum(weight * delta for weight, delta in zip(weights,column,strict=True))/denominator
                 for column in zip(*(example[-1] for example in subset), strict=True))
    return max(0, prediction), gaps
