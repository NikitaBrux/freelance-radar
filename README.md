# FreelanceRadar

Telegram-бот, который агрегирует заказы с фриланс-бирж, фильтрует их по твоим критериям и присылает уведомления в реальном времени.

## Возможности

- Парсинг **FL.ru** и **Kwork** каждые 10 минут
- Фильтрация по ключевым словам, минимальному бюджету и площадкам
- Уведомления в Telegram только о новых подходящих заказах
- Дедупликация — один заказ не придёт дважды
- Команды: `/filters`, `/latest`, `/stats`, `/pause`, `/resume`
- Деплой через Docker + Railway

## Стек

- Python 3.11+
- [aiogram 3](https://docs.aiogram.dev/) — Telegram Bot API
- [SQLAlchemy 2 async](https://docs.sqlalchemy.org/) + asyncpg — PostgreSQL
- [APScheduler](https://apscheduler.readthedocs.io/) — планировщик задач
- httpx + BeautifulSoup4 — парсинг
- Docker + docker-compose

## Структура проекта

```
freelance_radar/
├── bot/
│   ├── main.py                  # точка входа
│   ├── handlers/
│   │   ├── start.py             # /start, /pause, /resume, /help
│   │   ├── filters.py           # /filters — FSM-диалог
│   │   └── orders.py            # /latest, /stats
│   ├── keyboards.py
│   └── middlewares.py
├── parsers/
│   ├── base.py                  # BaseParser + ParsedOrder
│   ├── fl_ru.py
│   └── kwork.py
├── db/
│   ├── models.py                # User, UserFilter, Order, SentOrder
│   ├── database.py
│   └── crud.py
├── scheduler.py
├── notifier.py
├── config.py
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── railway.toml
```

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Главное меню |
| `/filters` | Настроить фильтры (ключевые слова, бюджет, площадки) |
| `/latest` | Последние 5 подходящих заказов |
| `/stats` | Статистика за 7 дней |
| `/pause` | Приостановить уведомления |
| `/resume` | Возобновить уведомления |
| `/help` | Список команд |

## Запуск локально

**1. Клонируй репозиторий**

```bash
git clone https://github.com/NikitaBrux/freelance-radar.git
cd freelance-radar
```

**2. Установи зависимости**

```bash
pip install -r requirements.txt
```

**3. Создай `.env`**

```bash
cp .env.example .env
```

Заполни переменные:

```
BOT_TOKEN=токен_от_BotFather
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/freelance_radar
```

**4. Запусти**

```bash
python bot/main.py
```

## Деплой на Railway

1. Подключи репозиторий на [railway.app](https://railway.app)
2. Добавь сервис **PostgreSQL** — `DATABASE_URL` подставится автоматически
3. В Variables добавь `BOT_TOKEN`
4. Railway соберёт образ по `Dockerfile` и запустит бота

## Лицензия

MIT
