from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from .logging import logger

class LabelLensException(Exception):
    """Base exception for all domain-specific LabelLens errors."""
    def __init__(self, message: str, status_code: int = 400, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class ImageQualityException(LabelLensException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, details=details)

class OCRProcessingException(LabelLensException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details=details)

class RuleEngineException(LabelLensException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, details=details)

class ResourceNotFoundException(LabelLensException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} with identifier '{identifier}' was not found.", status_code=status.HTTP_404_NOT_FOUND)

async def label_lens_exception_handler(request: Request, exc: LabelLensException):
    logger.warning(f"LabelLensException on {request.method} {request.url.path}: {exc.message} (details: {exc.details})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_type": exc.__class__.__name__,
            "message": exc.message,
            "detail": exc.message,
            "details": exc.details,
            "path": request.url.path
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    msg = exc.detail if isinstance(exc.detail, str) else "HTTP Exception"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_type": "HTTPException",
            "detail": exc.detail,
            "message": msg,
            "path": request.url.path
        },
        headers=getattr(exc, "headers", None)
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error_type": "ValidationError",
            "detail": exc.errors(),
            "message": "Validation error occurred.",
            "path": request.url.path
        }
    )

async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, StarletteHTTPException):
        return await http_exception_handler(request, exc)
    if isinstance(exc, RequestValidationError):
        return await validation_exception_handler(request, exc)
    logger.exception(f"Unhandled Exception on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_type": "InternalServerError",
            "message": "An unexpected error occurred during request processing.",
            "detail": "An unexpected error occurred during request processing.",
            "path": request.url.path
        }
    )

