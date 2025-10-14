# Repository Guidelines
Use this guide to align contributions with Noti's architecture, tooling, and review expectations.

## Project Structure & Module Organization
- `manage.py` is the Django entry point; framework settings and Celery wiring live in `core/`.
- The `notifications/` app owns models, serializers, views, tasks, and API routing for device and push flows.
- Tests currently start in `notifications/tests.py`; break out submodules (for example, `notifications/tests/test_devices.py`) as coverage expands.
- Infrastructure helpers include `docker-compose.yml` (PostgreSQL + Redis), `.env.example`, and `justfile` (formatting automation).

## Build, Test, and Development Commands
- `uv sync` installs dependencies declared in `pyproject.toml`.
- `docker-compose up -d` launches PostgreSQL and Redis for local development.
- `uv run python manage.py migrate` applies schema changes; run after editing models or pulling new migrations.
- `uv run python manage.py runserver 0.0.0.0:8000` starts the API; pair with `uv run celery -A core worker -l info` for background jobs.
- `uv run python manage.py test notifications` executes the Django test suite; append app paths to scope runs.
- `just format` runs the full pre-commit stack (ruff, pyupgrade, validate-pyproject, etc.).

## Coding Style & Naming Conventions
- Use 4-space indentation, snake_case for variables/functions, and PascalCase for Django models and serializers.
- Add type hints and focused docstrings for new modules; mirror the concise style in `notifications/models.py`.
- Keep Celery task names namespaced (for example, `notifications.tasks.send_push`) and group business logic into services/helpers before views.
- Run `uv run ruff check .` and `uv run ruff format .` if you are not invoking `just format`.

## Testing Guidelines
- Prefer Django `TestCase` or DRF `APIClient` tests under `notifications/tests/`, naming files `test_<feature>.py` and methods `test_<behavior>`.
- Cover device registration, push scheduling, and status transitions; mock APNs/httpx calls and assert Celery task dispatch.
- Run `uv run python manage.py test` before raising a PR; keep flaky or long-running integration tests opt-in via markers or explicit modules.

## Commit & Pull Request Guidelines
- Follow conventional commits (`feat:`, `fix:`, `chore:`, etc.) consistent with existing history (`feat: add notifications app...`).
- Keep commits scoped to one logical change and include generated migrations in the same commit as the model edits.
- PR descriptions should state motivation, summarize changes, list test evidence, and link tracking issues.
- Attach screenshots or curl examples for API-affecting changes and note any required `.env` updates or new Celery schedules.

## Environment & Configuration Notes
- Copy `.env.example` to `core/.env` and fill in APNs credentials locally; never commit secrets.
- Ensure Docker services are running before Celery workers; they rely on Redis and PostgreSQL availability.
- Update `core/celery.py` when introducing new periodic tasks and document their schedules in the PR.
