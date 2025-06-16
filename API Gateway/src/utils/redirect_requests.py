from fastapi import Request
from starlette.datastructures import MutableHeaders, QueryParams
from starlette_context import context


def generate_url_for_redirect(endpoint: str, query_params: QueryParams = None) -> str:
    url = f"{context.get('url')}{endpoint}"

    if query_params:
        url += f"?{query_params}"

    return url


def generate_headers(request: Request) -> MutableHeaders:
    new_headers = request.headers.mutablecopy()

    if context.get("user"):
        new_headers["API-User"] = context.get("user")

    new_headers["X-Request-ID"] = context.get("X-Request-ID")
    new_headers["X-Forwarded-Proto"] = new_headers.get("X-Forwarded-Proto", "http")
    new_headers["X-Forwarded-Host"] = new_headers.get("X-Forwarded-Host", new_headers.get("Host"))
    new_headers["X-Forwarded-For"] = f"{request.headers.get('X-Forwarded-For', '')}, {request.client.host}".strip(", ")

    headers_to_delete = [
        "accept-encoding",
        "connection",
        "content-length",
        "host",
    ]

    for header in headers_to_delete:
        del new_headers[header]

    return new_headers
