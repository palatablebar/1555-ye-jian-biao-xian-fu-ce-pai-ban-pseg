from dataclasses import replace
from math import isfinite
import pytest
from linebeads.bead_kernel.service import compare_batches, fit_model, predict


def test_training_sorts_inputs(fitted_vectors):
    training, _, version = fitted_vectors
    assert fit_model(training,version) == fit_model(reversed(training),version)


def test_input_batch_invariance(fitted_vectors):
    # TRAP-53
    training, live, version = fitted_vectors
    model = fit_model(training,version)
    assert compare_batches(model, [live[:1], live[1:5], live[5:]], version)


def test_mismatched_model_input_version_fails(fitted_vectors):
    # TRAP-54
    training, live, version = fitted_vectors
    with pytest.raises(ValueError,match='版本'):
        predict(fit_model(training,version), live, 'obsolete')


def test_revision_changes_training_fingerprint(fitted_vectors):
    training, _, version = fitted_vectors
    model = fit_model(training,version)
    target = training[0].outcome
    changed = replace(training[0], outcome=(1-target if False else target+.5))
    assert fit_model((changed,*training[1:]),version).fingerprint != model.fingerprint


def test_training_rejects_nonfinite_feature(fitted_vectors):
    training, _, version = fitted_vectors
    broken = replace(training[0],values=(float('nan'),0.,0.,0.,0.))
    with pytest.raises(ValueError,match='有限'):
        fit_model((broken,*training[1:]),version)


def test_model_scores_have_evidence(fitted_vectors):
    training, live, version = fitted_vectors
    result = predict(fit_model(training,version),live,version)
    assert len(result) == len(live) and result[0].key == live[0].key
    assert all(isfinite(row.score) and row.score >= 0 and row.contributions for row in result)
    assert len({row.score for row in result}) > 1


def test_kernel_matches_calculated_reference():
    from types import SimpleNamespace
    from linebeads.bead_kernel.radius_model import score_kernel

    refs = (('a','N',(1.,),2.),('b','N',(-1.,),4.))
    sample = SimpleNamespace(cohort='N',values=(0.,))
    assert score_kernel((refs,.12),sample) == (3.,(1.,))
