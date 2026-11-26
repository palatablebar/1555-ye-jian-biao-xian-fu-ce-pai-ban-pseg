from collections import Counter
from math import isfinite
from pathlib import Path

from linebeads.pipeline import open_fixture, preview, execute
from linebeads.retrocheck_slots.contracts import RISK_CUTOFF


def test_changing_workload_changes_scope_not_frozen_model():
    constrained = preview(1, 'balanced')
    larger = preview(33, 'focus')
    assert constrained['feature_stamp'] == larger['feature_stamp']
    projected = {row['key']: row['alternatives'] for row in constrained['rows']}
    assert {row['key']: row['alternatives'] for row in larger['rows']} == projected


def test_operational_measurements_are_finite_and_aligned():
    result = preview()
    feature_stage = result['sections'][2]
    observed = [item for item in feature_stage['records'] if '作业量' in item]
    assert len(observed) == 8
    assert all(item['有效读数'] <= len(result['rows']) for item in observed)
    assert all(isfinite(item['变动']) for item in observed if '变动' in item)
    assert all(item['越界量'] <= item['有效读数'] for item in observed if '越界量' in item)


def test_proposals_have_single_causal_input_and_conserve_output():
    for record in preview()['rows']:
        unique = set()
        for move in record['alternatives']:
            assert move['情形'] not in unique
            unique.add(move['情形'])
            field = move['变更项']
            assert field in record['measurements'] and field not in record['unmeasured']
            assert move['原值'] == record['measurements'][field]
            assert move['原值'] != move['置换值']
            error = abs((move['替换预测'] - move['原预测']) - move['预测变化'])
            assert error <= .0002


def test_work_order_types_keep_scope_and_valid_costs():
    info = preview(33)
    total = 0
    by_state = Counter(work['state'] for work in info['rows'])
    assert set(by_state) <= {'已分派','候补','暂停','人工判读','观察'}
    for work in info['rows']:
        assert 1 <= work['cost'] <= 12
        if work['state'] == '已分派':
            total += work['cost']
        if work['state'] == '暂停':
            assert work['reason'] == 'WET_LOW_LIGHT'
    assert total + info['metrics'][-1]['value'] == info['capacity']


def test_replay_comparison_reports_finite_out_of_time_loss():
    default = preview()
    benchmarks = [item for item in default['sections'][3]['records'] if item.get('基线') == '按路段历史反光衰减中位']
    assert len(benchmarks) >= 2
    for line in benchmarks:
        assert line['实绩数'] > 0
        assert line['估计代价'] >= 0
        assert isfinite(line['业务基线代价'])


def test_future_live_outcome_does_not_move_training_or_estimates():
    dataset = open_fixture()
    entries = [dict(row) for row in dataset['records']]
    contact = next(row for row in entries if row['day'] == 88)
    contact['result_day'] = 94
    contact['outcome'] = 1
    before = preview()
    after = execute(entries)
    assert after['feature_stamp'] == before['feature_stamp']
    assert after['rows'] == before['rows']
    assert after['sample_hash'] != before['sample_hash']


def test_joint_experiments_change_only_supported_controls():
    report=preview()
    assert any(row['joint_experiments'] for row in report['rows'])
    for row in report['rows']:
        for study in row['joint_experiments']:
            readings=study['联动量测']
            assert len(readings)>=2 and not set(readings)&set(row['unmeasured'])
            assert all(series['原值']==row['measurements'][field] for field,series in readings.items())
            assert any(series['原值']!=series['替换值'] for series in readings.values())
            assert abs(study['替换预测']-study['原预测']-study['变化']) <= .0002
