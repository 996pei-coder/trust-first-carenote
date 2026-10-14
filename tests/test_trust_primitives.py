from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_provenance_resolves_to_exact_entry_span(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'trust.db'}")

    with TestClient(app) as client:
        timeline = client.get(
            "/api/patients/1/timeline", headers={"X-User-ID": "3"}
        ).json()
        source = timeline["entries"][0]
        resolved = client.get(
            "/api/provenance/resolve",
            headers={"X-User-ID": "3"},
            params={"pointer": source["provenance_pointer"]},
        )

    assert resolved.status_code == 200
    assert resolved.json()["entry_id"] == source["id"]
    assert resolved.json()["excerpt"] == source["content"]


def test_conflicting_patient_fact_is_flagged_for_clinical_review(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'trust.db'}")

    with TestClient(app) as client:
        patient_fact = client.post(
            "/api/patients/1/entries",
            headers={"X-User-ID": "1"},
            json={
                "entry_type": "patient_insight",
                "section_key": "allergies",
                "title": "Patient-reported allergy",
                "content": "I was told I may be allergic to penicillin.",
                "visibility": "patient",
                "fact_key": "penicillin_allergy",
                "fact_value": "reported",
            },
        )
        clinician_fact = client.post(
            "/api/patients/1/entries",
            headers={"X-User-ID": "3"},
            json={
                "entry_type": "clinician_note",
                "section_key": "allergies",
                "title": "Allergy reconciliation",
                "content": "Penicillin allergy is not yet confirmed; review is required.",
                "visibility": "internal",
                "fact_key": "penicillin_allergy",
                "fact_value": "not_confirmed",
            },
        )
        conflicts = client.get(
            "/api/patients/1/conflicts", headers={"X-User-ID": "2"}
        )
        conflict = conflicts.json()[0]
        forbidden = client.post(
            f"/api/conflicts/{conflict['id']}/resolve",
            headers={"X-User-ID": "2"},
            json={"authoritative_entry_id": clinician_fact.json()["id"]},
        )
        resolved = client.post(
            f"/api/conflicts/{conflict['id']}/resolve",
            headers={"X-User-ID": "3"},
            json={"authoritative_entry_id": clinician_fact.json()["id"]},
        )

    assert patient_fact.status_code == 201
    assert clinician_fact.status_code == 201
    assert conflicts.status_code == 200
    assert conflict["status"] == "open"
    assert forbidden.status_code == 403
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolution_entry_id"] == clinician_fact.json()["id"]

