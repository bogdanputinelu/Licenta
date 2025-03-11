import asyncio
import traceback
from aiohttp import ClientSession
from typing import List, Dict, Union, Optional
from contextlib import asynccontextmanager
from asyncpg import create_pool, Pool
from fastapi import FastAPI, HTTPException, status
from starlette_context import context
from .splunk_logging import logger
from .constants import DB_USER, DB_PASSWORD, DB_HOST, DB_NAME


database_pool: Pool = None
client_session: ClientSession = None


async def get_client_session() -> ClientSession:
    global client_session

    if client_session is None or client_session.closed:
        print("sadasdadssad")
        client_session = ClientSession()

    return client_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This Async Context Manager creates a connection pool to the Database and a global client session used for
    forwarding requests at the start-up of the FastAPI application.
    At the FastAPI application shutdown, it will close the connection pool and the global client session.
    """
    global database_pool, client_session
    await get_client_session()
    database_pool = await create_pool(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        min_size=1,
        max_size=5
    )
    yield
    await database_pool.close()
    await client_session.close()


async def retry_database_query(
        query: str,
        *args,
        retry_limit: int = 3,
        fetchval: bool = False,
        exc_info: str = "Failed to query database"
) -> Union[Optional[str], List[Dict[str, str]]]:
    """
    This is a function that queries the database with the given parametrized query and parameters.
    It will retry, in case of error, for 3 times, by default. The retry limit can be changed.
    It will use the connection.fetch() or connection.fetchval() methods to retrieve data.

    This function is used by other intermediary functions to retrieve either the hashed password of a specified user
    or the groups that the user belongs to, which match a provided list of groups.

    :param query: the SQL query that will be executed in the database
    :param args: the parameters for the parametrized query
    :param retry_limit: the number of retries to fetch data from the database in case of error
    :param fetchval: set to False to use connection.fetch() for retrieving data, or True to use connection.fetchval().
    :param exc_info: the exception message in case all attempts of querying the database fail

    :return: either a hashed password (string), or a list of group names (list of Dict[str, str])
    """
    global database_pool
    for attempt in range(retry_limit):
        try:
            async with database_pool.acquire() as connection:
                if fetchval:
                    result = await connection.fetchval(query, *args)
                else:
                    result = await connection.fetch(query, *args)

                logger.info(
                    {
                        "message": f"Successfully queried database",
                        "X-Request-ID": context.get("X-Request-ID")
                    }
                )

                return result
        except Exception as exc:
            logger.error(
                {
                    "message": "Error when trying to query database",
                    "exception": "".join(traceback.format_exception(
                        type(exc), value=exc, tb=exc.__traceback__
                    )),
                    "X-Request-ID": context.get("X-Request-ID")
                }
            )
            wait_time = 2 ** attempt
            await asyncio.sleep(wait_time)

    logger.error(
        {
            "message": f"{exc_info} after {retry_limit} retries",
            "X-Request-ID": context.get("X-Request-ID")
        }
    )
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def get_password_from_database(username: str) -> Optional[str]:
    """
    Retrieves the hashed password of a specified user, if it exists.

    :param username: the specified user

    :return: the hashed password of the user or None if the user does not exist in the database
    """
    query = """
        SELECT password
        FROM users 
        WHERE username = $1;
    """
    logger.info(
        {
            "message": f"Retrieving hashed password from database",
            "X-Request-ID": context.get("X-Request-ID")
        }
    )

    return await retry_database_query(
        query,
        username,
        fetchval=True,
        exc_info="Failed to retrieve hashed password from database"
    )


async def get_user_groups_from_database(username: str, groups: List[str]) -> List[Dict[str, str]]:
    """
    Retrieves the groups that the user belongs to, which match a provided list of groups.

    :param username: the specified user
    :param groups: the specified groups

    :return: a list of dictionaries that contain the groups that the user belongs to,
             which match a provided list of groups

             example: [{"group_name": "group_1"}, {"group_name": "group_2"}]
    """
    query = """
        SELECT g.group_name
        FROM groups g
        JOIN user_groups ug ON g.group_id = ug.group_id
        JOIN users u ON u.user_id = ug.user_id
        WHERE u.username = $1
        AND g.group_name = ANY($2);
    """
    logger.info(
        {
            "message": f"Retrieving the groups that the user belongs to, which match to the ones provided: {groups}",
            "X-Request-ID": context.get("X-Request-ID")
        }
    )
    return await retry_database_query(
        query,
        username,
        groups,
        exc_info="Failed to retrieve user groups from database"
    )
