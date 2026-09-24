# SENTRA — Project Memory

## Identity
Project: SENTRA — AI-Assisted Multimodal Distress & Vulnerability Screening
SIH: 2026
Problem: SIH26093

## Product Definition
AI-assisted operational screening for victim/complainant interactions.

## Golden Principle
> Multimodal Signals → Feature Extraction → Assessment → Confidence → Safety Rules → Human Review → Human-Triggered Action → Audit Trail

## MVP Stack
Python 3.12+, Streamlit, Pydantic, PostgreSQL, SQLAlchemy, Alembic, PyTorch, scikit-learn, Transformers, faster-whisper/Whisper, librosa, soundfile, NumPy, Pandas, pytest, Ruff, Docker/Docker Compose.

## Dimensions
1. Acute distress
2. Fear/threat perception
3. Anxiety indicators
4. Trauma-related indicators
5. Immediate vulnerability
6. Social support availability
7. Urgency
8. Communication difficulty

## Triage
LOW, MODERATE, HIGH, CRITICAL, INSUFFICIENT_DATA.

## Safety
Human review is mandatory for consequential interpretation.

## Data
Use synthetic/non-sensitive data. Never commit real victim data or secrets.

## Architecture Decision
Prefer a modular Python monolith. No MERN and no unnecessary infrastructure.

## Development Rule
A feature should be added only when it directly supports the core SENTRA workflow or a documented requirement.
