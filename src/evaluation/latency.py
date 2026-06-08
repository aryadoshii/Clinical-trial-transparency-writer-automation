"""Latency tracking context manager for pipeline stage profiling."""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Generator, List


@dataclass
class LatencyRecord:
    stage: str
    elapsed_ms: float


class LatencyTracker:
    """Accumulate per-stage timing and report mean latencies."""

    def __init__(self) -> None:
        self._records: List[LatencyRecord] = []

    @contextmanager
    def track(self, stage: str) -> Generator[None, None, None]:
        """Context manager that records elapsed time for *stage*."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            self._records.append(LatencyRecord(stage=stage, elapsed_ms=elapsed))

    def summary(self) -> Dict[str, float]:
        """Return mean latency in milliseconds for each tracked stage."""
        totals: Dict[str, List[float]] = {}
        for rec in self._records:
            totals.setdefault(rec.stage, []).append(rec.elapsed_ms)
        return {stage: sum(vals) / len(vals) for stage, vals in totals.items()}
