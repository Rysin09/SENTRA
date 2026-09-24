# SENTRA — AI-Assisted Multimodal Distress & Vulnerability Screening

## SIH 2026 — SIH26093

SENTRA is a **Python-first, Streamlit-based AI-assisted screening prototype** for victims/complainants accessing NHAA (14566) and an integrated portal.

### Core Principle
> **AI assists. Human decides.**

SENTRA is an operational screening and triage-support system. It is **not a medical diagnostic system**, does not diagnose PTSD/depression/anxiety, does not determine legal guilt or victim status, and does not autonomously trigger consequential actions.

---

## MVP Goal

Build a working demonstration that accepts text and optional voice input, extracts linguistic/acoustic/contextual signals, performs multimodal assessment, estimates confidence, explains indicators, applies safety rules, and presents the result to an authorized human reviewer.

---

## Technology Policy

This project is **Python-only** for the MVP.

Required:
- Python 3.12+
- Streamlit
- Pydantic
- PostgreSQL
- SQLAlchemy + Alembic
- PyTorch
- scikit-learn
- Transformers
- Whisper/faster-whisper
- librosa
- soundfile
- NumPy
- Pandas
- pytest
- Ruff
- Docker/Docker Compose

### Explicitly excluded from MVP
- MERN / Node.js / Express / MongoDB
- React / Next.js
- Kafka
- Kubernetes
- Redis unless a concrete requirement appears
- Vector databases
- RAG
- Multi-agent orchestration
- Mobile app
- Facial emotion recognition
- Autonomous emergency/legal escalation
- Medical diagnosis

---

## Project Structure

```
SENTRA_MVP/
├── src/
│   └── sentra/
│       ├── __init__.py
│       ├── main.py                 # Application entry point
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py         # Typed settings via pydantic-settings
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── enums.py            # Shared enumerations
│       │   └── models.py           # Pydantic domain schemas
│       ├── database/
│       │   ├── __init__.py
│       │   ├── base.py             # SQLAlchemy declarative base
│       │   ├── models.py           # ORM mapped classes
│       │   └── session.py          # Engine, session factory, health check
│       ├── services/
│       │   ├── __init__.py
│       │   └── case_service.py     # Pipeline orchestration
│       ├── repositories/           # Data-access layer (Phase 1+)
│       ├── audio/                  # Audio processing (Phase 3+)
│       ├── nlp/                    # NLP pipeline (Phase 2+)
│       ├── assessment/             # Scoring engine (Phase 2–4+)
│       ├── safety/                 # Deterministic safety rules (Phase 5+)
│       ├── audit/                  # Audit trail (Phase 6+)
│       └── ui/
│           ├── __init__.py
│           ├── app.py              # Streamlit app shell
│           └── pages/
│               ├── case_intake.py
│               ├── reviewer_dashboard.py
│               └── case_history.py
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_domain_models.py
│   └── test_case_service.py
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── docs/                           # Project documentation
├── data/
│   └── synthetic/                  # Non-sensitive synthetic test data only
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Setup

### Prerequisites

- Python 3.12 or higher
- PostgreSQL 14+ (local install or Docker)
- Git

### 1. Clone the repository

```bash
git clone <repo-url>
cd SENTRA_MVP
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -e ".[dev]"
# or, using requirements.txt:
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum, set DATABASE_URL and SECRET_KEY
```

> **Never commit `.env`** — it is in `.gitignore`.

### 5. Set up the database

Start PostgreSQL and create the database:

```bash
# Example using psql:
psql -U postgres -c "CREATE USER sentra WITH PASSWORD 'changeme';"
psql -U postgres -c "CREATE DATABASE sentra_dev OWNER sentra;"
```

Run migrations:

```bash
alembic upgrade head
```

### 6. Run the application

```bash
streamlit run src/sentra/main.py
```

The app will open at `http://localhost:8501`.

### 7. Run tests

```bash
pytest
# With coverage:
pytest --cov
# Only unit tests (no database required):
pytest -m unit
```

### 8. Run linting

```bash
ruff check src/ tests/
ruff format --check src/ tests/
```

---

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — architecture and components
- [`docs/design.md`](docs/design.md) — UI and technical design
- [`docs/project_requirements_doc.md`](docs/project_requirements_doc.md) — requirements
- [`docs/rules.md`](docs/rules.md) — engineering and safety rules
- [`docs/phases.md`](docs/phases.md) — roadmap
- [`docs/memory.md`](docs/memory.md) — project memory
- [`docs/data_flow.md`](docs/data_flow.md) — end-to-end data flow
- [`docs/ml_pipeline.md`](docs/ml_pipeline.md) — ML/NLP/audio pipeline
- [`docs/testing.md`](docs/testing.md) — testing strategy
- [`docs/security_privacy.md`](docs/security_privacy.md) — security and privacy
- [`docs/implementation_plan.md`](docs/implementation_plan.md) — implementation sequence
- [`docs/antigravity_instructions.md`](docs/antigravity_instructions.md) — AI coding-agent instructions

---

## Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| **0** | Project Foundation | ✅ Complete |
| 1 | Text Intake & Persistence | 🔜 Next |
| 2 | Text/NLP Screening | 📅 Planned |
| 3 | Voice Pipeline | 📅 Planned |
| 4 | Multimodal Fusion | 📅 Planned |
| 5 | Safety Layer | 📅 Planned |
| 6 | Human Review | 📅 Planned |
| 7 | Testing & Hardening | 📅 Planned |
| 8 | SIH Demo Readiness | 📅 Planned |

---

## Safety Notice

SENTRA is a **screening support tool for authorized personnel only**.

- It does **not** diagnose medical or psychiatric conditions.
- It does **not** determine legal guilt, innocence, or victim status.
- It does **not** take autonomous consequential action.
- All outputs require review by an authorized human officer.
- AI assists. **Human decides.**
