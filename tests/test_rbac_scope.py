from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import Clinic, EntryType, Patient, Role, User


def _headers(user_id: int) -> dict:
    return {"X-User-ID": str(user_id)}


def _new_entry(entry_type: str) -> dict:
    return {
        "entry_type": entry_type,
        "section_key": "follow_up",
        "title": "Role boundary test",
        "content": "Synthetic test content",
        "visibility": "internal",
    }


def test_authentication_and_patient_safe_timeline(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'rbac.db'}")

    with TestClient(app) as client:
        assert client.get("/api/patients").status_code == 401
        patient_view = client.get("/api/patients/1/timeline", headers=_headers(1))

    assert patient_view.status_code == 200
    entries = patient_view.json()["entries"]
    assert entries
    assert all(entry["visibility"] == "patient" for entry in entries)
    assert all(not entry["entry_type"].startswith("ai_") for entry in entries)
    assert all("comments" not in entry for entry in entries)


def test_staff_and_clinician_cannot_write_as_each_other(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'rbac.db'}")

    with TestClient(app) as client:
        staff_note = client.post(
            "/api/patients/1/entries", json=_new_entry("staff_note"), headers=_headers(2)
        )
        clinician_note = client.post(
            "/api/patients/1/entries", json=_new_entry("clinician_note"), headers=_headers(3)
        )
        staff_as_clinician = client.post(
            "/api/patients/1/entries", json=_new_entry("clinician_note"), headers=_headers(2)
        )
        clinician_as_staff = client.post(
            "/api/patients/1/entries", json=_new_entry("staff_note"), headers=_headers(3)
        )
        staff_edits_clinician = client.patch(
            f"/api/entries/{clinician_note.json()['id']}",
            json={"expected_version": 1, "content": "Not allowed"},
            headers=_headers(2),
        )
        clinician_edits_staff = client.patch(
            f"/api/entries/{staff_note.json()['id']}",
            json={"expected_version": 1, "content": "Not allowed"},
            headers=_headers(3),
        )

    assert staff_note.status_code == 201
    assert clinician_note.status_code == 201
    assert staff_as_clinician.status_code == 403
    assert clinician_as_staff.status_code == 403
    assert staff_edits_clinician.status_code == 403
    assert clinician_edits_staff.status_code == 403


def test_clinic_scope_is_enforced_without_record_disclosure(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'rbac.db'}")

    with TestClient(app) as client:
        with app.state.session_factory() as session:
            other_clinic = Clinic(id=2, name="Other Clinic (Synthetic)")
            other_staff = User(
                id=20,
                clinic=other_clinic,
                display_name="Other Staff",
                role=Role.STAFF,
            )
            other_patient_user = User(
                id=21,
                clinic=other_clinic,
                display_name="Other Patient",
                role=Role.PATIENT,
            )
            other_patient = Patient(
                id=20,
                clinic=other_clinic,
                user=other_patient_user,
                medical_record_number="SYN-OTHER-1",
                display_name="Other Patient (Synthetic)",
                date_of_birth="1990-01-01",
                synthetic=True,
            )
            session.add_all([other_clinic, other_staff, other_patient_user, other_patient])
            session.commit()

        own_list = client.get("/api/patients", headers=_headers(2))
        foreign_read = client.get("/api/patients/20/timeline", headers=_headers(2))
        foreign_write = client.post(
            "/api/patients/1/entries", json=_new_entry("staff_note"), headers=_headers(20)
        )

    assert [patient["id"] for patient in own_list.json()] == [1]
    assert foreign_read.status_code == 404
    assert foreign_write.status_code == 404
