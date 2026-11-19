
"""Centralised API exception handlers."""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


logger = logging.getLogger("recon_x.api")


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Handle expected HTTP errors."""

    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": (
                    exc.detail
                    if isinstance(exc.detail, str)
                    else "The request could not be completed."
                ),
            },
            "request_id": get_request_id(request),
        },
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return safe validation error details."""

    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": errors,
            },
            "request_id": get_request_id(request),
        },
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Log unexpected errors and return a generic response."""

    logger.exception(
        "Unhandled API exception",
        extra={"request_id": get_request_id(request)},
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
            },
            "request_id": get_request_id(request),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register application-wide exception handlers."""

    app.add_exception_handler(
        HTTPException,
        http_exception_handler,
    )
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )
    app.add_exception_handler(
        Exception,
        unhandled_exception_handler,
    )
