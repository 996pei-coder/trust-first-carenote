# Demo Script (4-5 minutes)

## Before recording

1. Run `uvicorn app.main:app --reload` and open `/demo/patients/1?as_user=2`.
2. Run `python scripts/reset_demo_database.py --confirm` while the server is stopped.
3. Keep the browser at 100% zoom and close unrelated tabs/notifications.
4. Keep one terminal ready with `pytest` and the benchmark command.

## 0:00-0:30 - Problem and thesis

> “Clinical context is fragmented across dated notes. I built Trust-first CareNote: a shared longitudinal record where the Top Card is readable in ten seconds, every claim is traceable, and role boundaries are enforced by the server.”

Point out the synthetic-data badge and four role pills.

## 0:30-1:20 - Scenario A: Glance View and AI provenance

1. Stay in **staff** view.
2. Read the three Top Card items without scrolling.
3. Open the elevated blood-pressure item’s **View exact source** link.
4. Show that the timeline focuses the originating AI nurse summary and displays its session ID and provenance pointer.

Say:

> “The Top Card is derived, never a second source of truth. Its short risk reason and exact span remain connected to the original timeline entry.”

## 1:20-2:20 - Scenario B: collaboration, version trust, and learning

1. Add a staff follow-up note using **Add to Care Note**.
2. Add an internal comment and assign it to the clinician.
3. Switch to **clinician** view; resolve the comment.
4. Pin a Top Card highlight and explain: display status changes immediately, while the clinic topic weight increases by a bounded amount for later similar suggestions.
5. Briefly open `/docs` or use prepared API responses to show version list, diff, revert, and metadata-only audit.

Say:

> “Staff and clinicians collaborate without overwriting each other. Every edit creates a snapshot; stale same-section edits return 409; revert creates another version rather than deleting history.”

## 2:20-3:10 - Privacy and role boundaries

1. In clinician view, enter a synthetic scribe sample containing a name, IC/FIN, phone, and email.
2. Generate the draft and point out the redaction count.
3. Switch to **patient** view.
4. Show that internal comments, Top Card, and raw AI entries disappear; only patient-facing instructions remain.

Say:

> “The raw transcript is never persisted. Redaction runs before the adapter, and patient safety is a response policy, not CSS hiding.”

## 3:10-3:50 - Longitudinal context and conflict handling

1. Switch back to clinician.
2. Show entries from April 2025 and February 2026.
3. Explain scoring: risk, unresolved state, recency, review status, then bounded topic learning.
4. Mention that contradictory patient/AI and clinician facts create a visible conflict until clinician/admin confirmation.

## 3:50-4:30 - Evidence and trade-offs

Show terminal results:

```text
22 passed
P95 2.09 ms (warm, in-process approximation; requirement <= 300 ms)
```

Close with:

> “I prioritized a safe, working trust loop over voice capture or an opaque ML model. Production next steps are verified identity, encrypted managed storage, migrations, observability, and clinical workflow validation.”

## Recording checklist

- Patient view contains no raw AI note or internal comment.
- Exact-source jump is visible.
- One collaboration action and one importance action succeed.
- Terminal font is readable.
- Do not show personal email, phone, WhatsApp, WeChat, secrets, or unrelated browser content.
- Use [RECORDING_RUNBOOK.md](RECORDING_RUNBOOK.md) for exact input text, timings, and reset steps.
