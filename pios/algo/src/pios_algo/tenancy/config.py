"""Per-tenant config: account limits, approved strategy versions, sector map. Loaded from the tenant's repo.

No secrets here — broker keys come from the SecretStore port (SSM + per-tenant KMS, ADR-002 A4).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from pios_algo.core.risk import AccountLimits
from pios_algo.core.strategy_api import ApprovedVersion
from pios_algo.tenancy import TENANT_ID_RE


class ApprovedEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    param_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    approved_by: str
    approved_at: str

    def as_approved(self) -> ApprovedVersion:
        return ApprovedVersion(self.id, self.version, self.param_hash)


class TenantConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: str = Field(pattern=TENANT_ID_RE.pattern)
    account_limits: AccountLimits
    approved: list[ApprovedEntry] = Field(default_factory=list)
    sectors: dict[str, str] = Field(default_factory=dict)
    specs_dir: str = "specs"

    def approved_versions(self) -> list[ApprovedVersion]:
        return [a.as_approved() for a in self.approved]


def load_tenant_config(path: Path | str) -> TenantConfig:
    return TenantConfig.model_validate_json(Path(path).read_text(encoding="utf-8"))
