"""Safety package — deterministic safety rules applied after model inference.

Phase 0: package structure only. Implementation deferred to Phase 5.

Key contract: safety rules may force ``human_review_required = True`` and
may set ``operational_category = INSUFFICIENT_DATA``. They must NEVER
convert a failure into LOW priority.
"""
