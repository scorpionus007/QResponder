"""KB layer tests — library tier-1 match, tag-scoping, in-context loading."""

from pathlib import Path

from qresponder.kb.in_context import InContextKB
from qresponder.kb.library import AnswerLibrary
from qresponder.kb.tags import in_scope, parse_tags

FIX = Path(__file__).parent / "fixtures"


def test_parse_tags_and_scope():
    assert parse_tags("HIPAA, soc2 ,") == ["hipaa", "soc2"]
    assert in_scope(["soc2"], ["hipaa", "soc2"]) is True
    assert in_scope(["gdpr"], ["soc2"]) is False
    assert in_scope([], ["soc2"]) is True   # untagged = universal
    assert in_scope(["gdpr"], []) is True   # empty scope = everything


def test_library_matches_strong_and_rejects_weak():
    lib = AnswerLibrary.load(FIX / "qa.yaml")
    hit = lib.match("Do you encrypt data at rest?")
    assert hit is not None
    entry, score = hit
    assert "AES-256" in entry.answer
    assert score >= 0.62

    # An unrelated question should not match the library.
    assert lib.match("What is your office address in Berlin?") is None


def test_library_respects_tag_scope():
    lib = AnswerLibrary.load(FIX / "qa.yaml")
    # The encryption entry is tagged soc2/encryption; scope to gdpr excludes it.
    assert lib.match("Do you encrypt data at rest?", scope_tags=["gdpr"]) is None
    assert lib.match("Do you encrypt data at rest?", scope_tags=["soc2"]) is not None


def test_in_context_loads_chunks_with_tags():
    kb = InContextKB.load(FIX / "kb")
    assert kb.chunks
    enc = [c for c in kb.chunks if "AES-256" in c.text]
    assert enc and "encryption" in enc[0].tags

    ctx = kb.assemble_context(scope_tags=["soc2"])
    assert "AES-256" in ctx
    assert "[source:" in ctx

    # Scoping to an absent tag still includes untagged-universal chunks only;
    # here all chunks are soc2-tagged, so a gdpr-only scope yields no soc2 text.
    ctx_gdpr = kb.assemble_context(scope_tags=["gdpr"])
    assert "AES-256" not in ctx_gdpr
