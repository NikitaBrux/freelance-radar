"""Точка входа бота."""

import asyncio
import logging
import os
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import filters, orders, start
from bot.middlewares import DbSessionMiddleware, UserMiddleware
from config import config
from db.database import init_db
from scheduler import create_scheduler, run_all_parsers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """Действия при запуске бота."""
    logger.info("Инициализация базы данных...")
    await init_db()

    logger.info("Запуск планировщика...")
    scheduler = create_scheduler(bot)
    scheduler.start()

    # Запустить парсинг сразу при старте
    asyncio.create_task(run_all_parsers(bot))

    logger.info("Бот запущен!")


async def on_shutdown(bot: Bot) -> None:
    """Действия при остановке бота."""
    logger.info("Бот останавливается...")


async def main() -> None:
    if not config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN не задан в .env файле")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Middleware
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(UserMiddleware())

    # Роутеры хэндлеров
    dp.include_router(start.router)
    dp.include_router(filters.router)
    dp.include_router(orders.router)

    # Хуки запуска/остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Запуск polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def health_server() -> None:
    """Минимальный HTTP-сервер для Railway healthcheck."""
    port = int(os.getenv("PORT", "8080"))

    async def handle(_: web.Request) -> web.Response:
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health server запущен на порту %d", port)


async def run() -> None:
    """Запустить бота и health-сервер одновременно."""
    await asyncio.gather(main(), health_server())


if __name__ == "__main__":
    asyncio.run(run())
