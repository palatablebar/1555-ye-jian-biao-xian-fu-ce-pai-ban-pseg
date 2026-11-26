from dataclasses import replace
from math import isfinite
import pytest
from linebeads.seasonal_mix.service import coverage_by_group, fit_baseline, scan_current, shift_evidence, shop_floor_shift


def test_same_distribution_has_finite_drift(fitted_vectors):
    training,_,version=fitted_vectors
    reference=fit_baseline(training,version)
    actual=scan_current(reference,training,version)
    assert actual.status=='STABLE'
    assert actual.samples==len(training)
    maintain=shift_evidence(actual,coverage_by_group(training,training))
    assert all(isfinite(value) for _,value in actual.signals)
    assert maintain


def test_novel_group_is_reported(fitted_vectors):
    training, live, version = fitted_vectors
    candidate = replace(live[0],cohort='未登记')
    report = scan_current(fit_baseline(training,version),[candidate],version)
    assert report.novel == ('未登记',) and report.domain == (candidate.key,)


def test_stale_shift_baseline_is_invalid(fitted_vectors):
    training, live, version = fitted_vectors
    with pytest.raises(ValueError,match='重建'):
        scan_current(fit_baseline(training,version),live,'older')


def test_monitor_empty_batch_has_explicit_state(fitted_vectors):
    training, _, version = fitted_vectors
    empty = scan_current(fit_baseline(training,version),[],version)
    assert empty.status == 'NO_CURRENT_RECORDS' and empty.samples == 0


def test_group_coverage_counts_both_windows(fitted_vectors):
    _, live, _ = fitted_vectors
    assert coverage_by_group(live[:1],live[:1]) == ((live[0].cohort,1,1),)


def test_multiple_missing_measurements_force_review(fitted_vectors):
    # TRAP-44
    training, candidates, version = fitted_vectors
    current = replace(candidates[0],missing=('retro_cd','another'))
    found = scan_current(fit_baseline(training,version),[current],version)
    assert found.domain == (current.key,)


def test_operating_reference_keeps_physical_comparisons(fitted_vectors):
    training, live, _ = fitted_vectors
    report = shop_floor_shift(training,live)
    assert len(report) == 8
    assert all(sum(not item.missing for item in live) <= row['当班有效量'] <= len(live) for row in report)
    assert all(sum(not item.missing for item in training) <= row['训练有效量'] <= len(training) for row in report)
    assert all(0 <= item['越线比例'] <= 1 for item in report)


def test_unobserved_measurements_do_not_count_as_field_evidence(fitted_vectors):
    training, live, _ = fitted_vectors
    complete = next(row for row in live if not row.missing)
    present = shop_floor_shift(training,[complete])
    missing = replace(complete,missing=('retro_cd', 'age_days', 'wet_pct', 'traffic_k', 'beads_g', 'surface_c'))
    removed = shop_floor_shift(training,[missing])
    assert {row['当班有效量'] for row in present} == {1}
    assert {row['当班有效量'] for row in removed} == {0}
    assert all(row['越线比例'] is None for row in removed)
