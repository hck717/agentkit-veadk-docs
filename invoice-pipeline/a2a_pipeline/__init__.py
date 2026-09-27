"""A2A orchestration package for the invoice pipeline.

Contains the A2A executors, the single-process A2A server, the drive-chain
orchestrator, and the CLI.
"""

from a2a_pipeline.executors import (
    EXECUTORS,
    InvoiceExecutor,
    OcrExecutor,
    TranslationExecutor,
    ValidationExecutor,
    AggregationExecutor,
    ApprovalExecutor,
)
from a2a_pipeline.server import build_server
from a2a_pipeline.drive_chain import A2aDriveChain

__all__ = [
    "EXECUTORS",
    "InvoiceExecutor",
    "OcrExecutor",
    "TranslationExecutor",
    "ValidationExecutor",
    "AggregationExecutor",
    "ApprovalExecutor",
    "build_server",
    "A2aDriveChain",
]
