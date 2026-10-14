"""Versioning, audit, provenance and conflict primitives.

These functions contain no HTTP or UI assumptions, which keeps the trust rules
directly testable and reusable by future HTML routes.
"""

import re
from datetime import datetime
from difflib import unified_diff
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Conflict, Entry, EntryVersion, Role, User


POINTER_PATTERN = re.compile(r"^entry:(?P<entry_id>\d+)#chars=(?P<start>\d+)-(?P<end>\d+)$")


def append_version(
    entry: Entry,
    actor_id: Optional[int],
    reason: str,
) -> EntryVersion:
    snapshot = EntryVersion(
        version=entry.version,
        title_snapshot=entry.title,
        content_snapshot=entry.content,
        visibility_snapshot=entry.visibility,
        section_key_snapshot=entry.section_key,
        fact_key_snapshot=entry.fact_key,
        fact_value_snapshot=entry.fact_value,
        changed_by_id=actor_id,
        change_reason=reason,
    )
    entry.versions.append(snapshot)
    return snapshot


def record_audit(
    session: Session,
    actor: User,
    action: str,
    entry: Entry,
    from_version: Optional[int],
    to_version: Optional[int],
    changed_fields: str,
) -> AuditEvent:
    event = AuditEvent(
        clinic_id=actor.clinic_id,
        actor_id=actor.id,
        action=action,
        object_type="entry",
        object_id=entry.id,
        from_version=from_version,
        to_version=to_version,
        changed_fields=changed_fields,
    )
    session.add(event)
    return event


def get_version(session: Session, entry_id: int, version: int) -> EntryVersion:
    snapshot = session.scalar(
        select(EntryVersion).where(
            EntryVersion.entry_id == entry_id,
            EntryVersion.version == version,
        )
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Entry version not found")
    return snapshot


def render_version_diff(older: EntryVersion, newer: EntryVersion) -> str:
    older_text = f"{older.title_snapshot}\n\n{older.content_snapshot}\n"
    newer_text = f"{newer.title_snapshot}\n\n{newer.content_snapshot}\n"
    return "".join(
        unified_diff(
            older_text.splitlines(keepends=True),
            newer_text.splitlines(keepends=True),
            fromfile=f"version-{older.version}",
            tofile=f"version-{newer.version}",
        )
    )


def parse_provenance_pointer(pointer: str) -> Tuple[int, int, int]:
    match = POINTER_PATTERN.fullmatch(pointer)
    if match is None:
        raise HTTPException(status_code=422, detail="Invalid provenance pointer")
    return tuple(int(match.group(name)) for name in ("entry_id", "start", "end"))


def resolve_provenance(entry: Entry, pointer: str) -> Tuple[int, int, str]:
    entry_id, start, end = parse_provenance_pointer(pointer)
    if entry_id != entry.id or start < 0 or end <= start or end > len(entry.content):
        raise HTTPException(status_code=422, detail="Provenance span does not resolve")
    return start, end, entry.content[start:end]


def detect_fact_conflicts(session: Session, entry: Entry) -> List[Conflict]:
    if entry.author_role != Role.CLINICIAN or not entry.fact_key or not entry.fact_value:
        return []
    prior_entries = list(
        session.scalars(
            select(Entry).where(
                Entry.patient_id == entry.patient_id,
                Entry.id != entry.id,
                Entry.fact_key == entry.fact_key,
                Entry.author_role.in_([Role.PATIENT, Role.SYSTEM]),
            )
        )
    )
    conflicts = []
    for earlier in prior_entries:
        if earlier.fact_value and earlier.fact_value.casefold() != entry.fact_value.casefold():
            conflict = Conflict(
                patient_id=entry.patient_id,
                earlier_entry_id=earlier.id,
                later_entry_id=entry.id,
                reason=(
                    f"Conflicting {entry.fact_key}: earlier source says "
                    f"'{earlier.fact_value}', clinician says '{entry.fact_value}'"
                ),
            )
            session.add(conflict)
            conflicts.append(conflict)
    return conflicts


def resolve_conflict(conflict: Conflict, actor: User, authoritative_entry_id: int) -> None:
    if actor.role not in {Role.CLINICIAN, Role.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinical review required")
    allowed_entries = {conflict.earlier_entry_id, conflict.later_entry_id}
    if authoritative_entry_id not in allowed_entries:
        raise HTTPException(status_code=422, detail="Authoritative entry must belong to the conflict")
    if conflict.status != "open":
        raise HTTPException(status_code=409, detail="Conflict has already been resolved")
    conflict.status = "resolved"
    conflict.resolved_by_id = actor.id
    conflict.resolution_entry_id = authoritative_entry_id
    conflict.resolved_at = datetime.utcnow()
