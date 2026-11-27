from dataclasses import replace

import pytest

from linebeads.lane_samples.service import read_assay
from linebeads.reflection_factors.service import (
    ZONE_FILL_MIN_RECORDS, fit_features, transform, transform_all,
)
from linebeads.pipeline import execute, open_fixture, preview


def record(key, cohort, day, *, retro=240, age=200, wet=40, traffic=40, beads=300, surface=22, outcome=10.0):
    return {'key': key, 'cohort': cohort, 'day': day, 'received': day, 'revision': 1,
            'result_day': day, 'outcome': outcome, 'observed': True,
            'retro_cd': retro, 'age_days': age, 'wet_pct': wet, 'traffic_k': traffic,
            'beads_g': beads, 'surface_c': surface}


def thin_history():
    """Two mature zones plus a dim zone that is well covered and a thin zone."""
    rows = []
    for i in range(10):
        rows.append(record(f'N{i}', '常规线', 2 + i, retro=200 + i * 3, age=300 + i, wet=40, traffic=40))
    for i in range(8):
        rows.append(record(f'S{i}', '支线', 2 + i, retro=250 + i * 2, age=280 + i, wet=45, traffic=42))
    # A bright, low-age zone whose own median sits near the top of the envelope.
    for i in range(6):
        rows.append(record(f'X{i}', '高反区', 2 + i, retro=500, age=200 + i * 3, wet=40, traffic=40))
    # A zone with too little mature history for a local median.
    rows.append(record('B0', '薄区', 3, retro=220, age=250))
    rows.append(record('B1', '薄区', 4, retro=225, age=252))
    return [read_assay(row) for row in rows]


def live(key, cohort, **fields):
    base = {'key': key, 'cohort': cohort, 'day': 90, 'received': 90, 'revision': 1,
            'result_day': None, 'outcome': None, 'observed': True,
            'retro_cd': 240, 'age_days': 200, 'wet_pct': 40, 'traffic_k': 40,
            'beads_g': 300, 'surface_c': 22}
    base.update(fields)
    return read_assay(base)


def test_zone_median_is_adopted_when_same_zone_coverage_is_adequate():
    state = fit_features(thin_history())
    point = transform(live('L1', '常规线', wet_pct=None), state)
    assert len(point.fills) == 1
    fill = point.fills[0]
    assert fill.field == 'wet_pct'
    assert fill.basis == 'ZONE'
    assert fill.records >= ZONE_FILL_MIN_RECORDS
    assert point.review_reason() is None


def test_thin_zone_coverage_falls_back_to_pooled_and_holds_for_review():
    state = fit_features(thin_history())
    point = transform(live('L2', '薄区', retro_cd=220, age_days=250, wet_pct=None), state)
    fill = point.fills[0]
    assert fill.basis == 'COHORT'
    assert fill.records < ZONE_FILL_MIN_RECORDS
    assert point.review_reason() == 'FILL_ZONE_COVERAGE_LOW'


def test_fill_that_pushes_a_feature_out_of_range_is_held():
    state = fit_features(thin_history())
    # Bright-zone median for retro, but a very young observed age drives the
    # retention feature above the frozen ceiling, hiding a dark segment.
    point = transform(live('L3', '高反区', retro_cd=None, age_days=4), state)
    fill = point.fills[0]
    assert fill.basis == 'ZONE'
    assert fill.masked
    assert point.review_reason() == 'FILL_EXCEEDS_TRAINING_RANGE'


def test_in_range_zone_fill_stays_dispatchable():
    state = fit_features(thin_history())
    point = transform(live('L4', '高反区', retro_cd=None, age_days=210), state)
    assert point.fills[0].basis == 'ZONE'
    assert point.review_reason() is None


def test_fill_basis_is_identical_between_fit_and_serving():
    history = thin_history()
    state = fit_features(history)
    # A mature training record and the same ticket served live must resolve to
    # the same frozen basis, field for field.
    row = history[3]
    missing = replace(row, key='probe', wet_pct=None, outcome=None, result_day=None, observed=True)
    served = transform(missing, state)
    assert served.fills[0].basis == 'ZONE'
    assert transform(replace(missing, day=90), state).fills == served.fills


