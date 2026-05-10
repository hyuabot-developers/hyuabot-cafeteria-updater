# hyuabot-cafeteria-updater

A recurring job that scrapes Hanyang University's dining portal for daily menus and keeps the HYUabot database up to date. Runs every hour as a Kubernetes CronJob (deadline: 10 minutes per run).

## Overview

On each run the job:

1. Scrapes the university dining portal using aiohttp and BeautifulSoup4.
2. Parses menu items for each restaurant and meal type.
3. Upserts records into the `menu` and `restaurant` tables.

## Architecture

```
src/
├── main.py              # Entry point; fetches and stores menus for all restaurants
├── models.py            # SQLAlchemy ORM models (Restaurant, Menu)
├── scripts/
│   └── menu.py          # Menu HTML parsing logic
└── utils/
    └── database.py      # PostgreSQL engine factory
```

## Requirements

- Python ≥ 3.12
- PostgreSQL

## Environment Variables

| Variable            | Description              |
|---------------------|--------------------------|
| `POSTGRES_ID`       | PostgreSQL username      |
| `POSTGRES_PASSWORD` | PostgreSQL password      |
| `POSTGRES_HOST`     | PostgreSQL host          |
| `POSTGRES_PORT`     | PostgreSQL port          |
| `POSTGRES_DB`       | PostgreSQL database name |

## Running Locally

```bash
pip install -e .

export POSTGRES_ID=postgres
export POSTGRES_PASSWORD=password
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=hyuabot

cd src && python main.py
```

## Docker

The container exits after a single run — schedule it externally (Kubernetes CronJob every hour at :00).

```bash
docker build -t hyuabot-cafeteria-updater .

docker run --rm \
  -e POSTGRES_ID=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_DB=hyuabot \
  hyuabot-cafeteria-updater
```

## Development

```bash
pip install -e .[lint]       # flake8
pip install -e .[typecheck]  # mypy
pip install -e .[test]       # pytest
```

```bash
python -m flake8 src/ tests/
python -m mypy src/ tests/
python -m pytest -v
```

Tests run against a PostgreSQL instance at `localhost:25432`.

## CI/CD

| Workflow | Trigger | Jobs |
|---|---|---|
| `code-check.yml` | Push to any branch except `main` | lint, typecheck, test |
| `deploy.yml` | PR merged to `main` (or manual dispatch) | Docker build → push to `localhost:5000` |

CI runners: self-hosted X64 Linux (code checks) · ARM64 Linux (Docker build).

## License

GPLv3
