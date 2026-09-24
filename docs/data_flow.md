# SENTRA — Data Flow Specification

## End-to-End
```text
Victim / Complainant
        ↓
Text / Voice Input
        ↓
Consent + Validation
        ↓
 ┌──────────────┬────────────────┐
 │ Text         │ Voice          │
 ↓              ↓                │
NLP/Context     ASR + Language   │
Analysis        Identification   │
 │              ↓                │
 │         Acoustic Features    │
 └──────────────┴────────────────┘
        ↓
Multimodal Feature Fusion
        ↓
Assessment Engine
        ↓
Confidence + Explainability
        ↓
Safety Rules
        ↓
Human Reviewer
        ↓
Authorized Human Action
        ↓
Audit Trail
```

## Text Path
Validate → normalize → language handling → structured indicators → context → fusion.

## Voice Path
Validate → quality check → ASR → language handling → acoustic features → fusion.

## Fusion
Represent available and missing modalities explicitly.

Conceptual structure:
```python
{
    "text": {...},
    "audio": {...},
    "context": {...},
    "modalities_available": ["text", "audio"],
    "missing_modalities": []
}
```

## Assessment
Return eight dimensions, confidence, supporting indicators, limitations and operational category.

## Safety
Safety rules execute after assessment and can force human review.

## Persistence
Store structured metadata in PostgreSQL. If audio persistence is required, store it separately and reference it by an opaque ID.

## Audit
Record case creation, processing, assessment, review and override events without raw complaint text.
