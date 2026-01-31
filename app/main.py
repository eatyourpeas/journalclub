import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import papers

app = FastAPI(
    title="JournalClub",
    description="AI-powered academic paper reader and podcast generator",
    version="0.1.0",
)

allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5500,http://127.0.0.1:5500",  # Default for local dev
).split(",")

# CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(papers.router, prefix="/api/papers", tags=["papers"])


@app.get("/")
async def root():
    return {"message": "Welcome to JournalClub API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "medical-journal-summariser"}


@app.get("/api/swagger-ui")
async def swagger_ui():
    return {"message": "Swagger UI endpoint"}
