from datetime import datetime, time

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, Index, String, Text,
                        Time, UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(10))
    __table_args__ = (CheckConstraint("role IN ('client','master')", name="ck_users_role"),)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Master(Base):
    __tablename__ = "masters"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    city: Mapped[str] = mapped_column(String(100))
    bio: Mapped[str] = mapped_column(Text, default="")
    user: Mapped[User] = relationship()
    category: Mapped[Category] = relationship()
    __table_args__ = (Index("ix_masters_city_category", "city", "category_id"),)


class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(primary_key=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column()  # у гривнях
    duration_min: Mapped[int] = mapped_column()
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_services_price"),
        CheckConstraint("duration_min > 0", name="ck_services_duration"),
    )


class WorkSchedule(Base):
    __tablename__ = "work_schedule"
    id: Mapped[int] = mapped_column(primary_key=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"))
    weekday: Mapped[int] = mapped_column()  # 0 = понеділок
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    __table_args__ = (
        UniqueConstraint("master_id", "weekday", name="uq_schedule_master_weekday"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_schedule_weekday"),
        CheckConstraint("start_time < end_time", name="ck_schedule_time"),
    )


class Booking(Base):
    """master_id дублює services.master_id свідомо (обґрунтована денормалізація):
    потрібен для швидкої перевірки зайнятості слота та часткового UNIQUE-індексу."""

    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"))
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(10), default="booked")
    service: Mapped[Service] = relationship()
    __table_args__ = (
        CheckConstraint("status IN ('booked','cancelled')", name="ck_bookings_status"),
        CheckConstraint("end_at > start_at", name="ck_bookings_time"),
        Index("uq_booking_active_slot", "master_id", "start_at", unique=True,
              sqlite_where=text("status = 'booked'"),
              postgresql_where=text("status = 'booked'")),
    )


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True)
    rating: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),)
