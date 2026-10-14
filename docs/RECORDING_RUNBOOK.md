# Recording Runbook

Target length: **4:00-4:30**. Record at 1080p or higher, browser zoom 100%, with system notifications disabled.

## 1. Prepare a deterministic demo state

Stop the local server first, then run:

```bash
source .venv/bin/activate
python scripts/reset_demo_database.py --confirm
uvicorn app.main:app
```

Open `http://127.0.0.1:8000/demo/patients/1?as_user=2`. Before recording, confirm:

- three Top Card items are visible;
- five timeline entries are visible;
- the page says `Synthetic data`;
- the first Top Card item is `suggested`, not accepted, rejected, or pinned;
- no test AI-scribe entry appears.

Keep a second terminal ready with:

```bash
pytest -q
python scripts/benchmark_glance.py --warmup 20 --iterations 300
```

## 2. Recording sequence

### 0:00-0:30 - Thesis

Show the patient banner, synthetic-data label, role selector, and Top Card.

> Clinical context is fragmented across dated notes. I built Trust-first CareNote: a shared longitudinal record where the current state is readable in ten seconds, every important claim is traceable, and roles are enforced by the server.

### 0:30-1:10 - Top Card and provenance

1. In staff view, point to the three ranked items and their reasons.
2. Click **View exact source** for the elevated blood-pressure item.
3. Show the focused AI nurse summary, session ID, and exact character-span pointer.

> The Top Card is derived, not a second source of truth. Each claim resolves to its exact timeline span.

### 1:10-2:05 - Collaboration and bounded learning

1. In the existing `Follow-up action`, type: `@Dr Daniel Lim Repeat reading is now available for review.`
2. Assign the comment to `Dr Daniel Lim` and click **Comment**.
3. Switch to clinician and click **Resolve** on the new comment.
4. Click **Pin** on the blood-pressure Top Card item.

> Staff and clinicians collaborate without overwriting each other's sections. Pinning updates an explainable, clinic-level topic weight within strict bounds.

### 2:05-2:55 - Redaction before AI and patient-safe output

In clinician view use a unique session ID such as `recording-20260826-01` and this explicitly synthetic transcript:

```text
Maya Tan, S1234567D, called from +65 9123 4567 and maya@example.com. Repeat blood pressure was 146/90 and no breathlessness was reported.
```

Click **Redact and generate draft**, show the redaction counts, then switch to patient.

> The raw transcript is never persisted. Names, Singapore IDs, phones, and emails are removed before the deterministic AI boundary. The patient view excludes internal comments, the clinical Top Card, and raw AI notes through server response policy.

### 2:55-3:35 - Longitudinal trust

Return to clinician and show entries from April 2025 and February 2026. Briefly open `/docs` and point to version, diff, revert, conflict, audit, provenance, and RBAC endpoints.

> Every edit creates an immutable snapshot. Stale same-entry edits return 409, and revert creates a new version instead of deleting history. Contradictory structured facts remain visible until clinician or admin review.

### 3:35-4:20 - Evidence and trade-offs

Show the prepared terminal results: `22 passed` and the measured warm-path P95.

> I prioritized a safe, working trust loop over voice capture or an opaque ML model. Production next steps are verified identity, encrypted managed storage, migrations, observability, and clinical workflow validation.

## 3. Post-recording checks

- Watch the complete export once at normal speed.
- Confirm browser and terminal text remain readable at full-screen playback.
- Confirm no personal notifications, email addresses, phone numbers, WhatsApp, WeChat, secrets, or unrelated tabs appear. The synthetic transcript above is allowed.
- Trim dead time only; do not remove evidence of successful actions.
- Export as MP4, H.264, 1080p, with clear voice audio.
- Run the reset script again after recording if another clean take is needed.
