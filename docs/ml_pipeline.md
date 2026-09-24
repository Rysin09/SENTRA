# SENTRA — ML, NLP & Audio Pipeline

## Principle
Models provide screening signals, not medical diagnoses.

## Text
```text
Raw Text → Validation → Normalization → Language Handling → Indicator Extraction → Structured Features
```

## Voice
```text
Audio → Validation → Quality Check → ASR → Transcript → NLP
                         │
                         └→ Acoustic Features
```

## Candidate Acoustic Features
- fundamental frequency
- pitch variability
- speaking rate
- pause duration/frequency
- speech energy
- jitter
- shimmer
- spectral characteristics

Individual features are never proof of trauma or a medical condition.

## NLP Indicators
Potential operational indicators:
- fear
- distress
- threat perception
- urgency
- helplessness
- safety concerns
- social isolation
- support availability
- communication difficulty
- request for immediate assistance

## Context
Incident type, ongoing threat, immediate safety concern, displacement, social isolation, support availability and legal-process delay where authorized and necessary.

## Fusion
Start simple and interpretable. Explicitly represent missing modalities.

## Confidence
Consider modality availability, input quality, model confidence, completeness and consistency.

## LLM Use
If an LLM is used, restrict it to structured extraction, summarization, context extraction, translation or explanation. Validate outputs with schemas. LLMs must not make final consequential decisions.

## Synthetic Testing
Cover low/moderate/elevated indicators, high urgency, limited support, insufficient text, noisy audio, ASR failure, contradictory inputs and prompt-injection attempts.
