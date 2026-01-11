from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models import Event
from app.schemas import EventCreate, EventResponse, BookingCreate, BookingResponse
from app.services.booking_service import BookingService

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    """
    Initialize a new event with a specific number of available tickets.
    """
    db_event = Event(
        name=event.name,
        total_tickets=event.total_tickets,
        available_tickets=event.total_tickets
    )
    
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    return db_event


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: UUID, db: Session = Depends(get_db)):
    """
    Get event details by ID.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    return event


@router.post(
    "/{event_id}/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED
)
def book_tickets(
    event_id: UUID,
    booking: BookingCreate,
    db: Session = Depends(get_db)
):
    """
    Book ticket(s) for an event.
    
    Validates:
    - Ticket availability
    - User limit (max 2 tickets per user per event)
    
    Uses pessimistic locking to handle concurrent requests safely.
    """
    return BookingService.book_tickets(
        db=db,
        event_id=event_id,
        user_id=booking.user_id,
        ticket_count=booking.ticket_count
    )

