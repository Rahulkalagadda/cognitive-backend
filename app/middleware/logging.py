import logging
import time
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.datastructures import MutableHeaders

logger = logging.getLogger("app.api.access")


class LoggingMiddleware:
    """
    Pure ASGI logging middleware.

    Why NOT BaseHTTPMiddleware:
    BaseHTTPMiddleware wraps the response in a new Response object after
    calling `call_next`, which discards headers set by inner middleware
    (e.g. CORSMiddleware's Access-Control-Allow-Origin). This pure ASGI
    implementation intercepts only the 'http.response.start' ASGI event to
    read the status code and then forwards every event unmodified, so all
    headers — including CORS headers — are preserved.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            # Pass through non-HTTP scopes (websocket, lifespan) untouched
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        method = scope.get("method", "")
        path = scope.get("path", "")
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        status_code = 0

        async def send_with_logging(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_logging)
            process_time = (time.time() - start_time) * 1000
            logger.info(
                f"Client: {client_ip} | Request: {method} {path} | "
                f"Response: {status_code} | Duration: {process_time:.2f}ms"
            )
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Client: {client_ip} | Request: {method} {path} | "
                f"Response: Failed with exception | Duration: {process_time:.2f}ms | Error: {e}"
            )
            raise
