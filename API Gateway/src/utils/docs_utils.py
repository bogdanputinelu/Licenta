import re
import traceback
import asyncio
from typing import Dict, Any, Optional, Union, Tuple, List, Set
import aiohttp
from starlette_context import context
from .splunk_logging import logger
from .constants import (
    DOCS_API_GATEWAY_URL,
    INTERNAL_DOCS,
    EXTERNAL_DOCS,
    ENDPOINT_RULES
)


def build_initial_openapi_schema():
    return {
        "openapi": "3.1.0",
        "info": {"title": "API Gateway", "version": "0.1.0"},
        "paths": {},
        "components": {
            "schemas": {}, "responses": {}, "parameters": {}, "headers": {}, "securitySchemes": {},
            "links": {}, "callbacks": {}, "pathItems": {}, "requestBodies": {}, "examples": {}
        },
        "servers": [{"url": DOCS_API_GATEWAY_URL, "description": "api-gateway"}],
    }


def build_http_bearer_openapi_security_schema() -> Dict[str, Any]:
    return {
        "HTTPBearer": {
            "type": "http",
            "description": "Bearer token for the API Gateway, needed for authorization",
            "scheme": "bearer"
        }
    }


def build_login_endpoint_openapi_component_schema() -> Dict[str, Any]:
    return {
        "properties": {
            "grant_type": {
                "anyOf": [
                    {
                        "type": "string",
                        "pattern": "password"
                    },
                    {
                        "type": "null"
                    }
                ],
                "title": "Grant Type"
            },
            "username": {
                "type": "string",
                "title": "Username"
            },
            "password": {
                "type": "string",
                "title": "Password",
                "format": "password"
            },
            "scope": {
                "type": "string",
                "title": "Scope",
                "default": ""
            },
            "client_id": {
                "anyOf": [
                    {
                        "type": "string"
                    },
                    {
                        "type": "null"
                    }
                    ],
                "title": "Client Id"
            },
            "client_secret": {
                "anyOf": [
                    {
                        "type": "string"
                    },
                    {
                        "type": "null"
                    }
                ],
                "title": "Client Secret"
            }
        },
        "type": "object",
        "required": [
            "username",
            "password"
        ],
        "title": "Body_login_login_post"
    }


def build_login_endpoint_openapi_path() -> Dict[str, Any]:
    return {
        "/login": {
            "post": {
                "tags": [
                    "NETENG-INTERNAL|api-gateway"
                ],
                "summary": "API Gateway Login",
                "description": "API Gateway Login",
                "operationId": "login_login_post",
                "requestBody": {
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "$ref": "#/components/schemas/Body_login_login_post"
                            }
                        }
                    },
                    "required": True
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {}
                            }
                        }
                    },
                    "422": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError"
                                }
                            }
                        }
                    }
                }
            }
        }
    }


def build_openapi_http_validation_error_component_schema() -> Dict[str, Any]:
    return {
        "properties": {
            "detail": {
                "items": {
                    "$ref": "#/components/schemas/ValidationError"
                },
                "type": "array",
                "title": "Detail"
            }
        },
        "type": "object",
        "title": "HTTPValidationError"
    }


def build_openapi_validation_error_component_schema() -> Dict[str, Any]:
    return {
        "properties": {
            "loc": {
                "items": {
                    "anyOf": [
                        {
                            "type": "string"
                        },
                        {
                            "type": "integer"
                        }
                    ]
                },
                "type": "array",
                "title": "Location"
                },
            "msg": {
                "type": "string",
                "title": "Message"
            },
            "type": {
                "type": "string",
                "title": "Error Type"
            }
        },
        "type": "object",
        "required": [
            "loc",
            "msg",
            "type"
        ],
        "title": "ValidationError"
    }

def generate_components_for_openapi_schema() -> Dict[str, Dict]:
    return {
        "schemas": {}, "responses": {}, "parameters": {}, "headers": {}, "securitySchemes": {},
        "links": {}, "callbacks": {}, "pathItems": {}, "requestBodies": {}, "examples": {}
    }


def find_modifications_for_components(
        url_openapi_schema: Dict[str, Any],
        openapi_schema: Dict[str, Any],
        service_name: str,
        version: str
) -> Dict[str, str]:
    modifications = {}
    components = url_openapi_schema["components"]

    for component_property in components:
        for component_name in components[component_property]:
            if openapi_schema["components"][component_property].get(component_name):
                modifications[component_name] = f"{component_name}-{service_name}-{version}"

    return modifications


def replace_components_with_modifications(
        openapi_schema: Dict[str, Any], modifications: Dict[str, str]
) -> None:
    if isinstance(openapi_schema, dict):
        if "$ref" in openapi_schema:
            components = openapi_schema["$ref"].split("/")
            if components[-1] in modifications:
                components[-1] = modifications[components[-1]]
                openapi_schema["$ref"] = "/".join(components)
        else:
            for component in openapi_schema:
                replace_components_with_modifications(openapi_schema[component], modifications)


