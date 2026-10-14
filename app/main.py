"""FastAPI entry point for the CareNote API."""

from contextlib import asynccontextmanager
from datetime import datetime
from functools import partial
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import Base, build_engine, build_session_factory, default_database_url, session_dependency
from app.importance import apply_feedback, ranked_highlights
from app.models import (
    AuditEvent,
    Comment,
    Conflict,
    Entry,
    EntryType,
    EntryVersion,
    Highlight,
    Patient,
    Role,
    SourceArtifact,
    TopicWeight,
    User,
    Visibility,
)
from app.redaction import DeterministicScribe, redact_phi
from app.schemas import (
    ActorSummary,
    AuditEventSummary,
    ConflictResolveRequest,
    ConflictSummary,
    CommentCreate,
    CommentState,
    CommentSummary,
    EntryCreate,
    EntryUpdate,
    EntryVersionSummary,
    HealthResponse,
    HighlightAction,
    HighlightCreate,
    HighlightSummary,
    PatientSummary,
    PatientTimeline,
    ProvenanceResolution,
    RevertRequest,
    ScribeRequest,
    ScribeResult,
    TopCard,
    TopicWeightSummary,
    TimelineEntry,
    VersionDiff,
)
from app.security import (
    can_view_entry,
    normalized_visibility,
    require_create_permission,
    require_edit_permission,
    require_patient_access,
)
from app.seed import seed_database
from app.trust import (
    append_version,
    detect_fact_conflicts,
    get_version,
    parse_provenance_pointer,
    record_audit,
    render_version_diff,
    resolve_conflict,
    resolve_provenance,
)


