from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


STAFF = {"X-User-ID": "2"}
CLINICIAN = {"X-User-ID": "3"}


def _create_staff_note(client: TestClient) -> dict:
    response = client.post(
        "/api/patients/1/entries",
        headers=STAFF,
        json={
            "entry_type": "staff_note",
            "section_key": "open_actions",
            "title": "Initial action",
            "content": "Call patient tomorrow.",
            "visibility": "internal",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_edit_increments_version_and_diff_is_available(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'revision.db'}")

    with TestClient(app) as client:
        entry = _create_staff_note(client)
        edited = client.patch(
            f"/api/entries/{entry['id']}",
            headers=STAFF,
            json={"expected_version": 1, "content": "Call patient today and record outcome."},
        )
        versions = client.get(f"/api/entries/{entry['id']}/versions", headers=STAFF)
        diff = client.get(
            f"/api/entries/{entry['id']}/diff",
            headers=STAFF,
            params={"from_version": 1, "to_version": 2},
        )

    assert edited.status_code == 200
    assert edited.json()["version"] == 2
    assert [item["version"] for item in versions.json()] == [2, 1]
    assert "-Call patient tomorrow." in diff.json()["unified_diff"]
    assert "+Call patient today and record outcome." in diff.json()["unified_diff"]


def test_revert_restores_content_as_new_version_and_audit_is_metadata_only(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'revision.db'}")

    with TestClient(app) as client:
        entry = _create_staff_note(client)
        client.patch(
            f"/api/entries/{entry['id']}",
            headers=STAFF,
            json={"expected_version": 1, "content": "Changed content."},
        )
        reverted = client.post(
            f"/api/entries/{entry['id']}/revert",
            headers=STAFF,
            json={"target_version": 1, "expected_version": 2},
        )
        audit = client.get("/api/audit", headers=CLINICIAN, params={"object_id": entry["id"]})

    assert reverted.status_code == 200
    assert reverted.json()["version"] == 3
    assert reverted.json()["content"] == "Call patient tomorrow."
    events = audit.json()
    assert {event["action"] for event in events} == {
        "entry.created",
        "entry.edited",
        "entry.reverted",
    }
    assert all(event["actor_id"] == 2 for event in events)
    assert all("content" not in event and "title" not in event for event in events)
    assert {event["changed_fields"] for event in events} == {
        "entry",
        "content",
        "title,content,visibility,section_key,facts",
    }
