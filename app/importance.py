"""Transparent, bounded scoring for the under-10-second Top Card."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Highlight, Patient, TopicWeight, User
from app.security import can_view_entry


RISK_POINTS = {"critical": 50, "high": 38, "medium": 24, "low": 10, "info": 4}
STATUS_POINTS = {"pinned": 20, "accepted": 12, "suggested": 0, "rejected": -100}
FEEDBACK_DELTAS = {"pin": 8, "accept": 4, "reject": -6, "clinician_comment": 1}
MIN_TOPIC_WEIGHT = -20
MAX_TOPIC_WEIGHT = 30


def calculate_importance(highlight: Highlight, now: datetime, topic_weight: int = 0) -> int:
    age_days = max((now - highlight.entry.occurred_at).days, 0)
    recency = max(20 - min(age_days, 20), 0)
    unresolved = 20 if highlight.unresolved else 0
    return max(
        0,
        RISK_POINTS.get(highlight.risk_level, 4)
        + STATUS_POINTS.get(highlight.status, 0)
        + recency
        + unresolved
        + topic_weight,
    )


def apply_feedback(
    session: Session, clinic_id: int, topic: str, action: str
) -> TopicWeight:
    if action not in FEEDBACK_DELTAS:
        raise ValueError(f"Unsupported importance feedback action: {action}")
    learned = session.scalar(
        select(TopicWeight).where(
            TopicWeight.clinic_id == clinic_id,
            TopicWeight.topic == topic,
        )
    )
    if learned is None:
        learned = TopicWeight(
            clinic_id=clinic_id,
            topic=topic,
            weight=0,
            feedback_count=0,
        )
        session.add(learned)
    learned.weight = max(
        MIN_TOPIC_WEIGHT,
        min(MAX_TOPIC_WEIGHT, learned.weight + FEEDBACK_DELTAS[action]),
    )
    learned.feedback_count += 1
    return learned


def ranked_highlights(
    session: Session,
    patient: Patient,
    actor: User,
    limit: int = 5,
    now: Optional[datetime] = None,
) -> List[Highlight]:
    effective_now = now or datetime.utcnow()
    candidates = list(
        session.scalars(select(Highlight).where(Highlight.patient_id == patient.id))
    )
    topic_weights = {
        item.topic: item.weight
        for item in session.scalars(
            select(TopicWeight).where(TopicWeight.clinic_id == actor.clinic_id)
        )
    }
    visible = [
        item
        for item in candidates
        if item.status != "rejected" and can_view_entry(actor, item.entry)
    ]
    for item in visible:
        item.importance_score = calculate_importance(
            item, effective_now, topic_weights.get(item.topic, 0)
        )
    return sorted(
        visible,
        key=lambda item: (item.importance_score, item.entry.occurred_at, item.id),
        reverse=True,
    )[:limit]
