"""Нотификатор — рассылает подходящие заказы активным пользователям."""

import logging
from datetime import datetime

from aiogram import Bot

from db.crud import (
    get_all_active_users,
    get_new_orders_for_notification,
    mark_order_sent,
    update_last_notified,
)
from db.database import async_session_factory
from db.models import Order

logger = logging.getLogger(__name__)

SOURCE_EMOJI = {
    "fl.ru": "🔵",
    "kwork": "🟠",
    "telegram": "✈️",
}


def format_order_notification(order: Order) -> str:
    """Сформировать текст уведомления о заказе."""
    emoji = SOURCE_EMOJI.get(order.source, "📌")

    budget_str = ""
    if order.budget:
        budget_str = f"\n💰 <b>Бюджет:</b> {order.budget:,} ₽".replace(",", " ")

    pub_str = ""
    if order.published_at:
        pub_str = f"\n🕐 {order.published_at.strftime('%d.%m.%Y %H:%M')}"

    return (
        f"🆕 Новый заказ!\n\n"
        f"{emoji} <b>{order.title}</b>"
        f"{budget_str}"
        f"{pub_str}\n"
        f"🔗 <a href='{order.url}'>Открыть заказ</a>"
    )


async def notify_users(bot: Bot) -> None:
    """Найти подходящие заказы для каждого активного пользователя и отправить."""
    async with async_session_factory() as session:
        try:
            users = await get_all_active_users(session)
        except Exception as exc:
            logger.error("Ошибка получения пользователей для нотификации: %s", exc)
            return

        for user in users:
            user_filter = user.filters
            if not user_filter:
                continue

            if not user_filter.keywords:
                # Пользователь ещё не настроил фильтры — пропускаем
                continue

            try:
                orders = await get_new_orders_for_notification(session, user, user_filter)
            except Exception as exc:
                logger.error(
                    "Ошибка получения заказов для пользователя %s: %s",
                    user.telegram_id, exc
                )
                continue

            if not orders:
                continue

            logger.info(
                "Отправляем %d заказов пользователю %s",
                len(orders), user.telegram_id
            )

            now = datetime.utcnow()
            sent_count = 0

            for order in orders:
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=format_order_notification(order),
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                    await mark_order_sent(session, user_id=user.id, order_id=order.id)
                    sent_count += 1
                except Exception as exc:
                    logger.error(
                        "Ошибка отправки заказа #%s пользователю %s: %s",
                        order.id, user.telegram_id, exc
                    )

            # Обновить время последнего уведомления
            if sent_count > 0:
                try:
                    await update_last_notified(session, user_filter.id, now)
                except Exception as exc:
                    logger.error("Ошибка обновления last_notified_at: %s", exc)
