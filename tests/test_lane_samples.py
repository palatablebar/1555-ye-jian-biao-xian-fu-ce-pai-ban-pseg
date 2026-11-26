from dataclasses import replace
import pytest
from linebeads.lane_samples.service import load_samples, number, profile_intake, read_assay


def test_normalized_number_field(observation):
    value = observation['retro_cd']
    source = {**observation, 'retro_cd': str(value), 'key': '　ＡＢ-１２　'}
    row = read_assay(source)
    assert row.key == 'AB-12'
    assert row.retro_cd == value


def test_bool_and_nonfinite_values_are_isolated(observation):
    tickets = [{**observation, 'retro_cd': raw} for raw in [True, 'Infinity', 'NaN', [], 'x'*100]]
    result = load_samples(tickets + [observation], 96)
    assert len(result.entries) == 1
    assert [item.code for item in result.issues] == ['NUMBER_REQUIRED','NUMBER_RANGE','NUMBER_RANGE','NUMBER_REQUIRED','NUMBER_INVALID']


def test_latest_recognized_version_before_cutoff(observation):
    result = load_samples([observation, {**observation,'revision':2}, {**observation,'revision':3,'received':100}], 96)
    assert [entry.revision for entry in result.entries] == [2]
    assert [issue.code for issue in result.issues] == ['OLDER_REVISION','AFTER_CUTOFF']


def test_conflicting_same_version_is_order_independent(observation):
    # TRAP-14: no arrival-order overwrite.
    alternative = {**observation, 'retro_cd': observation['retro_cd'] + .1}
    for documents in ([observation, alternative], [alternative, observation]):
        loaded = load_samples(documents, 96)
        assert loaded.entries == ()
        assert [row.code for row in loaded.issues] == ['CONFLICTING_REVISION'] * 2


def test_import_report_conserves_rejected_rows(observation):
    profile = profile_intake(load_samples([observation, dict(observation), None], 96))
    assert profile['received'] == profile['retained'] + profile['discarded'] == 3
    assert profile['by_issue'] == {'OBJECT_REQUIRED':1,'REPEATED_REVISION':1}


def test_result_requires_mature_timestamp_pair(observation):
    document = {**observation,'result_day':None}
    report = load_samples([document], 96)
    assert report.issues[0].code == 'RESULT_TIMESTAMP_PAIR_REQUIRED'


def test_numeric_lower_bound_is_inclusive():
    assert number('4','quantity',4,10,integral=True) == 4
    with pytest.raises(ValueError, match='WHOLE_REQUIRED'):
        number('4.1','quantity',4,10,integral=True)
