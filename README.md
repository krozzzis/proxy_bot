# proxy_bot

A Telegram bot that hands out access links by code. A user sends a code and
gets one or more links back; admins create and manage codes through an
inline admin panel.

## Features

- **User**: `/start`, `/help`, `/link`, `/code` — one shared menu, no
  duplicated logic. Enter a code, get its link(s), revisit them anytime.
  One account can redeem several codes.
- **Admin** (`/admin`, gated by `admins.toml` or `ROOT_ADMIN_ID`): create
  and edit codes (multiple links per code), list users and their codes,
  ban/unban, revoke codes, add admins, broadcast messages.

## Stack

Python 3.12, [aiogram 3](https://docs.aiogram.dev/) +
[aiogram-dialog](https://aiogram-dialog.readthedocs.io/). Data lives in
TOML files (`data/`). Dialog state uses SQLite for dev or Redis for
production (`FSM_BACKEND`). Translations are [Fluent](https://projectfluent.org/)
(`locales/ru`, `locales/en`), hot-reloaded on file change.

## Quick start

```sh
nix develop            # python 3.12 + uv
uv sync                # install dependencies
cp .env.example .env   # set BOT_TOKEN and ROOT_ADMIN_ID
uv run proxy-bot        # run (long polling)
```

`ROOT_ADMIN_ID` is a Telegram user id that always has `/admin` access,
even before `admins.toml` exists. More admins can be added from the panel.

## Configuration

| Variable | Required | Default | Purpose |
|---|:---:|---|---|
| `BOT_TOKEN` | yes | — | token from @BotFather |
| `ROOT_ADMIN_ID` | yes | — | root admin's Telegram id |
| `DATA_DIR` | no | `./data` | TOML data directory |
| `LOGS_DIR` | no | `./logs` | log directory |
| `LOCALES_DIR` | no | `./locales` | `.ftl` translation directory |
| `DEFAULT_LOCALE` | no | `ru` | default locale |
| `LOG_LEVEL` | no | `INFO` | log level |
| `FSM_BACKEND` | no | `sqlite` | dialog state store: `sqlite` or `redis` |
| `FSM_SQLITE_PATH` | no | `./data/fsm.sqlite3` | used when `FSM_BACKEND=sqlite` |
| `REDIS_URL` | if `redis` | — | e.g. `redis://localhost:6379/0` |

See [`.env.example`](.env.example) for the full, commented list.

## Deploy

```sh
cp .env.example .env
mkdir -p data logs
docker compose up -d --build
```

`data/` and `logs/` are mounted volumes, so state survives container
recreation. To use Redis instead of SQLite, set `FSM_BACKEND=redis` and
`REDIS_URL` in `.env`, then run with the `redis` profile:

```sh
docker compose --profile redis up -d --build
```

Pushing to `main` builds and publishes an image via GitHub Actions
(`.github/workflows/docker-publish.yml`); a Watchtower service can poll
the registry and redeploy automatically (see `docker-compose.yml`).

## Project structure

```
src/proxy_bot/
  storage/     TOML-backed repositories: users, codes, admins
  fsm/         aiogram dialog-state backends (SQLite, Redis)
  dialogs/     aiogram-dialog flows: user menu, admin panel
  handlers/    /start /help /link /code, fallback handling
  filters/     IsAdmin
  utils/       i18n, HTML escaping, link formatting
locales/       ru, en translations (.ftl)
data/, logs/   runtime state, not in git
```

## License

[MIT](LICENSE)
