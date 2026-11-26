from collections import Counter
from dataclasses import replace

from .readiness import formation_tail
from .contracts import Chronology, FoldSummary, Span, WindowRule


def assign_fold(record, rule):
    if record.day in rule.live and record.day <= rule.as_of and record.received <= rule.as_of:
        return 'live', 'OPEN_RUN'
    for name, span in rule.folds():
        if record.day not in span:
            continue
        if record.received >= span.end or record.result_day is None or record.result_day >= span.end:
            return None, 'RESULT_NOT_MATURE'
        if record.result_day < record.day:
            return None, 'REVERSED_RESULT_TIME'
        if record.outcome is None:
            return None, 'MISSING_OUTCOME'
        if not record.observed and not rule.allow_censor:
            return None, 'CENSORED_OUTCOME'
        return name, 'LOCKED_HISTORY'
    return None, 'EMBARGO_OR_UNSCHEDULED'


def route_history(records, rule):
    panels = {name: [] for name, _ in rule.folds()}
    panels['live'] = []
    lost = []
    for record in records:
        fold, reason = assign_fold(record, rule)
        if fold is None:
            lost.append((record.key, reason))
        else:
            panels[fold].append(record)
    folds = {}
    for name, values in panels.items():
        folds[name] = tuple(sorted(values, key=lambda item: (item.day, item.key)))
    return Chronology(**folds, excluded=tuple(sorted(lost)))


def build_windows(records, rule=None):
    active = rule or WindowRule.standard(allow_censor=False)
    views = route_history(records, active)
    views.check_conservation(len(records))
    return views


def partition_summary(windows):
    rows = []
    for name, records in windows.partitions():
        cohorts = Counter(record.cohort for record in records)
        window = FoldSummary(name, len(records), len(cohorts),
                             sum(not row.observed for row in records),
                             records[0].day if records else None, records[-1].day if records else None)
        rows.append(window)
    return tuple(rows)


def window_evidence(windows):
    names = {'train': '拟合', 'calibration': '校准', 'replay': '回放', 'live': '当班'}
    evidence = [
        {'时段': names[part.name], '单据': part.count, '分组': part.cohort_count,
         '截尾': part.censored, '首日': part.first_day, '末日': part.last_day}
        for part in partition_summary(windows)
    ]
    for code, count in sorted(Counter(reason for _, reason in windows.excluded).items()):
        evidence.append({'时段': code, '单据': count, '分组': None, '截尾': None, '首日': None, '末日': None})
    return evidence


def model_inputs(windows):
    if len(windows.train) < 16:
        raise ValueError('至少需要 16 条在拟合期内成熟的记录')
    if not windows.calibration:
        raise ValueError('校准期没有可用结果')
    if not windows.replay:
        raise ValueError('回放期没有可用结果')
    if not windows.live:
        raise ValueError('当班时段没有可用单据')
    return tuple(row.key for row in windows.train)


def readiness_evidence(windows, as_of=96):
    valid = formation_tail(windows, replace(WindowRule.standard(), as_of=as_of))
    stages = ('train','calibration','replay','live')
    return sorted(valid,key=lambda row:(stages.index(row['交班段']), -row['有效单'], row['来源']))
