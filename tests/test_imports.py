"""S3: the package must import with retrieval-only deps absent, so the default
(non-retrieval) Docker image and the in-context path work without
sentence-transformers / rank-bm25 / numpy / torch. Those are imported lazily,
only when retrieval is actually used."""

import subprocess
import sys
import textwrap


def test_no_top_level_retrieval_deps():
    code = textwrap.dedent(
        """
        import sys
        # Block heavy/retrieval-only deps: importing any of these now raises.
        for m in ("sentence_transformers", "rank_bm25", "numpy", "torch"):
            sys.modules[m] = None
        import importlib
        for mod in (
            "qresponder.cli",
            "qresponder.core.orchestrate",
            "qresponder.core.pipeline",
            "qresponder.core.confidence",
            "qresponder.core.faithfulness",
            "qresponder.core.interpretations",
            "qresponder.core.attachments",
            "qresponder.core.flywheel",
            "qresponder.kb.retrieval",
            "qresponder.kb.evidence",
            "qresponder.llm.embeddings",
            "qresponder.llm.reranker",
            "qresponder.eval.runner",
            "qresponder.output.writeback",
            "qresponder.output.writer",
        ):
            importlib.import_module(mod)
        print("IMPORT_OK")
        """
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert "IMPORT_OK" in r.stdout, f"stdout={r.stdout!r} stderr={r.stderr!r}"
