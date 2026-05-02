"""Benchmark API surface.

Every endpoint under /api/v1/ is shaped exactly to what the benchmark
evaluator expects: field names, status codes, and response envelopes match the
spec verbatim. Internal /api/* routes (used by our own frontend) live in the
parent routes/ package and have their own shapes.
"""
from . import health, query, system, knowledge

__all__ = ["health", "query", "system", "knowledge"]