def test_fill_verdict_is_independent_of_batch_grouping():
    state = fit_features(thin_history())
    batch = [live('A', '常规线', wet_pct=None), live('B', '薄区', retro_cd=220, age_days=250, wet_pct=None),
             live('C', '高反区', retro_cd=None, age_days=4)]
    whole = transform_all(batch, state)
    split = transform_all(batch[:1], state) + transform_all(batch[1:], state)
    assert tuple(row.fills for row in whole) == tuple(row.fills for row in split)


def test_live_measurements_cannot_feed_back_into_the_frozen_fill_basis():
    dataset = open_fixture()
    base = execute(dataset['records'])
    edited = [dict(row) for row in dataset['records']]
    for row in edited:
        if row['key'] == 'LB-1270':
            row['wet_pct'] = 10  # different current-shift reading, same ticket
    rerun = execute(edited)
    assert rerun['fill_version'] == base['fill_version']
    assert rerun['feature_stamp'] == base['feature_stamp']


def test_same_batch_rerun_adds_no_fill_version_or_signing_result():
    dataset = open_fixture()
    first = execute(dataset['records'])
    second = execute(list(reversed(dataset['records'])))
    assert first['run_id'] == second['run_id']
    assert first['fill_version'] == second['fill_version']
    assert first['sections'][7]['imputation_review'] == second['sections'][7]['imputation_review']


def test_current_ticket_cannot_be_resolved_after_a_bad_fill():
    dataset = open_fixture()
    edited = [dict(row) for row in dataset['records']]
    # Move a well-covered current ticket into an unregistered zone and drop a
    # measurement: coverage is missing, so it must be held for manual review.
    for row in edited:
        if row['key'] == 'LB-1272':
            row['cohort'] = '临时接管区'
            row['wet_pct'] = ''
    result = execute(edited)
    ticket = next(row for row in result['rows'] if row['key'] == 'LB-1272')
    assert ticket['state'] == '人工判读'
    assert ticket['reason'] == 'FILL_ZONE_COVERAGE_LOW'
    review = next(item for item in result['sections'][7]['imputation_review'] if item['单号'] == 'LB-1272')
    assert review['审查结论'] == '保留实测转人工'


def test_signing_guard_rejects_dispatched_held_ticket():
    from linebeads.marking_evidence.service import check_imputation_signing
    from linebeads.retrocheck_slots.contracts import Job, Plan

    rows = [{'key': 'HELD', 'zone': '薄区', 'unmeasured': ['wet_pct'], 'state': '人工判读',
             'fills': [{'补值依据': '全班历史中位'}], 'fill_review': 'FILL_ZONE_COVERAGE_LOW'}]
    # A forged plan that wrongly dispatches the held ticket trips the guard.
    job = Job('HELD', '薄区', 12.0, None, None, 1, '已分派', 'ABOVE_TRIGGER', 'x', 0.5, ())
    plan = Plan((job,), 4, 3, (('薄区', 1),))
    with pytest.raises(ArithmeticError, match='补值审查未通过'):
        check_imputation_signing(rows, plan)


def test_default_shift_separates_dispatchable_and_held_imputations():
    result = preview()
    review = result['sections'][7]['imputation_review']
    missing_live = [row for row in result['rows'] if row['unmeasured']]
    # Every imputed live ticket appears exactly once in the pre-signing review.
    assert sorted(item['单号'] for item in review) == sorted(row['key'] for row in missing_live)
    verdicts = {item['单号']: item['审查结论'] for item in review}
    assert '可据补值派工' in verdicts.values()
    assert '保留实测转人工' in verdicts.values()
    # Held tickets are never dispatched.
    for row in result['rows']:
        if verdicts.get(row['key']) == '保留实测转人工':
            assert row['state'] != '已分派'


def test_partial_fill_in_a_covered_zone_keeps_the_ticket_dispatchable():
    from linebeads.pipeline import open_fixture, execute

    dataset = open_fixture()
    edited = [dict(row) for row in dataset['records']]
    for row in edited:
        # A current ticket in a well-covered zone loses one measurement.
        if row['key'] == 'LB-1270':
            row['wet_pct'] = ''
    result = execute(edited)
    ticket = next(row for row in result['rows'] if row['key'] == 'LB-1270')
    assert ticket['fill_review'] is None
    assert ticket['state'] != '人工判读'
    review = next(item for item in result['sections'][7]['imputation_review'] if item['单号'] == 'LB-1270')
    assert review['审查结论'] == '可据补值派工'
    assert review['同区成熟记录'] > 0
