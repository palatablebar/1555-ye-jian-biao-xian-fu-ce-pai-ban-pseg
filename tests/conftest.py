import pytest
from linebeads.pipeline import open_fixture
from linebeads.lane_samples.service import load_samples
from linebeads.surface_windows.service import build_windows
from linebeads.reflection_factors.service import fit_features, transform_windows
from linebeads.bead_kernel.service import fit_model, predict


@pytest.fixture
def observation():
    return dict(open_fixture()['records'][0])


@pytest.fixture(scope='session')
def fitted_vectors():
    sample = open_fixture()
    intake = load_samples(sample['records'],sample['as_of'])
    windows = build_windows(intake.entries)
    reference = fit_features(windows.train)
    prepared = transform_windows(windows,reference)
    return prepared.train, prepared.live, reference.fingerprint


@pytest.fixture(scope='session')
def prediction(fitted_vectors):
    train, live, stamp = fitted_vectors
    anchor = fit_model(train,stamp)
    inferred = predict(anchor,live[:1],stamp)[0]
    return inferred
