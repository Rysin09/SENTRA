"""
Assessment package — Phase 2 text screening pipeline.

Public API:
    TextScreeningPipeline  — orchestrates normalize → extract → score
    PIPELINE_VERSION       — current pipeline version string
"""

from sentra.assessment.pipeline import PIPELINE_VERSION, TextScreeningPipeline

__all__ = ["PIPELINE_VERSION", "TextScreeningPipeline"]
