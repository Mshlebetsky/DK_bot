from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Text, DateTime, func, Boolean, INTEGER


class Base(DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    img: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    is_shown: Mapped[bool] = mapped_column(Boolean, default=True)
    announsed: Mapped[bool] = mapped_column(Boolean, default=False)

class Events(Base):
    __tablename__ = "events"
#
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text)
    date: Mapped[datetime] = mapped_column(DateTime)
    description: Mapped[str] = mapped_column(Text)
    link: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    img: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    is_shown: Mapped[bool] = mapped_column(Boolean, default=True)
    announsed: Mapped[bool] = mapped_column(Boolean, default=False)



class Studios(Base):
    __tablename__ = "studios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    teacher: Mapped[str] = mapped_column(String, nullable=True)
    cost: Mapped[int] = mapped_column(INTEGER)
    age: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(Text)
    qr_img: Mapped[str] = mapped_column(Text, nullable=True)
    img: Mapped[str] = mapped_column(Text, nullable=True)
    is_shown: Mapped[bool] = mapped_column(Boolean, default=True)
    announsed: Mapped[bool] = mapped_column(Boolean, default=False)


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    news_subscribed: Mapped[bool] = mapped_column(Boolean ,default=False)
    events_subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    admin : Mapped[bool] = mapped_column(Boolean, default=False)