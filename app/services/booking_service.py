from sqlalchemy.orm import Session
from uuid import UUID
from fastapi import HTTPException, status

from app.models import Event, Booking, BookingStatus


class BookingService:
    """Service layer for handling booking business logic with concurrency safety"""

    @staticmethod
    def book_tickets(
        db: Session, 
        event_id: UUID, 
        user_id: str, 
        ticket_count: int
    ) -> Booking:
        """
        Book tickets for an event with concurrency safety.
        
        Uses SELECT FOR UPDATE to lock the event row, preventing race conditions
        when multiple requests try to book the last available tickets.
        """
        # Start a transaction and lock the event row
        # This ensures no other transaction can modify this event until we commit
        event = db.query(Event).with_for_update().filter(Event.id == event_id).first()
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        # Check ticket availability
        if event.available_tickets < ticket_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough tickets available. Available: {event.available_tickets}, Requested: {ticket_count}"
            )
        
        # Check user's existing bookings for this event
        # This query is within the same transaction, so it sees consistent data
        existing_bookings = db.query(Booking).filter(
            Booking.event_id == event_id,
            Booking.user_id == user_id,
            Booking.status == BookingStatus.ACTIVE
        ).all()
        
        total_user_tickets = sum(booking.ticket_count for booking in existing_bookings)
        
        if total_user_tickets + ticket_count > 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User limit exceeded. User already has {total_user_tickets} tickets. Maximum allowed: 2"
            )
        
        # Create booking
        booking = Booking(
            event_id=event_id,
            user_id=user_id,
            ticket_count=ticket_count,
            status=BookingStatus.ACTIVE
        )
        
        # Atomically update available tickets
        event.available_tickets -= ticket_count
        
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        return booking

    @staticmethod
    def cancel_booking(db: Session, booking_id: UUID) -> Booking:
        """
        Cancel a booking and return tickets to the available pool.
        
        Uses SELECT FOR UPDATE to lock both booking and event rows atomically.
        """
        # Lock the booking row
        booking = db.query(Booking).with_for_update().filter(Booking.id == booking_id).first()
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        if booking.status == BookingStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking is already cancelled"
            )
        
        # Lock the event row to update available tickets atomically
        event = db.query(Event).with_for_update().filter(Event.id == booking.event_id).first()
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Event associated with booking not found"
            )
        
        # Return tickets to available pool
        event.available_tickets += booking.ticket_count
        
        # Update booking status
        booking.status = BookingStatus.CANCELLED
        
        db.commit()
        db.refresh(booking)
        
        return booking