def create_app(database_url: Optional[str] = None) -> FastAPI:
    engine = build_engine(database_url or default_database_url())
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        Base.metadata.create_all(engine)
        with session_factory() as session:
            seed_database(session)
        yield
        engine.dispose()

    application = FastAPI(
        title="Trust-first CareNote",
        version="0.1.0",
        description="Synthetic-data prototype with clinic-scoped, server-enforced demo RBAC.",
        lifespan=lifespan,
    )
    package_dir = Path(__file__).resolve().parent
    application.mount("/static", StaticFiles(directory=package_dir / "static"), name="static")
    templates = Jinja2Templates(directory=package_dir / "templates")
    scribe_adapter = DeterministicScribe()
    get_session = partial(session_dependency, session_factory)

    def current_user(
        x_user_id: Annotated[Optional[int], Header(alias="X-User-ID")] = None,
        session: Session = Depends(get_session),
    ) -> User:
        if x_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-User-ID is required for the demo",
            )
        actor = session.get(User, x_user_id)
        if actor is None or actor.role == Role.SYSTEM:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown demo user")
        return actor

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="trust-first-carenote")

    @application.get("/api/me", response_model=ActorSummary)
    def me(actor: User = Depends(current_user)) -> User:
        return actor

    @application.get("/api/patients", response_model=List[PatientSummary])
    def list_patients(
        actor: User = Depends(current_user), session: Session = Depends(get_session)
    ) -> List[Patient]:
        statement = select(Patient).where(Patient.clinic_id == actor.clinic_id)
        if actor.role == Role.PATIENT:
            statement = statement.where(Patient.user_id == actor.id)
        return list(session.scalars(statement.order_by(Patient.id)))

    @application.get("/api/patients/{patient_id}/timeline", response_model=PatientTimeline)
    def patient_timeline(
        patient_id: int,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> PatientTimeline:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        require_patient_access(actor, patient)
        entries = list(
            session.scalars(
                select(Entry).where(Entry.patient_id == patient_id).order_by(Entry.occurred_at.desc())
            )
        )
        return PatientTimeline(
            patient=PatientSummary.model_validate(patient),
            entries=[
                TimelineEntry.model_validate(entry) for entry in entries if can_view_entry(actor, entry)
            ],
        )

    @application.post(
        "/api/patients/{patient_id}/entries",
        response_model=TimelineEntry,
        status_code=status.HTTP_201_CREATED,
    )
    def create_entry(
        patient_id: int,
        payload: EntryCreate,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> Entry:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        require_patient_access(actor, patient)
        require_create_permission(actor, payload.entry_type)

        entry = Entry(
            patient_id=patient.id,
            author_id=actor.id,
            author_role=actor.role,
            entry_type=payload.entry_type,
            visibility=normalized_visibility(actor, payload.visibility),
            section_key=payload.section_key,
            title=payload.title,
            content=payload.content,
            fact_key=payload.fact_key,
            fact_value=payload.fact_value,
            version=1,
            provenance_pointer="pending",
            occurred_at=datetime.utcnow(),
        )
        session.add(entry)
        session.flush()
        entry.provenance_pointer = f"entry:{entry.id}#chars=0-{len(entry.content)}"
        append_version(entry, actor.id, "created")
        record_audit(session, actor, "entry.created", entry, None, 1, "entry")
        detect_fact_conflicts(session, entry)
        session.commit()
        return entry

    @application.patch("/api/entries/{entry_id}", response_model=TimelineEntry)
    def update_entry(
        entry_id: int,
        payload: EntryUpdate,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> Entry:
        entry = session.get(Entry, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        require_patient_access(actor, entry.patient)
        require_edit_permission(actor, entry)
        if payload.expected_version != entry.version:
            raise HTTPException(status_code=409, detail="Stale version; reload before editing")

        prior_version = entry.version
        changed_fields = []
        if payload.title is not None and payload.title != entry.title:
            changed_fields.append("title")
        if payload.content is not None and payload.content != entry.content:
            changed_fields.append("content")
        if payload.visibility is not None and payload.visibility != entry.visibility:
            changed_fields.append("visibility")
        entry.title = payload.title if payload.title is not None else entry.title
        entry.content = payload.content if payload.content is not None else entry.content
        if payload.visibility is not None:
            entry.visibility = normalized_visibility(actor, payload.visibility)
        entry.version += 1
        entry.provenance_pointer = f"entry:{entry.id}#chars=0-{len(entry.content)}"
        append_version(entry, actor.id, "edited")
        record_audit(
            session,
            actor,
            "entry.edited",
            entry,
            prior_version,
            entry.version,
            ",".join(changed_fields) or "no-op",
        )
        session.commit()
        return entry

    def require_history_access(actor: User, entry: Entry) -> None:
        require_patient_access(actor, entry.patient)
        if actor.role in {Role.CLINICIAN, Role.ADMIN}:
            return
        if actor.role == entry.author_role and can_view_entry(actor, entry):
            return
        raise HTTPException(status_code=403, detail="Version history is not available for this role")

    @application.get(
        "/api/entries/{entry_id}/versions", response_model=List[EntryVersionSummary]
    )
    def entry_versions(
        entry_id: int,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> List:
        entry = session.get(Entry, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        require_history_access(actor, entry)
        return list(
            session.scalars(
                select(EntryVersion)
                .where(EntryVersion.entry_id == entry.id)
                .order_by(EntryVersion.version.desc())
            )
        )

    @application.get("/api/entries/{entry_id}/diff", response_model=VersionDiff)
    def entry_diff(
        entry_id: int,
        from_version: int,
        to_version: int,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> VersionDiff:
        entry = session.get(Entry, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        require_history_access(actor, entry)
        older = get_version(session, entry.id, from_version)
        newer = get_version(session, entry.id, to_version)
        return VersionDiff(
            entry_id=entry.id,
            from_version=from_version,
            to_version=to_version,
            unified_diff=render_version_diff(older, newer),
        )

    @application.post("/api/entries/{entry_id}/revert", response_model=TimelineEntry)
    def revert_entry(
        entry_id: int,
        payload: RevertRequest,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> Entry:
        entry = session.get(Entry, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        require_patient_access(actor, entry.patient)
        require_edit_permission(actor, entry)
        if payload.expected_version != entry.version:
            raise HTTPException(status_code=409, detail="Stale version; reload before reverting")
        target = get_version(session, entry.id, payload.target_version)
        prior_version = entry.version
        entry.title = target.title_snapshot
        entry.content = target.content_snapshot
        entry.visibility = target.visibility_snapshot
        entry.section_key = target.section_key_snapshot
        entry.fact_key = target.fact_key_snapshot
        entry.fact_value = target.fact_value_snapshot
        entry.version += 1
        entry.provenance_pointer = f"entry:{entry.id}#chars=0-{len(entry.content)}"
        append_version(entry, actor.id, f"reverted from version {payload.target_version}")
        record_audit(
            session,
            actor,
            "entry.reverted",
            entry,
            prior_version,
            entry.version,
            "title,content,visibility,section_key,facts",
        )
        session.commit()
        return entry

    @application.get("/api/audit", response_model=List[AuditEventSummary])
    def audit_log(
        object_id: Optional[int] = None,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> List[AuditEvent]:
        if actor.role not in {Role.CLINICIAN, Role.ADMIN}:
            raise HTTPException(status_code=403, detail="Audit oversight requires clinician or admin")
        statement = select(AuditEvent).where(AuditEvent.clinic_id == actor.clinic_id)
        if object_id is not None:
            statement = statement.where(AuditEvent.object_id == object_id)
        return list(session.scalars(statement.order_by(AuditEvent.created_at.desc())))

    @application.get("/api/provenance/resolve", response_model=ProvenanceResolution)
    def provenance(
        pointer: str,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> ProvenanceResolution:
        entry_id, _, _ = parse_provenance_pointer(pointer)
        entry = session.get(Entry, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Provenance source not found")
        require_patient_access(actor, entry.patient)
        if not can_view_entry(actor, entry):
            raise HTTPException(status_code=403, detail="Provenance source is not visible to this role")
        start, end, excerpt = resolve_provenance(entry, pointer)
        return ProvenanceResolution(
            pointer=pointer,
            entry_id=entry.id,
            entry_version=entry.version,
            source_start=start,
            source_end=end,
            excerpt=excerpt,
        )

    @application.get(
        "/api/patients/{patient_id}/conflicts", response_model=List[ConflictSummary]
    )
    def patient_conflicts(
        patient_id: int,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> List[Conflict]:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        require_patient_access(actor, patient)
        if actor.role == Role.PATIENT:
            raise HTTPException(status_code=403, detail="Internal conflict review is not patient-facing")
        return list(
            session.scalars(
                select(Conflict)
                .where(Conflict.patient_id == patient.id)
                .order_by(Conflict.created_at.desc())
            )
        )

    @application.post("/api/conflicts/{conflict_id}/resolve", response_model=ConflictSummary)
    def review_conflict(
        conflict_id: int,
        payload: ConflictResolveRequest,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> Conflict:
        conflict = session.get(Conflict, conflict_id)
        if conflict is None:
            raise HTTPException(status_code=404, detail="Conflict not found")
        patient = session.get(Patient, conflict.patient_id)
        require_patient_access(actor, patient)
        resolve_conflict(conflict, actor, payload.authoritative_entry_id)
        session.commit()
        return conflict

    def require_internal_collaboration(actor: User, entry: Entry) -> None:
        require_patient_access(actor, entry.patient)
        if actor.role == Role.PATIENT or not can_view_entry(actor, entry):
            raise HTTPException(status_code=403, detail="Internal collaboration is not available")

    def validate_collaborator(session: Session, actor: User, user_id: Optional[int]) -> None:
        if user_id is None:
            return
        collaborator = session.get(User, user_id)
        if (
            collaborator is None
            or collaborator.clinic_id != actor.clinic_id
            or collaborator.role not in {Role.STAFF, Role.CLINICIAN, Role.ADMIN}
        ):
            raise HTTPException(status_code=422, detail="Mention or assignee is outside clinic scope")

    @application.get("/api/entries/{entry_id}/comments", response_model=List[CommentSummary])
    def entry_comments(
        entry_id: int,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> List[Comment]:
        entry = session.get(Entry, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        require_internal_collaboration(actor, entry)
        return list(
            session.scalars(
                select(Comment).where(Comment.entry_id == entry.id).order_by(Comment.created_at)
            )
        )

    @application.post(
        "/api/entries/{entry_id}/comments",
        response_model=CommentSummary,
        status_code=status.HTTP_201_CREATED,
    )
    def create_comment(
        entry_id: int,
        payload: CommentCreate,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> Comment:
        entry = session.get(Entry, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        require_internal_collaboration(actor, entry)
        validate_collaborator(session, actor, payload.mention_user_id)
        validate_collaborator(session, actor, payload.assigned_to_id)
        comment = Comment(
            entry_id=entry.id,
            author_id=actor.id,
            body=payload.body,
            mention_user_id=payload.mention_user_id,
            assigned_to_id=payload.assigned_to_id,
        )
        session.add(comment)
        session.flush()
        if actor.role == Role.CLINICIAN and entry.entry_type in {
            EntryType.AI_DOCTOR_CONSULT_SUMMARY,
            EntryType.AI_NURSE_CONSULT_SUMMARY,
            EntryType.AI_PATIENT_SESSION_SUMMARY,
        }:
            for topic in {highlight.topic for highlight in entry.highlights}:
                apply_feedback(session, actor.clinic_id, topic, "clinician_comment")
        session.add(
            AuditEvent(
                clinic_id=actor.clinic_id,
                actor_id=actor.id,
                action="comment.created",
                object_type="comment",
                object_id=comment.id,
                changed_fields="body,mention,assignee",
            )
        )
        session.commit()
        return comment

    @application.patch("/api/comments/{comment_id}", response_model=CommentSummary)
    def set_comment_state(
        comment_id: int,
        payload: CommentState,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> Comment:
        comment = session.get(Comment, comment_id)
        if comment is None:
            raise HTTPException(status_code=404, detail="Comment not found")
        require_internal_collaboration(actor, comment.entry)
        comment.resolved = payload.resolved
        session.add(
            AuditEvent(
                clinic_id=actor.clinic_id,
                actor_id=actor.id,
                action="comment.resolved" if payload.resolved else "comment.reopened",
                object_type="comment",
                object_id=comment.id,
                changed_fields="resolved",
            )
        )
        session.commit()
        return comment

    @application.get("/api/patients/{patient_id}/top-card", response_model=TopCard)
    def top_card(
        patient_id: int,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> TopCard:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        require_patient_access(actor, patient)
        if actor.role == Role.PATIENT:
            raise HTTPException(status_code=403, detail="Clinical Top Card is not patient-facing")
        highlights = ranked_highlights(session, patient, actor)
        open_conflicts = session.scalar(
            select(func.count(Conflict.id)).where(
                Conflict.patient_id == patient.id, Conflict.status == "open"
            )
        )
        open_items = sum(1 for item in highlights if item.unresolved)
        return TopCard(
            patient_id=patient.id,
            headline=f"{open_items} open priorities · {open_conflicts} conflicts for review",
            highlights=[HighlightSummary.model_validate(item) for item in highlights],
            open_conflicts=open_conflicts or 0,
        )

    @application.post("/api/highlights/{highlight_id}/action", response_model=HighlightSummary)
    def act_on_highlight(
        highlight_id: int,
        payload: HighlightAction,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> Highlight:
        highlight = session.get(Highlight, highlight_id)
        if highlight is None:
            raise HTTPException(status_code=404, detail="Highlight not found")
        require_internal_collaboration(actor, highlight.entry)
        highlight.status = {"accept": "accepted", "reject": "rejected", "pin": "pinned"}[
            payload.action
        ]
        apply_feedback(session, actor.clinic_id, highlight.topic, payload.action)
        session.add(
            AuditEvent(
                clinic_id=actor.clinic_id,
                actor_id=actor.id,
                action=f"highlight.{payload.action}",
                object_type="highlight",
                object_id=highlight.id,
                changed_fields="status",
            )
        )
        session.commit()
        ranked_highlights(session, highlight.entry.patient, actor)
        return highlight

    @application.post(
        "/api/entries/{entry_id}/highlights",
        response_model=HighlightSummary,
        status_code=status.HTTP_201_CREATED,
    )
    def create_manual_highlight(
        entry_id: int,
        payload: HighlightCreate,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> Highlight:
        entry = session.get(Entry, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        require_internal_collaboration(actor, entry)
        if actor.role != Role.CLINICIAN:
            raise HTTPException(status_code=403, detail="Clinician confirmation is required")
        if payload.source_end <= payload.source_start or payload.source_end > len(entry.content):
            raise HTTPException(status_code=422, detail="Highlight span does not resolve")
        highlight = Highlight(
            patient_id=entry.patient_id,
            entry_id=entry.id,
            source_start=payload.source_start,
            source_end=payload.source_end,
            text=entry.content[payload.source_start : payload.source_end],
            risk_level=payload.risk_level,
            risk_reason=payload.risk_reason,
            status="pinned",
            topic=payload.topic,
            unresolved=True,
            provenance_pointer=(
                f"entry:{entry.id}#chars={payload.source_start}-{payload.source_end}"
            ),
        )
        session.add(highlight)
        session.flush()
        apply_feedback(session, actor.clinic_id, highlight.topic, "pin")
        session.add(
            AuditEvent(
                clinic_id=actor.clinic_id,
                actor_id=actor.id,
                action="highlight.manual_pin",
                object_type="highlight",
                object_id=highlight.id,
                changed_fields="source_span,risk,topic,status",
            )
        )
        session.commit()
        ranked_highlights(session, entry.patient, actor)
        return highlight

    @application.get("/api/importance/weights", response_model=List[TopicWeightSummary])
    def importance_weights(
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> List[TopicWeight]:
        if actor.role not in {Role.CLINICIAN, Role.ADMIN}:
            raise HTTPException(status_code=403, detail="Importance model oversight required")
        return list(
            session.scalars(
                select(TopicWeight)
                .where(TopicWeight.clinic_id == actor.clinic_id)
                .order_by(TopicWeight.weight.desc(), TopicWeight.topic)
            )
        )

    @application.post(
        "/api/patients/{patient_id}/ai-scribe",
        response_model=ScribeResult,
        status_code=status.HTTP_201_CREATED,
    )
    def create_ai_scribe(
        patient_id: int,
        payload: ScribeRequest,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> ScribeResult:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        require_patient_access(actor, patient)
        allowed_type = {
            Role.PATIENT: EntryType.AI_PATIENT_SESSION_SUMMARY,
            Role.STAFF: EntryType.AI_NURSE_CONSULT_SUMMARY,
            Role.CLINICIAN: EntryType.AI_DOCTOR_CONSULT_SUMMARY,
        }.get(actor.role)
        if payload.interaction_type != allowed_type:
            raise HTTPException(status_code=403, detail="Interaction type does not match role")
        if session.scalar(
            select(SourceArtifact.id).where(SourceArtifact.session_id == payload.session_id)
        ):
            raise HTTPException(status_code=409, detail="Session has already been processed")

        clinic_names = list(
            session.scalars(select(User.display_name).where(User.clinic_id == actor.clinic_id))
        )
        redaction = redact_phi(payload.raw_text, [patient.display_name, *clinic_names])
        summary = scribe_adapter.summarize(redaction.text)
        artifact = SourceArtifact(
            patient_id=patient.id,
            created_by_id=actor.id,
            session_id=payload.session_id,
            interaction_type=payload.interaction_type,
            redacted_text=redaction.text,
            redacted_sha256=sha256(redaction.text.encode("utf-8")).hexdigest(),
        )
        session.add(artifact)
        entry = Entry(
            patient_id=patient.id,
            author_id=None,
            author_role=Role.SYSTEM,
            entry_type=payload.interaction_type,
            visibility=Visibility.INTERNAL,
            section_key="ai_scribe",
            title="AI-scribed interaction summary",
            content=summary,
            version=1,
            source_session_id=payload.session_id,
            provenance_pointer="pending",
            occurred_at=datetime.utcnow(),
        )
        session.add(entry)
        session.flush()
        entry.provenance_pointer = f"entry:{entry.id}#chars=0-{len(entry.content)}"
        append_version(entry, actor.id, "AI draft created from redacted source")
        record_audit(
            session,
            actor,
            "ai_scribe.generated",
            entry,
            None,
            1,
            "redacted_source,ai_summary",
        )
        session.commit()
        return ScribeResult(
            entry_id=entry.id,
            entry=TimelineEntry.model_validate(entry) if can_view_entry(actor, entry) else None,
            redaction_counts=redaction.counts,
        )

    def demo_actor(session: Session, as_user: int) -> User:
        actor = session.get(User, as_user)
        if actor is None or actor.role == Role.SYSTEM:
            raise HTTPException(status_code=404, detail="Demo identity not found")
        return actor

    @application.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/demo/patients/1?as_user=2", status_code=302)

    @application.get("/demo/patients/{patient_id}", response_class=HTMLResponse, include_in_schema=False)
    def demo_patient(
        request: Request,
        patient_id: int,
        as_user: int = 2,
        source: Optional[int] = None,
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        actor = demo_actor(session, as_user)
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        require_patient_access(actor, patient)
        entries = [entry for entry in reversed(patient.entries) if can_view_entry(actor, entry)]
        highlights = [] if actor.role == Role.PATIENT else ranked_highlights(session, patient, actor)
        conflicts = []
        comments_by_entry: Dict[int, List[Comment]] = {}
        if actor.role != Role.PATIENT:
            conflicts = list(
                session.scalars(
                    select(Conflict).where(
                        Conflict.patient_id == patient.id, Conflict.status == "open"
                    )
                )
            )
            comments = list(
                session.scalars(
                    select(Comment)
                    .join(Entry)
                    .where(Entry.patient_id == patient.id)
                    .order_by(Comment.created_at)
                )
            )
            for comment in comments:
                comments_by_entry.setdefault(comment.entry_id, []).append(comment)
        users = list(session.scalars(select(User).where(User.clinic_id == actor.clinic_id)))
        users_by_id = {user.id: user for user in users}
        return templates.TemplateResponse(
            request=request,
            name="care_note.html",
            context={
                "actor": actor,
                "patient": patient,
                "entries": entries,
                "highlights": highlights,
                "conflicts": conflicts,
                "comments_by_entry": comments_by_entry,
                "users": users,
                "users_by_id": users_by_id,
                "source": source,
            },
        )

    application.state.engine = engine
    application.state.session_factory = session_factory
    return application


app = create_app()
