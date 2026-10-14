"""Relational model for the longitudinal Care Note trust graph."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.utcnow()


class Role(str, Enum):
    PATIENT = "patient"
    STAFF = "staff"
    CLINICIAN = "clinician"
    ADMIN = "admin"
    SYSTEM = "system"


class EntryType(str, Enum):
    PATIENT_INSIGHT = "patient_insight"
    STAFF_NOTE = "staff_note"
    CLINICIAN_NOTE = "clinician_note"
    AI_DOCTOR_CONSULT_SUMMARY = "ai_doctor_consult_summary"
    AI_NURSE_CONSULT_SUMMARY = "ai_nurse_consult_summary"
    AI_PATIENT_SESSION_SUMMARY = "ai_patient_session_summary"
    SYSTEM_EVENT = "system_event"


class Visibility(str, Enum):
    PATIENT = "patient"
    INTERNAL = "internal"


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)

    users: Mapped[List["User"]] = relationship(back_populates="clinic")
    patients: Mapped[List["Patient"]] = relationship(back_populates="clinic")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(SqlEnum(Role, native_enum=False), index=True)

    clinic: Mapped[Clinic] = relationship(back_populates="users")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    medical_record_number: Mapped[str] = mapped_column(String(40), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    date_of_birth: Mapped[str] = mapped_column(String(10))
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True)

    clinic: Mapped[Clinic] = relationship(back_populates="patients")
    user: Mapped[User] = relationship()
    entries: Mapped[List["Entry"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", order_by="Entry.occurred_at"
    )
    source_artifacts: Mapped[List["SourceArtifact"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class SourceArtifact(Base):
    __tablename__ = "source_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[str] = mapped_column(String(120), unique=True)
    interaction_type: Mapped[EntryType] = mapped_column(SqlEnum(EntryType, native_enum=False))
    redacted_text: Mapped[str] = mapped_column(Text)
    redacted_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    patient: Mapped[Patient] = relationship(back_populates="source_artifacts")


class Entry(Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    author_role: Mapped[Role] = mapped_column(SqlEnum(Role, native_enum=False), index=True)
    entry_type: Mapped[EntryType] = mapped_column(SqlEnum(EntryType, native_enum=False), index=True)
    visibility: Mapped[Visibility] = mapped_column(SqlEnum(Visibility, native_enum=False), index=True)
    section_key: Mapped[str] = mapped_column(String(80), default="timeline")
    title: Mapped[str] = mapped_column(String(180))
    content: Mapped[str] = mapped_column(Text)
    fact_key: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    fact_value: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    source_session_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    provenance_pointer: Mapped[str] = mapped_column(String(200))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    patient: Mapped[Patient] = relationship(back_populates="entries")
    author: Mapped[Optional[User]] = relationship()
    versions: Mapped[List["EntryVersion"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", order_by="EntryVersion.version"
    )
    comments: Mapped[List["Comment"]] = relationship(back_populates="entry", cascade="all, delete-orphan")
    highlights: Mapped[List["Highlight"]] = relationship(back_populates="entry", cascade="all, delete-orphan")


class EntryVersion(Base):
    __tablename__ = "entry_versions"
    __table_args__ = (UniqueConstraint("entry_id", "version", name="uq_entry_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    title_snapshot: Mapped[str] = mapped_column(String(180))
    content_snapshot: Mapped[str] = mapped_column(Text)
    visibility_snapshot: Mapped[Visibility] = mapped_column(SqlEnum(Visibility, native_enum=False))
    section_key_snapshot: Mapped[str] = mapped_column(String(80))
    fact_key_snapshot: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    fact_value_snapshot: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    changed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    change_reason: Mapped[str] = mapped_column(String(160), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    entry: Mapped[Entry] = relationship(back_populates="versions")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    mention_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_to_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    entry: Mapped[Entry] = relationship(back_populates="comments")


class Highlight(Base):
    __tablename__ = "highlights"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"), index=True)
    source_start: Mapped[int] = mapped_column(Integer)
    source_end: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String(20), default="info")
    risk_reason: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(20), default="suggested")
    topic: Mapped[str] = mapped_column(String(80), default="general", index=True)
    unresolved: Mapped[bool] = mapped_column(Boolean, default=True)
    importance_score: Mapped[int] = mapped_column(Integer, default=0)
    provenance_pointer: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    entry: Mapped[Entry] = relationship(back_populates="highlights")


class TopicWeight(Base):
    __tablename__ = "topic_weights"
    __table_args__ = (UniqueConstraint("clinic_id", "topic", name="uq_clinic_topic_weight"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), index=True)
    topic: Mapped[str] = mapped_column(String(80), index=True)
    weight: Mapped[int] = mapped_column(Integer, default=0)
    feedback_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), index=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    object_type: Mapped[str] = mapped_column(String(80))
    object_id: Mapped[int] = mapped_column(Integer)
    from_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    to_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    changed_fields: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Conflict(Base):
    __tablename__ = "conflicts"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    earlier_entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"))
    later_entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"))
    reason: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(20), default="open")
    resolved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolution_entry_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entries.id"), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
