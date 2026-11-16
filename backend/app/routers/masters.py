from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, exists, func, select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db, require_master
from ..models import (Booking, Category, Master, Review, Service, User,
                      WorkSchedule)
from ..scheduling import free_slots
from ..schemas import (MasterCreate, MasterOut, ReviewOut, ScheduleItem,
                       ServiceCreate, ServiceOut, SlotsOut)

router = APIRouter(prefix="/masters", tags=["masters"])


def _rating_subquery():
    return (
        select(Booking.master_id.label("master_id"),
               func.avg(Review.rating).label("avg_rating"),
               func.count(Review.id).label("cnt"))
        .join(Review, Review.booking_id == Booking.id)
        .group_by(Booking.master_id)
        .subquery()
    )


def _to_out(master: Master, avg, cnt) -> MasterOut:
    return MasterOut(
        id=master.id, full_name=master.user.full_name, city=master.city,
        category_id=master.category_id, category_name=master.category.name,
        bio=master.bio, rating=round(float(avg), 2) if avg is not None else None,
        reviews_count=cnt or 0,
    )


def _get_master_or_404(db: Session, master_id: int) -> Master:
    master = db.get(Master, master_id)
    if master is None:
        raise HTTPException(404, "Майстра не знайдено")
    return master


@router.post("", response_model=MasterOut, status_code=201)
def create_profile(data: MasterCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    if user.role != "master":
        raise HTTPException(403, "Профіль майстра можуть створити лише майстри")
    if db.scalar(select(Master).where(Master.user_id == user.id)):
        raise HTTPException(409, "Профіль майстра вже існує")
    if db.get(Category, data.category_id) is None:
        raise HTTPException(400, "Невідома категорія")
    master = Master(user_id=user.id, city=data.city.strip(),
                    category_id=data.category_id, bio=data.bio)
    db.add(master)
    db.commit()
    return _to_out(master, None, 0)


@router.get("", response_model=list[MasterOut])
def search_masters(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    city: str | None = None,
    category_id: int | None = None,
    q: str | None = Query(default=None, max_length=100),
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    rs = _rating_subquery()
    stmt = (select(Master, rs.c.avg_rating, rs.c.cnt)
            .join(User, User.id == Master.user_id)
            .outerjoin(rs, rs.c.master_id == Master.id))
    if city:
        stmt = stmt.where(func.lower(Master.city) == city.strip().lower())
    if category_id:
        stmt = stmt.where(Master.category_id == category_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            User.full_name.ilike(like)
            | exists(select(Service.id).where(Service.master_id == Master.id,
                                              Service.name.ilike(like))))
    if min_price is not None or max_price is not None:
        conds = [Service.master_id == Master.id]
        if min_price is not None:
            conds.append(Service.price >= min_price)
        if max_price is not None:
            conds.append(Service.price <= max_price)
        stmt = stmt.where(exists(select(Service.id).where(and_(*conds))))
    if min_rating:
        stmt = stmt.where(func.coalesce(rs.c.avg_rating, 0) >= min_rating)
    stmt = (stmt.order_by(func.coalesce(rs.c.avg_rating, 0).desc(), Master.id)
            .limit(limit).offset(offset))
    return [_to_out(m, avg, cnt) for m, avg, cnt in db.execute(stmt).all()]


@router.post("/me/services", response_model=ServiceOut, status_code=201)
def add_service(data: ServiceCreate, master: Master = Depends(require_master),
                db: Session = Depends(get_db)):
    service = Service(master_id=master.id, name=data.name.strip(),
                      price=data.price, duration_min=data.duration_min)
    db.add(service)
    db.commit()
    return service


@router.delete("/me/services/{service_id}", status_code=204)
def delete_service(service_id: int, master: Master = Depends(require_master),
                   db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if service is None or service.master_id != master.id:
        raise HTTPException(404, "Послугу не знайдено")
    if db.scalar(select(Booking.id).where(Booking.service_id == service_id).limit(1)):
        raise HTTPException(409, "Неможливо видалити послугу, за якою є записи")
    db.delete(service)
    db.commit()


@router.put("/me/schedule", response_model=list[ScheduleItem])
def set_schedule(items: list[ScheduleItem], master: Master = Depends(require_master),
                 db: Session = Depends(get_db)):
    if len({i.weekday for i in items}) != len(items):
        raise HTTPException(400, "Кожен день тижня можна вказати лише один раз")
    db.execute(delete(WorkSchedule).where(WorkSchedule.master_id == master.id))
    for i in items:
        db.add(WorkSchedule(master_id=master.id, weekday=i.weekday,
                            start_time=i.start_time, end_time=i.end_time))
    db.commit()
    return items


@router.get("/{master_id}", response_model=MasterOut)
def get_master(master_id: int, db: Session = Depends(get_db)):
    master = _get_master_or_404(db, master_id)
    row = db.execute(
        select(func.avg(Review.rating), func.count(Review.id))
        .join(Booking, Booking.id == Review.booking_id)
        .where(Booking.master_id == master_id)).one()
    return _to_out(master, row[0], row[1])


@router.get("/{master_id}/services", response_model=list[ServiceOut])
def list_services(master_id: int, db: Session = Depends(get_db)):
    _get_master_or_404(db, master_id)
    return db.scalars(select(Service).where(Service.master_id == master_id)
                      .order_by(Service.id)).all()


@router.get("/{master_id}/schedule", response_model=list[ScheduleItem])
def get_schedule(master_id: int, db: Session = Depends(get_db)):
    _get_master_or_404(db, master_id)
    return db.scalars(select(WorkSchedule).where(WorkSchedule.master_id == master_id)
                      .order_by(WorkSchedule.weekday)).all()


@router.get("/{master_id}/slots", response_model=SlotsOut)
def get_slots(master_id: int, service_id: int, day: date = Query(alias="date"),
              db: Session = Depends(get_db)):
    _get_master_or_404(db, master_id)
    service = db.get(Service, service_id)
    if service is None or service.master_id != master_id:
        raise HTTPException(404, "Послугу не знайдено")
    return SlotsOut(date=day, slots=free_slots(db, master_id, service, day))


@router.get("/{master_id}/reviews", response_model=list[ReviewOut])
def list_reviews(master_id: int, db: Session = Depends(get_db)):
    _get_master_or_404(db, master_id)
    rows = db.execute(
        select(Review, User.full_name)
        .join(Booking, Booking.id == Review.booking_id)
        .join(User, User.id == Booking.client_id)
        .where(Booking.master_id == master_id)
        .order_by(Review.created_at.desc())).all()
    return [ReviewOut(id=r.id, booking_id=r.booking_id, author=name, rating=r.rating,
                      text=r.text, created_at=r.created_at) for r, name in rows]
