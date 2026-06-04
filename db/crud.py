"""CRUD-операции с базой данных."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Order, SentOrder, User, UserFilter

logger = logging.getLogger(__name__)


# ---------- User ----------

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: Optional[str]) -> User:
    """Получить пользователя или создать нового."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("Создан новый пользователь telegram_id=%s", telegram_id)
    else:
        # Обновить username если изменился
        if user.username != username:
            user.username = username
            await session.commit()
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(selectinload(User.filters))
    )
    return result.scalar_one_or_none()


async def get_all_active_users(session: AsyncSession) -> list[User]:
    """Получить всех активных пользователей с загруженными фильтрами."""
    result = await session.execute(
        select(User)
        .where(User.is_active == True)
        .options(selectinload(User.filters))
    )
    return list(result.scalars().all())


async def set_user_active(session: AsyncSession, telegram_id: int, is_active: bool) -> None:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user:
        user.is_active = is_active
        await session.commit()


# ---------- UserFilter ----------

async def save_user_filter(
    session: AsyncSession,
    user_id: int,
    keywords: list[str],
    min_budget: Optional[int],
    sources: list[str],
) -> UserFilter:
    """Создать или обновить фильтр пользователя."""
    result = await session.execute(select(UserFilter).where(UserFilter.user_id == user_id))
    uf = result.scalar_one_or_none()
    if uf is None:
        uf = UserFilter(user_id=user_id)
        session.add(uf)
    uf.keywords = keywords
    uf.min_budget = min_budget
    uf.sources = sources
    await session.commit()
    await session.refresh(uf)
    return uf


async def get_user_filter(session: AsyncSession, user_id: int) -> Optional[UserFilter]:
    result = await session.execute(select(UserFilter).where(UserFilter.user_id == user_id))
    return result.scalar_one_or_none()


async def update_last_notified(session: AsyncSession, user_filter_id: int, dt: datetime) -> None:
    result = await session.execute(select(UserFilter).where(UserFilter.id == user_filter_id))
    uf = result.scalar_one_or_none()
    if uf:
        uf.last_notified_at = dt
        await session.commit()


# ---------- Order ----------

async def save_order_if_new(session: AsyncSession, order_data: dict) -> Optional[Order]:
    """Сохранить заказ только если его ещё нет в БД (по external_id + source)."""
    result = await session.execute(
        select(Order).where(
            Order.external_id == order_data["external_id"],
            Order.source == order_data["source"],
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return None

    order = Order(**order_data)
    session.add(order)
    try:
        await session.commit()
        await session.refresh(order)
        return order
    except Exception as exc:
        await session.rollback()
        logger.warning("Дубликат заказа при сохранении: %s", exc)
        return None


async def get_orders_for_user(
    session: AsyncSession,
    user_filter: UserFilter,
    after_dt: Optional[datetime] = None,
    limit: int = 5,
) -> list[Order]:
    """Получить заказы подходящие под фильтр пользователя."""
    stmt = select(Order).order_by(Order.created_at.desc())

    if after_dt:
        stmt = stmt.where(Order.created_at > after_dt)

    # Фильтр по источникам
    if user_filter.sources:
        stmt = stmt.where(Order.source.in_(user_filter.sources))

    # Фильтр по бюджету
    if user_filter.min_budget:
        stmt = stmt.where(
            (Order.budget == None) | (Order.budget >= user_filter.min_budget)
        )

    result = await session.execute(stmt.limit(limit * 10))  # берём с запасом для фильтра по ключам
    orders = list(result.scalars().all())

    # Фильтр по ключевым словам (в Python, т.к. SQLite не поддерживает регистронезависимый JSON-поиск)
    if user_filter.keywords:
        keywords_lower = [kw.lower() for kw in user_filter.keywords]
        orders = [
            o for o in orders
            if any(
                kw in (o.title + " " + o.description).lower()
                for kw in keywords_lower
            )
        ]

    return orders[:limit]


async def get_new_orders_for_notification(
    session: AsyncSession,
    user: User,
    user_filter: UserFilter,
) -> list[Order]:
    """Заказы после last_notified_at, не отправлявшиеся ранее."""
    after_dt = user_filter.last_notified_at

    stmt = select(Order).order_by(Order.created_at.asc())

    if after_dt:
        stmt = stmt.where(Order.created_at > after_dt)

    if user_filter.sources:
        stmt = stmt.where(Order.source.in_(user_filter.sources))

    if user_filter.min_budget:
        stmt = stmt.where(
            (Order.budget == None) | (Order.budget >= user_filter.min_budget)
        )

    # Исключить уже отправленные
    sent_subq = select(SentOrder.order_id).where(SentOrder.user_id == user.id)
    stmt = stmt.where(Order.id.not_in(sent_subq))

    result = await session.execute(stmt)
    orders = list(result.scalars().all())

    # Фильтр по ключевым словам
    if user_filter.keywords:
        keywords_lower = [kw.lower() for kw in user_filter.keywords]
        orders = [
            o for o in orders
            if any(
                kw in (o.title + " " + o.description).lower()
                for kw in keywords_lower
            )
        ]

    return orders


# ---------- SentOrder ----------

async def mark_order_sent(session: AsyncSession, user_id: int, order_id: int) -> None:
    """Записать что заказ был отправлен пользователю."""
    sent = SentOrder(user_id=user_id, order_id=order_id)
    session.add(sent)
    try:
        await session.commit()
    except Exception:
        await session.rollback()


# ---------- Stats ----------

async def get_user_stats(session: AsyncSession, user_id: int) -> dict:
    """Статистика пользователя за последние 7 дней."""
    week_ago = datetime.utcnow() - timedelta(days=7)

    # Всего заказов найдено за неделю
    total_result = await session.execute(
        select(func.count(Order.id)).where(Order.created_at >= week_ago)
    )
    total = total_result.scalar_one() or 0

    # Отправлено пользователю за неделю
    sent_result = await session.execute(
        select(func.count(SentOrder.id)).where(
            SentOrder.user_id == user_id,
            SentOrder.sent_at >= week_ago,
        )
    )
    sent = sent_result.scalar_one() or 0

    # Разбивка по площадкам среди отправленных
    breakdown_result = await session.execute(
        select(Order.source, func.count(Order.id))
        .join(SentOrder, SentOrder.order_id == Order.id)
        .where(SentOrder.user_id == user_id, SentOrder.sent_at >= week_ago)
        .group_by(Order.source)
    )
    breakdown = {row[0]: row[1] for row in breakdown_result.all()}

    return {"total": total, "sent": sent, "breakdown": breakdown}
