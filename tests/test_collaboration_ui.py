from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_internal_comment_assignment_and_resolution(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'comments.db'}")

    with TestClient(app) as client:
        created = client.post(
            "/api/entries/5/comments",
            headers={"X-User-ID": "2"},
            json={"body": "Please review the repeat reading.", "mention_user_id": 3, "assigned_to_id": 3},
        )
        patient_read = client.get(
            "/api/entries/5/comments", headers={"X-User-ID": "1"}
        )
        resolved = client.patch(
            f"/api/comments/{created.json()['id']}",
            headers={"X-User-ID": "3"},
            json={"resolved": True},
        )

    assert created.status_code == 201
    assert created.json()["assigned_to_id"] == 3
    assert patient_read.status_code == 403
    assert resolved.status_code == 200
    assert resolved.json()["resolved"] is True


def test_demo_page_has_top_card_timeline_and_patient_safe_view(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'ui.db'}")

    with TestClient(app) as client:
        staff_page = client.get("/demo/patients/1?as_user=2")
        patient_page = client.get("/demo/patients/1?as_user=1")

    assert staff_page.status_code == 200
    assert "What needs attention now" in staff_page.text
    assert "One elevated blood pressure reading of 158/96" in staff_page.text
    assert 'id="entry-4"' in staff_page.text
    assert patient_page.status_code == 200
    assert "Your shared summary" in patient_page.text
    assert "doctor-consult-2025-04-15" not in patient_page.text
    assert "@Dr Daniel Lim" not in patient_page.text

