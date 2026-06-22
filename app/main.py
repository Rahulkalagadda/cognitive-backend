import logging
from contextlib import asynccontextmanager
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

# ---------------------------------------------------------------------------
# 3. Add middleware
#
# Starlette/FastAPI middleware is a stack: the LAST middleware added becomes
# the OUTERMOST wrapper (first to receive the request, last to touch the
# response).
#
# Required execution order (outermost → innermost):
#   LoggingMiddleware → CORSMiddleware → Route handler
#
# Therefore CORSMiddleware must be added FIRST so that LoggingMiddleware
# wraps around it and CORSMiddleware can set CORS headers on the response
# before LoggingMiddleware forwards it to the client.
# ---------------------------------------------------------------------------

# Added first → will execute SECOND (inner)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Added second → will execute FIRST (outer) — pure ASGI, does not buffer
# or re-wrap responses, so CORS headers set by CORSMiddleware are preserved.
app.add_middleware(LoggingMiddleware)

# Startup diagnostic — printed once when the process starts on Railway.
print("=" * 60)
print(f"BACKEND_CORS_ORIGINS = {settings.BACKEND_CORS_ORIGINS}")
print("=" * 60)


# 4. Standard verification routes
@app.get("/health", tags=["System"])
async def health_check():
    """Verify service is active."""
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/cors-test", tags=["System"])
async def cors_test():
    """
    Temporary CORS diagnostic endpoint.
    Call from the browser console:
      fetch('https://cognitive-backend-production-503e.up.railway.app/cors-test',
            {credentials: 'include'})
        .then(r => r.json()).then(console.log)
    The response must include Access-Control-Allow-Origin matching the
    Vercel origin, and Access-Control-Allow-Credentials: true.
    """
    return {"status": "ok", "cors_origins": settings.BACKEND_CORS_ORIGINS}


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
