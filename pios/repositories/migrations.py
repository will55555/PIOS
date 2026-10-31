"""Find modular migrations: migrations/<module>/<dialect>/NNNN_name.sql. Adding a module is adding a folder."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Dialect = Literal["sqlite", "postgres"]

_FILE_RE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


@dataclass(frozen=True)
class Migration:
    module: str
    version: int
    path: Path


def discover(root: Path | str, dialect: Dialect) -> list[Migration]:
    """Every migration for a dialect, ordered by module then version. A misnamed file is an error, not a skip."""
    found: list[Migration] = []
    for path in Path(root).glob(f"*/{dialect}/*.sql"):
        match = _FILE_RE.fullmatch(path.name)
        if match is None:
            raise ValueError(f"misnamed migration: {path}")
        found.append(Migration(path.parent.parent.name, int(match.group(1)), path))
    return sorted(found, key=lambda m: (m.module, m.version))
