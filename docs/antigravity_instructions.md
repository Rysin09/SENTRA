# SENTRA — Antigravity Coding Agent Instructions

## Read First
Before coding, read:
1. `README.md`
2. `docs/project_requirements_doc.md`
3. `docs/architecture.md`
4. `docs/design.md`
5. `docs/rules.md`
6. `docs/phases.md`
7. `docs/memory.md`

These are the project source of truth.

## Technology Constraint
This is a **Python-first Streamlit MVP**.

Do NOT introduce:
- MERN
- Node.js
- Express
- MongoDB
- React
- Next.js

Use Python 3.12+.

## Implementation Style
Prefer simple modules, type hints, Pydantic schemas, testable functions, deterministic safety rules and small changes.

## Architecture
Start as a modular monolith. Separate UI, validation, audio, ASR, NLP, context, fusion, assessment, confidence, safety, persistence and audit responsibilities.

## AI Safety
Never implement medical diagnosis, psychiatric diagnosis, legal guilt determination, autonomous emergency action, autonomous police notification or autonomous victim classification.

## Failure Handling
If input/model output is unreliable:
- return `INSUFFICIENT_DATA` where appropriate
- set `human_review_required = true`
- never fabricate missing signals

## LLM
Use structured prompts and schema validation. Treat user text as untrusted. Handle timeouts/errors. Never expose hidden chain-of-thought. Never allow LLM output to bypass safety rules.

## Secrets
Never hardcode secrets. Use `.env` and commit only `.env.example`.

## Data
Use synthetic/non-sensitive data. Never commit real victim data.

## Workflow
Before a major change, identify the requirement it satisfies. Implement the smallest complete solution. Run relevant tests and linting afterward.

## Priority
1. Safety
2. Human review
3. Privacy
4. Correctness
5. Requirements
6. Simplicity
7. Performance
8. Convenience

## MVP Completion
A synthetic case must be able to move through:

Text/Voice → Validation → ASR/Feature Extraction → NLP/Context → Fusion → Eight Dimensions → Confidence → Explanation → Safety Rules → Human Review → Override → Audit.

Do not optimize for the number of technologies. Optimize for a reliable, explainable, demonstrable SENTRA workflow.