def replace_names_of_components_with_modifications(
        openapi_schema: Dict[str, Any], modifications: Dict[str, str]
) -> None:
    new_components = generate_components_for_openapi_schema()

    for comp_prop in openapi_schema["components"]:
        for component_name in openapi_schema["components"][comp_prop]:
            if component_name in modifications:
                new_components[comp_prop][modifications[component_name]] = \
                    openapi_schema["components"][comp_prop][component_name]
            else:
                new_components[comp_prop][component_name] = \
                    openapi_schema["components"][comp_prop][component_name]

    openapi_schema["components"] = new_components


def find_openapi_components_to_keep(
        openapi_schema: Dict[str, Any],
        schema_to_search: Dict[str, Any],
        openapi_components_to_keep: Set[str]
) -> None:
    if isinstance(schema_to_search, dict):
        if "$ref" in schema_to_search:
            openapi_components_to_keep.add(schema_to_search["$ref"])

            component_openapi_specification = openapi_schema
            component_location = schema_to_search["$ref"].split("/")[1:]

            for key in component_location:
                component_openapi_specification = component_openapi_specification[key]

            find_openapi_components_to_keep(openapi_schema, component_openapi_specification, openapi_components_to_keep)
        else:
            for component in schema_to_search:
                find_openapi_components_to_keep(openapi_schema, schema_to_search[component], openapi_components_to_keep)


def remove_unused_components(
        openapi_schema: Dict[str, Any],
        openapi_components_to_keep: Set[str]
) -> None:
    filtered_components = {
        "components": generate_components_for_openapi_schema()
    }

    for component_location in openapi_components_to_keep:
        component_definition, component_name = component_location.split("/")[2:]
        if component_name in openapi_schema["components"].get(component_definition, {}):
            filtered_components["components"][component_definition][component_name] = (
                openapi_schema)["components"][component_definition][component_name]

    openapi_schema["components"] = filtered_components["components"]


def solve_name_collisions_for_components_in_openapi_schema(
        url_openapi_schema: Dict[str, Any],
        openapi_schema: Dict[str, Any],
        service_name: str,
        version: str
) -> None:
    openapi_components_to_keep = set()
    find_openapi_components_to_keep(url_openapi_schema, url_openapi_schema["paths"], openapi_components_to_keep)
    remove_unused_components(url_openapi_schema, openapi_components_to_keep)

    modifications = find_modifications_for_components(
        url_openapi_schema, openapi_schema, service_name, version
    )

    if len(modifications) != 0:
        replace_components_with_modifications(url_openapi_schema, modifications)
        replace_names_of_components_with_modifications(url_openapi_schema, modifications)


def get_http_methods_for_endpoint(endpoint: str, api_name: str, version: str) -> Set[str]:
    for endpoint_config in ENDPOINT_RULES.get(api_name, {}).get(version, []):
        (template, config), = endpoint_config.items()
        if re.match(template, endpoint):
            return {method for method in config if method not in {"url"}}

    return set()


def populate_external_openapi_schema_with_auth(openapi_schema: Dict[str, Any]) -> None:
    openapi_schema["components"]["securitySchemes"] = build_http_bearer_openapi_security_schema()
    openapi_schema["components"]["schemas"]["Body_login_login_post"] = build_login_endpoint_openapi_component_schema()
    openapi_schema["paths"].update(build_login_endpoint_openapi_path())
    openapi_schema["components"]["schemas"][
        "HTTPValidationError"] = build_openapi_http_validation_error_component_schema()
    openapi_schema["components"]["schemas"]["ValidationError"] = build_openapi_validation_error_component_schema()


def obscure_password_field_in_internal_docs(openapi_schema: Dict[str, Any]) -> None:
    openapi_schema["components"]["schemas"]["Body_login_login_post"]["properties"]["password"]["format"] = "password"


def update_openapi_schema_with_url_openapi_schema(
        openapi_schema: Dict[str, Any],
        url_openapi_schema: Dict[str, Any]
) -> None:
    openapi_schema["paths"].update(url_openapi_schema["paths"])

    if "components" in url_openapi_schema:
        for component_property in url_openapi_schema["components"]:
            openapi_schema["components"][component_property].update(
                url_openapi_schema["components"][component_property]
            )


