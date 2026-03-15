# Repo Ops Dashboard

Local dashboard for repo architecture visibility, command control, and daily-brief runtime inspection.

## Launch

Install the project and dev dependencies from the repo root:

```bash
python -m pip install -e ".[dev]"
```

Start the dashboard with one command:

```bash
python -m tools.repo_dashboard.app
```

Open `http://127.0.0.1:8000/`.

## What The Dashboard Shows

- architecture, data model, and run-flow document links from `artifacts/modelling/`
- latest health status for fixture demo, eval suite, targeted tests, and live daily brief
- latest publish decision, reason, and `reason_codes`
- recent dashboard-triggered runs and the latest log tail
- artifact links for the generated HTML brief, decision record, and run summary when present

## Commands Triggered By The UI

- `python scripts/run_daily_brief_fixture.py --base-dir .tmp_repo_dashboard/demo`
- `python evals/run_eval_suite.py`
- `python -m unittest tests.agent.daily_brief.test_runner tests.agent.delivery.test_html_report tests.agent.validators.test_citation_validator -v`
- `python scripts/run_daily_brief.py --base-dir .tmp_repo_dashboard/live`

## Local Storage

- state seed and latest dashboard state: `tools/repo_dashboard/data/dashboard_state.json`
- per-run metadata and logs: `tools/repo_dashboard/data/runs/`
- generated fixture artifacts: `.tmp_repo_dashboard/demo/`
- generated live artifacts: `.tmp_repo_dashboard/live/`

## Verification

```bash
python -m ruff check apps tests scripts tools
python -m mypy apps tools
python scripts/validate_artifacts.py
python scripts/validate_decision_record_schema.py
python -m compileall -q apps tests scripts tools
python -m unittest discover -s tests -t . -p "test_*.py" -v
```
