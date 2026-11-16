import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import Category
from .routers import auth, bookings, masters

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("beauty")

DEFAULT_CATEGORIES = ["Манікюр і педикюр", "Перукарські послуги", "Брови та вії",
                      "Макіяж", "Косметологія", "Масаж"]


def seed_categories(db) -> None:
    existing = set(db.scalars(select(Category.name)).all())
    for name in DEFAULT_CATEGORIES:
        if name not in existing:
            db.add(Category(name=name))
    db.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_categories(db)
    yield


app = FastAPI(title="Beauty Booking API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])
app.include_router(auth.router)
app.include_router(masters.router)
app.include_router(bookings.router)


@app.exception_handler(Exception)
async def unhandled_error(_request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Внутрішня помилка сервера"})


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}
