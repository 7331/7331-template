# 7331-template

A [Copier](https://copier.readthedocs.io/en/stable/) template that starts a Python backend app with one shape: FastAPI
on Python 3.15, typed structlog events, a typer CLI, uv, and Docker Compose, with PostgreSQL through SQLAlchemy and
Alembic unless you turn it off. It is backend only; the OpenAPI document is the contract for any client.
`ARCHITECTURE.md` in the generated app describes the rules the code follows.

## Start an app

```sh
uvx copier copy --trust gh:7331/7331-template my-app
```

`--trust` lets Copier run the template's tasks after copying: `git init -b main` (unless the folder is already a
repository), `uv lock` in `backend/` and `e2e/`, an import sort and format pass (the import order depends on the
package name you pick), and `uvx prek install` for the pre-commit and pre-push hooks. Without `--trust`, run those by
hand.

`uv.lock` is not part of the template: each app generates its own on first copy and commits it.

Then:

```sh
cd my-app
cp .env.example .env        # with Postgres: fill POSTGRES_PASSWORD and the same password in the DATABASE_URL line
docker compose up -d --build --wait
curl http://127.0.0.1:8000/health
uvx prek run --all-files    # every gate
```

Compose reads the env file named by `<PREFIX>_ENVIRONMENT_FILE` (default `.env`), both for its own interpolation
(`--env-file`) and as the backend containers' `env_file:`. `deploy/deploy.sh` requires it to point at the deploy env
file, kept outside the checkout with mode 600. With Postgres it also requires
`<PREFIX>_POSTGRES_BACKUP_ENVIRONMENT_FILE`, the bucket and WAL-G key file made from
`deploy/postgres/backup.env.example`, also mode 600 and outside the checkout.
The generated `ARCHITECTURE.md` (Postgres operations) covers the server settings, memory limits, backups, the restore
drill and how to run the backup schedule.

## Questions

| Question | What it does |
| --- | --- |
| `project_slug` | Lowercase name with hyphens (for example `shop-7331`). Names the compose project, the image, the Postgres database and user (hyphens removed), the CLI script, and the API's service name. Its first segment, upper-cased, is the env prefix (`shop-7331` gives `SHOP_`). |
| `root_package` | The domain root package under `backend/app/` (for example `shop` or `payments`). Defaults to the slug's first segment. Every domain package goes inside it. |
| `project_description` | One line, used in `pyproject.toml` and the CLI help. |
| `include_postgres` | Default yes. Adds `app/infrastructure/postgres/`, Alembic (`alembic.ini`, `migrations/`), the `postgres` and `migrate` compose services, the DSN setting, a request-scoped `DatabaseSession`, a schema check at startup, and `deploy/postgres/` (the production image with WAL-G, the backup script, the restore drill and the backup schedule loop). With it off the app has no database at all. |
| `include_accounts` | Asked only when `include_postgres` is on, and off without it: accounts keep their tables in Postgres. Default yes. Adds `app/<root>/accounts/`: open sign-up with a username and a passkey, passkey sign-in, cookie sessions, sign-out and `GET /api/v1/me`, its tables in the first migration, and a per-IP budget on passkey writes. |

## Update an app

```sh
cd my-app
uvx copier update --trust
```

`copier update` needs the app to be a git repository with a clean working tree, and reads `.copier-answers.yml`
(never edit it by hand). It replays the template at the recorded version, diffs it against the newest release tag
(PEP 440, for example `v0.2.0`), and applies that diff to the app, leaving conflicts as inline markers to resolve.
Tag every template release.

## Repository layout

- `copier.yml`: the questions, the tasks and the message after copy. `_subdirectory: template` keeps this README and
  the workflow out of generated apps.
- `template/`: the files Copier renders. Only files ending in `.jinja` are rendered; the rest are copied as they are.
  File and folder names are rendered too, and one that renders empty (an option that is off) is skipped.
- `.github/workflows/template-check.yml`: on every push and pull request, generates the app three ways (no
  Postgres; Postgres without accounts; Postgres with accounts), and runs every gate in each with
  `uvx prek run --all-files`.
  A second job audits the workflows and the Dependabot config with [zizmor](https://docs.zizmor.sh/).
- `.github/dependabot.yml`: weekly updates for the pinned actions, held back 7 days after each release.
- `.github/pull_request_template.md`: the shape of a pull request description. Generated apps get the same file.
