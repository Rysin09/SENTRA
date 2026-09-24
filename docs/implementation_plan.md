# SENTRA — Implementation Plan

## 1. Initialize
Create `src/`, `tests/`, `data/synthetic/`, `docs/`. Set up Python 3.12+.

## 2. Configuration
Typed settings and `.env.example`. Never hardcode secrets.

## 3. Domain Models
Create Pydantic models for Case, Input, Modality, AudioMetadata, AssessmentDimension, AssessmentResult, SafetyFlag, HumanReview and AuditEvent.

## 4. Text Processing
Implement validation, normalization, indicator extraction and context extraction behind clean interfaces.

## 5. Audio
Implement validation, quality checks, ASR adapter and acoustic extractor.

## 6. Assessment
Implement a simple baseline assessment engine returning all required dimensions.

## 7. Fusion
Implement available modality tracking, missing-modality mask and feature combination.

## 8. Safety
Implement deterministic safety rules after model inference.

## 9. Persistence
Implement PostgreSQL repositories and migrations.

## 10. Streamlit
Build intake, processing, assessment, review and history pages.

## 11. Human Override
Persist reviewer ID, timestamp, previous AI result, reviewer result and note.

## 12. Audit
Record key state transitions.

## 13. Tests
Implement unit, integration and safety tests.

## 14. Demo
Create synthetic cases covering both normal and failure paths.

## 15. Documentation
Update documentation when implementation decisions change.
