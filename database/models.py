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
    img: Mapped[str] = mapped_column(Text)
    is_shown: Mapped[bool] = mapped_column(Boolean)
    announsed: Mapped[bool] = mapped_column(Boolean)

class Events(Base):
    __tablename__ = "events"
#
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text)
    date: Mapped[datetime] = mapped_column(DateTime)
    description: Mapped[str] = mapped_column(Text)
    link: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    is_free: Mapped[bool] = mapped_column(Boolean)
    img: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    is_shown: Mapped[bool] = mapped_column(Boolean)
    announsed: Mapped[bool] = mapped_column(Boolean)



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
    name: Mapped[str] = mapped_column(Text)
    agreement: Mapped[bool] = mapped_column(Boolean)
    subscribed: Mapped[bool] = mapped_column(Boolean)

class Product(Base):
    __tablename__ = 'product'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Float(asdecimal=True), nullable=False)
    image: Mapped[str] = mapped_column(String(150))