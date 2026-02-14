"""Shared data structures for reports and operation results."""
from dataclasses import dataclass
from typing import List


@dataclass
class NormalizationReport:
    """Result of a single file normalization attempt."""
    original_path: str
    new_name: str
    status: str  # SUCCESS, REJECTED, ERROR, SKIPPED
    reason: str


@dataclass
class OperationSummary:
    """Summary of folder organize/move operation."""
    moved: int
    failed: int
    not_found: int
    errors: List[str]
