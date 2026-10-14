# Acceptance Matrix

Source: *72 Hour Build: Nightingale Candidate Brief* supplied by the candidate on 2026-08-26.

| Requirement | MVP evidence | Planned automated evidence |
|---|---|---|
| Under-10-second Glance/Top Card | Risks, open actions, recent changes, short reasons, and source links above the timeline | API shape assertions plus demo scenario A |
| Longitudinal Care Note | Ordered manual, patient, system, and three AI-scribed entry types with required metadata | Timeline API tests |
| Inline collaboration | Threaded comment, resolve/unresolve, mention, and assignee | Collaboration permission tests |
| Revision history and revert | Immutable full snapshots, diff view, restore as a new version | `test_revision_history.py` |
| Server-side RBAC | Patient/staff/clinician/admin rules and clinic scoping enforced in dependencies/services | `test_rbac_scope.py` |
| Role ownership | Staff cannot overwrite clinician sections; clinicians cannot overwrite staff notes | `test_rbac_scope.py` |
| Patient-safe output | No internal comments or raw AI-scribed notes in patient responses | `test_rbac_scope.py` |
| Highlight provenance | Every highlight resolves to an entry and exact source span | `test_highlight_provenance.py` |
| Conflict handling | Contradictions are flagged; reviewed clinician facts become authoritative | Conflict service tests and demo |
| Concurrent editing | Different sections update independently; stale same-section write deterministically returns 409 | `test_concurrent_edits.py` |
| PHI redaction before LLM | Names, IC/ID values, phone numbers, and emails are redacted before the AI adapter call | Redaction boundary tests |
| Metadata-only audit | Actor, action, object, version, and timestamp recorded without note content | `test_revision_history.py` |
| Adaptive importance bonus | Pin/accept/reject feedback adjusts bounded topic weights for later suggestions | `test_self_learning_importance.py` |
| Warm P95 at most 300 ms | Repeatable local warm-path benchmark and stated hardware/method | Performance test/script and brief |
| Synthetic data only | Clearly fictional fixtures and UI labeling | Fixture review and README |
| Required communication | Setup/run guide, redaction and RBAC explanations, 2–3 page brief, diagrams, schema, attribution, demo plan | Final deliverables checklist |

## Required filenames

- `tests/test_rbac_scope.py`
- `tests/test_revision_history.py`
- `tests/test_highlight_provenance.py`
- `tests/test_concurrent_edits.py`
- `tests/test_self_learning_importance.py` (bonus)

## Demo acceptance path

1. Staff opens the patient page and reads the Top Card.
2. Staff follows an AI-derived highlight to the exact timeline source.
3. Staff adds a note and mentions a clinician in a comment.
4. Clinician pins an AI-derived phrase and updates the plan.
5. Revision diff, audit metadata, and revert are demonstrated.
6. Historical entries show why recent unresolved and clinician-confirmed facts rank above older context.

