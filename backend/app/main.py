from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="OpenRedact Clinical",
    description="Medical document anonymization for German clinical documents",
    version="2.0.0"
)

# CORS configuration for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "OpenRedact Clinical API", "version": "2.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
