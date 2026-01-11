from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import events, bookings

app = FastAPI(
    title="Ticketing Platform API",
    description="RESTful API for booking tickets for events with concurrency safety",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(events.router)
app.include_router(bookings.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    init_db()


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Ticketing Platform API",
        "docs": "/docs",
        "health": "/health"
    }

