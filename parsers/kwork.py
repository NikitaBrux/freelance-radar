"""Парсер Kwork.ru — раздел «Проекты / Разработка»."""

import asyncio
import hashlib
import logging
import random
import re
from datetime import datetime

from bs4 import BeautifulSoup

from parsers.base import BaseParser, ParsedOrder

logger = logging.getLogger(__name__)

KWORK_URL = "https://kwork.ru/projects?c=11"  # категория 11 — разработка


class KworkParser(BaseParser):
    """Парсит раздел заказов на kwork.ru."""

    source_name = "kwork"

    async def fetch(self) -> list[ParsedOrder]:
        """Вернуть список заказов с Kwork."""
        try:
            await asyncio.sleep(random.uniform(1.0, 3.0))

            async with await self._get_client() as client:
                response = await client.get(KWORK_URL)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            orders = self._parse_projects(soup)
            logger.info("Kwork: получено %d заказов", len(orders))
            return orders

        except Exception as exc:
            logger.error("Ошибка парсинга Kwork: %s", exc)
            return []

    def _parse_projects(self, soup: BeautifulSoup) -> list[ParsedOrder]:
        """Извлечь заказы из HTML."""
        orders: list[ParsedOrder] = []

        # Карточки проектов
        cards = soup.select(".wants-card, .project-card, article.want")
        if not cards:
            cards = soup.select("div[class*='project']")

        for card in cards:
            try:
                order = self._parse_card(card)
                if order:
                    orders.append(order)
            except Exception as exc:
                logger.debug("Kwork: ошибка разбора карточки: %s", exc)
                continue

        return orders

    def _parse_card(self, card) -> ParsedOrder | None:
        """Разобрать карточку заказа."""
        # Заголовок
        title_tag = card.select_one("a.wants-card__header-title, .project-card__title a, h2 a")
        if not title_tag:
            return None

        title = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        if not href:
            return None

        url = f"https://kwork.ru{href}" if href.startswith("/") else href

        # External ID из URL или хеш
        match = re.search(r"/projects/(\d+)/", href)
        external_id = match.group(1) if match else hashlib.md5(url.encode()).hexdigest()[:12]

        # Описание
        desc_tag = card.select_one(".wants-card__description, .project-card__description")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # Бюджет
        budget = self._parse_budget(card)

        return ParsedOrder(
            title=title,
            description=description[:1000],
            url=url,
            source=self.source_name,
            external_id=external_id,
            budget=budget,
            published_at=datetime.utcnow(),
        )

    def _parse_budget(self, card) -> int | None:
        """Извлечь бюджет."""
        budget_tag = card.select_one(".wants-card__price, .project-card__price, .price")
        if not budget_tag:
            return None

        text = budget_tag.get_text(strip=True)
        digits = re.sub(r"[^\d]", "", text)
        if digits:
            # Kwork показывает диапазон — берём минимальное
            return int(digits[:8])  # обрезаем на случай конкатенации
        return None
