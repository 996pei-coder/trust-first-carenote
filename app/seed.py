"""Small, deterministic and explicitly synthetic demo story."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Clinic,
    Comment,
    Entry,
    EntryType,
    EntryVersion,
    Highlight,
    Patient,
    Role,
    User,
    Visibility,
)


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def seed_database(session: Session) -> None:
    if session.scalar(select(Clinic.id).limit(1)) is not None:
        return

    clinic = Clinic(name="Harbour Family Clinic (Synthetic)")
    users = [
        User(id=1, clinic=clinic, display_name="Maya Tan (patient demo)", role=Role.PATIENT),
        User(id=2, clinic=clinic, display_name="Aisha Rahman (staff demo)", role=Role.STAFF),
        User(id=3, clinic=clinic, display_name="Dr Daniel Lim (clinician demo)", role=Role.CLINICIAN),
        User(id=4, clinic=clinic, display_name="Clinic Admin (demo)", role=Role.ADMIN),
    ]
    patient = Patient(
        id=1,
        clinic=clinic,
        user_id=1,
        medical_record_number="SYN-NTG-0001",
        display_name="Maya Tan (Synthetic)",
        date_of_birth="1988-04-12",
        synthetic=True,
    )

    entry_specs = [
        dict(
            id=1,
            author_id=None,
            author_role=Role.SYSTEM,
            entry_type=EntryType.AI_PATIENT_SESSION_SUMMARY,
            visibility=Visibility.INTERNAL,
            section_key="patient_context",
            title="Pre-visit AI patient session",
            content="Patient reports three weeks of worsening night cough and asks whether the new symptom could be medication-related.",
            source_session_id="ai-patient-session-2025-04-15",
            occurred_at=_dt("2025-04-15T09:10:00"),
        ),
        dict(
            id=2,
            author_id=3,
            author_role=Role.CLINICIAN,
            entry_type=EntryType.CLINICIAN_NOTE,
            visibility=Visibility.PATIENT,
            section_key="assessment",
            title="Clinician assessment",
            content="Night cough reviewed. No breathlessness or fever. Trial medication adjustment discussed with safety-net instructions.",
            source_session_id=None,
            occurred_at=_dt("2025-04-15T10:05:00"),
        ),
        dict(
            id=3,
            author_id=None,
            author_role=Role.SYSTEM,
            entry_type=EntryType.AI_DOCTOR_CONSULT_SUMMARY,
            visibility=Visibility.INTERNAL,
            section_key="consult_summary",
            title="AI-scribed doctor consult summary",
            content="Persistent night cough. Clinician advised medication review and urgent assessment if breathlessness develops.",
            source_session_id="doctor-consult-2025-04-15",
            occurred_at=_dt("2025-04-15T10:08:00"),
        ),
        dict(
            id=4,
            author_id=None,
            author_role=Role.SYSTEM,
            entry_type=EntryType.AI_NURSE_CONSULT_SUMMARY,
            visibility=Visibility.INTERNAL,
            section_key="nurse_follow_up",
            title="AI-scribed nurse follow-up",
            content="Home readings reviewed. One elevated blood pressure reading of 158/96; repeat measurement and clinician review remain open.",
            source_session_id="nurse-consult-2026-02-06",
            occurred_at=_dt("2026-02-06T14:30:00"),
        ),
        dict(
            id=5,
            author_id=2,
            author_role=Role.STAFF,
            entry_type=EntryType.STAFF_NOTE,
            visibility=Visibility.INTERNAL,
            section_key="open_actions",
            title="Follow-up action",
            content="Call patient for repeat blood pressure reading and route result to clinician by 7 February.",
            source_session_id=None,
            occurred_at=_dt("2026-02-06T14:42:00"),
        ),
    ]

    entries = []
    for spec in entry_specs:
        entry = Entry(patient=patient, version=1, **spec)
        entry.provenance_pointer = f"entry:{entry.id}#chars=0-{len(entry.content)}"
        entry.versions.append(
            EntryVersion(
                version=1,
                title_snapshot=entry.title,
                content_snapshot=entry.content,
                visibility_snapshot=entry.visibility,
                section_key_snapshot=entry.section_key,
                fact_key_snapshot=entry.fact_key,
                fact_value_snapshot=entry.fact_value,
                changed_by_id=entry.author_id,
                change_reason="seeded synthetic entry",
                created_at=entry.occurred_at,
            )
        )
        entries.append(entry)

    highlight_specs = [
        (
            entries[3],
            "One elevated blood pressure reading of 158/96",
            "high",
            "Elevated reading needs repeat measurement and clinician review.",
            "blood_pressure",
        ),
        (
            entries[4],
            "Call patient for repeat blood pressure reading",
            "high",
            "Unresolved staff action has a near-term deadline.",
            "follow_up",
        ),
        (
            entries[1],
            "safety-net instructions",
            "medium",
            "Clinician-confirmed escalation guidance.",
            "safety_net",
        ),
    ]
    highlights = []
    for highlight_id, (entry, phrase, risk, reason, topic) in enumerate(highlight_specs, start=1):
        start = entry.content.index(phrase)
        highlights.append(
            Highlight(
                id=highlight_id,
                patient_id=patient.id,
                entry=entry,
                source_start=start,
                source_end=start + len(phrase),
                text=phrase,
                risk_level=risk,
                risk_reason=reason,
                topic=topic,
                unresolved=True,
                provenance_pointer=f"entry:{entry.id}#chars={start}-{start + len(phrase)}",
            )
        )

    demo_comment = Comment(
        id=1,
        entry=entries[4],
        author_id=2,
        body="@Dr Daniel Lim Please review after the repeat reading is available.",
        mention_user_id=3,
        assigned_to_id=3,
    )

    session.add_all([clinic, *users, patient, *entries, *highlights, demo_comment])
    session.commit()
