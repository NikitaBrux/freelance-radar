"""Планировщик задач — запускает парсеры и нотификатор по расписанию."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from config import config
from db.crud import save_order_if_new
from db.database import async_session_factory
from notifier import notify_users
from parsers.fl_ru import FlRuParser
from parsers.kwork import KworkParser

logger = logging.getLogger(__name__)


async def run_all_parsers(bot: Bot) -> None:
    """Запустить все парсеры, сохранить новые заказы, отправить уведомления."""
    parsers = [
        FlRuParser(),
        KworkParser(),
    ]

    all_orders = []
    for parser in parsers:
        try:
            orders = await parser.fetch()
            all_orders.extend(orders)
            logger.info(
                "Парсер %s вернул %d заказов",
                parser.source_name, len(orders)
            )
        except Exception as exc:
            logger.error("Необработанная ошибка парсера %s: %s", parser.source_name, exc)

    # Сохранить новые заказы в БД
    new_count = 0
    async with async_session_factory() as session:
        for order_data in all_orders:
            try:
                saved = await save_order_if_new(session, order_data.to_dict())
                if saved:
                    new_count += 1
            except Exception as exc:
                logger.error("Ошибка сохранения заказа: %s", exc)

    logger.info("Сохранено новых заказов: %d из %d", new_count, len(all_orders))

    # Уведомить пользователей
    try:
        await notify_users(bot)
    except Exception as exc:
        logger.error("Ошибка в notify_users: %s", exc)


def create_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Создать и настроить планировщик."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_all_parsers,
        trigger="interval",
        minutes=config.PARSE_INTERVAL_MINUTES,
        args=[bot],
        id="parse_and_notify",
        replace_existing=True,
        # Запустить сразу при старте и затем по расписанию
        misfire_grace_time=60,
    )
    logger.info(
        "Планировщик настроен: интервал %d минут",
        config.PARSE_INTERVAL_MINUTES
    )
    return scheduler
