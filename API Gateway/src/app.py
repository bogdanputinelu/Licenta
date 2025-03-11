from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import Response, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware import Middleware
from starlette_context.middleware import RawContextMiddleware
from starlette_context.plugins import RequestIdPlugin
from starlette_context import context
from starlette.templating import Jinja2Templates
from src.utils.splunk_logging import LoggingMiddleware, error_response
from src.utils.authorization import create_jwt_token, authorize_redirects
from src.utils.database_and_client import lifespan, get_password_from_database, get_client_session
from src.utils.constants import PASSWORD_CONTEXT
from src.utils.redirect_requests import generate_url_for_redirect, generate_headers


middlewares = [
    Middleware(RawContextMiddleware, plugins=(RequestIdPlugin(),)),
    # Middleware(LoggingMiddleware)
]
exception_handlers = {500: error_response}
app = FastAPI(
    title="API Gateway",
    # docs_url=None,
    # redoc_url=None,
    # openapi_url=None,
    middleware=middlewares,
    lifespan=lifespan,
    exception_handlers=exception_handlers,
)


@app.post("/login")
async def login(credentials: OAuth2PasswordRequestForm = Depends()):
    password = await get_password_from_database(credentials.username)

    if not password or not PASSWORD_CONTEXT.verify(credentials.password, password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"token": create_jwt_token(credentials.username), "token_type": "bearer"}
    )


@app.get("/{api_name}/api/{version}/{endpoint:path}", dependencies=[Depends(authorize_redirects)])
async def redirect_requests(request: Request, api_name: str, version: str, endpoint: str):
    async with (await get_client_session()).request(
            method=request.method,
            url=generate_url_for_redirect(endpoint, request.query_params),
            headers=generate_headers(request),
            data=await request.body(),
    ) as response:
        # return Response(
        #     content=await response.read(),
        #     status_code=response.status,
        #     headers=response.headers,
        #     media_type=response.headers.get("content-type"),
        # )
        return {}


