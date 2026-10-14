# Trust-first CareNote

**Nightingale 72 Hour Build - Technical Brief**  
**Candidate:** Peiheng Li (李佩衡)  
**Build thesis:** A 10-second clinical brief is only useful when every claim can be traced, challenged, and corrected without weakening role boundaries.

## 1. Product decision and first-principles scope

EHR tables record snapshots; care teams reason from the story between those snapshots. CareNote therefore treats the timeline as the source of truth and the Top Card as a small, derived view - never as an independent summary that can silently drift.

The prototype optimizes for three promises:

1. **Glanceability:** five or fewer ranked items explain current risk, open work, recent context, and why each item matters.
2. **Trust:** every highlight contains an exact `entry:{id}#chars={start}-{end}` pointer. Clicking it returns to the timeline source. Conflicting patient/AI and clinician facts remain visible until reviewed.
3. **Safe collaboration:** patient, staff, clinician, and admin permissions are enforced in FastAPI services. Staff and clinicians cannot overwrite each other's entries. Patients cannot retrieve internal comments or raw AI-scribed notes.

The build deliberately excludes voice capture, production identity, real EHR/FHIR integration, real patient data, CRDT editing, and an external LLM. A deterministic scribe keeps tests repeatable while preserving the real security boundary: redaction happens before the adapter call.

## 2. Architecture and request flow

The application is a compact Python monolith: FastAPI routes and Jinja2 pages call explicit policy and trust services; SQLAlchemy persists a SQLite relational trust graph. The browser never decides authorization. `X-User-ID` selects a seeded demo identity only; each protected operation still checks actor role, clinic scope, patient ownership, entry visibility, and role-owned write rules.

For AI-scribed input, the server accepts a synthetic transcript, removes known or labelled names, Singapore-style IC/FIN values, phone numbers, and email addresses, then stores only the redacted source artifact and its redacted-content hash. Only the redacted text crosses into the deterministic AI adapter. The generated draft is stored as a distinct `system` entry with its source session ID. A patient receives a receipt and redaction counts, not the raw AI entry.

For edits, clients submit `expected_version`. A matching version creates a new immutable snapshot and metadata-only audit event. A stale same-entry write returns HTTP 409; different entries/sections update independently. Revert restores a selected snapshot as a new version so history is never erased.

## 3. Data model and provenance

`Patient` is clinic-scoped and owns the longitudinal `Entry` collection. Entry metadata includes author role, type, visibility, section, version, source session, optional structured fact, and provenance pointer. The three AI types are distinct: doctor consult, nurse consult, and patient session.

`EntryVersion` stores title, content, visibility, section, and fact snapshots. `Comment` stores internal discussion, mention, assignment, and resolution state. `Highlight` stores the server-derived exact text span, risk reason, topic, unresolved state, status, score, and provenance pointer. `TopicWeight` stores bounded clinic-specific feedback. `Conflict` links the earlier patient/system assertion to the later clinician assertion and records the explicitly selected authoritative entry. `AuditEvent` records actor, action, object, versions, changed field names, and time - never note bodies.

Provenance is validated, not merely displayed. The resolver parses the pointer, checks record scope and role visibility, validates bounds against the current entry, and returns the exact substring. The automated provenance test applies this to every Top Card item, including AI-derived highlights.

## 4. Importance logic and adaptation

The base score is intentionally explainable:

`risk + recency + unresolved + review status + bounded topic weight`

Critical/high risk and unresolved work dominate. Recency contributes at most 20 points. Pin adds 20 display points, accept adds 12, and reject removes the item. Interaction also updates a clinic-level topic weight: pin `+8`, accept `+4`, reject `-6`, and a clinician comment on an AI-derived topic `+1`. The learned weight is bounded from `-20` to `+30`, is visible to clinicians/admins, and cannot change provenance. A manual clinician highlight is constructed from a server-validated source span rather than client-supplied text.

This is a deliberate interpretation of “self-learning”: small, auditable adaptation is safer for a 72-hour clinical prototype than an opaque model trained on sparse interaction data.

## 5. Security, performance, and trade-offs

The RBAC micro-tests prove cross-role write separation, clinic isolation, and the patient-safe response. Out-of-scope records return 404 to avoid confirming that they exist. Internal comment APIs reject patient access. Audit responses contain metadata only. Synthetic data is labelled in the UI and repository.

SQLite is appropriate for a single-process prototype, not a production security claim. Production deployment would use verified OIDC sessions, TLS, a managed encrypted PostgreSQL database with row-level defense in depth, secret management, structured security monitoring, migrations, backups, and retention policies. The local `.db` file is ignored by Git.

The warm Top Card path was measured in-process on Darwin arm64 / Python 3.9.6 after 20 warm-ups and across 300 requests: P50 1.83 ms, P95 2.09 ms, P99 2.28 ms, max 12.21 ms. This includes routing, RBAC, SQLite queries, ranking, and serialization, but excludes TLS, network, browser rendering, production concurrency, and managed-database latency. It satisfies the candidate brief's 300 ms warm-path target as an approximation, not a production SLO.

All required micro-test files are present. The full suite currently has 22 passing tests covering RBAC, revisions, revert, audit, provenance, concurrent edits, redaction, collaboration, UI safety, importance learning, and performance.

## 6. What I would build next

First, replace the demo identity selector and SQLite with verified identity and encrypted managed storage. Second, add structured clinical entity extraction behind the existing redaction/adapter boundary, with clinician confirmation before promotion to the Top Card. Third, add production latency and authorization observability. Voice capture and data-decay tiers come only after the trust and governance controls survive real clinical workflow testing.

