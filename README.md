# Ticketing Platform Backend API

A RESTful API for booking tickets for events with concurrency safety, built with FastAPI and PostgreSQL.

## Features

- **Initialize Events**: Create events with a specific number of available tickets
- **Book Tickets**: Book tickets with automatic validation (availability and user limits)
- **Cancel Bookings**: Cancel bookings and return tickets to the available pool
- **Concurrency Safety**: Handles concurrent requests safely using database-level pessimistic locking
- **User Limits**: Enforces maximum of 2 tickets per user per event

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy
- **Containerization**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git (for cloning the repository)

### Running the Application

1. Clone the repository:
```bash
git clone <repository-url>
cd teachmint
```

2. Start the services:
```bash
docker-compose up --build
```

This will:
- Start PostgreSQL database on port 5432
- Start the FastAPI application on port 8000
- Create database tables automatically

3. Access the API:
- API Base URL: `http://localhost:8000`
- Interactive API Documentation: `http://localhost:8000/docs`
- Alternative API Documentation: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/health`

## API Endpoints

### 1. Initialize Event

Create a new event with a specific number of tickets.

**Endpoint**: `POST /events`

**Request Body**:
```json
{
  "name": "Concert 2024",
  "total_tickets": 100
}
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Concert 2024",
  "total_tickets": 100,
  "available_tickets": 100,
  "created_at": "2024-01-15T10:30:00"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/events" \
  -H "Content-Type: application/json" \
  -d '{"name": "Concert 2024", "total_tickets": 100}'
```

### 2. Book Tickets

Book one or two tickets for an event.

**Endpoint**: `POST /events/{event_id}/bookings`

**Path Parameters**:
- `event_id`: UUID of the event

**Request Body**:
```json
{
  "user_id": "user123",
  "ticket_count": 1
}
```

**Response**:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "ticket_count": 1,
  "status": "active",
  "created_at": "2024-01-15T10:35:00",
  "updated_at": "2024-01-15T10:35:00"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/events/550e8400-e29b-41d4-a716-446655440000/bookings" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "ticket_count": 1}'
```

**Error Responses**:
- `400 Bad Request`: Not enough tickets available or user limit exceeded
- `404 Not Found`: Event not found

### 3. Cancel Booking

Cancel a booking and return tickets to the available pool.

**Endpoint**: `DELETE /bookings/{booking_id}`

**Path Parameters**:
- `booking_id`: UUID of the booking

**Response**:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "ticket_count": 1,
  "status": "cancelled",
  "created_at": "2024-01-15T10:35:00",
  "updated_at": "2024-01-15T10:40:00"
}
```

**Example**:
```bash
curl -X DELETE "http://localhost:8000/bookings/660e8400-e29b-41d4-a716-446655440000"
```

**Error Responses**:
- `400 Bad Request`: Booking is already cancelled
- `404 Not Found`: Booking not found

### 4. Get Event Details

**Endpoint**: `GET /events/{event_id}`

**Example**:
```bash
curl "http://localhost:8000/events/550e8400-e29b-41d4-a716-446655440000"
```

### 5. Get Booking Details

**Endpoint**: `GET /bookings/{booking_id}`

**Example**:
```bash
curl "http://localhost:8000/bookings/660e8400-e29b-41d4-a716-446655440000"
```

## Testing Concurrent Bookings

To test concurrent booking scenarios, you can use a script like this:

```bash
# Create an event with 10 tickets
EVENT_ID=$(curl -s -X POST "http://localhost:8000/events" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Event", "total_tickets": 10}' | jq -r '.id')

# Try to book 15 tickets concurrently (should only succeed for 10)
for i in {1..15}; do
  curl -X POST "http://localhost:8000/events/$EVENT_ID/bookings" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"user$i\", \"ticket_count\": 1}" &
done
wait
```

## Architecture

### Concurrency Handling

The system uses PostgreSQL's `SELECT FOR UPDATE` (pessimistic locking) to handle concurrent ticket bookings:

1. When a booking request arrives, the event row is locked
2. Availability and user limits are checked within the same transaction
3. Tickets are decremented atomically
4. The transaction commits, releasing the lock

This ensures that:
- No race conditions occur when multiple users try to book the last tickets
- User limits (max 2 tickets per user per event) are enforced correctly
- Database consistency is maintained

See [decisions.md](decisions.md) for detailed architectural decisions.

## Development

### Local Development (without Docker)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up PostgreSQL database:
```bash
createdb ticketing_db
```

3. Set environment variable:
```bash
export DATABASE_URL=postgresql://your_user:your_password@localhost:5432/ticketing_db
```

4. Run the application:
```bash
uvicorn app.main:app --reload
```

### Project Structure

```
/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization
│   ├── database.py          # Database connection & session management
│   ├── models.py            # SQLAlchemy models (Event, Booking)
│   ├── schemas.py           # Pydantic schemas for request/response
│   ├── routers/
│   │   ├── events.py        # Event endpoints
│   │   └── bookings.py     # Booking endpoints
│   └── services/
│       └── booking_service.py  # Business logic for bookings
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── decisions.md
└── README.md
```

## Database Schema

### Events Table
- `id` (UUID, primary key)
- `name` (string)
- `total_tickets` (integer)
- `available_tickets` (integer)
- `created_at` (timestamp)

### Bookings Table
- `id` (UUID, primary key)
- `event_id` (UUID, foreign key)
- `user_id` (string)
- `ticket_count` (integer, 1-2)
- `status` (enum: 'active', 'cancelled')
- `created_at` (timestamp)
- `updated_at` (timestamp)

## License

This project is provided as-is for demonstration purposes.

