import logging
import time
import datetime
import traceback
from typing import Set
from logging.handlers import SocketHandler
from pythonjsonlogger import jsonlogger
from fastapi.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, PlainTextResponse
from starlette_context import context


# logger_format = '[%(levelname)s %(message)s]'
# logger = logging.getLogger("FluentBit")
# logger.setLevel(logging.DEBUG)
#
# formatter = jsonlogger.JsonFormatter(
#     logger_format,
#     rename_fields={"levelname": "level"},
#     static_fields={
#         "app": "gateway",
#         "namespace": "namespace needs to be set",
#     }
# )
#
#
# class FluentBitHandler(SocketHandler):
#     def emit(self, record):
#         try:
#             self.send((self.format(record)).encode())
#         except Exception:
#             self.handleError(record)
#
#
# socket_handler = FluentBitHandler(
#     "fluentbit.logging-namespace.svc.cluster.local", 5170
# )
#
# socket_handler.setFormatter(formatter)
# logger.addHandler(socket_handler)
# logger = logging.getLogger()
logger = logging.getLogger("uvicorn")


async def error_response(request: Request, exc: Exception) -> Response:
    logger.error(
        {
            "message": "Internal Server Error",
            "exception": "".join(traceback.format_exception(
                type(exc), value=exc, tb=exc.__traceback__
            )),
            "X-Request-ID": context.get("X-Request-ID")
        }
    )

    return PlainTextResponse("Internal Server Error", status_code=500)


class LoggingMiddleware(BaseHTTPMiddleware):

    def format_log(self, request: Request, response: Response):
        event = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "X-Request-ID": context.get("X-Request-ID"),
            "message": "API request",
            "user": {
                "username": context.get("user"),
                "group": context.get("group"),
            },
            "request": {
                "method": request.method,
                "path": request.url.path,
            },
            "response": {
                "status_code": response.status_code,
                "size_bytes": response.headers.get("Content-Length"),
                "response_time_ms": (time.time() - context.get("gateway_start_time")) * 1000,
                "backend_api_response_time_ms": (context.get("backend_end_time") - context.get("backend_start_time")) * 1000,
            },
            "client": {
                "ip": request.headers.get("X-Forwarded-For", request.client.host).split(",")[0],
                "X-Forwarded-For": f"{request.headers.get('X-Forwarded-For', '')}, {request.client.host}".strip(", "),
                "X-Forwarded-Host": request.headers.get("X-Forwarded-Host", request.headers.get("Host")),
                "user-agent": request.headers.get("User-Agent", "unknown"),
            }
        }
        if request.path_params.get("api_name"):
            event["request"]["api_name"] = request.path_params.get("api_name")

        if request.path_params.get("version"):
            event["request"]["version"] = request.path_params.get("version")

        if request.headers.get("Referer"):
            event["client"]["Referer"] = request.headers.get("Referer")

        if len(request.query_params) > 0:
            event["request"]["query_params"] = f"?{request.url.query}"

        return event

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        context["X-Request-ID"] = request.headers.get("X-Request-ID", context.get("X-Request-ID"))

        response = await call_next(request)

        event = self.format_log(request, response)
        logger.log(
            level=logging.INFO if response.status_code < 400 else logging.ERROR,
            msg=event
        )

        return response
