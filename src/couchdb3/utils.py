#!/usr/bin/env python3

import base64
import mimetypes
import re
from collections.abc import Generator
from enum import Enum
from typing import Any
from urllib import parse
from urllib.parse import urlparse

import httpx

from . import exceptions

__all__ = [
    "COUCHDB_GLOBAL_CHANGES_DB_NAME",
    "COUCHDB_REPLICATOR_DB_NAME",
    "COUCHDB_USERS_DB_NAME",
    "COUCH_DB_RESERVED_DB_NAMES",
    "COUCH_DB_RESERVED_DOC_FIELDS",
    "DEFAULT_AUTH_METHOD",
    "DEFAULT_TIMEOUT",
    "PATTERN_DB_NAME",
    "PATTERN_USER_ID",
    "VALID_AUTH_METHODS",
    "VALID_SCHEMES",
    "MimeTypeEnum",
    "basic_auth",
    "build_query",
    "build_url",
    "check_response",
    "extract_url_data",
    "partitioned_db_resource_parser",
    "rm_nones_from_dict",
    "user_name_to_id",
    "validate_auth_method",
    "validate_db_name",
    "validate_proxy",
    "validate_user_id",
]


COUCHDB_USERS_DB_NAME: str = "_users"
"""Reserved CouchDB users database name."""
COUCHDB_REPLICATOR_DB_NAME: str = "_replicator"
"""Reserved CouchDB replicator database name."""
COUCHDB_GLOBAL_CHANGES_DB_NAME: str = "_global_changes"
"""Reserved CouchDB global changes database name."""

COUCH_DB_RESERVED_DB_NAMES: set[str] = {
    COUCHDB_USERS_DB_NAME,
    COUCHDB_REPLICATOR_DB_NAME,
    COUCHDB_GLOBAL_CHANGES_DB_NAME,
}
"""Reserved CouchDB database names."""

COUCH_DB_RESERVED_DOC_FIELDS: set[str] = {
    "_id",
    "_rev",
}
"""Reserved CouchDB document fields."""

DEFAULT_AUTH_METHOD: str = "cookie"
"""The default authentication method - values to `\"cookie\"`."""

DEFAULT_TIMEOUT: int = 300
"""The default timeout set in requests - values to `300`."""

MimeTypeEnum: type[Enum] = Enum(
    "MimeTypeEnum",
    {"mime_type_" + k.removeprefix("."): v for k, v in mimetypes.types_map.items()},
)
"""An Enum containing all existing mime types."""

PATTERN_DB_NAME: re.Pattern = re.compile(r"^[a-z][a-z0-9_$()+/-]*$")
"""The pattern for valid database names."""
PATTERN_USER_ID: re.Pattern = re.compile(r"^org\.couchdb\.user:.*")
"""The pattern for valid user IDs."""

VALID_AUTH_METHODS: set[str] = {"basic", "cookie"}
"""The valid auth method arguments. Possible values are `\"basic\"` or `\"cookie\"`."""
VALID_SCHEMES: set[str] = {"http", "https", "socks5"}
"""The valid TCP schemes. Possible values are `\"http\"` or `\"https\"` or `\"socks5\"`."""


def _handler(x: Any) -> str:
    if isinstance(x, (Generator, map, list, set, tuple)):
        return "[{}]".format(",".join(f'"{_handler(_)}"' for _ in x))
    elif isinstance(x, dict):
        return str({key: _handler(val) for key, val in x.items()})
    elif isinstance(x, bool):
        return str(x).lower()
    return str(x)


def basic_auth(user: str, password: str) -> str:
    """
    Create basic authentication headers value.

    Parameters
    ----------
    user : str
        A CouchDB user name.
    password : str
        A corresponding CouchDB user password.

    Returns
    -------
    str : The credentials concatenated with a colon and base64 encoded.
    """
    return base64.b64encode(f"{user}:{password}".encode()).decode()


def build_query(
    **kwargs,
) -> str | None:
    """

    Parameters
    ----------
    kwargs
        Arbitrary keyword-args to be passed as query-params in a URL.
    Returns
    -------
    str : A string containing the keyword-args encoded as URL query-params.
    """
    return parse.urlencode({key: _handler(val) for key, val in kwargs.items() if val is not None})


