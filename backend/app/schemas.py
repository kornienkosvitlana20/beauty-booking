from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    role: Literal["client", "master"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class MasterCreate(BaseModel):
    city: str = Field(min_length=1, max_length=100)
    category_id: int
    bio: str = Field(default="", max_length=2000)


class MasterOut(BaseModel):
    id: int
    full_name: str
    city: str
    category_id: int
    category_name: str
    bio: str
    rating: float | None
    reviews_count: int


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: int = Field(gt=0, le=100_000)
    duration_min: int = Field(ge=5, le=480)


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    master_id: int
    name: str
    price: int
    duration_min: int


class ScheduleItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def _check_order(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time має бути раніше за end_time")
        return self


class SlotsOut(BaseModel):
    date: date
    slots: list[datetime]


class BookingCreate(BaseModel):
    service_id: int
    start_at: datetime

    @field_validator("start_at")
    @classmethod
    def _drop_tz(cls, value: datetime) -> datetime:
        # Усі часи — локальні, без часового поясу.
        return value.replace(tzinfo=None)


class RescheduleIn(BaseModel):
    start_at: datetime

    @field_validator("start_at")
    @classmethod
    def _drop_tz(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=None)


class BookingOut(BaseModel):
    id: int
    client_id: int
    master_id: int
    service_id: int
    service_name: str
    start_at: datetime
    end_at: datetime
    status: str


class ReviewCreate(BaseModel):
    booking_id: int
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=1000)


class ReviewOut(BaseModel):
    id: int
    booking_id: int
    author: str
    rating: int
    text: str
    created_at: datetime
