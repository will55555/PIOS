"""Tenant identity helpers. Every record carries a validated ``tenant_id`` (ADR-002 §11)."""

from __future__ import annotations

import re
from pathlib import Path

TENANT_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


class InvalidTenantId(ValueError):
    pass


def validate_tenant_id(tenant_id: str) -> str:
    """Return ``tenant_id`` if it is a safe slug, else raise.

    Safe = lowercase letters, digits and inner hyphens, 1–64 chars. This is what
    makes it safe to build per-tenant file paths from it.
    """
    if not isinstance(tenant_id, str) or not TENANT_ID_RE.fullmatch(tenant_id):
        raise InvalidTenantId(f"invalid tenant_id: {tenant_id!r}")
    return tenant_id


def tenant_dir(root: Path, tenant_id: str) -> Path:
    """Per-tenant data directory: ``<root>/tenants/<tenant_id>``."""
    return Path(root) / "tenants" / validate_tenant_id(tenant_id)
