
"""Request correlation and structured request logging."""

import logging
import re
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


logger = logging.getLogger("recon_x.api")

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a safe request ID to every HTTP request."""

    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        incoming_id = request.headers.get("X-Request-ID", "")

        request_id = (
            incoming_id
            if REQUEST_ID_PATTERN.fullmatch(incoming_id)
            else str(uuid4())
        )

        request.state.request_id = request_id
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Request processing failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            raise

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "API request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response
