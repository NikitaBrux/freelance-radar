"""Базовый класс парсера и датакласс заказа."""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx

from config import config


@dataclass
class ParsedOrder:
    """Данные заказа полученные от парсера."""

    title: str
    description: str
    url: str
    source: str
    external_id: str
    budget: Optional[int] = None
    published_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "source": self.source,
            "external_id": self.external_id,
            "budget": self.budget,
            "published_at": self.published_at,
        }


class BaseParser(ABC):
    """Базовый класс для всех парсеров."""

    source_name: str = ""

    def _get_random_headers(self) -> dict[str, str]:
        """Вернуть заголовки со случайным User-Agent."""
        return {
            "User-Agent": random.choice(config.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Создать HTTP-клиент с таймаутом."""
        return httpx.AsyncClient(
            headers=self._get_random_headers(),
            timeout=30.0,
            follow_redirects=True,
        )

    @abstractmethod
    async def fetch(self) -> list[ParsedOrder]:
        """Получить список заказов с площадки."""
        ...
