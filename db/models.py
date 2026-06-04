"""SQLAlchemy-модели базы данных."""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """Пользователь бота."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    filters: Mapped[Optional["UserFilter"]] = relationship(
        "UserFilter", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    sent_orders: Mapped[list["SentOrder"]] = relationship(
        "SentOrder", back_populates="user", cascade="all, delete-orphan"
    )


class UserFilter(Base):
    """Настройки фильтрации заказов для пользователя."""

    __tablename__ = "user_filters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    # JSON-массив ключевых слов, например ["python", "django"]
    keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    min_budget: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # JSON-массив источников, например ["fl.ru", "kwork", "telegram"]
    sources_json: Mapped[str] = mapped_column(Text, default='["fl.ru","kwork","telegram"]')
    last_notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="filters")

    @property
    def keywords(self) -> list[str]:
        return json.loads(self.keywords_json)

    @keywords.setter
    def keywords(self, value: list[str]) -> None:
        self.keywords_json = json.dumps(value, ensure_ascii=False)

    @property
    def sources(self) -> list[str]:
        return json.loads(self.sources_json)

    @sources.setter
    def sources(self, value: list[str]) -> None:
        self.sources_json = json.dumps(value, ensure_ascii=False)


class Order(Base):
    """Заказ с фриланс-площадки."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    budget: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("external_id", "source", name="uq_order_external_source"),
    )

    sent_orders: Mapped[list["SentOrder"]] = relationship(
        "SentOrder", back_populates="order", cascade="all, delete-orphan"
    )


class SentOrder(Base):
    """Лог отправленных заказов — для дедупликации уведомлений."""

    __tablename__ = "sent_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "order_id", name="uq_sent_user_order"),
    )

    user: Mapped["User"] = relationship("User", back_populates="sent_orders")
    order: Mapped["Order"] = relationship("Order", back_populates="sent_orders")
