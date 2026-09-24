"""
Assessment repository — data-access layer for the ``assessments`` table.

Persists and retrieves ``AssessmentResult`` domain objects via the
``AssessmentRecord`` ORM model.

Security:
  - Raw complaint text is NEVER stored in or returned from assessments.
  - All JSON blobs contain only scoring metadata, not narrative text.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from sentra.database.models import AssessmentRecord as AssessmentORM
from sentra.domain.models import (
    AssessmentDimension,
    AssessmentResult,
    ModalityStatus,
    SafetyFlag,
)

logger = logging.getLogger(__name__)


class AssessmentRepository:
    """Handles persistence and retrieval of assessment results.

    Accepts a SQLAlchemy ``Session`` injected at construction. The caller
    is responsible for committing or rolling back the session.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Write ─────────────────────────────────────────────────────────────────

    def create(self, result: AssessmentResult) -> AssessmentORM:
        """Persist an ``AssessmentResult`` to the assessments table.

        Args:
            result: A fully populated ``AssessmentResult``.

        Returns:
            The newly created ORM record (not yet committed by caller).

        Notes:
            Complaint text is NOT stored here. Only scoring metadata is persisted.
        """
        record = AssessmentORM(
            id=uuid.uuid4(),
            case_id=result.case_id,
            assessed_at=result.assessed_at if result.assessed_at else datetime.now(tz=UTC),
            pipeline_version=result.pipeline_version,
            operational_category=result.operational_category.value,
            confidence=result.confidence,
            explanation=result.explanation,
            human_review_required=result.human_review_required,
            dimensions_json=_serialize_dimensions(result.dimensions, result.extra_metadata),
            modalities_json=_serialize_modalities(result.modalities_used),
            safety_flags_json=_serialize_safety_flags(result.safety_flags),
            india_context_json=result.india_context.model_dump() if result.india_context else None,
        )
        self._session.add(record)
        logger.info(
            "Assessment staged: case_id=%s category=%s confidence=%.3f",
            result.case_id,
            result.operational_category.value,
            result.confidence,
        )
        return record

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_case_id(self, case_id: uuid.UUID) -> AssessmentORM | None:
        """Return the most recent assessment for a case, or None."""
        stmt = (
            select(AssessmentORM)
            .where(AssessmentORM.case_id == case_id)
            .order_by(desc(AssessmentORM.assessed_at))
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def list_recent(self, limit: int = 50) -> list[AssessmentORM]:
        """Return the most recently assessed cases, newest first."""
        stmt = (
            select(AssessmentORM)
            .order_by(desc(AssessmentORM.assessed_at))
            .limit(limit)
        )
        return list(self._session.scalars(stmt))

    # ── Mapping ───────────────────────────────────────────────────────────────

    @staticmethod
    def to_domain(record: AssessmentORM) -> AssessmentResult:
        """Reconstruct a domain ``AssessmentResult`` from an ORM record."""
        from sentra.domain.enums import OperationalCategory

        dimensions, meta = _deserialize_dimensions(record.dimensions_json)
        modalities = _deserialize_modalities(record.modalities_json)
        flags = _deserialize_safety_flags(record.safety_flags_json)

        return AssessmentResult(
            case_id=record.case_id,
            assessed_at=record.assessed_at,
            pipeline_version=record.pipeline_version,
            modalities_used=modalities,
            dimensions=dimensions,
            operational_category=OperationalCategory(record.operational_category),
            confidence=record.confidence,
            explanation=record.explanation,
            safety_flags=flags,
            human_review_required=record.human_review_required,
            extra_metadata=meta,
            india_context=_deserialize_india_context(record.india_context_json) if record.india_context_json else None,
        )


# ── Serialization helpers ─────────────────────────────────────────────────────


def _serialize_dimensions(dimensions: list[AssessmentDimension], meta: dict | None = None) -> dict:
    """Convert dimension list to a JSON-serializable dict keyed by name, adding _meta."""
    data = {
        d.name: {
            "score": d.score,
            "label": d.label,
            "supporting_indicators": d.supporting_indicators,
            "missing_signals": d.missing_signals,
        }
        for d in dimensions
    }
    if meta:
        data["_meta"] = meta
    return data


def _deserialize_dimensions(data: dict) -> tuple[list[AssessmentDimension], dict]:
    """Reconstruct AssessmentDimension list and extra_metadata from the stored JSON dict."""
    # Copy data to avoid mutating the original dict (which caused a P6 lint issue)
    data_copy = data.copy()
    meta = data_copy.pop("_meta", {})
    dimensions = [
        AssessmentDimension(
            name=name,
            score=v.get("score", 0.0),
            label=v.get("label"),
            supporting_indicators=v.get("supporting_indicators", []),
            missing_signals=v.get("missing_signals", []),
        )
        for name, v in data_copy.items()
    ]
    return dimensions, meta


def _serialize_modalities(modalities: list[ModalityStatus]) -> dict:
    """Convert modality list to JSON-serializable dict."""
    return {
        m.modality.value: {
            "quality": m.quality.value,
            "available": m.available,
            "notes": m.notes,
        }
        for m in modalities
    }


def _deserialize_modalities(data: dict) -> list[ModalityStatus]:
    """Reconstruct ModalityStatus list from stored JSON dict."""
    from sentra.domain.enums import ModalityQuality, ModalityType

    result = []
    for modality_val, v in data.items():
        try:
            result.append(
                ModalityStatus(
                    modality=ModalityType(modality_val),
                    quality=ModalityQuality(v.get("quality", "NOT_PROVIDED")),
                    available=v.get("available", False),
                    notes=v.get("notes"),
                )
            )
        except (ValueError, KeyError):
            pass  # Skip unknown modality types (forward-compat)
    return result


def _serialize_safety_flags(flags: list[SafetyFlag]) -> dict:
    """Convert safety flags to JSON-serializable dict."""
    return {
        f.rule_id: {
            "description": f.description,
            "forces_human_review": f.forces_human_review,
        }
        for f in flags
    }


def _deserialize_safety_flags(data: dict) -> list[SafetyFlag]:
    """Reconstruct SafetyFlag list from stored JSON dict."""
    return [
        SafetyFlag(
            rule_id=rule_id,
            description=v.get("description", ""),
            forces_human_review=v.get("forces_human_review", True),
        )
        for rule_id, v in data.items()
    ]


def _deserialize_india_context(data: dict) -> IndiaContextAssessment:
    """Reconstruct IndiaContextAssessment from stored JSON dict."""
    from sentra.context.india_context_layer import IndiaContextAssessment
    return IndiaContextAssessment(**data)