async def get_schema_from_service(
        session: aiohttp.ClientSession, service_details: Dict[str, str], service_name: str, version: str, url: str
) -> Union[Tuple[str, str, str, Dict, str], Tuple[str, str, str]]:
    api_name = service_details["api_name"]
    trim = service_details["trim"]
    headers = {
        "request-id": context.get("request_id")
    }

    try:
        async with session.get(url, headers=headers, timeout=15) as response:
            if response.status != 200:
                logger.error(
                    {
                        "message": "Failed to get service openapi schema",
                        "service_called": service_name,
                        "request_id": context.get("request_id"),
                        "status_code": response.status,
                        "version": version,
                        "api_name": api_name,
                    }
                )
                return api_name, service_name, version

            try:
                service_openapi_schema = await response.json()
            except Exception:
                logger.error(
                    {
                        "message": "Failed to decode service openapi schema",
                        "service_called": service_name,
                        "request_id": context.get("request_id"),
                        "status_code": response.status,
                        "version": version,
                        "api_name": api_name,
                    }
                )
                return api_name, service_name, version

            logger.info(
                {
                    "message": "Successfully fetched the OpenAPI schema from the service",
                    "service_called": service_name,
                    "request_id": context.get("request_id"),
                    "version": version,
                    "api_name": api_name,
                }
            )
            return api_name, service_name, version, service_openapi_schema, trim
    except Exception as exc:

        logger.error(
            {
                "message": "Failed when making a request to the service for the OpenAPI schema",
                "exception": "".join(traceback.format_exception(
                    type(exc), value=exc, tb=exc.__traceback__
                )),
                "service_called": service_name,
                "request_id": context.get("request_id"),
                "version": version,
                "api_name": api_name,
            }
        )
        return api_name, service_name, version


async def get_openapi_schemas_from_services(
        services: List[Dict[str, Any]]
) -> List[Union[Tuple[str, str, str, Dict, str], Tuple[str, str, str]]]:
    async with aiohttp.ClientSession() as session:
        tasks = [
            get_schema_from_service(
                session,
                config[service][version],
                service,
                version,
                url
            )
            for config in services
            for service in config
            for version in config[service]
            for url in config[service][version]['openapi_url']
        ]

        return await asyncio.gather(*tasks)


def get_dummy_path(api_name: str, version: str) -> Dict[str, Any]:
    api_name = api_name.upper()
    return {
        f"/{api_name.lower()}/api/{version}/dummy_path": {
            "get": {"tags": [f"{api_name}|{version} documentation is down"],
                    "summary": f"Check {api_name} - {version}'s documentation",
                    "security": [{"HTTPBearer": []}],
                    "description": f"This is a dummy path that does nothing. There is something "
                                   f"wrong with {api_name} - {version}'s documentation. Please "
                                   f"check {api_name} - {version}'s documentation for any errors.",
                    "responses": {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "schema": {}
                                }
                            }
                        }
                    },
                    "operationId": "disabled_path_dummy_path_get"}
        }
    }


def clean_up_openapi_schema(
        openapi_schema: Dict[str, Any], service_name: str, api_name: str, version: str, trim: str
) -> None:
    paths = {}

    for path in openapi_schema["paths"]:
        trimmed_path = path

        if trimmed_path.startswith(trim):
            trimmed_path = path[len(trim):]

        methods = get_http_methods_for_endpoint(trimmed_path, api_name, version)

        for method in methods:
            new_path = f"/{api_name}/api/{version}{trimmed_path}"

            if new_path not in paths:
                paths[new_path] = {}

            if method in openapi_schema["paths"][path]:
                existing_tags = ""

                if "tags" in openapi_schema["paths"][path][method]:
                    existing_tags = "|" + "|".join(openapi_schema["paths"][path][method]["tags"])

                paths[new_path].update({method: openapi_schema["paths"][path][method]})
                paths[new_path][method].update({
                    "tags": [f"{api_name.upper()}|{service_name}|{version}{existing_tags}"],
                    "security": [{"HTTPBearer": []}]
                })

    openapi_schema["paths"] = paths


async def build_openapi_schema(
        api_gateway_openapi_schema: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    openapi_schema = build_initial_openapi_schema()

    if context.get("docs_option") == "external":
        services = EXTERNAL_DOCS
        populate_external_openapi_schema_with_auth(openapi_schema)
    else:
        services = INTERNAL_DOCS
        update_openapi_schema_with_url_openapi_schema(openapi_schema, api_gateway_openapi_schema)
        obscure_password_field_in_internal_docs(openapi_schema)

    openapi_schemas_from_services = await get_openapi_schemas_from_services(services)

    for service_openapi_schema in openapi_schemas_from_services:
        if len(service_openapi_schema) == 3:
            openapi_schema["paths"].update(
                get_dummy_path(service_openapi_schema[0], service_openapi_schema[2])
            )
        else:
            clean_up_openapi_schema(
                service_openapi_schema[3],
                service_openapi_schema[1],
                service_openapi_schema[0],
                service_openapi_schema[2],
                service_openapi_schema[4]
            )

            if "components" in service_openapi_schema[3]:
                solve_name_collisions_for_components_in_openapi_schema(
                    service_openapi_schema[3],
                    openapi_schema,
                    service_openapi_schema[1],
                    service_openapi_schema[2],
                )
            update_openapi_schema_with_url_openapi_schema(
                openapi_schema, service_openapi_schema[3]
            )

    return openapi_schema
