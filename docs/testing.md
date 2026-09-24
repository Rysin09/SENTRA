# SENTRA — Testing Strategy

## Unit Tests
Test validators, audio utilities, feature extractors, schemas, safety rules, confidence logic and assessment mapping.

## Integration Tests
Test:
- text → assessment
- voice → ASR → assessment
- text + voice → fusion
- assessment → safety
- assessment → database
- human override → audit

## Mandatory Safety Tests

### Insufficient Input
Expected: `INSUFFICIENT_DATA` and `human_review_required = true`.

### ASR Failure
No fabricated transcript.

### Acoustic Failure
Acoustic modality marked unavailable.

### Invalid Model Output
Reject output and require human review.

### Low Confidence
Require human review.

### Prompt Injection
User text cannot modify system rules.

### Human Override
Override persists and creates an audit event.

## Commands
```bash
pytest
ruff check .
ruff format --check .
```

## Test Data
Use synthetic cases only.

## Regression
Any change to assessment, safety, confidence, prompts or fusion must run the safety/regression suite.
