import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.api.access")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request basic properties
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        try:
            response = await call_next(request)
            
            # Calculate execution duration
            process_time = (time.time() - start_time) * 1000
            status_code = response.status_code
            
            # Standard access log formatting
            logger.info(
                f"Client: {client_ip} | Request: {method} {path} | "
                f"Response: {status_code} | Duration: {process_time:.2f}ms"
            )
            return response
            
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Client: {client_ip} | Request: {method} {path} | "
                f"Response: Failed with exception | Duration: {process_time:.2f}ms | Error: {e}"
            )
            raise
