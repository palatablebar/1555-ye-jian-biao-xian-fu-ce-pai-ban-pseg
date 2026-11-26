from dataclasses import replace
import pytest
from linebeads.marking_evidence.service import check_flow, compare, data_fingerprint, policy_fingerprint
from linebeads.marking_evidence.contracts import LedgerCheck
from linebeads.pipeline import open_fixture, preview


def test_payload_identity_remains_if_import_order_changes(observation):
    # Reordering the import preserves decisions, as checked separately by the API integration test.
    second = {**observation,'key':'linked'}
    assert data_fingerprint([observation,second]) == data_fingerprint([second,observation])
    assert data_fingerprint([observation]) != data_fingerprint([observation,second])


def test_policy_change_recomputes_audit_stamp():
    assert policy_fingerprint(4,'focus','fv','fit') != policy_fingerprint(4,'balanced','fv','fit')
    assert policy_fingerprint(4,'focus','fv','fit') != policy_fingerprint(4,'focus','fv2','fit')


def test_incomplete_balance_cannot_be_signed():
    with pytest.raises(ArithmeticError,match='额度'):
        LedgerCheck(10,0,0,5,9,8,2,(('派发',5),))


def test_missing_decision_cannot_be_signed():
    with pytest.raises(ArithmeticError,match='数量'):
        LedgerCheck(10,0,0,5,9,8,1,(('派发',4),))


def test_reference_revision_signature_tracks_changes(observation):
    later = {**observation,'revision':2}
    assert data_fingerprint([observation]) != data_fingerprint([later])


def test_sample_settlement_counts_match_worklist():
    report = preview()
    assert sum(count for _,count in report['flow_counts']) == len(report['rows'])
    assert sum(row['cost'] for row in report['rows'] if row['state'] == '已分派') + report['metrics'][-1]['value'] == 12


def test_repeat_results_are_identical():
    assert preview() == preview()
