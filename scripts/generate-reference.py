#!/usr/bin/env python3
"""Generate high-level reference pages from the Ragrails implementation.

Run from the documentation repository root:

    RAGRAILS_SOURCE=/path/to/ragrails/source uv run python scripts/generate-reference.py
"""
from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = os.environ.get("RAGRAILS_SOURCE")
if SOURCE:
    sys.path.insert(0, SOURCE)


def write(rel: str, text: str) -> None:
    (ROOT / rel).write_text(text.rstrip() + "\n")


def cli_reference() -> str:
    import click
    from ragrails.interfaces.cli.main import cli

    rows = []
    ctx = click.Context(cli, info_name="ragrails")
    for name in cli.list_commands(ctx):
        command = cli.get_command(ctx, name)
        if command is None:
            continue
        help_text = (command.short_help or command.help or "").strip().splitlines()[0]
        rows.append(f"| `ragrails {name}` | {help_text} |")

    return """---
title: "CLI Reference"
icon: "terminal"
description: "All ragrails commands."
---

<Note>This page is generated from the Click command tree. Run `RAGRAILS_SOURCE=/path/to/ragrails uv run python scripts/generate-reference.py` from the docs repo after CLI changes.</Note>

Commands read defaults from [`.ragrails.toml`](/getting-started/configuration); flags override per run. The setup wizard is launched by running bare `ragrails` with no subcommand; there is no `ragrails setup` command.

## Setup

| Command | Description |
| --- | --- |
| `ragrails` | Interactive setup wizard (writes `.ragrails.toml`) |

## Commands

| Command | Description |
| --- | --- |
""" + "\n".join(rows) + "\n"


def sdk_reference() -> str:
    from ragrails.interfaces.sdk import RagRails

    sections = {
        "Constructor": ["__init__"],
        "Ingestion": ["setup_url", "scrape", "parse", "fetch"],
        "Chunking": ["chunk"],
        "Embedding": ["embedder", "embed"],
        "Storing": ["store", "edit", "delete"],
        "Retrieval": ["reranker", "retrieve"],
        "Chat": ["llm", "chat"],
        "Pipeline": ["ingest", "query"],
    }
    out = ["""---
title: "SDK Reference"
icon: "code"
description: "All RagRails SDK methods."
---

<Note>This page is generated from `inspect.signature(RagRails)`. Run `RAGRAILS_SOURCE=/path/to/ragrails uv run python scripts/generate-reference.py` from the docs repo after SDK signature changes.</Note>

SDK defaults live on each `RagRails(...)` instance. They do not write `.ragrails.toml` and they do not change CLI or REST defaults.

"""]
    for heading, methods in sections.items():
        out.append(f"## {heading}\n")
        out.append("| Method | Signature |\n| --- | --- |")
        for method in methods:
            obj = getattr(RagRails, method)
            name = "RagRails" if method == "__init__" else method
            sig = str(inspect.signature(obj))
            if method != "__init__" and sig.startswith("(self, "):
                sig = "(" + sig[len("(self, "):]
            elif sig == "(self)":
                sig = "()"
            elif method == "__init__" and sig.startswith("(self, "):
                sig = "(" + sig[len("(self, "):]
            out.append(f"| `{name}` | `{name}{sig}` |")
        out.append("")
    out.append("""## Important validation notes

- `rag.llm()` requires a model unless `llm={"model": ...}` was configured on the constructor.
- Provider, embedding, vector-store, and reranker defaults are constructor defaults only.
- SDK `fetch(apis=...)` supports batch API ingestion; REST `/v1/ingest/api` currently requires `url`.

## Config objects

| Class | Used with | Description |
| --- | --- | --- |
| `DLQ(path, items)` | `scrape(dlq=...)` | Dead-letter queue for retryable scrape failures |
| `QueryRewriteConfig(enabled, session_context, llm)` | `chat(query_rewrite=...)` | Query rewriting config |
| `HistoryCompactionConfig(enabled, history_limit, keep_recent)` | `chat(history_compaction=...)` | History summarisation config |
| `IntentRoutingConfig(enabled)` | `chat(intent_routing=...)` | Intent routing config |
| `ChatRetrievalQualityConfig(min_retrieval_score, min_rerank_score, low_confidence_mode, max_context_chunks)` | `chat(retrieval_quality=...)` | Retrieval quality thresholds |
""")
    return "\n".join(out)


def rest_reference() -> str:
    from ragrails.interfaces.server.app import create_app

    app = create_app()
    rows = []
    for route in app.routes:
        methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
        path = getattr(route, "path", "")
        if not methods or not path.startswith("/v1"):
            continue
        name = getattr(route, "name", "") or ""
        rows.append((path, ", ".join(methods), name.replace("_", " ").capitalize()))
    rows.sort()
    table = "\n".join(f"| {method} | `{path}` | {desc} |" for path, method, desc in rows)
    return f"""---
title: "REST API Reference"
icon: "server"
description: "All HTTP endpoints."
---

<Note>This page is generated from the FastAPI route table. Run `RAGRAILS_SOURCE=/path/to/ragrails uv run python scripts/generate-reference.py` from the docs repo after REST route or schema changes.</Note>

Start the server:

```bash
pip install "ragrails[server-qdrant]"
ragrails-api
```

Base URL: `http://127.0.0.1:8000`

Interactive docs: `http://127.0.0.1:8000/docs`

OpenAPI schema: `http://127.0.0.1:8000/v1/openapi.json`

REST defaults are request payload fields. REST examples do not inherit SDK constructor defaults or CLI `.ragrails.toml` values.

## Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
{table}

See the Swagger UI at `/docs` for full request and response schemas.
"""


write("reference/cli.mdx", cli_reference())
write("reference/sdk.mdx", sdk_reference())
write("reference/rest-api.mdx", rest_reference())
print("Generated reference/cli.mdx, reference/sdk.mdx, reference/rest-api.mdx")
