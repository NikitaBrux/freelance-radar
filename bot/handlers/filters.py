"""FSM-диалог настройки фильтров (/filters)."""

import logging
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.keyboards import back_to_menu_keyboard, confirm_keyboard, sources_keyboard
from db.crud import save_user_filter
from db.models import User

logger = logging.getLogger(__name__)
router = Router()

# Площадки по умолчанию (все включены)
DEFAULT_SOURCES = ["fl.ru", "kwork"]


class FilterSetup(StatesGroup):
    """Состояния FSM для настройки фильтров."""
    waiting_keywords = State()
    waiting_budget = State()
    choosing_sources = State()
    confirming = State()


@router.message(Command("filters"))
@router.callback_query(F.data == "open_filters")
async def start_filter_setup(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Начать пошаговый диалог настройки фильтров."""
    text = (
        "⚙️ <b>Настройка фильтров</b> — шаг 1/3\n\n"
        "Введи ключевые слова через запятую.\n"
        "Например: <code>python, django, fastapi</code>\n\n"
        "Заказы будут показываться только если содержат хотя бы одно слово."
    )
    await state.set_state(FilterSetup.waiting_keywords)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(FilterSetup.waiting_keywords)
async def process_keywords(message: Message, state: FSMContext) -> None:
    """Обработать введённые ключевые слова."""
    raw = message.text or ""
    keywords = [kw.strip().lower() for kw in raw.split(",") if kw.strip()]

    if not keywords:
        await message.answer(
            "⚠️ Не удалось распознать ключевые слова. Попробуй ещё раз.\n"
            "Пример: <code>python, django, fastapi</code>",
            parse_mode="HTML",
        )
        return

    await state.update_data(keywords=keywords)

    await state.set_state(FilterSetup.waiting_budget)
    await message.answer(
        f"✅ Ключевые слова сохранены: <b>{', '.join(keywords)}</b>\n\n"
        "⚙️ Шаг 2/3\n\n"
        "Введи минимальный бюджет в рублях (только цифры).\n"
        "Или отправь <code>0</code> чтобы не ограничивать.",
        parse_mode="HTML",
    )


@router.message(FilterSetup.waiting_budget)
async def process_budget(message: Message, state: FSMContext) -> None:
    """Обработать введённый бюджет."""
    raw = (message.text or "").strip()

    if not raw.isdigit():
        await message.answer(
            "⚠️ Нужно ввести число. Например: <code>5000</code> или <code>0</code>",
            parse_mode="HTML",
        )
        return

    min_budget: Optional[int] = int(raw) if int(raw) > 0 else None
    await state.update_data(min_budget=min_budget)

    # Инициализировать выбранные площадки всеми по умолчанию
    await state.update_data(sources=DEFAULT_SOURCES.copy())

    await state.set_state(FilterSetup.choosing_sources)
    budget_str = f"{min_budget:,} ₽".replace(",", " ") if min_budget else "без ограничений"
    await message.answer(
        f"✅ Минимальный бюджет: <b>{budget_str}</b>\n\n"
        "⚙️ Шаг 3/3\n\n"
        "Выбери площадки для поиска (нажимай чтобы включить/выключить):",
        reply_markup=sources_keyboard(DEFAULT_SOURCES),
        parse_mode="HTML",
    )


@router.callback_query(FilterSetup.choosing_sources, F.data.startswith("toggle_source:"))
async def toggle_source(call: CallbackQuery, state: FSMContext) -> None:
    """Переключить включение/выключение площадки."""
    source_id = call.data.split(":", 1)[1]
    data = await state.get_data()
    selected: list[str] = data.get("sources", DEFAULT_SOURCES.copy())

    if source_id in selected:
        selected.remove(source_id)
    else:
        selected.append(source_id)

    await state.update_data(sources=selected)
    await call.message.edit_reply_markup(reply_markup=sources_keyboard(selected))
    await call.answer()


@router.callback_query(FilterSetup.choosing_sources, F.data == "save_sources")
async def save_sources(call: CallbackQuery, state: FSMContext) -> None:
    """Перейти к подтверждению настроек."""
    data = await state.get_data()
    sources: list[str] = data.get("sources", [])

    if not sources:
        await call.answer("⚠️ Выбери хотя бы одну площадку!", show_alert=True)
        return

    keywords: list[str] = data.get("keywords", [])
    min_budget: Optional[int] = data.get("min_budget")

    budget_str = f"{min_budget:,} ₽".replace(",", " ") if min_budget else "без ограничений"
    sources_str = ", ".join(sources) or "нет"

    summary = (
        "📋 <b>Проверь настройки:</b>\n\n"
        f"🔑 Ключевые слова: <b>{', '.join(keywords)}</b>\n"
        f"💰 Минимальный бюджет: <b>{budget_str}</b>\n"
        f"🌐 Площадки: <b>{sources_str}</b>\n\n"
        "Сохранить?"
    )

    await state.set_state(FilterSetup.confirming)
    await call.message.edit_text(summary, reply_markup=confirm_keyboard(), parse_mode="HTML")
    await call.answer()


@router.callback_query(FilterSetup.confirming, F.data == "confirm_filters")
async def confirm_filters(call: CallbackQuery, state: FSMContext, session, db_user: User) -> None:
    """Сохранить фильтры в БД."""
    data = await state.get_data()
    await state.clear()

    try:
        await save_user_filter(
            session,
            user_id=db_user.id,
            keywords=data.get("keywords", []),
            min_budget=data.get("min_budget"),
            sources=data.get("sources", DEFAULT_SOURCES),
        )
        await call.message.edit_text(
            "✅ <b>Фильтры сохранены!</b>\n\nБуду присылать подходящие заказы автоматически.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        logger.info("Пользователь %s сохранил фильтры", db_user.telegram_id)
    except Exception as exc:
        logger.error("Ошибка сохранения фильтров: %s", exc)
        await call.message.edit_text(
            "❌ Ошибка при сохранении. Попробуй позже.",
            reply_markup=back_to_menu_keyboard(),
        )

    await call.answer()


@router.callback_query(FilterSetup.confirming, F.data == "cancel_filters")
async def cancel_filters(call: CallbackQuery, state: FSMContext) -> None:
    """Отменить настройку фильтров."""
    await state.clear()
    await call.message.edit_text(
        "❌ Настройка отменена.",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer()
