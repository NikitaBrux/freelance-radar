# FreelanceRadar

Telegram-бот, который агрегирует заказы с фриланс-бирж, фильтрует их по твоим критериям и присылает уведомления в реальном времени.
https://t.me/FreelanceRadarParser_bot

## Возможности

- Парсинг **FL.ru** и **Kwork** каждые 10 минут
- Фильтрация по ключевым словам, минимальному бюджету и площадкам
- Уведомления в Telegram только о новых подходящих заказах
- Дедупликация — один заказ не придёт дважды
- Команды: `/filters`, `/latest`, `/stats`, `/pause`, `/resume`
- Деплой через Docker + Railway

## Стек

- Python
- [aiogram 3](https://docs.aiogram.dev/) — Telegram Bot API
- [SQLAlchemy 2 async](https://docs.sqlalchemy.org/) + asyncpg — PostgreSQL
- [APScheduler](https://apscheduler.readthedocs.io/) — планировщик задач
- httpx + BeautifulSoup4 — парсинг
- Docker + docker-compose
