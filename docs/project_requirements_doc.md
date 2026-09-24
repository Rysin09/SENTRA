# SENTRA — Project Requirements Document

## 1. Purpose
SENTRA provides AI-assisted, multimodal screening support during the initial interaction of victims/complainants with an NHAA-oriented workflow.

## 2. In Scope
1. Text complaint/input
2. Optional voice/audio input
3. Consent acknowledgement
4. Input validation
5. Speech-to-text
6. Basic language identification/handling
7. Acoustic feature extraction
8. NLP/language signal extraction
9. Context signal extraction
10. Multimodal fusion
11. Eight operational assessment dimensions
12. Confidence estimation
13. Explainability
14. Safety rules
15. Operational triage
16. Human review
17. Human override
18. PostgreSQL persistence
19. Audit logging
20. Streamlit reviewer interface
21. Synthetic-data testing

## 3. Out of Scope
- Medical or psychiatric diagnosis
- Legal guilt determination
- Autonomous victim classification
- Autonomous police/legal escalation
- Automated emergency calls
- Facial/video emotion recognition
- Production deployment with real victim data
- Kafka/Kubernetes/microservice complexity
- RAG/vector databases
- Multi-agent architecture
- Mobile application

## 4. Core Assessment Dimensions
- `acute_distress`
- `fear_threat_perception`
- `anxiety_indicators`
- `trauma_related_indicators`
- `immediate_vulnerability`
- `social_support_availability`
- `urgency`
- `communication_difficulty`

These are screening indicators, not diagnoses.

## 5. Operational Categories
- `LOW`
- `MODERATE`
- `HIGH`
- `CRITICAL`
- `INSUFFICIENT_DATA`

These categories represent operational review priority only.

## 6. Required Result
Every assessment should contain:
- case_id
- timestamp
- modalities_used
- modality_quality
- assessment_dimensions
- operational_category
- confidence
- explanation
- missing_signals
- safety_flags
- human_review_required
- model/pipeline version

## 7. Human-in-the-Loop
The reviewer must be able to inspect the AI summary, supporting indicators, confidence and limitations, override the AI output, and record a review note.

## 8. Insufficient Data
If information is insufficient, noisy, contradictory or processing fails:

> Insufficient data for reliable screening — Human Review Required.

Never fabricate missing signals.

## 9. Acceptance Criteria
The MVP is acceptable when:
1. Text-only cases work end-to-end.
2. Voice cases can be transcribed.
3. Acoustic features are extracted when possible.
4. Text/context indicators are structured.
5. Available modalities can be fused.
6. Eight dimensions are returned.
7. Confidence is shown.
8. Explainability is shown.
9. Safety rules can force human review.
10. Human override is recorded.
11. Assessment history is stored.
12. Audit events are stored.
13. AI failures fail safely.
14. No secrets or real victim data are committed.
