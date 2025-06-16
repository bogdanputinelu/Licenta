import os
import traceback
import fnmatch
import yaml
from typing import Dict, Any
from .splunk_logging import logger
from passlib.context import CryptContext


DENY_ALL_ACCESS_FLAG = "DENY_ALL_ACCESS"
AUTHENTICATE_FLAG = "AUTHENTICATE"
NO_AUTHENTICATION_FLAG = "NO_AUTHENTICATION"
PASSWORD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
TOKEN_SECRET_KEY = "fbceab2049df658b1ad993c3433a10bdcbc340da78af7153a1f01ee42fd0221a"
DB_USER = "user"
DB_PASSWORD = "password"
DB_NAME = "auth_db"
DB_HOST = "localhost"
ENDPOINT_RULES = {}
INTERNAL_DOCS = {}
EXTERNAL_DOCS = {}
DOCS_API_GATEWAY_URL = "http://127.0.0.1:8000/"


def read_data_from_yaml_file(root: str, file: str) -> Dict[str, Any]:
    for _ in range(3):
        try:
            with open(os.path.join(root, file), encoding="utf-8") as f:
                return yaml.safe_load(f.read())
        except Exception as e:
            logger.error(
                {
                    "message": f"Error when reading f{file} from {root}. Retrying...",
                    "process": "onboarding",
                    "exception": "".join(traceback.format_exception(
                        type(e), value=e, tb=e.__traceback__
                    ))
                }
            )
    logger.error(
        {
            "message": f"Error when reading f{file} from {root} after 3 retries. This configuration will be skipped.",
            "process": "onboarding",
        }
    )
    return {}


def populate_automatic_docs_data(onboarding_data: Dict[str, Any]):
    api_name = onboarding_data.get("api-name")
    namespace = onboarding_data.get("namespace")
    port = onboarding_data.get("port")
    version = onboarding_data.get("version")
    docs_type = onboarding_data.get("type")
    docs_tag = onboarding_data.get("docs-tag")
    docs_openapi_endpoint = onboarding_data.get("docs-openapi-endpoint")

    docs_details = {
        "openapi_url": f"http://{api_name}.{namespace}.svc.cluster.local:{port}{docs_openapi_endpoint}",
        "api_name": api_name,
        "tag": docs_tag
    }

    if api_name not in INTERNAL_DOCS:
        INTERNAL_DOCS[api_name] = {}

    INTERNAL_DOCS[api_name][version] = docs_details

    if docs_type.lower() == "external":
        if api_name not in EXTERNAL_DOCS:
            EXTERNAL_DOCS[api_name] = {}

        EXTERNAL_DOCS[api_name][version] = docs_details


def populate_endpoint_rules(onboarding_data: Dict[str, Any]):
    api_name = onboarding_data.get("api-name")
    namespace = onboarding_data.get("namespace")
    version = onboarding_data.get("version")
    port = onboarding_data.get("port")
    endpoints = onboarding_data.get("endpoints")

    url = f"http://{api_name}.{namespace}.svc.cluster.local:{port}/"

    if api_name not in ENDPOINT_RULES:
        ENDPOINT_RULES[api_name] = {}

    if version not in ENDPOINT_RULES[api_name]:
        ENDPOINT_RULES[api_name][version] = []

    for rule in endpoints:
        ((endpoint, permissions),) = rule.items()
        permissions = {
            method.upper(): [options] if not isinstance(options, list) else options
            for method, options in permissions.items()
        }

        endpoint = fnmatch.translate(endpoint)

        api_endpoint = {
            endpoint: {
                "url": url,
            }
        }
        api_endpoint[endpoint].update(permissions)
        ENDPOINT_RULES[api_name][version].append(api_endpoint)


def parse_onboarding_config_and_populate_data_structures():
    for root, _, files in os.walk("src/onboarding-config"):
        for file in files:
            if not (file.endswith(".yaml") or file.endswith(".yml")):
                continue

            onboarding_data = read_data_from_yaml_file(root, file)

            if not onboarding_data:
                continue

            populate_automatic_docs_data(onboarding_data)
            populate_endpoint_rules(onboarding_data)

            logger.info(
                {
                    "message": f"Successfully onboarded {onboarding_data.get('api-name')} {onboarding_data.get('version')}",
                    "process": "onboarding"
                }
            )


parse_onboarding_config_and_populate_data_structures()
