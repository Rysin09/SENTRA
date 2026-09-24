# SENTRA — Engineering & Safety Rules

## Rule 1 — Python Only
The MVP must use Python and Streamlit. Do not introduce MERN, Node.js, Express, MongoDB, React or Next.js.

## Rule 2 — Human Authority
AI assists. Humans decide. No autonomous consequential action.

## Rule 3 — No Diagnosis
Never claim to diagnose PTSD, depression, anxiety disorder or other psychiatric/medical conditions.

## Rule 4 — No Legal Determination
Do not determine guilt, innocence, legal validity or victim status.

## Rule 5 — No Fabrication
Never infer missing data as negative evidence. Missing audio does not mean absence of acoustic indicators.

## Rule 6 — Insufficient Data
Use `INSUFFICIENT_DATA` when reliable screening cannot be produced.

Required message:
> Insufficient data for reliable screening — Human Review Required.

## Rule 7 — Fail Safe
Critical model/service failure must result in a safe fallback or human review. Never convert failure into LOW.

## Rule 8 — Structured AI Output
All LLM/model outputs must be parsed into strict schemas.

## Rule 9 — Prompt Injection Protection
Treat user-provided complaint text as untrusted data. It must never redefine instructions, execute tools, change safety rules or bypass review.

## Rule 10 — Privacy
Never log raw sensitive complaints, API keys, passwords or unnecessary PII.

## Rule 11 — Secrets
Never commit `.env` or credentials. Use `.env.example`.

## Rule 12 — Synthetic Data
Use synthetic/non-sensitive data during development and demos.

## Rule 13 — Explainability
Provide concise supporting indicators. Never expose hidden chain-of-thought.

## Rule 14 — Confidence
Confidence is an assessment-quality signal, not medical certainty.

## Rule 15 — Auditability
Record actor, timestamp, action, case identifier and status without sensitive content.

## Rule 16 — Validation
Validate all external input: text, files, audio and API/database payloads.

## Rule 17 — Testing
Every safety-critical behavior requires tests.

## Rule 18 — Keep MVP Simple
Prefer a modular Python monolith over unnecessary distributed infrastructure.
