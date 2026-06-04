"""Хэндлеры /start, /pause, /resume, /help и главное меню."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import back_to_menu_keyboard, main_menu_keyboard
from db.crud import set_user_active
from db.models import User

logger = logging.getLogger(__name__)
router = Router()

WELCOME_TEXT = (
    "👋 <b>FreelanceRadar</b> — агрегатор фриланс-заказов!\n\n"
    "Я буду искать заказы на FL.ru и Kwork "
    "и присылать только те, что подходят под твои фильтры.\n\n"
    "Выбери действие:"
)

HELP_TEXT = (
    "📖 <b>Доступные команды:</b>\n\n"
    "/start — главное меню\n"
    "/filters — настроить фильтры (ключевые слова, бюджет, площадки)\n"
    "/latest — последние 5 подходящих заказов\n"
    "/pause — приостановить уведомления\n"
    "/resume — возобновить уведомления\n"
    "/stats — статистика за неделю\n"
    "/help — это сообщение\n"
)


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=back_to_menu_keyboard(), parse_mode="HTML")


@router.message(Command("pause"))
async def cmd_pause(message: Message, session, db_user: User) -> None:
    await set_user_active(session, message.from_user.id, False)
    await message.answer(
        "⏸ Уведомления приостановлены. Возобнови командой /resume.",
        reply_markup=back_to_menu_keyboard(),
    )


@router.message(Command("resume"))
async def cmd_resume(message: Message, session, db_user: User) -> None:
    await set_user_active(session, message.from_user.id, True)
    await message.answer(
        "▶️ Уведомления возобновлены! Буду слать новые заказы.",
        reply_markup=back_to_menu_keyboard(),
    )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery) -> None:
    await call.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "open_help")
async def cb_help(call: CallbackQuery) -> None:
    await call.message.edit_text(HELP_TEXT, reply_markup=back_to_menu_keyboard(), parse_mode="HTML")
    await call.answer()
