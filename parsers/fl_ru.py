"""Парсер FL.ru — фриланс-биржа."""

import asyncio
import hashlib
import logging
import random
import re
from datetime import datetime

from bs4 import BeautifulSoup

from parsers.base import BaseParser, ParsedOrder

logger = logging.getLogger(__name__)

FL_URL = "https://www.fl.ru/projects/?category=1"


class FlRuParser(BaseParser):
    """Парсит раздел IT-проекты на fl.ru."""

    source_name = "fl.ru"

    async def fetch(self) -> list[ParsedOrder]:
        """Вернуть список заказов с FL.ru."""
        try:
            # Случайная задержка 1-3 секунды перед запросом
            await asyncio.sleep(random.uniform(1.0, 3.0))

            async with await self._get_client() as client:
                response = await client.get(FL_URL)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            orders = self._parse_projects(soup)
            logger.info("FL.ru: получено %d заказов", len(orders))
            return orders

        except Exception as exc:
            logger.error("Ошибка парсинга FL.ru: %s", exc)
            return []

    def _parse_projects(self, soup: BeautifulSoup) -> list[ParsedOrder]:
        """Извлечь заказы из HTML-страницы."""
        orders: list[ParsedOrder] = []

        # Блоки с проектами
        project_blocks = soup.select("div.b-post.b-post_pad_all")
        if not project_blocks:
            # Запасной селектор
            project_blocks = soup.select("article.b-post")

        for block in project_blocks:
            try:
                order = self._parse_single_project(block)
                if order:
                    orders.append(order)
            except Exception as exc:
                logger.debug("FL.ru: ошибка разбора блока: %s", exc)
                continue

        return orders

    def _parse_single_project(self, block) -> ParsedOrder | None:
        """Разобрать один блок проекта."""
        # Заголовок и ссылка
        title_tag = block.select_one("h2 a, .b-post__title a")
        if not title_tag:
            return None

        title = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        if not href:
            return None

        url = f"https://www.fl.ru{href}" if href.startswith("/") else href

        # Уникальный ID из URL
        match = re.search(r"/projects/(\d+)/", href)
        external_id = match.group(1) if match else hashlib.md5(url.encode()).hexdigest()[:12]

        # Описание
        desc_tag = block.select_one(".b-post__body, .b-post__descr")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # Бюджет
        budget = self._parse_budget(block)

        return ParsedOrder(
            title=title,
            description=description[:1000],
            url=url,
            source=self.source_name,
            external_id=external_id,
            budget=budget,
            published_at=datetime.utcnow(),
        )

    def _parse_budget(self, block) -> int | None:
        """Извлечь бюджет в рублях."""
        budget_tag = block.select_one(".b-post__price, .price")
        if not budget_tag:
            return None

        text = budget_tag.get_text(strip=True)
        # Убрать всё кроме цифр
        digits = re.sub(r"[^\d]", "", text)
        if digits:
            return int(digits)
        return None
