from dataclasses import replace
import pytest
from linebeads.night_accuracy.service import check_point, prepare_verification, performance, ranked_error, boundary_diagnostics


def test_no_outcome_gets_undefined_metrics(prediction):
    # TRAP-43
    row = replace(prediction,outcome=None)
    stats = performance([check_point(row,prepare_verification([]))])
    assert (stats.status,stats.count,stats.mae,stats.error) == ('NO_MATURE_RESULT',0,None,None)


def test_empty_calibration_requires_review(prediction):
    # TRAP-44
    checked = check_point(prediction,prepare_verification([]))
    assert checked.uncertain and checked.upper is None


def test_conformal_finite_sample_quantile_is_conservative():
    assert ranked_error([1,2,3,4,5],.8) == 5
    assert ranked_error([1,2,3,4,5],.4) == 3
    with pytest.raises(ValueError,match='比例'):
        ranked_error([1],1)


def test_interval_stretches_toward_observed_misses(prediction):
    source = replace(prediction,score=8.,outcome=12.,observed=True)
    checked = check_point(source,prepare_verification([source]))
    assert checked.lower == 8. and checked.upper == 12.


def test_censored_target_does_not_fit_error_band(prediction):
    point = replace(prediction,observed=False,outcome=0.)
    assert prepare_verification([point]).size == 0


def test_interval_is_exact_when_residual_vanishes(prediction):
    anchor = replace(prediction,outcome=prediction.score,observed=True)
    check = check_point(anchor,prepare_verification([anchor],coverage=.8))
    assert check.lower == check.upper == check.estimate


def test_cutoff_slices_separate_underrun_and_overrun(prediction):
    checks = [check_point(replace(prediction,score=score,outcome=outcome,observed=True),prepare_verification([]))
              for score,outcome in [(2.0,4.0),(3.0,2.0),(4.0,4.0)]]
    stats = boundary_diagnostics(checks,3)
    assert (stats['实绩超线'],stats['估计超线'],stats['额外复测'],stats['漏查']) == (2,2,1,1)
