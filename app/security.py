"""Pure authorization policy functions used by every protected route."""

from fastapi import HTTPException, status

from app.models import Entry, EntryType, Patient, Role, User, Visibility


AI_ENTRY_TYPES = {
    EntryType.AI_DOCTOR_CONSULT_SUMMARY,
    EntryType.AI_NURSE_CONSULT_SUMMARY,
    EntryType.AI_PATIENT_SESSION_SUMMARY,
}


def require_patient_access(actor: User, patient: Patient) -> None:
    """Return 404 for out-of-scope records so their existence is not disclosed."""
    same_clinic = actor.clinic_id == patient.clinic_id
    owns_record = actor.role != Role.PATIENT or patient.user_id == actor.id
    if not same_clinic or not owns_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")


def can_view_entry(actor: User, entry: Entry) -> bool:
    if actor.role in {Role.CLINICIAN, Role.ADMIN}:
        return True
    if actor.role == Role.STAFF:
        return entry.entry_type != EntryType.CLINICIAN_NOTE or entry.visibility == Visibility.PATIENT
    if actor.role == Role.PATIENT:
        return entry.visibility == Visibility.PATIENT and entry.entry_type not in AI_ENTRY_TYPES
    return False


def require_create_permission(actor: User, entry_type: EntryType) -> None:
    allowed_type = {
        Role.PATIENT: EntryType.PATIENT_INSIGHT,
        Role.STAFF: EntryType.STAFF_NOTE,
        Role.CLINICIAN: EntryType.CLINICIAN_NOTE,
    }.get(actor.role)
    if entry_type != allowed_type:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{actor.role.value} cannot create {entry_type.value}",
        )


def require_edit_permission(actor: User, entry: Entry) -> None:
    editable_type = {
        Role.PATIENT: EntryType.PATIENT_INSIGHT,
        Role.STAFF: EntryType.STAFF_NOTE,
        Role.CLINICIAN: EntryType.CLINICIAN_NOTE,
    }.get(actor.role)
    owns_patient_entry = actor.role != Role.PATIENT or entry.author_id == actor.id
    if entry.entry_type != editable_type or not owns_patient_entry:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role boundary prevents editing this entry",
        )


def normalized_visibility(actor: User, requested: Visibility) -> Visibility:
    if actor.role == Role.PATIENT:
        return Visibility.PATIENT
    if actor.role == Role.STAFF:
        return Visibility.INTERNAL
    return requested

