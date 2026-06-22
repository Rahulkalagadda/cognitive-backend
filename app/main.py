import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.middleware.logging import LoggingMiddleware
from app.api.v1.endpoints import auth, patients, sessions, reports, templates, dashboard

# 1. Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)

# 2. Instantiate application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Cognitive Assessment Platform (CAP) FastAPI Backend Service.",
)

# 3. Add middleware
app.add_middleware(LoggingMiddleware)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Standard verification routes
@app.get("/health", tags=["System"])
async def health_check():
    """Verify service is active."""
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/db-test", tags=["System"])
async def db_connectivity_check(db: AsyncSession = Depends(get_db)):
    """Verify database connection can run queries."""
    try:
        result = await db.execute(text("SELECT value FROM system_metadata WHERE key = 'schema_version'"))
        val = result.scalar()
        return {
            "status": "connected",
            "schema_version": val or "unknown",
            "msg": "Database connectivity check passed."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connectivity failed: {e}"
        )


# 5. Include API Routers under /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(patients.router, prefix="/api/v1/patients", tags=["Patients Management"])
app.include_router(sessions.router, prefix="/api/v1/assessment", tags=["Assessment Sessions"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports Management"])
app.include_router(templates.router, prefix="/api/v1/templates", tags=["Cognitive Batteries Templates"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Doctor Dashboard Analytics"])
