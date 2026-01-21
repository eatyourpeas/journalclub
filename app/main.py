from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import papers

app = FastAPI(
    title="JournalClub",
    description="AI-powered academic paper reader and podcast generator",
    version="0.1.0"
)

# CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
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
    return {"status": "healthy"}