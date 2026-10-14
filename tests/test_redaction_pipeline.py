from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.models import SourceArtifact
from app.redaction import redact_phi


def test_rule_based_phi_redaction_covers_required_identifiers() -> None:
    raw = "Maya Tan, S1234567D, +65 9123 4567, maya.tan@example.com"
    result = redact_phi(raw, known_names=["Maya Tan"])

    assert result.text == "[NAME], [ID], [PHONE], [EMAIL]"
    assert result.counts == {"name": 1, "id": 1, "phone": 1, "email": 1}


def test_labelled_or_titled_unknown_names_are_redacted() -> None:
    result = redact_phi("My name is John Doe and Dr Alice Wong joined the call.")

    assert "John Doe" not in result.text
    assert "Alice Wong" not in result.text
    assert result.counts["name"] == 2


def test_scribe_persists_only_redacted_source_before_ai_boundary(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'redaction.db'}")
    raw = "Maya Tan called from +65 9123 4567; email maya.tan@example.com."

    with TestClient(app) as client:
        response = client.post(
            "/api/patients/1/ai-scribe",
            headers={"X-User-ID": "3"},
            json={
                "interaction_type": "ai_doctor_consult_summary",
                "session_id": "redaction-boundary-test",
                "raw_text": raw,
            },
        )
        with app.state.session_factory() as session:
            artifact = session.scalar(
                select(SourceArtifact).where(SourceArtifact.session_id == "redaction-boundary-test")
            )
            stored_text = artifact.redacted_text

    assert response.status_code == 201
    assert response.json()["redaction_counts"] == {
        "name": 1,
        "id": 0,
        "phone": 1,
        "email": 1,
    }
    assert "Maya Tan" not in stored_text
    assert "9123" not in stored_text
    assert "example.com" not in stored_text
    assert raw not in response.text


def test_patient_does_not_receive_raw_ai_entry(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'patient-scribe.db'}")

    with TestClient(app) as client:
        response = client.post(
            "/api/patients/1/ai-scribe",
            headers={"X-User-ID": "1"},
            json={
                "interaction_type": "ai_patient_session_summary",
                "session_id": "patient-ai-session-test",
                "raw_text": "Maya Tan asks a synthetic follow-up question.",
            },
        )

    assert response.status_code == 201
    assert response.json()["entry"] is None
