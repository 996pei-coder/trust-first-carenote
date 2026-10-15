# Trust-first CareNote

A 72-hour Nightingale candidate build focused on three promises:

1. a clinician or staff member can understand the patient's current state in under 10 seconds;
2. every important claim can be traced to its source;
3. role boundaries are enforced by the server, not merely hidden in the UI.

Only synthetic patient data is used.

## Quick start

Requires Python 3.9 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the current API. Run tests with:

```bash
pytest
```

The database is seeded with an explicitly synthetic longitudinal patient story on first start.

The primary demo page is `http://127.0.0.1:8000/demo/patients/1?as_user=2`. Use its role pills to compare patient, staff, clinician, and admin views.

## Deliverables

- [3-page technical brief](output/pdf/trust-first-carenote-technical-brief.pdf)
- [Technical brief source](docs/TECHNICAL_BRIEF.md)
- [Architecture diagram](docs/diagrams/architecture.png)
- [Data model diagram](docs/diagrams/data-model.png)
- [Attribution and licenses](ATTRIBUTION.txt)

## Demo identities and RBAC

Protected requests require an `X-User-ID` header. This header selects a seeded demo identity; it is not presented as production authentication.

| ID | Role |
|---:|---|
| 1 | Patient |
| 2 | Staff |
| 3 | Clinician |
| 4 | Clinic admin |

For example:

```bash
curl -H 'X-User-ID: 3' http://127.0.0.1:8000/api/patients/1/timeline
```

The backend checks clinic scope, patient ownership, entry visibility, entry type, and edit ownership policy on every protected route. Patient timeline responses exclude internal entries and all raw AI-scribed notes. Staff and clinicians cannot create or edit entries owned by the other's role.

## Trust and collaboration API

- Every entry carries an optimistic-lock `version` and an immutable full snapshot per change.
- `PATCH /api/entries/{id}` requires `expected_version`; a stale same-entry write returns HTTP 409.
- `GET /api/entries/{id}/diff` compares any two saved versions.
- `POST /api/entries/{id}/revert` restores a snapshot as a new version, preserving history.
- `GET /api/audit` exposes actor, action, object, versions, timestamp, and changed field names only—never note content.
- `GET /api/provenance/resolve` validates an `entry:{id}#chars={start}-{end}` pointer and returns the exact visible source span.
- Contradictory structured facts from patient/system and clinician entries create a reviewable conflict. Staff can see the flag; only a clinician or admin can choose the authoritative source.

## Redaction before AI

`POST /api/patients/{id}/ai-scribe` implements a strict local boundary:

1. accept a synthetic transcript;
2. redact known names, Singapore-style IC/FIN identifiers, phone numbers, and email addresses;
3. persist only the redacted source artifact and its redacted-content hash;
4. pass only redacted text to the deterministic AI adapter;
5. store the resulting draft as a distinct system-authored AI entry with its source session ID.

The unredacted transcript is never written to the database or audit log. A patient can initiate a patient-session summary but receives only a receipt and redaction counts, never the raw AI entry.

## Top Card and comments

The Top Card shows at most five ranked items, each with a short reason and exact-span provenance pointer. Its transparent score combines risk, unresolved state, recency, and clinician/staff accept, reject, or pin feedback. The timeline supports internal threaded-style comments, mentions, assignments, and resolve/reopen state; all comment APIs reject patient access server-side.

### Bounded self-learning

Each clinic has explainable topic weights rather than an opaque model. Pin adds 8 points, accept adds 4, reject subtracts 6, and a clinician comment on an AI-derived topic adds 1. Weights are bounded from -20 to +30 to prevent runaway feedback. `GET /api/importance/weights` exposes the learned state to clinicians and admins. Manual clinician highlights derive their text from a server-validated source span, so learning cannot break provenance.

### Performance

Run `python scripts/benchmark_glance.py --warmup 20 --iterations 300`. The recorded local warm-path result was P95 **2.09 ms**, compared with the 300 ms requirement. See [docs/PERFORMANCE.md](docs/PERFORMANCE.md) for method and limitations.

## Recording and submission staging

With the demo server stopped, run `python scripts/reset_demo_database.py --confirm` to back up the current local database under ignored `tmp/recording-backups/` and restore the deterministic five-entry synthetic seed. Build the code-only archive and candidate bundle with `python scripts/build_submission.py`. The generated ZIP files live under `output/submission/` and are intentionally not committed.

## Status

Task block 8 has completed the end-to-end demo rehearsal, deterministic recording reset, and reproducible ZIP staging. Video recording and external repository/video links remain candidate-owned final steps. The header-based identity selector remains demo-only; production would replace it with verified session or token authentication while retaining these authorization policies.

See [docs/ACCEPTANCE_MATRIX.md](docs/ACCEPTANCE_MATRIX.md) and [docs/SCOPE.md](docs/SCOPE.md).
