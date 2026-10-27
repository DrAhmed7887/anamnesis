"""The single report artifact for one intake, with referential integrity checks."""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from anamnesis.schema.evidence import AudioTurn, ImageRegion
from anamnesis.schema.findings import Finding
from anamnesis.schema.medication import PackObservation, PatientClaim


class AgentAction(StrEnum):
    """Fixed vocabulary of loop steps; no model chooses among them."""

    TRANSCRIBE = "transcribe"
    EXTRACT_CLAIMS = "extract_claims"
    SEGMENT = "segment"
    READ = "read"
    ZOOM_READ = "zoom_read"
    RECONCILE = "reconcile"
    BUDGET_EXHAUSTED = "budget_exhausted"


class AgentStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int = Field(ge=0)
    action: AgentAction
    target: str
    outcome: str
    call_ids: list[str] = Field(default_factory=list)


class ReconciliationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intake_id: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    turns: list[AudioTurn]
    claims: list[PatientClaim]
    regions: list[ImageRegion]
    observations: list[PackObservation]
    findings: list[Finding]
    steps: list[AgentStep]
    calls: int = Field(ge=0)
    spend_usd: Decimal = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def check_references(self) -> "ReconciliationReport":
        turn_ids = {turn.turn_id for turn in self.turns}
        region_ids = {region.region_id for region in self.regions}
        claim_ids = {claim.claim_id for claim in self.claims}
        observation_ids = {obs.observation_id for obs in self.observations}
        problems = [
            *(f"claim {c.claim_id}: {t}" for c in self.claims for t in c.audio_evidence if t not in turn_ids),
            *(f"observation {o.observation_id}: {r}" for o in self.observations
              for r in o.visual_evidence if r not in region_ids),
            *(f"finding {f.finding_id}: {t}" for f in self.findings for t in f.audio_evidence
              if t not in turn_ids),
            *(f"finding {f.finding_id}: {r}" for f in self.findings for r in f.visual_evidence
              if r not in region_ids),
            *(f"finding {f.finding_id}: claim {f.claim_id}" for f in self.findings
              if f.claim_id is not None and f.claim_id not in claim_ids),
            *(f"finding {f.finding_id}: observation {f.observation_id}" for f in self.findings
              if f.observation_id is not None and f.observation_id not in observation_ids),
        ]
        if problems:
            raise ValueError("dangling references: " + "; ".join(problems))
        return self
