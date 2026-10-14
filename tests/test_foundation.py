from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_and_seeded_timeline(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")

    with TestClient(app) as client:
        health = client.get("/health")
        timeline = client.get("/api/patients/1/timeline", headers={"X-User-ID": "3"})

    assert health.json() == {"status": "ok", "service": "trust-first-carenote"}
    assert timeline.status_code == 200
    payload = timeline.json()
    assert payload["patient"]["synthetic"] is True
    assert len(payload["entries"]) == 5
    assert {
        "ai_doctor_consult_summary",
        "ai_nurse_consult_summary",
        "ai_patient_session_summary",
    }.issubset({entry["entry_type"] for entry in payload["entries"]})
    assert all(entry["provenance_pointer"].startswith("entry:") for entry in payload["entries"])


def test_unknown_patient_is_404(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")

    with TestClient(app) as client:
        response = client.get("/api/patients/999/timeline", headers={"X-User-ID": "3"})

    assert response.status_code == 404


def test_timeline_rejects_non_integer_patient_id(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")

    with TestClient(app) as client:
        response = client.get("/api/patients/not-an-id/timeline", headers={"X-User-ID": "3"})

    assert response.status_code == 422
    payload = response.json()
    assert isinstance(payload["detail"], list)
    assert any(error["loc"] == ["path", "patient_id"] for error in payload["detail"])
    assert "patient" not in payload
    assert "entries" not in payload
