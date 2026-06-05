"""Парсер FL.ru через RSS-ленту."""

import hashlib
import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from parsers.base import BaseParser, ParsedOrder

logger = logging.getLogger(__name__)

# RSS всех проектов FL.ru
FL_RSS_URL = "https://www.fl.ru/rss/all.xml"


class FlRuParser(BaseParser):
    """Парсит RSS-ленту FL.ru."""

    source_name = "fl.ru"

    async def fetch(self) -> list[ParsedOrder]:
        """Вернуть список заказов из RSS FL.ru."""
        try:
            async with await self._get_client() as client:
                response = await client.get(FL_RSS_URL)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "xml")
            items = soup.find_all("item")
            orders = []

            for item in items:
                try:
                    order = self._parse_item(item)
                    if order:
                        orders.append(order)
                except Exception as exc:
                    logger.debug("FL.ru RSS: ошибка разбора item: %s", exc)
                    continue

            logger.info("FL.ru: получено %d заказов из RSS", len(orders))
            return orders

        except Exception as exc:
            logger.error("Ошибка парсинга FL.ru RSS: %s", exc)
            return []

    def _parse_item(self, item) -> ParsedOrder | None:
        """Разобрать один RSS-элемент."""
        title_tag = item.find("title")
        link_tag = item.find("link")
        desc_tag = item.find("description")
        pub_tag = item.find("pubDate")
        guid_tag = item.find("guid")

        if not title_tag or not link_tag:
            return None

        title = title_tag.get_text(strip=True)
        url = link_tag.get_text(strip=True)

        # Описание — убираем HTML-теги
        raw_desc = desc_tag.get_text(strip=True) if desc_tag else ""
        description = BeautifulSoup(raw_desc, "html.parser").get_text(strip=True)

        # External ID из guid или URL
        guid = guid_tag.get_text(strip=True) if guid_tag else url
        external_id = hashlib.md5(guid.encode()).hexdigest()[:16]

        # Время публикации
        published_at = datetime.utcnow()
        if pub_tag:
            try:
                published_at = parsedate_to_datetime(pub_tag.get_text(strip=True)).replace(tzinfo=None)
            except Exception:
                pass

        # Попытка извлечь бюджет из описания
        budget = self._extract_budget(description)

        return ParsedOrder(
            title=title,
            description=description[:1000],
            url=url,
            source=self.source_name,
            external_id=external_id,
            budget=budget,
            published_at=published_at,
        )

    def _extract_budget(self, text: str) -> int | None:
        """Извлечь бюджет из текста описания."""
        patterns = [
            r"Бюджет[:\s]+(\d[\d\s]*)",
            r"(\d[\d\s]{3,})\s*(?:руб|₽|р\.?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                digits = re.sub(r"\s", "", match.group(1))
                if digits.isdigit():
                    amount = int(digits)
                    if 100 <= amount <= 100_000_000:
                        return amount
        return None
