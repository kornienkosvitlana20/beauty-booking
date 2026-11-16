from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db, require_client
from ..models import Booking, Master, Review, Service, User
from ..scheduling import check_slot
from ..schemas import BookingCreate, BookingOut, RescheduleIn, ReviewCreate, ReviewOut

router = APIRouter(tags=["bookings"])


def _out(b: Booking) -> BookingOut:
    return BookingOut(id=b.id, client_id=b.client_id, master_id=b.master_id,
                      service_id=b.service_id, service_name=b.service.name,
                      start_at=b.start_at, end_at=b.end_at, status=b.status)


def _commit_or_conflict(db: Session):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Цей час уже зайнятий") from exc


def _lock_master(db: Session, master_id: int):
    # У PostgreSQL серіалізує одночасні записи до одного майстра; SQLite ігнорує.
    db.execute(select(Master.id).where(Master.id == master_id).with_for_update())


@router.post("/bookings", response_model=BookingOut, status_code=201)
def create_booking(data: BookingCreate, user: User = Depends(require_client),
                   db: Session = Depends(get_db)):
    service = db.get(Service, data.service_id)
    if service is None:
        raise HTTPException(404, "Послугу не знайдено")
    _lock_master(db, service.master_id)
    end_at = check_slot(db, service.master_id, service, data.start_at)
    booking = Booking(client_id=user.id, service_id=service.id, master_id=service.master_id,
                      start_at=data.start_at, end_at=end_at, status="booked")
    db.add(booking)
    _commit_or_conflict(db)
    return _out(booking)


@router.get("/bookings/my", response_model=list[BookingOut])
def my_bookings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Booking).order_by(Booking.start_at.desc())
    if user.role == "client":
        stmt = stmt.where(Booking.client_id == user.id)
    else:
        master = db.scalar(select(Master).where(Master.user_id == user.id))
        if master is None:
            return []
        stmt = stmt.where(Booking.master_id == master.id)
    return [_out(b) for b in db.scalars(stmt).all()]


def _load_for_user(db: Session, booking_id: int, user: User) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(404, "Запис не знайдено")
    is_client = booking.client_id == user.id
    master = db.scalar(select(Master).where(Master.user_id == user.id))
    is_master = master is not None and master.id == booking.master_id
    if not (is_client or is_master):
        raise HTTPException(403, "Це не ваш запис")
    return booking


@router.post("/bookings/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(booking_id: int, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    booking = _load_for_user(db, booking_id, user)
    if booking.status != "booked":
        raise HTTPException(400, "Запис уже скасовано")
    if booking.start_at <= datetime.now():
        raise HTTPException(400, "Не можна скасувати запис, який уже минув")
    booking.status = "cancelled"
    db.commit()
    return _out(booking)


@router.post("/bookings/{booking_id}/reschedule", response_model=BookingOut)
def reschedule_booking(booking_id: int, data: RescheduleIn,
                       user: User = Depends(require_client), db: Session = Depends(get_db)):
    booking = _load_for_user(db, booking_id, user)
    if booking.client_id != user.id:
        raise HTTPException(403, "Це не ваш запис")
    if booking.status != "booked" or booking.start_at <= datetime.now():
        raise HTTPException(400, "Цей запис не можна перенести")
    _lock_master(db, booking.master_id)
    end_at = check_slot(db, booking.master_id, booking.service, data.start_at,
                        exclude_id=booking.id)
    booking.start_at, booking.end_at = data.start_at, end_at
    _commit_or_conflict(db)
    return _out(booking)


@router.post("/reviews", response_model=ReviewOut, status_code=201)
def create_review(data: ReviewCreate, user: User = Depends(require_client),
                  db: Session = Depends(get_db)):
    booking = db.get(Booking, data.booking_id)
    if booking is None:
        raise HTTPException(404, "Запис не знайдено")
    if booking.client_id != user.id:
        raise HTTPException(403, "Це не ваш запис")
    if booking.status != "booked" or booking.end_at > datetime.now():
        raise HTTPException(400, "Відгук можна залишити лише після відбутого візиту")
    if db.scalar(select(Review.id).where(Review.booking_id == booking.id)):
        raise HTTPException(409, "Відгук на цей запис уже залишено")
    review = Review(booking_id=booking.id, rating=data.rating, text=data.text.strip())
    db.add(review)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Відгук на цей запис уже залишено") from exc
    return ReviewOut(id=review.id, booking_id=booking.id, author=user.full_name,
                     rating=review.rating, text=review.text, created_at=review.created_at)
