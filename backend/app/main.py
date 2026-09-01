from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import (
    LabelLensException,
    label_lens_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler
)
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from app.database.session import init_db
from app.services.rules.rule_loader import RuleLoader
from app.api.v1.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup:
    logger.info("Initializing LabelLens Backend Services...")
    try:
        init_db()
        RuleLoader.load_all_rules()
        logger.info("Application startup completed successfully.")
    except Exception as e:
        logger.error(f"Startup initialization warning: {e}")
    yield
    # Shutdown:
    logger.info("LabelLens Backend shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-Style AI/Computer-Vision Legal Metrology Label Compliance Engine. "
        "SIH 2026 Problem Statement: AI/Computer-Vision Legal Metrology Label Compliance."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(LabelLensException, label_lens_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Mount API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Hosted deployments serve the compiled React app from this same process. This
# keeps API requests and secure session cookies same-origin.
FRONTEND_DIR = settings.BASE_DIR / "static"
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="frontend-assets")

@app.get("/")
def root():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "api_docs": "/api/docs",
        "health_check": f"{settings.API_V1_STR}/health"
    }


@app.get("/{full_path:path}", include_in_schema=False)
def frontend_route(full_path: str):
    """Serve React routes while leaving API routes to their registered router."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"detail": "Frontend build is not available in this environment"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
