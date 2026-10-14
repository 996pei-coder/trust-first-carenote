"""Response shapes deliberately expose provenance as first-class data."""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import EntryType, Role, Visibility


class PatientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medical_record_number: str
    display_name: str
    date_of_birth: str
    synthetic: bool


class TimelineEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_id: Optional[int]
    author_role: Role
    entry_type: EntryType
    visibility: Visibility
    section_key: str
    title: str
    content: str
    fact_key: Optional[str]
    fact_value: Optional[str]
    version: int
    source_session_id: Optional[str]
    provenance_pointer: str
    occurred_at: datetime


class PatientTimeline(BaseModel):
    patient: PatientSummary
    entries: List[TimelineEntry]


class HealthResponse(BaseModel):
    status: str
    service: str


class ActorSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clinic_id: int
    display_name: str
    role: Role


class EntryCreate(BaseModel):
    entry_type: EntryType
    section_key: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1, max_length=20_000)
    visibility: Visibility = Visibility.INTERNAL
    fact_key: Optional[str] = Field(default=None, min_length=1, max_length=80)
    fact_value: Optional[str] = Field(default=None, min_length=1, max_length=160)

    @model_validator(mode="after")
    def fact_fields_are_a_pair(self) -> "EntryCreate":
        if (self.fact_key is None) != (self.fact_value is None):
            raise ValueError("fact_key and fact_value must be supplied together")
        return self


class EntryUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    title: Optional[str] = Field(default=None, min_length=1, max_length=180)
    content: Optional[str] = Field(default=None, min_length=1, max_length=20_000)
    visibility: Optional[Visibility] = None


class EntryVersionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    title_snapshot: str
    content_snapshot: str
    visibility_snapshot: Visibility
    section_key_snapshot: str
    fact_key_snapshot: Optional[str]
    fact_value_snapshot: Optional[str]
    changed_by_id: Optional[int]
    change_reason: str
    created_at: datetime


class VersionDiff(BaseModel):
    entry_id: int
    from_version: int
    to_version: int
    unified_diff: str


class RevertRequest(BaseModel):
    target_version: int = Field(ge=1)
    expected_version: int = Field(ge=1)


class AuditEventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: Optional[int]
    action: str
    object_type: str
    object_id: int
    from_version: Optional[int]
    to_version: Optional[int]
    changed_fields: str
    created_at: datetime


class ProvenanceResolution(BaseModel):
    pointer: str
    entry_id: int
    entry_version: int
    source_start: int
    source_end: int
    excerpt: str


class ConflictSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    earlier_entry_id: int
    later_entry_id: int
    reason: str
    status: str
    resolved_by_id: Optional[int]
    resolution_entry_id: Optional[int]
    created_at: datetime
    resolved_at: Optional[datetime]


class ConflictResolveRequest(BaseModel):
    authoritative_entry_id: int


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2_000)
    mention_user_id: Optional[int] = None
    assigned_to_id: Optional[int] = None


class CommentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_id: int
    author_id: int
    body: str
    mention_user_id: Optional[int]
    assigned_to_id: Optional[int]
    resolved: bool
    created_at: datetime


class CommentState(BaseModel):
    resolved: bool


class HighlightSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_id: int
    text: str
    risk_level: str
    risk_reason: str
    status: str
    topic: str
    unresolved: bool
    importance_score: int
    provenance_pointer: str


class TopCard(BaseModel):
    patient_id: int
    headline: str
    highlights: List[HighlightSummary]
    open_conflicts: int


class HighlightAction(BaseModel):
    action: Literal["accept", "reject", "pin"]


class HighlightCreate(BaseModel):
    source_start: int = Field(ge=0)
    source_end: int = Field(gt=0)
    risk_level: Literal["critical", "high", "medium", "low", "info"] = "info"
    risk_reason: str = Field(min_length=1, max_length=240)
    topic: str = Field(min_length=1, max_length=80)


class TopicWeightSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic: str
    weight: int
    feedback_count: int
    updated_at: datetime


class ScribeRequest(BaseModel):
    interaction_type: EntryType
    session_id: str = Field(min_length=3, max_length=120)
    raw_text: str = Field(min_length=1, max_length=30_000)


class ScribeResult(BaseModel):
    entry_id: int
    entry: Optional[TimelineEntry]
    redaction_counts: Dict[str, int]
