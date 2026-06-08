#!/usr/bin/env python3
"""Check docs contracts that are easy to drift from implementation.

Run from the documentation repository root:

    RAGRAILS_SOURCE=/path/to/ragrails/source python scripts/check-docs-contracts.py

The source path is optional if `ragrails` is importable in the current Python
process. This script intentionally checks a small set of high-value docs
contracts rather than every example.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = os.environ.get("RAGRAILS_SOURCE")
if SOURCE:
    sys.path.insert(0, SOURCE)

ERRORS: list[str] = []

GOLDEN_FILES = [
    "index.mdx",
    "getting-started/quickstart.mdx",
    "usage/sdk/quickstart.mdx",
    "usage/cli/quickstart.mdx",
    "usage/server/quickstart.mdx",
]
GOLDEN_TERMS = [
    "support",
    "http://localhost:6333",
    "voyage-3",
    "gpt-4o-mini",
    "How long do I have to request a refund?",
    "Customers can request a refund within 30 days of purchase",
]


def read(rel: str) -> str:
    return (ROOT / rel).read_text()


def require(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


for rel in GOLDEN_FILES:
    text = read(rel)
    for term in GOLDEN_TERMS:
        require(term in text, f"{rel} is missing golden-path term: {term}")

cli_overview = read("usage/cli/overview.mdx")
require("| `setup` |" not in cli_overview, "usage/cli/overview.mdx documents nonexistent `setup` command")
require("run `ragrails` with no subcommand" in cli_overview.lower(), "CLI setup wizard should be documented as bare `ragrails`")

server_ingestion = read("usage/server/ingestion.mdx")
require("| `apis` |" not in server_ingestion, "REST ingestion docs list `apis` batch mode although REST url is required")
require("Batch API ingestion with `apis` is SDK-only" in server_ingestion, "REST ingestion docs should state `apis` is SDK-only for now")

sdk_chat = read("usage/sdk/chat.mdx")
require("constructor default, else required" in sdk_chat, "SDK chat docs should mark `llm().model` as required without constructor default")
require("does not choose a fallback model" in sdk_chat, "SDK chat docs should state `rag.llm()` has no fallback model")

try:
    from ragrails.interfaces.cli.main import cli
    from click.testing import CliRunner

    result = CliRunner().invoke(cli, ["--help"])
    require(result.exit_code == 0, "ragrails --help failed through Click runner")
    require("setup" not in [line.strip().split()[0] for line in result.output.splitlines() if line.startswith("  ")], "CLI exposes unexpected setup command")
except Exception as exc:  # pragma: no cover - diagnostics for docs environments
    ERRORS.append(f"Could not import/check CLI implementation: {exc}")

try:
    from ragrails.interfaces.server.ingestion.schemas import ApiIngestRequest

    fields = getattr(ApiIngestRequest, "model_fields", {})
    require("url" in fields and fields["url"].is_required(), "REST ApiIngestRequest.url should still be required or docs contract needs updating")
except Exception as exc:  # pragma: no cover
    ERRORS.append(f"Could not import/check REST schema implementation: {exc}")

try:
    from ragrails.interfaces.sdk import RagRails

    try:
        RagRails().llm()
    except ValueError as exc:
        require("model is required" in str(exc), "RagRails().llm() should fail with `model is required` without a default")
    else:
        ERRORS.append("RagRails().llm() no longer requires model; update docs contract")
except Exception as exc:  # pragma: no cover
    ERRORS.append(f"Could not import/check SDK implementation: {exc}")

if ERRORS:
    for error in ERRORS:
        print(f"ERROR: {error}")
    raise SystemExit(1)

print("Docs contracts OK")
