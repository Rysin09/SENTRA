# SENTRA — Architecture

## Architectural Principle
> Multimodal Signals → Feature Extraction → Assessment → Confidence → Safety Rules → Human Review → Human-Triggered Action → Audit Trail

## Architecture Style
Use a **Python modular monolith** for the MVP. Streamlit is the primary interface. Do not introduce microservices unless an actual requirement appears.

## Components

### Presentation
- Streamlit UI
- Case intake
- Audio upload
- Reviewer dashboard
- Assessment visualization
- Human override

### Validation
- Pydantic schemas
- File/MIME validation
- Size and text limits
- Consent validation

### Audio
- Audio decoding
- Quality checks
- Speech-to-text
- Language handling
- Acoustic features

### NLP
- Text normalization
- Indicator extraction
- Context extraction
- OpenAI integration (single provider for MVP)

### Fusion
Combine available text, acoustic and context features. Maintain an explicit missing-modality representation.

### Assessment
Generate the eight operational dimensions.

### Confidence
Consider modality availability, signal quality, model confidence, completeness and consistency.

### Safety
Deterministic rules run after model inference. Safety rules can force `HUMAN_REVIEW_REQUIRED`.

### Persistence
PostgreSQL stores structured cases, assessments, review decisions and audit metadata.

### Audit
Record important state changes without sensitive complaint content.

## Reference Flow
```text
User
 ↓
Streamlit
 ↓
Consent + Validation
 ↓
 ┌───────────────┬──────────────────┐
 │ Text          │ Voice            │
 ↓               ↓                  │
NLP/Context      ASR + Acoustic     │
 └───────────────┴──────────────────┘
 ↓
Multimodal Fusion
 ↓
Assessment Engine
 ↓
Confidence + Explainability
 ↓
Safety Rules
 ↓
Human Reviewer
 ↓
Human-Authorized Action
 ↓
Audit Trail
```

## Failure Behavior
- ASR failure → use available modalities or human review
- Acoustic failure → mark modality unavailable
- NLP/LLM failure → deterministic fallback or human review
- Invalid model output → reject and human review
- Low confidence → human review
- Database failure → do not claim successful persistence
- Critical AI outage → manual review
