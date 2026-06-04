"""Middleware: автоматически создаёт/получает пользователя из БД."""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from db.crud import get_or_create_user
from db.database import async_session_factory

logger = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """Открывает сессию БД и передаёт её в хэндлер через data."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_factory() as session:
            data["session"] = session
            return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    """Автоматически создаёт запись User в БД при первом обращении."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Получаем telegram_id из разных типов событий
        user = data.get("event_from_user")
        if user and "session" in data:
            try:
                db_user = await get_or_create_user(
                    data["session"],
                    telegram_id=user.id,
                    username=user.username,
                )
                data["db_user"] = db_user
            except Exception as exc:
                logger.error("UserMiddleware: ошибка получения пользователя: %s", exc)
                data["db_user"] = None

        return await handler(event, data)
