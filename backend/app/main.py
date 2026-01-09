import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.endpoints import router
from app.storage import ensure_storage_dir

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OpenRedact Clinical",
    description="Medical document anonymization for German clinical documents",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize storage on startup"""
    ensure_storage_dir()
    logger.info("OpenRedact Clinical API started")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "OpenRedact Clinical API",
        "version": "2.0.0",
        "docs": "/docs"
    }

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy"}
