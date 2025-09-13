"""
Модели базы данных для Telegram-бота ДК "Яуза".
"""

from datetime import datetime
from sqlalchemy import (
    String,
    Text,
    DateTime,
    func,
    Boolean,
    Integer,
    BigInteger,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех моделей.

    Автоматически добавляет поля `created` и `updated`
    для отслеживания времени создания и изменения записей.
    """

    __abstract__ = True

    created: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class News(Base):
    """Новости, отображаемые пользователям."""

    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    img: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    is_shown: Mapped[bool] = mapped_column(Boolean, default=True)
    announced: Mapped[bool] = mapped_column(Boolean, default=False)


class Events(Base):
    """Мероприятия, доступные для записи."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    age_limits: Mapped[int] = mapped_column(Integer, nullable=False)
    link: Mapped[str | None] = mapped_column(Text, nullable=True, default='')
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    img: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    is_shown: Mapped[bool] = mapped_column(Boolean, default=True)
    announced: Mapped[bool] = mapped_column(Boolean, default=False)


class Studios(Base):
    """Студии и кружки."""

    __tablename__ = "studios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    teacher: Mapped[str | None] = mapped_column(String, nullable=True)
    cost: Mapped[int] = mapped_column(Integer, nullable=False)
    age: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    qr_img: Mapped[str | None] = mapped_column(Text, nullable=True)
    img: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_shown: Mapped[bool] = mapped_column(Boolean, default=True)
    announced: Mapped[bool] = mapped_column(Boolean, default=False)


class Users(Base):
    """Пользователи Telegram-бота."""

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String, default="", nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, default="", nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, default="", nullable=True)
    subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    news_subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    events_subscribed: Mapped[bool] = mapped_column(Boolean, default=False)


class UserEventTracking(Base):
    """Трекинг участия пользователей в событиях."""

    __tablename__ = "user_event_tracking"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_id: Mapped[int] = mapped_column(Integer, nullable=False)


class Admin(Base):
    """Администраторы (суперадмины и редакторы)."""

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role: Mapped[str] = mapped_column(String, default="editor")  # "editor" | "superadmin"