def build_url(
    *,
    scheme: str,
    host: str,
    path: str | None = None,
    port: int | None = None,
    **kwargs,
) -> str:
    """
    Build a URL using the provided scheme, host, path & kwargs.

    Parameters
    ----------
    scheme : str
        The URL scheme (e.g `http`).
    host : str
        The URL host (e.g. `example.com`).
    path : str
        The URL path (e.g. `/api/data`). Default `None`.
    port : int
        The port to connect to (e.g. `5984`). Default `None`.
    kwargs
        Arbitrary keyword-args to be passed as query-params in a URL.
    Returns
    -------
    str : The fully constructed URL string.
    """
    host_part = f"{host}:{port}" if port else host
    base = f"{scheme}://{host_part}"
    if path:
        base += f"/{path.lstrip('/')}"
    query = build_query(**kwargs)
    if query:
        base += f"?{query}"
    return base


def rm_nones_from_dict(data: dict, /) -> dict:
    """
    Removes all `None` keys from a dictionary.

    Parameters
    ----------
    data : dict
        A dictionary.

    Returns
    -------
    dict : A dictionary without `None` keys.
    """
    return {k: v for k, v in data.items() if v is not None}


def validate_db_name(name: str) -> bool:
    """
    Checks a name for CouchDB name-compliance.

    Parameters
    ----------
    name : str
        A prospective database name.

    Returns
    -------
    bool : `True` if the provided name is CouchDB compliant.
    """
    return name in COUCH_DB_RESERVED_DB_NAMES or bool(PATTERN_DB_NAME.fullmatch(name))


def validate_auth_method(auth_method: str) -> bool:
    """
    Checks if the provided authentication method is valid.

    Parameters
    ----------
    auth_method : str

    Returns
    -------
    bool: `True` if `auth_method` is in `VALID_AUTH_METHODS`.
    """
    return auth_method in VALID_AUTH_METHODS


def validate_proxy(proxy: str) -> bool:
    """
    Check a proxy scheme for CouchDB proxy-scheme-compliance

    Parameters
    ----------
    proxy : str
        A prospective proxy.

    Returns
    -------
    bool : `True` if the provided proxy is CouchDB compliant.
    """
    return urlparse(proxy).scheme in VALID_SCHEMES


def validate_user_id(user_id: str) -> bool:
    """
    Checks a user ID for CouchDB user-id-compliance.

    Parameters
    ----------
    user_id : str
        A prospective user ID.

    Returns
    -------
    bool : `True` if the provided user ID is CouchDB compliant.

    """
    return bool(PATTERN_USER_ID.fullmatch(user_id))


def user_name_to_id(name: str) -> str:
    """
    Convert a name into a valid CouchDB user ID.

    Parameters
    ----------
    name : str
        A user name.

    Returns
    -------
    str : A valid CouchDB ID, i.e. of the form `org.couchdb.user:{name}`.
    """
    return f"org.couchdb.user:{name}"


def check_response(response: httpx.Response) -> None:
    """
    Check if a request yields a successful response.

    Parameters
    ----------
    response : httpx.Response
        An `httpx.Response` object.
    Returns
    -------
    None
    Raises
    ------
    One of the following exceptions:

    - couchdb3.error.CouchDBError
    - ConnectionError
    - TimeoutError
    - httpx.ConnectError
    - httpx.HTTPStatusError

    """
    try:
        response.raise_for_status()
    except (
        ConnectionError,
        TimeoutError,
        httpx.ConnectError,
        httpx.HTTPStatusError,
    ):
        if response.status_code in exceptions.STATUS_CODE_ERROR_MAPPING:
            _ = exceptions.STATUS_CODE_ERROR_MAPPING[response.status_code]
            if _:
                raise _(response.text)
            else:
                return
        raise


def extract_url_data(url: str) -> dict:
    """
    Extract scheme, credentials, host, port & path from a URL.

    Parameters
    ----------
    url : str
        A URL string.

    Returns
    -------
    Dict : A dictionary containing with the following items.

      - scheme
      - user
      - password
      - host
      - port
      - path
    """
    if not any(url.startswith(_) for _ in VALID_SCHEMES):
        url = f"http://{url}"
    parsed = urlparse(url)
    return {
        "scheme": parsed.scheme,
        "user": parsed.username or None,
        "password": parsed.password or None,
        "host": parsed.hostname,
        "port": parsed.port,
        "path": parsed.path or None,
    }


def partitioned_db_resource_parser(
    resource: str | None = None,
    partition: str | None = None,
) -> str | None:
    """
    Build resource path with optional partition ID.

    Parameters
    ----------
    resource : str
        The resource to fetch (relative to the host). Default `None`.
    partition: str
        An optional partition ID. Only valid for partitioned databases. (Default `None`.)
    Returns
    ----------
        The (relative) path of the resource.
    """
    return f"_partition/{partition}/{resource}" if partition else resource
