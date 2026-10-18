"""Pydantic models: request validation and response shapes."""
from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

PHONE_PATTERN = r"^\+?[0-9][0-9\s\-]{6,14}$"


def _dob_not_future(v: Optional[date]) -> Optional[date]:
    if v is not None and v > date.today():
        raise ValueError("date_of_birth cannot be in the future")
    return v


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, pattern=PHONE_PATTERN)
    course: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=255)
    enrollment_date: Optional[date] = None

    _check_dob = field_validator("date_of_birth")(_dob_not_future)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be blank")
        return v

    @model_validator(mode="after")
    def need_contact(self):
        if not self.email and not self.phone:
            raise ValueError("provide at least one contact: email or phone")
        return self


class StudentUpdate(BaseModel):
    """PATCH body: every field optional."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, pattern=PHONE_PATTERN)
    course: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=255)
    enrollment_date: Optional[date] = None


class Student(StudentCreate):
    id: int


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AskResponse(BaseModel):
    answer: str
    records_used: list[dict]
    matched_count: int
    total_students: int
