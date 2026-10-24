# data-kondo

[![CI](https://github.com/eliem08/data-kondo/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/data-kondo/actions/workflows/ci.yml)

> **Marie Kondo for your company's data** — clean it up so agents can use it.

Agents choke on messy spreadsheets: `N/A` vs blank vs `null`, five date
formats in one column, duplicated customers, headers like `Cust. Name (old)`.
`data-kondo` profiles a CSV, tells you how "agent-ready" it is, and tidies it.

## What the MVP does

- **Profile**: per-column type inference (int, float, date, email, phone, bool,
  text), null rate, distinct count, whitespace and mixed-format issues
- **Agent-readiness score** (0–100) with the issues that cost points
- **Clean**:
  - `snake_case` headers, dedupe header names
  - unify null tokens (`N/A`, `null`, `-`, `none`, `?`) → empty
  - trim / collapse whitespace
  - ISO-8601 dates from 8 common formats
  - lowercase emails, digits-only phones, `true/false` booleans
  - drop fully empty columns, drop exact-duplicate rows (or by `--key`)
- Writes a cleaned CSV plus a change log ("sparks joy" report)

## Quickstart

```bash
pip install -e .
data-kondo profile customers.csv
data-kondo clean customers.csv customers.clean.csv --key email
```

## Roadmap

- Excel / Parquet / database table inputs
- Entity resolution across files (same customer, different spellings)
- Auto-generated data dictionary + `schema.json` agents can read
- Scheduled tidy jobs on Google Drive / SharePoint

## Development

Zero runtime dependencies; Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m unittest discover -s tests -t .           # unit + CLI smoke tests
ruff check . && ruff format --check .               # lint + format
```

```
data_kondo/core.py       domain logic (pure, importable, fully tested)
data_kondo/__main__.py   CLI (`data-kondo ...` / `python -m data_kondo ...`)
tests/                unit tests + generated CLI smoke tests
examples/             sample inputs used by the docs and smoke tests
```

CI runs lint and tests on Ubuntu and Windows across Python 3.10, 3.12 and 3.13.
Design, data model, trade-offs and production path: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Part of the [agent-economy](https://github.com/eliem08/agent-economy) portfolio (idea #5).
