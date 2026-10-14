from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


CLINICIAN = {"X-User-ID": "3"}


def test_every_top_card_highlight_resolves_to_exact_timeline_span(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'highlights.db'}")

    with TestClient(app) as client:
        top_card = client.get("/api/patients/1/top-card", headers=CLINICIAN)
        for highlight in top_card.json()["highlights"]:
            resolved = client.get(
                "/api/provenance/resolve",
                headers=CLINICIAN,
                params={"pointer": highlight["provenance_pointer"]},
            )
            assert resolved.status_code == 200
            assert resolved.json()["entry_id"] == highlight["entry_id"]
            assert resolved.json()["excerpt"] == highlight["text"]

    assert top_card.status_code == 200
    assert len(top_card.json()["highlights"]) >= 3


def test_clinician_can_pin_a_suggestion(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'highlights.db'}")

    with TestClient(app) as client:
        top_card = client.get("/api/patients/1/top-card", headers=CLINICIAN).json()
        target = top_card["highlights"][0]
        pinned = client.post(
            f"/api/highlights/{target['id']}/action",
            headers=CLINICIAN,
            json={"action": "pin"},
        )

    assert pinned.status_code == 200
    assert pinned.json()["status"] == "pinned"
    assert pinned.json()["importance_score"] >= target["importance_score"]

