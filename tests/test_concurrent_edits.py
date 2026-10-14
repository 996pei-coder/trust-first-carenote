from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def _create(client: TestClient, user_id: int, entry_type: str, section: str) -> dict:
    response = client.post(
        "/api/patients/1/entries",
        headers={"X-User-ID": str(user_id)},
        json={
            "entry_type": entry_type,
            "section_key": section,
            "title": f"{section} section",
            "content": "Version one",
            "visibility": "internal",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_different_sections_do_not_overwrite_each_other(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'concurrency.db'}")

    with TestClient(app) as client:
        staff_entry = _create(client, 2, "staff_note", "follow_up")
        clinician_entry = _create(client, 3, "clinician_note", "care_plan")
        staff_update = client.patch(
            f"/api/entries/{staff_entry['id']}",
            headers={"X-User-ID": "2"},
            json={"expected_version": 1, "content": "Staff update"},
        )
        clinician_update = client.patch(
            f"/api/entries/{clinician_entry['id']}",
            headers={"X-User-ID": "3"},
            json={"expected_version": 1, "content": "Clinician update"},
        )

    assert staff_update.status_code == 200
    assert clinician_update.status_code == 200
    assert staff_update.json()["content"] == "Staff update"
    assert clinician_update.json()["content"] == "Clinician update"


def test_same_section_stale_write_is_rejected_deterministically(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'concurrency.db'}")

    with TestClient(app) as client:
        entry = _create(client, 2, "staff_note", "follow_up")
        winner = client.patch(
            f"/api/entries/{entry['id']}",
            headers={"X-User-ID": "2"},
            json={"expected_version": 1, "content": "First writer wins"},
        )
        stale = client.patch(
            f"/api/entries/{entry['id']}",
            headers={"X-User-ID": "2"},
            json={"expected_version": 1, "content": "Stale writer"},
        )

    assert winner.status_code == 200
    assert winner.json()["version"] == 2
    assert stale.status_code == 409
    assert stale.json()["detail"] == "Stale version; reload before editing"

