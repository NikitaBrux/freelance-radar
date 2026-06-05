"""Клавиатуры и inline-кнопки бота."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню после /start."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚙️ Настроить фильтры", callback_data="open_filters"),
        InlineKeyboardButton(text="📋 Последние заказы", callback_data="latest_orders"),
    )
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="open_help"),
    )
    return builder.as_markup()


def sources_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    """Чекбоксы выбора площадок."""
    all_sources = [
        ("fl.ru", "FL.ru"),
        ("kwork", "Хабр Карьера"),
    ]
    builder = InlineKeyboardBuilder()
    for source_id, label in all_sources:
        # Ставим галочку если источник выбран
        check = "✅" if source_id in selected else "☐"
        builder.row(
            InlineKeyboardButton(
                text=f"{check} {label}",
                callback_data=f"toggle_source:{source_id}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="💾 Сохранить", callback_data="save_sources"),
    )
    return builder.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Кнопки подтверждения/отмены."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_filters"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_filters"),
    )
    return builder.as_markup()


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
    )
    return builder.as_markup()
