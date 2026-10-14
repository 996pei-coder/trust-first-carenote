from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.importance import calculate_importance
from app.main import create_app
from app.models import Entry, Highlight


CLINICIAN = {"X-User-ID": "3"}


def test_pinning_topic_increases_priority_of_later_similar_suggestion(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'learning.db'}")

    with TestClient(app) as client:
        initial = client.get("/api/patients/1/top-card", headers=CLINICIAN).json()
        blood_pressure = next(
            item for item in initial["highlights"] if item["topic"] == "blood_pressure"
        )
        pinned = client.post(
            f"/api/highlights/{blood_pressure['id']}/action",
            headers=CLINICIAN,
            json={"action": "pin"},
        )
        weights = client.get("/api/importance/weights", headers=CLINICIAN).json()

        with app.state.session_factory() as session:
            source = session.get(Entry, 4)
            phrase = "repeat measurement"
            start = source.content.index(phrase)
            suggestion = Highlight(
                patient_id=1,
                entry_id=source.id,
                source_start=start,
                source_end=start + len(phrase),
                text=phrase,
                risk_level="info",
                risk_reason="Similar blood-pressure follow-up topic.",
                status="suggested",
                topic="blood_pressure",
                unresolved=False,
                provenance_pointer=f"entry:{source.id}#chars={start}-{start + len(phrase)}",
            )
            session.add(suggestion)
            session.commit()
            suggestion_id = suggestion.id
            score_without_learning = calculate_importance(
                suggestion, now=datetime.utcnow(), topic_weight=0
            )

        subsequent = client.get("/api/patients/1/top-card", headers=CLINICIAN).json()
        learned_suggestion = next(
            item for item in subsequent["highlights"] if item["id"] == suggestion_id
        )

    assert pinned.status_code == 200
    learned = next(item for item in weights if item["topic"] == "blood_pressure")
    assert learned["weight"] == 8
    assert learned["feedback_count"] == 1
    assert learned_suggestion["importance_score"] == score_without_learning + 8


def test_manual_clinician_highlight_uses_server_derived_exact_span(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'manual-highlight.db'}")

    with TestClient(app) as client:
        timeline = client.get("/api/patients/1/timeline", headers=CLINICIAN).json()
        ai_entry = next(
            entry
            for entry in timeline["entries"]
            if entry["entry_type"] == "ai_doctor_consult_summary"
        )
        phrase = "urgent assessment"
        start = ai_entry["content"].index(phrase)
        created = client.post(
            f"/api/entries/{ai_entry['id']}/highlights",
            headers=CLINICIAN,
            json={
                "source_start": start,
                "source_end": start + len(phrase),
                "risk_level": "medium",
                "risk_reason": "Clinician confirmed escalation language.",
                "topic": "safety_net",
            },
        )
        resolved = client.get(
            "/api/provenance/resolve",
            headers=CLINICIAN,
            params={"pointer": created.json()["provenance_pointer"]},
        )

    assert created.status_code == 201
    assert created.json()["text"] == phrase
    assert created.json()["status"] == "pinned"
    assert resolved.json()["excerpt"] == phrase

