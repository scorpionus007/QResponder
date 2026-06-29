"""Library health check tests (Phase 7 Part B). Read-only by default."""

import yaml

from qresponder.core.kb_health import check_library, merge_duplicates


def _write_qa(path, entries):
    path.write_text(yaml.safe_dump(entries, sort_keys=False), encoding="utf-8")


def test_internal_contradiction_flagged(tmp_path):
    qa = tmp_path / "qa.yaml"
    _write_qa(qa, [
        {"question": "Do you encrypt data at rest?", "answer": "Yes, data at rest is encrypted.", "version": 1},
        {"question": "Is data at rest encrypted?", "answer": "No, data at rest is not encrypted.", "version": 1},
    ])
    report = check_library(qa)
    assert report["clean"] is False
    assert len(report["contradictions"]) == 1
    assert report["duplicates"] == []


def test_near_duplicates_flagged(tmp_path):
    qa = tmp_path / "qa.yaml"
    _write_qa(qa, [
        {"question": "Do you support SSO?", "answer": "Yes.", "version": 1},
        {"question": "Do you support SSO?!", "answer": "Yes, SAML and OIDC.", "version": 1},
    ])
    report = check_library(qa)
    assert len(report["duplicates"]) == 1
    assert report["contradictions"] == []


def test_clean_library_no_false_positives(tmp_path):
    qa = tmp_path / "qa.yaml"
    _write_qa(qa, [
        {"question": "Do you encrypt data at rest?", "answer": "Yes, AES-256.", "version": 1},
        {"question": "Where is your headquarters?", "answer": "Berlin.", "version": 1},
        {"question": "Do you run penetration tests?", "answer": "Yes, annually.", "version": 1},
    ])
    report = check_library(qa)
    assert report["clean"] is True
    assert report["contradictions"] == [] and report["duplicates"] == []


def test_default_check_is_read_only(tmp_path):
    """NEGATIVE CASE: a plain check mutates nothing."""
    qa = tmp_path / "qa.yaml"
    _write_qa(qa, [
        {"question": "Do you support SSO?", "answer": "Yes.", "version": 1},
        {"question": "Do you support SSO?!", "answer": "Yes, SAML.", "version": 1},
    ])
    before = qa.read_text(encoding="utf-8")
    check_library(qa)
    assert qa.read_text(encoding="utf-8") == before  # untouched

    # Only --merge-duplicates mutates (version-bump, never delete).
    res = merge_duplicates(qa)
    assert res["merged"] == 1
    after = yaml.safe_load(qa.read_text(encoding="utf-8"))
    assert len(after) == 2  # nothing deleted
    assert max(e["version"] for e in after) == 2  # canonical version-bumped
