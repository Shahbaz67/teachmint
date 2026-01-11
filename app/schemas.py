from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional


class EventCreate(BaseModel):
    name: str = Field(..., min_length=1)
    total_tickets: int = Field(..., gt=0)

    @field_validator('total_tickets')
    @classmethod
    def validate_tickets(cls, v):
        if v <= 0:
            raise ValueError('total_tickets must be greater than 0')
        return v


class EventResponse(BaseModel):
    id: UUID
    name: str
    total_tickets: int
    available_tickets: int
    created_at: datetime

    class Config:
        from_attributes = True


class BookingCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    ticket_count: int = Field(..., ge=1, le=2)

    @field_validator('ticket_count')
    @classmethod
    def validate_ticket_count(cls, v):
        if v < 1 or v > 2:
            raise ValueError('ticket_count must be between 1 and 2')
        return v


class BookingResponse(BaseModel):
    id: UUID
    event_id: UUID
    user_id: str
    ticket_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    detail: str

