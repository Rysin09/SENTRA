"""
SENTRA application entry point.

Run with:
    streamlit run src/sentra/main.py
"""

from sentra.ui.app import run_app


def main() -> None:
    """Start the SENTRA Streamlit application."""
    run_app()


if __name__ == "__main__":
    main()
