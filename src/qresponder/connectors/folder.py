"""Folder connector (Phase 10 B) — ingest a local/mounted directory of docs.

Zero-dependency, path-contained: only files inside the given directory are read,
and the bulk-ingest path sanitizes every filename (basename only) so nothing
escapes the workspace kb/.
"""

from __future__ import annotations

from pathlib import Path

from .base import Connector, ConnectorError, SourceDoc


class FolderConnector(Connector):
    def __init__(self, path: str, tags=None):
        self.base = Path(path)
        self.tags = list(tags or [])

    def test_connection(self) -> dict:
        if not self.base.exists():
            return {"ok": False, "detail": f"Path not found: {self.base}"}
        if not self.base.is_dir():
            return {"ok": False, "detail": f"Not a directory: {self.base}"}
        n = sum(1 for fp in self.base.rglob("*") if fp.is_file())
        return {"ok": True, "detail": f"Folder OK — {n} file(s) present."}

    def fetch(self) -> list[SourceDoc]:
        if not self.base.exists() or not self.base.is_dir():
            raise ConnectorError(f"Not a directory: {self.base}")
        root = self.base.resolve()
        docs: list[SourceDoc] = []
        for fp in sorted(root.rglob("*")):
            if not fp.is_file():
                continue
            # Path containment: rglob stays under root; double-check resolved path.
            try:
                fp.resolve().relative_to(root)
            except ValueError:
                continue
            docs.append(SourceDoc(source_name=fp.name, content=fp.read_bytes(),
                                  origin=str(fp), tags=self.tags))
        return docs
