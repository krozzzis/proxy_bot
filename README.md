# proxy_bot

Telegram-бот выдачи доступа по кодам. Пользователь вводит код — получает одну
или несколько ссылок. Администраторы создают и редактируют коды, управляют
пользователями и рассылают сообщения через встроенную админ-панель.

## Содержание

- [Возможности](#возможности)
- [Стек](#стек)
- [Быстрый старт](#быстрый-старт)
- [Переменные окружения](#переменные-окружения)
- [Команды бота](#команды-бота)
- [Деплой](#деплой)
  - [Docker вручную](#docker-вручную)
  - [GitOps: автодеплой из GitHub](#gitops-автодеплой-из-github)
- [Структура проекта](#структура-проекта)

## Возможности

**Пользователь** — единое меню с inline-кнопками (`/start`, `/help`, `/link`,
`/code` открывают соответствующие разделы этого же меню, не дублируя логику):

- ввод кода доступа → одна или несколько ссылок сразу;
- к одному аккаунту можно привязать несколько кодов;
- повторный просмотр своих ссылок в любой момент.

**Администратор** (`/admin`, доступно тем, кто есть в `admins.toml`, либо
`ROOT_ADMIN_ID`):

- создание кода с одной или несколькими ссылками;
- просмотр и редактирование всех кодов (добавить/удалить ссылку, изменить
  описание, удалить код);
- список пользователей и их активированных кодов, отзыв кода, бан/разбан;
- добавление новых администраторов;
- рассылки — всем пользователям или только держателям конкретного кода.

## Стек

| Область | Решение |
|---|---|
| Бот-фреймворк | Python 3.12, [aiogram 3](https://docs.aiogram.dev/) + [aiogram-dialog](https://aiogram-dialog.readthedocs.io/) |
| Данные бота | TOML-файлы (`data/users.toml`, `data/codes.toml`, `data/admins.toml`), атомарная запись через `asyncio.Lock` + write-tmp-then-replace |
| FSM/состояние диалогов | SQLite для разработки (один файл, без внешних сервисов), Redis для продакшена — переключается `FSM_BACKEND` (`src/proxy_bot/fsm/`) |
| Локализация | [Fluent](https://projectfluent.org/) (`locales/ru`, `locales/en`) через `aiogram-i18n`, см. ниже |
| Логирование | ежедневная ротация, `logs/bot.log`, хранится 14 дней |
| Разработка | Nix (devShell с python3.12 + uv) + uv |
| Деплой | Docker / docker-compose, автообновление — GitHub Actions + GHCR + Watchtower |

Локализация — без прямого юникода в `.ftl`-файлах
(`EmojiFluentCompileCore` в `utils/i18n.py`):

- `:shortcode:` — GitHub/Slack-алиасы (пакет `emoji`), например `:wave:` вместо 👋;
- `[tg_emoji:<custom_emoji_id>:<fallback_shortcode>]` — Telegram Premium/custom
  emoji по числовому id, с обычным shortcode как fallback-символом для
  клиентов без поддержки custom emoji; разворачивается в
  `<tg-emoji emoji-id="...">` (нужен HTML parse mode);
- сами `.ftl`-файлы отслеживаются на лету (`watchfiles`,
  `utils/i18n.py: watch_locales`) — правки в переводах подхватываются без
  перезапуска бота.

## Быстрый старт

```sh
nix develop            # даёт python3.12 и uv
uv sync                # ставит зависимости в .venv
cp .env.example .env   # заполнить BOT_TOKEN и ROOT_ADMIN_ID
uv run proxy-bot       # запустить бота (long polling)
```

`ROOT_ADMIN_ID` — Telegram id пользователя, который всегда имеет доступ к
`/admin`, даже до того как в `admins.toml` появится хоть одна запись.
Остальных администраторов можно добавлять прямо из панели.

## Переменные окружения

| Переменная | Обязательна | По умолчанию | Назначение |
|---|:---:|---|---|
| `BOT_TOKEN` | да | — | токен бота от @BotFather |
| `ROOT_ADMIN_ID` | да | — | Telegram id корневого администратора |
| `DATA_DIR` | нет | `./data` | каталог TOML-файлов |
| `LOGS_DIR` | нет | `./logs` | каталог логов |
| `LOCALES_DIR` | нет | `./locales` | каталог `.ftl`-файлов |
| `DEFAULT_LOCALE` | нет | `ru` | локаль по умолчанию |
| `LOG_LEVEL` | нет | `INFO` | уровень логирования |
| `FSM_BACKEND` | нет | `sqlite` | хранилище состояния диалогов: `sqlite` или `redis` |
| `FSM_SQLITE_PATH` | нет | `./data/fsm.sqlite3` | путь к файлу SQLite (если `FSM_BACKEND=sqlite`) |
| `REDIS_URL` | если `redis` | — | `redis://host:6379/0`, обязателен при `FSM_BACKEND=redis` |

Полный список с комментариями — в [`.env.example`](.env.example).

## Команды бота

Все команды лишь открывают соответствующий раздел единого меню:

| Команда | Действие |
|---|---|
| `/start` | приветствие и открытие меню |
| `/help` | раздел «Помощь» |
| `/link` | раздел «Мои ссылки» |
| `/code` | раздел «Ввести код» (ссылок на аккаунте может быть несколько) |
| `/admin` | админ-панель (только для администраторов) |

## Деплой

### Docker вручную

```sh
cp .env.example .env       # заполнить BOT_TOKEN и ROOT_ADMIN_ID
mkdir -p data logs          # data/ и logs/ не в git — создаются один раз
docker compose up -d --build
```

`data/` и `logs/` смонтированы как volume — состояние переживает пересоздание
контейнера. По умолчанию используется SQLite (`data/fsm.sqlite3`) — поднимать
для него ничего дополнительно не нужно.

Чтобы вместо SQLite использовать Redis (рекомендуется для прода, особенно при
масштабировании за пределы одного контейнера), в `.env` укажите:

```env
FSM_BACKEND=redis
REDIS_URL=redis://redis:6379/0
```

и запустите с профилем `redis` — тогда поднимется и сам Redis:

```sh
docker compose --profile redis up -d --build
```

### GitOps: автодеплой из GitHub

После пуша в `main` сервер сам подтягивает новую версию — без ручного захода
на сервер. Схема:

```
git push (main) → GitHub Actions собирает и пушит образ в GHCR
                → Watchtower на сервере видит новый digest и пересоздаёт контейнер
```

Компоненты:

- **`.github/workflows/docker-publish.yml`** — при пуше в `main` (или вручную
  через `workflow_dispatch`) собирает Docker-образ и пушит его в
  `ghcr.io/<owner>/<repo>` с тегами `latest` и коротким SHA коммита.
  Аутентификация — встроенный `secrets.GITHUB_TOKEN`, никаких своих секретов
  заводить не нужно; правами на публикацию его наделяет
  `permissions: packages: write` в самом workflow.
- **Watchtower** — сервис-сосед бота в `docker-compose.yml`. Каждые 5 минут
  проверяет реестр и, если у тега `latest` появился новый digest,
  пересоздаёт контейнер бота. Помечен `com.centurylinklabs.watchtower.enable`,
  поэтому не трогает другие контейнеры на том же хосте.
- **`data/` и `logs/`** — volume, а не часть образа: коды, пользователи и
  логи переживают пересоздание контейнера при каждом деплое.

#### Настройка с нуля (в своём форке/репозитории)

1. Запушить репозиторий на GitHub — workflow сработает автоматически при
   первом пуше в `main` и опубликует образ в GHCR
   (`ghcr.io/<owner>/<repo>`).
2. Сделать пакет в GHCR публичным (Settings пакета → Danger Zone → Change
   visibility → Public) — тогда серверу не нужны отдельные учётные данные для
   `docker pull`. Пакет создаётся только после первого успешного запуска
   workflow, и по умолчанию GHCR делает новые пакеты приватными независимо от
   видимости самого репозитория.
   - Если оставить пакет приватным — на сервере один раз потребуется
     `docker login ghcr.io` с PAT (scope `read:packages`), см. ниже.
3. В `docker-compose.yml` поле `image:` уже указывает на нужный путь в GHCR;
   при необходимости поменяйте `<owner>/<repo>` под свой репозиторий.

#### Первоначальная настройка сервера (один раз)

```sh
# на сервере
mkdir -p /opt/proxy_bot/data /opt/proxy_bot/logs && cd /opt/proxy_bot
scp user@local:/path/to/repo/docker-compose.yml .
scp user@local:/path/to/repo/.env .   # содержит секреты — передавайте аккуратно, chmod 600

# только если пакет в GHCR оставлен приватным:
# echo <PAT> | docker login ghcr.io -u <github-username> --password-stdin

docker compose pull   # тянет готовый образ из ghcr.io, без сборки и без исходников
docker compose up -d
```

**Важно:** на сервере используйте `docker compose pull && docker compose up -d`,
а не `up -d --build` — на сервере нет `Dockerfile`/исходников, только образ из
реестра.

После этого сервер больше не трогается руками — весь дальнейший цикл
обновлений идёт через push → Actions → Watchtower. Деплой занимает до ~5 минут
после завершения сборки — это интервал опроса Watchtower (`WATCHTOWER_POLL_INTERVAL`
в `docker-compose.yml`), не баг.

Ручной прогон без нового коммита: вкладка **Actions** на GitHub → выбрать
workflow → **Run workflow**.

## Структура проекта

```
src/proxy_bot/
  storage/     TOML-репозитории: users, codes (много ссылок на код), admins
  fsm/         FSM/dialog-состояние aiogram: SQLiteStorage (dev), RedisStorage (prod)
  dialogs/     aiogram-dialog сценарии (меню пользователя, админ-панель)
  handlers/    команды /start /help /link /code, fallback на неизвестные сообщения
  filters/     IsAdmin
  utils/       i18n (Fluent, эмодзи-шорткоды, watch_locales), html.esc(), форматирование ссылок
  config.py, logging_config.py, commands.py, main.py
locales/ru, locales/en     .ftl-файлы
data/, logs/                состояние во время выполнения (не в git, создать вручную)
```
