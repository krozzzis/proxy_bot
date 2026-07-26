# proxy_bot — Telegram-бот выдачи доступа по кодам

Бот выдаёт ссылки доступа по кодам. Пользователь вводит код — получает одну или
несколько ссылок. Администраторы создают и редактируют коды, управляют
пользователями и рассылают сообщения через встроенную админ-панель (aiogram-dialog).

## Стек

- Python 3.12, [aiogram 3](https://docs.aiogram.dev/) + [aiogram-dialog](https://aiogram-dialog.readthedocs.io/)
- Хранилище — TOML-файлы (`data/users.toml`, `data/codes.toml`, `data/admins.toml`),
  атомарная запись через `asyncio.Lock` + write-tmp-then-replace
- Локализация — [Fluent](https://projectfluent.org/) (`locales/ru`, `locales/en`) через `aiogram-i18n`
- Логирование — ежедневная ротация (`logs/bot.log`, хранится 14 дней)
- Разработка — Nix (devShell с python3.12 + uv) + uv
- Деплой — Docker / docker-compose, автообновление на сервере — GitHub Actions + GHCR + Watchtower

## Разработка

```sh
nix develop            # даёт python3.12 и uv
uv sync                # ставит зависимости в .venv
cp .env.example .env   # заполнить BOT_TOKEN и ROOT_ADMIN_ID
uv run proxy-bot        # запустить бота (long polling)
```

`ROOT_ADMIN_ID` — Telegram id пользователя, который всегда имеет доступ к `/admin`,
даже до того как в `admins.toml` появится хоть одна запись. Остальных администраторов
можно добавлять прямо из панели.

## Переменные окружения

| Переменная       | Обязательна | По умолчанию | Назначение                              |
|-------------------|:-----------:|---------------|------------------------------------------|
| `BOT_TOKEN`       | да          | —             | токен бота от @BotFather                 |
| `ROOT_ADMIN_ID`   | да          | —             | Telegram id корневого администратора     |
| `DATA_DIR`        | нет         | `./data`      | каталог TOML-файлов                      |
| `LOGS_DIR`        | нет         | `./logs`      | каталог логов                            |
| `LOCALES_DIR`     | нет         | `./locales`   | каталог `.ftl`-файлов                    |
| `DEFAULT_LOCALE`  | нет         | `ru`          | локаль по умолчанию                      |
| `LOG_LEVEL`       | нет         | `INFO`        | уровень логирования                      |

## Команды бота

Пользовательский интерфейс — единое меню с inline-кнопками (➕ Ввести код,
🔑 Мои ссылки, ❓ Помощь). Команды ниже лишь открывают соответствующий пункт
этого меню, а не дублируют отдельную логику:

- `/start` — приветствие и открытие меню
- `/help` — открывает раздел «Помощь»
- `/link` — открывает раздел «Мои ссылки»
- `/code` — открывает раздел «Ввести код» (ссылок на аккаунте может быть несколько)

Админские (видны только тем, кто есть в `admins.toml`, либо `ROOT_ADMIN_ID`):

- `/admin` — открыть админ-панель:
  - создание кода с одной или несколькими ссылками
  - просмотр и редактирование всех кодов (добавить/удалить ссылку, изменить
    описание, удалить код)
  - список пользователей и их активированных кодов, отзыв кода, бан/разбан
  - добавление новых администраторов
  - рассылки (всем пользователям или только держателям конкретного кода)

## Деплой (Docker, локально/вручную)

```sh
cp .env.example .env      # заполнить BOT_TOKEN и ROOT_ADMIN_ID
mkdir -p data logs         # data/ и logs/ не в git — создаются один раз
docker compose up -d --build
```

`data/` и `logs/` монтируются как volume — состояние переживает пересоздание контейнера.

## GitOps / автодеплой

Пуш в `main` автоматически докатывается на сервер без ручных действий:

1. `git push` в `main` запускает GitHub Actions (`.github/workflows/docker-publish.yml`).
2. Actions собирает образ и пушит его в `ghcr.io/krozzzis/proxy_bot` с тегами
   `latest` и коротким SHA коммита.
3. Watchtower — сосед бота в `docker-compose.yml` — каждые 5 минут проверяет
   реестр и, увидев новый digest у `latest`, пересоздаёт контейнер `proxy_bot`.
4. `data/` и `logs/` — volume, а не часть образа, поэтому состояние (коды,
   пользователи, логи) переживает пересоздание контейнера.

Ручной прогон без нового коммита: вкладка Actions на GitHub → выбрать workflow
→ Run workflow.

### Первоначальная настройка сервера (один раз)

```sh
# на сервере
mkdir -p /opt/proxy_bot/data /opt/proxy_bot/logs && cd /opt/proxy_bot
scp user@local:/path/to/repo/docker-compose.yml .
scp user@local:/path/to/repo/.env .   # содержит секреты — передавайте аккуратно, chmod 600

docker compose pull   # тянет готовый образ из ghcr.io, без сборки и без исходников
docker compose up -d
```

**Важно:** на сервере используйте `docker compose pull && docker compose up -d`,
а не `up -d --build` — на сервере нет `Dockerfile`/исходников, только образ из
реестра.

Если пакет `proxy_bot` в GHCR не сделан публичным, перед `pull` на сервере
нужно один раз авторизоваться (PAT со scope `read:packages`):

```sh
echo <PAT> | docker login ghcr.io -u krozzzis --password-stdin
```

После первоначальной настройки сервер больше не трогается руками — весь
дальнейший цикл обновлений идёт через push → Actions → Watchtower (деплой
занимает до ~5 минут после завершения сборки — это интервал опроса Watchtower,
не баг).

## Структура

```
src/proxy_bot/
  storage/     TOML-репозитории: users, codes (много ссылок на код), admins
  dialogs/     aiogram-dialog сценарии (меню пользователя, админ-панель)
  handlers/    команды /start /help /link /code, fallback на неизвестные сообщения
  filters/     IsAdmin
  utils/       i18n (Fluent), html.esc(), форматирование списков ссылок
  config.py, logging_config.py, commands.py, main.py
locales/ru, locales/en     .ftl-файлы
data/, logs/                состояние во время выполнения (не в git, создать вручную)
```
