# MVP Scope and Decisions

## Product thesis

The prototype is a trust system, not a generic collaborative document. It gives clinicians and staff a concise Top Card while preserving a direct route from every highlight to the originating timeline entry and span.

## In scope

- One clinic with multiple synthetic patients; the demo centers on one longitudinal patient story.
- Four roles: patient, staff, clinician, and clinic admin.
- Server-side, clinic-scoped RBAC.
- A single longitudinal timeline containing manual, system, and three distinct AI-scribed entry types.
- A patient-safe view that excludes internal comments and raw AI-scribed notes.
- Top Card with critical risks, unresolved actions, recent changes, and provenance links.
- Deterministic importance scoring based on risk, recency, clinical entities, unresolved work, and clinician interaction.
- Accept/reject/pin interactions for highlight suggestions, with a small adaptive topic-weight mechanism.
- Threaded comments with resolve state, optional mention, and assignment.
- Full note snapshots, version comparison, revert, and metadata-only audit events.
- Optimistic concurrency using section version numbers. Different sections can be edited independently; a stale same-section write returns HTTP 409.
- Conflict flagging when clinician facts contradict AI- or patient-originated facts; clinician-confirmed information wins only after an explicit review action.
- Rule-based redaction of names, Singapore-style IC/ID values, phone numbers, and email addresses before the simulated LLM boundary.
- Warm-path Top Card latency measurement with a P95 target of 300 ms or less.

## Deliberately out of scope

- Voice recording, transcription, diarization, noisy-room handling, and multilingual capture.
- Real EHR/FHIR integrations and real patient data.
- Production identity provider, billing, multi-region deployment, or full multi-tenancy.
- A real external LLM dependency; AI output is deterministic for repeatable tests and demos.
- Complex machine learning, embeddings, vector databases, and full historical data-decay implementation.
- Native mobile apps, rich-text CRDT collaboration, and WebSocket presence.

## Security assumptions

- Authentication is represented by seeded demo identities; authorization still occurs on every protected server operation.
- SQLite is a prototype store. The technical brief will describe TLS and encrypted-volume/database requirements for production because SQLite does not itself satisfy production encryption-at-rest requirements.
- Logs contain identifiers and change metadata, not note bodies or raw PHI.

## Internal schedule

- Internal completion deadline: 2026-08-28 16:30 SGT.
- Official submission deadline: 2026-08-28 17:30 SGT.
- No email submission or external account action is performed from this workspace without explicit user instruction at that time.

