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
TOKEN_SECRET_KEY = os.getenv("TOKEN_SECRET_KEY")
DB_USER = "user"
DB_PASSWORD = "password"
DB_NAME = "auth_db"
DB_HOST = "postgresql.database-namespace.svc.cluster.local"
DB_PORT = 5432
ENDPOINT_RULES = {}


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
    for root, _, files in os.walk("./onboarding-config"):
        for file in files:
            if not (file.endswith(".yaml") or file.endswith(".yml")):
                continue

            onboarding_data = read_data_from_yaml_file(root, file)

            if not onboarding_data:
                continue

            populate_endpoint_rules(onboarding_data)

            logger.info(
                {
                    "message": f"Successfully onboarded {onboarding_data.get('api-name')} {onboarding_data.get('version')}",
                    "process": "onboarding"
                }
            )


parse_onboarding_config_and_populate_data_structures()
