import time
import traceback
import datetime
import re
import jwt
from typing import Annotated, Dict, Union, List
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette_context import context
from .constants import (
    TOKEN_SECRET_KEY, ALGORITHM, ENDPOINT_RULES, AUTHENTICATE_FLAG, NO_AUTHENTICATION_FLAG, DENY_ALL_ACCESS_FLAG
)
from .splunk_logging import logger
from .database_and_client import get_user_groups_from_database


BEARER_TOKEN = HTTPBearer(
    auto_error=False,
    description=(
        "This authentication scheme requires a **Bearer Token** for authorization.\n\n"
        "Clients must include a valid **JWT** token in the `Authorization` header as `Bearer <token>`.\n\n"
        "This token will be automatically added to the headers of all of the endpoints.\n\n"
        "For endpoints that do not require authentication, the presence of the token will be ignored."
    )
)


def create_jwt_token(username: str) -> str:
    """
    Generates a JWT token with an 8-hour expiration.

    :param username: the specified user

    :return: a JWT token with an 8-hour expiration and the username as the subject
    """
    token = jwt.encode(
        {"sub": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)},
        TOKEN_SECRET_KEY,
        algorithm=ALGORITHM
    )
    logger.info(
        {
            "message": f"Created token for {username}",
            "X-Request-ID": context.get("X-Request-ID")
        }
    )
    return token


def decode_and_check_jwt_token(token: str) -> str:
    """

    checks automatically when decoding if the signature has expired !!
    """
    try:
        payload = jwt.decode(token, TOKEN_SECRET_KEY, ALGORITHM)
        return payload["sub"]
    except jwt.PyJWTError as exc:
        logger.error(
            {
                "message": "Error when decoding JWT token",
                "exception": "".join(traceback.format_exception(
                    type(exc), value=exc, tb=exc.__traceback__
                )),
                "X-Request-ID": context.get("X-Request-ID")
            }
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


def get_endpoint_authorization_config(api_name: str, version: str, endpoint: str) -> Dict[str, Union[str, List[str]]]:
    if api_name not in ENDPOINT_RULES or version not in ENDPOINT_RULES[api_name]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    for endpoint_rule in ENDPOINT_RULES[api_name][version]:
        ((pattern, authorization_config),) = endpoint_rule.items()
        if re.match(pattern, endpoint):
            return authorization_config

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


async def authorize_redirects(
        request: Request,
        api_name: str,
        version: str,
        endpoint: str,
        token: Annotated[HTTPAuthorizationCredentials, Depends(BEARER_TOKEN)]
) -> None:
    context["api_name"] = api_name
    context["version"] = version
    endpoint = f"/{endpoint}"
    authorization_config = get_endpoint_authorization_config(api_name, version, endpoint)
    context["url"] = authorization_config["url"]

    if request.method not in authorization_config:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

    authorization_groups = authorization_config.get(request.method)

    if DENY_ALL_ACCESS_FLAG in authorization_groups:
        context["group"] = DENY_ALL_ACCESS_FLAG
        logger.info(
            {
                "message": f"{DENY_ALL_ACCESS_FLAG} flag matched",
                "X-Request-ID": context.get("X-Request-ID")
            }
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    group_names_with_no_flags = list(set(authorization_groups).difference({AUTHENTICATE_FLAG, NO_AUTHENTICATION_FLAG}))
    if len(group_names_with_no_flags) > 0:
        context["user"] = decode_and_check_jwt_token(token.credentials)
        matched_groups = await get_user_groups_from_database(context["user"], group_names_with_no_flags)

        if len(matched_groups) > 0:
            context["group"] = matched_groups[0]["group_name"]
            logger.info(
                {
                    "message": f"{context['group']} group matched",
                    "X-Request-ID": context.get("X-Request-ID")
                }
            )
        else:
            logger.info(
                {
                    "message": f"No groups matched",
                    "X-Request-ID": context.get("X-Request-ID")
                }
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    elif AUTHENTICATE_FLAG in authorization_groups:
        context["user"] = decode_and_check_jwt_token(token.credentials)
        context["group"] = AUTHENTICATE_FLAG
        logger.info(
            {
                "message": f"{AUTHENTICATE_FLAG} flag matched",
                "X-Request-ID": context.get("X-Request-ID")
            }
        )
    elif NO_AUTHENTICATION_FLAG in authorization_groups:
        context["group"] = NO_AUTHENTICATION_FLAG
        logger.info(
            {
                "message": f"{NO_AUTHENTICATION_FLAG} flag matched",
                "X-Request-ID": context.get("X-Request-ID")
            }
        )
