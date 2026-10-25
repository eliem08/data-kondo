<!-- sell-kit:start -->
# Data Kondo

[![CI](https://github.com/eliem08/data-kondo/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/data-kondo/actions/workflows/ci.yml)

> **Clean messy company data so AI agents can actually use it.**

**Who it's for:** Ops and data teams preparing spreadsheets and exports for AI projects.

**The problem:** Agents choke on inconsistent CSVs: mixed dates, duplicate rows, junk columns and broken encodings.

**What you get:** Profile any CSV, get an agent-readiness score, and run a deterministic cleaner that logs every change it makes.

## Quickstart

Customers receive a release archive with the wheel and the examples. Python 3.10+ and no other dependencies.

```bash
pip install data_kondo-0.1.0-py3-none-any.whl
data-kondo profile examples/customers.csv
data-kondo clean examples/customers.csv clean.csv --key e_mail
```

## Pricing

Every plan starts with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Starter** | $19 per month | Unlimited profiling; Readiness score; Clean files up to 50 MB |
| **Pro** | $79 per month | Unlimited file size; Batch cleaning; Change-log export |
| **Team** | $249 per month | 5 seats; Shared cleaning rules; Priority support |

To start a trial or buy a plan, email **sales@YOUR-DOMAIN.com**.

## Licence

Proprietary. Copyright (c) 2026 eliem08. All rights reserved. Use requires a paid plan or an active trial; see [LICENSE](LICENSE).
<!-- sell-kit:end -->

## What it does

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
