"""Логіка вільних слотів і перевірки запису."""
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Booking, Service, WorkSchedule

STEP = timedelta(minutes=settings.slot_step_minutes)


def _schedule_for(db: Session, master_id: int, day: date) -> WorkSchedule | None:
    return db.scalar(
        select(WorkSchedule).where(
            WorkSchedule.master_id == master_id, WorkSchedule.weekday == day.weekday()
        )
    )


def _conflict_query(master_id: int, start: datetime, end: datetime, exclude_id: int | None):
    stmt = select(Booking.id).where(
        Booking.master_id == master_id,
        Booking.status == "booked",
        Booking.start_at < end,
        Booking.end_at > start,
    )
    if exclude_id is not None:
        stmt = stmt.where(Booking.id != exclude_id)
    return stmt.limit(1)


def free_slots(db: Session, master_id: int, service: Service, day: date,
               now: datetime | None = None) -> list[datetime]:
    now = now or datetime.now()
    sched = _schedule_for(db, master_id, day)
    if sched is None:
        return []
    day_start = datetime.combine(day, sched.start_time)
    day_end = datetime.combine(day, sched.end_time)
    duration = timedelta(minutes=service.duration_min)
    slots, current = [], day_start
    while current + duration <= day_end:
        busy = db.scalar(_conflict_query(master_id, current, current + duration, None))
        if current > now and busy is None:
            slots.append(current)
        current += STEP
    return slots


def check_slot(db: Session, master_id: int, service: Service, start_at: datetime,
               now: datetime | None = None, exclude_id: int | None = None) -> datetime:
    """Перевіряє, що слот можна забронювати. Повертає час завершення або кидає HTTPException."""
    now = now or datetime.now()
    if start_at <= now:
        raise HTTPException(400, "Не можна записатися на минулий час")
    sched = _schedule_for(db, master_id, start_at.date())
    if sched is None:
        raise HTTPException(400, "Майстер не працює в цей день")
    end_at = start_at + timedelta(minutes=service.duration_min)
    day_start = datetime.combine(start_at.date(), sched.start_time)
    day_end = datetime.combine(start_at.date(), sched.end_time)
    if start_at < day_start or end_at > day_end:
        raise HTTPException(400, "Час поза графіком роботи майстра")
    if (start_at - day_start) % STEP != timedelta(0):
        raise HTTPException(400, "Час має збігатися з сіткою слотів (крок 30 хв від початку зміни)")
    if db.scalar(_conflict_query(master_id, start_at, end_at, exclude_id)) is not None:
        raise HTTPException(409, "Цей час уже зайнятий")
    return end_at
