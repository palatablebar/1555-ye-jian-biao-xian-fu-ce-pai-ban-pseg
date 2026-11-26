from copy import deepcopy
import json
from pathlib import Path

from linebeads.lane_samples.service import load_samples, read_assay
from linebeads.pipeline import open_fixture


def form_record():
    source = Path(__file__).resolve().parents[1] / 'sample_data' / 'lane_samples_form.json'
    return json.loads(source.read_text(encoding='utf-8'))


def test_industry_form_matches_same_flat_record():
    original = open_fixture()['records'][0]
    result = read_assay(form_record())
    assert read_assay(original) == result


def test_industry_form_preserves_repeat_detection():
    native = form_record()
    result = load_samples((native, deepcopy(native)), 96)
    assert len(result.entries) == 1
    assert result.issues[0].code == 'REPEATED_REVISION'


def test_partial_form_reports_missing_section():
    native = form_record()
    name = next(iter(native['form']))
    native['form'].pop(name)
    report = load_samples([native], 96)
    assert len(report.entries) == 0
    assert (report.issues[0].field, report.issues[0].code) == (name,'FORM_SECTION_REQUIRED')


def test_cannot_submit_two_measurement_formats():
    sample = {**open_fixture()['records'][0], **form_record()}
    result = load_samples([sample], 96)
    assert result.issues[0].code == 'MIXED_FORM_AND_FLAT_READING'
