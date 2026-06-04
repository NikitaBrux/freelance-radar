"""Парсер Telegram-каналов через Telethon."""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import Message

from config import config
from parsers.base import BaseParser, ParsedOrder

logger = logging.getLogger(__name__)

# Количество последних сообщений на канал
MESSAGES_LIMIT = 30


class TgChannelsParser(BaseParser):
    """Парсит сообщения из списка Telegram-каналов."""

    source_name = "telegram"

    def __init__(self) -> None:
        self._client: Optional[TelegramClient] = None

    async def _get_client(self) -> TelegramClient:  # type: ignore[override]
        """Получить (или создать) Telethon-клиент."""
        if self._client is None or not self._client.is_connected():
            self._client = TelegramClient(
                "freelance_radar_session",
                config.TG_API_ID,
                config.TG_API_HASH,
            )
            await self._client.start(phone=config.TG_PHONE)
        return self._client

    async def fetch(self) -> list[ParsedOrder]:
        """Вернуть список заказов из всех настроенных каналов."""
        orders: list[ParsedOrder] = []
        try:
            client = await self._get_client()
            for channel in config.TG_CHANNELS:
                try:
                    channel_orders = await self._fetch_channel(client, channel)
                    orders.extend(channel_orders)
                    logger.info("TG @%s: получено %d сообщений", channel, len(channel_orders))
                except Exception as exc:
                    logger.error("Ошибка парсинга канала @%s: %s", channel, exc)
        except Exception as exc:
            logger.error("Ошибка подключения к Telegram: %s", exc)

        return orders

    async def _fetch_channel(self, client: TelegramClient, channel: str) -> list[ParsedOrder]:
        """Получить последние сообщения из одного канала."""
        orders: list[ParsedOrder] = []

        async for message in client.iter_messages(channel, limit=MESSAGES_LIMIT):
            if not isinstance(message, Message) or not message.text:
                continue

            order = self._message_to_order(message, channel)
            if order:
                orders.append(order)

        return orders

    def _message_to_order(self, message: Message, channel: str) -> Optional[ParsedOrder]:
        """Преобразовать Telegram-сообщение в заказ."""
        text = message.text or ""
        if len(text) < 20:
            # Слишком короткое сообщение — пропустить
            return None

        # Первая строка — заголовок, остальное — описание
        lines = text.strip().split("\n", 1)
        title = lines[0][:255]
        description = lines[1].strip() if len(lines) > 1 else ""

        # Ссылка на сообщение
        url = f"https://t.me/{channel}/{message.id}"

        # Уникальный ID = канал + id сообщения
        external_id = f"{channel}_{message.id}"

        # Попытаться извлечь бюджет из текста
        budget = self._extract_budget(text)

        # Время публикации
        published_at = message.date
        if published_at and published_at.tzinfo:
            published_at = published_at.replace(tzinfo=None)

        return ParsedOrder(
            title=title,
            description=description[:1000],
            url=url,
            source=self.source_name,
            external_id=external_id,
            budget=budget,
            published_at=published_at or datetime.utcnow(),
        )

    def _extract_budget(self, text: str) -> Optional[int]:
        """Попытаться найти сумму бюджета в тексте сообщения."""
        import re
        # Ищем паттерны: "от 5000", "бюджет: 10000", "5 000 руб", "10к"
        patterns = [
            r"(?:бюджет|budget|оплата|зарплата)[:\s]+(\d[\d\s]*)",
            r"от\s+(\d[\d\s]{2,})",
            r"(\d+)\s*[кk]\s*(?:руб|₽|р\.?)",
            r"(\d[\d\s]{3,})\s*(?:руб|₽|р\.?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw = re.sub(r"\s", "", match.group(1))
                if raw.isdigit():
                    amount = int(raw)
                    # Если "к" был в паттерне — умножить на 1000
                    if "к" in match.group(0).lower() or "k" in match.group(0).lower():
                        amount *= 1000
                    return amount if 100 <= amount <= 100_000_000 else None
        return None

    async def stop(self) -> None:
        """Остановить Telethon-клиент."""
        if self._client and self._client.is_connected():
            await self._client.disconnect()
