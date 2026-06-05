"""Хэндлеры /latest и /stats."""

import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import back_to_menu_keyboard
from db.crud import get_orders_for_user, get_user_filter, get_user_stats
from db.models import Order, User

logger = logging.getLogger(__name__)
router = Router()

# Иконки для источников
SOURCE_EMOJI = {
    "fl.ru": "🔵",
    "kwork": "🟢",  # Хабр Карьера
}


def format_order(order: Order) -> str:
    """Отформатировать заказ для отправки пользователю."""
    emoji = SOURCE_EMOJI.get(order.source, "📌")

    budget_str = ""
    if order.budget:
        budget_str = f"\n💰 <b>Бюджет:</b> {order.budget:,} ₽".replace(",", " ")

    # Время публикации
    pub_str = ""
    if order.published_at:
        pub_str = f"\n🕐 {order.published_at.strftime('%d.%m.%Y %H:%M')}"

    return (
        f"{emoji} <b>{order.title}</b>"
        f"{budget_str}"
        f"{pub_str}\n"
        f"🔗 <a href='{order.url}'>Открыть заказ</a>"
    )


@router.message(Command("latest"))
@router.callback_query(F.data == "latest_orders")
async def show_latest(event: Message | CallbackQuery, session, db_user: User) -> None:
    """Показать последние 5 подходящих заказов."""
    is_callback = isinstance(event, CallbackQuery)
    send = event.message.answer if is_callback else event.answer

    user_filter = await get_user_filter(session, db_user.id)
    if not user_filter or not user_filter.keywords:
        await send(
            "⚠️ Сначала настрой фильтры командой /filters",
            reply_markup=back_to_menu_keyboard(),
        )
        if is_callback:
            await event.answer()
        return

    orders = await get_orders_for_user(session, user_filter, limit=5)

    if not orders:
        await send(
            "📭 Подходящих заказов пока нет.\n"
            "Попробуй изменить фильтры командой /filters",
            reply_markup=back_to_menu_keyboard(),
        )
        if is_callback:
            await event.answer()
        return

    # Отправляем вводное сообщение
    await send(f"📋 <b>Последние заказы по твоим фильтрам ({len(orders)} шт.):</b>", parse_mode="HTML")

    # Каждый заказ отдельным сообщением
    chat_id = event.message.chat.id if is_callback else event.chat.id
    bot = event.bot if is_callback else event.bot
    for order in orders:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=format_order(order),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception as exc:
            logger.error("Ошибка отправки заказа #%s: %s", order.id, exc)

    if is_callback:
        await event.answer()


@router.message(Command("stats"))
async def cmd_stats(message: Message, session, db_user: User) -> None:
    """Показать статистику за неделю."""
    try:
        stats = await get_user_stats(session, db_user.id)

        breakdown_lines = "\n".join(
            f"  {SOURCE_EMOJI.get(src, '•')} {src}: {cnt} заказов"
            for src, cnt in stats["breakdown"].items()
        ) or "  (нет данных)"

        text = (
            "📊 <b>Твоя статистика за 7 дней:</b>\n\n"
            f"🔍 Найдено заказов всего: <b>{stats['total']}</b>\n"
            f"📨 Подходящих и отправленных тебе: <b>{stats['sent']}</b>\n\n"
            f"<b>По площадкам (отправленные):</b>\n{breakdown_lines}"
        )
        await message.answer(text, reply_markup=back_to_menu_keyboard(), parse_mode="HTML")
    except Exception as exc:
        logger.error("Ошибка получения статистики: %s", exc)
        await message.answer("❌ Не удалось загрузить статистику. Попробуй позже.")
