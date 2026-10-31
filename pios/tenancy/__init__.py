"""Layer 4, multi-tenancy: schema-level isolation in PostgreSQL, one file per tenant in SQLite (ADR-012)."""

from __future__ import annotations

import re

TENANT_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def validate_tenant_id(tenant_id: str) -> str:
    if not TENANT_ID_RE.fullmatch(tenant_id):
        raise ValueError(f"invalid tenant id: {tenant_id!r}")
    return tenant_id


def schema_name(tenant_id: str) -> str:
    """The PostgreSQL schema that holds this tenant's tables."""
    return f"tenant_{validate_tenant_id(tenant_id)}"


__all__ = ["TENANT_ID_RE", "schema_name", "validate_tenant_id"]
