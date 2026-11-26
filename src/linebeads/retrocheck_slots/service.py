from .operating_ledger import operating_ledger
from collections import Counter, defaultdict
from math import exp, isfinite

from .contracts import RuleNotice, Job, Plan, Policy, RISK_CUTOFF
from .constraints import WorkOrder, apply_retrocheck_slots


def measures(raw):
    return tuple(raw)


def signals(data, estimate, missing=()):
    absent=frozenset(missing)
    retro_cd, age_days, wet_pct, traffic_k, beads_g, surface_c = data
    hits = []
    if not absent.intersection(('retro_cd', 'wet_pct')) and (wet_pct >= 75 and retro_cd <= 140):
        hits.append(RuleNotice('WET_LOW_LIGHT', '潮湿低反光，现场复测', hard=True))
    if not absent.intersection(('age_days', 'traffic_k')) and (age_days >= 300 and traffic_k >= 40):
        hits.append(RuleNotice('LONG_SERVICE', '高暴露路段优先复测', hard=False))
    if not absent.intersection(('retro_cd', 'beads_g')) and (beads_g < 210 and retro_cd < 230):
        hits.append(RuleNotice('BEAD_SUPPLY', '核对投放班组记录', hard=False))
    return tuple(hits)


def expected_load(measurements):
    retro_cd, age_days, wet_pct, traffic_k, beads_g, surface_c = measurements
    return 1 + int(traffic_k >= 38)


def dispatch_pressure(values, estimate):
    retro_cd, age_days, wet_pct, traffic_k, beads_g, surface_c = values
    return max(0,180-retro_cd)/55 + wet_pct/80 + traffic_k/110


def confidence_weight(estimate, cutoff):
    shifted = (estimate - cutoff) / max(.5, abs(cutoff) * .35)
    if shifted >= 0:
        return 1 / (1 + exp(-shifted))
    bounded = exp(shifted)
    return bounded / (1 + bounded)


def recommend(assessment, attention, policy):
    raw = assessment.raw
    data = measures(raw.input_values)
    estimate = assessment.estimate
    domain_codes = signals(data, estimate, raw.missing)
    level = confidence_weight(estimate, policy.trigger)
    cost = expected_load(data)
    if not isfinite(estimate) or not 1 <= cost <= 12:
        raise ValueError('处置量不在有效范围')
    if domain_codes and domain_codes[0].hard:
        state = '暂停'
        reason = domain_codes[0].rule_id
        summary = domain_codes[0].meaning
    elif raw.key in attention or assessment.uncertain:
        state = '人工判读'
        reason = 'OUT_OF_REFERENCE' if raw.key in attention else 'INSUFFICIENT_CALIBRATION'
        summary = '分布偏移或校准量不足，需核对原始单据'
    elif domain_codes or estimate >= policy.trigger:
        state = '候选'
        reason = domain_codes[0].rule_id if domain_codes else 'ABOVE_TRIGGER'
        summary = domain_codes[0].meaning if domain_codes else '达到本班复核阈值'
    else:
        state = '观察'
        reason = 'BELOW_TRIGGER'
        summary = '保留记录并等待下一次巡查'
    return Job(raw.key, raw.cohort, round(estimate, 4), assessment.lower, assessment.upper, cost,
               state, reason, summary, round(level, 5), tuple(item.rule_id for item in domain_codes))


def allocate(assessments, attention, policy):
    work = [WorkOrder(recommend(assessment, attention, policy), assessment) for assessment in assessments]
    if len({item.job.key for item in work}) != len(work):
        raise ValueError('待处理单据编号重复')
    candidates = sorted((order for order in work if order.job.state == '候选'),
                        key=lambda order: (not bool(order.job.rule_hits), -dispatch_pressure(order.assessment.raw.input_values, order.job.estimate),
                                           -order.job.priority, order.job.cost, order.job.key))
    remaining = policy.capacity
    used = defaultdict(int)
    allocated = {}

    def wait(order, reason, evidence):
        allocated[order.job.key] = order.job.change('候补', reason, evidence)

    def admit(order):
        nonlocal remaining
        job = order.job
        if job.cost > remaining:
            wait(order,'CAPACITY_REACHED','剩余作业额度不足')
        elif used[job.cohort] + job.cost > policy.group_quota:
            wait(order,'GROUP_CAP_REACHED','已达分区额度上限')
        else:
            remaining -= job.cost
            used[job.cohort] += job.cost
            allocated[job.key] = job.change('已分派', job.reason, job.summary)
            return True
        return False

    apply_retrocheck_slots(candidates, admit, wait)
    if set(allocated) != {item.job.key for item in candidates}:
        raise ArithmeticError('存在未经过工位规则的候选单据')
    resolved = sorted((allocated.get(item.job.key,item.job) for item in work),
                      key=lambda job: (job.state != '已分派', job.state == '观察', -job.priority, job.key))
    if sum(used.values()) + remaining != policy.capacity:
        raise ArithmeticError('派发余额核对失败')
    return Plan(tuple(resolved), policy.capacity, remaining, tuple(sorted(used.items())))


def plan_jobs(assessments, attention, capacity, mode='balanced'):
    return allocate(assessments, frozenset(attention), Policy.select(capacity, mode))


def action_evidence(plan):
    counts = Counter(job.state for job in plan.jobs)
    status = [{'处置': state, '单量': count} for state, count in sorted(counts.items())]
    status.extend({'处置': '分区 ' + group, '额度': cost} for group, cost in plan.used_by_group)
    status += [{'处置': '剩余额度', '额度': plan.balance}]
    return status


def segment_focus(raw):
    wet_pct = raw[2]
    return int(wet_pct//18)


def operating_group(assessments, progression):
    source={line.raw.key:line.raw.input_values for line in assessments}
    cells=Counter()
    for work in progression.jobs:
        if work.state != '已分派':
            continue
        band=segment_focus(source[work.key])
        cells[work.cohort,band] += work.cost
    return [{ '作业区': zone, '巡线班位': band, '班组用量': total } for (zone,band),total in sorted(cells.items())]
