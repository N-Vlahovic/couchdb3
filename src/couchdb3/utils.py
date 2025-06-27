#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
from collections.abc import Generator
from enum import Enum
import mimetypes
import re
import requests
from typing import Any, Dict, Optional, Set, Type
from urllib import parse
from urllib3.util import Url, parse_url

from . import exceptions


__all__ = [
    "basic_auth",
    "build_query",
    "build_url",
    "rm_nones_from_dict",
    "user_name_to_id",
    "validate_auth_method",
    "validate_db_name",
    "validate_proxy",
    "validate_user_id",
    "check_response",
    "extract_url_data",
    "partitioned_db_resource_parser",
    "COUCHDB_USERS_DB_NAME",
    "COUCHDB_REPLICATOR_DB_NAME",
    "COUCHDB_GLOBAL_CHANGES_DB_NAME",
    "COUCH_DB_RESERVED_DB_NAMES",
    "DEFAULT_AUTH_METHOD",
    "DEFAULT_TIMEOUT",
    "MimeTypeEnum",
    "PATTERN_DB_NAME",
    "PATTERN_USER_ID",
    "VALID_AUTH_METHODS",
    "VALID_SCHEMES",
]


COUCHDB_USERS_DB_NAME: str = "_users"
"""Reserved CouchDB users database name."""
COUCHDB_REPLICATOR_DB_NAME: str = "_replicator"
"""Reserved CouchDB replicator database name."""
COUCHDB_GLOBAL_CHANGES_DB_NAME: str = "_global_changes"
"""Reserved CouchDB global changes database name."""

COUCH_DB_RESERVED_DB_NAMES: Set[str] = {
    COUCHDB_USERS_DB_NAME,
    COUCHDB_REPLICATOR_DB_NAME,
    COUCHDB_GLOBAL_CHANGES_DB_NAME
}
"""Reserved CouchDB database names."""

COUCH_DB_RESERVED_DOC_FIELDS: Set[str] = {
    "_id",
    "_rev",
}
"""Reserved CouchDB document fields."""

DEFAULT_AUTH_METHOD: str = "cookie"
"""The default authentication method - values to `\"cookie\"`."""

DEFAULT_TIMEOUT: int = 300
"""The default timeout set in requests - values to `300`."""

MimeTypeEnum: Type[Enum] = Enum(
    'MimeTypeEnum',
    {'mime_type_' + k.removeprefix('.'): v for k, v in mimetypes.types_map.items()}
)
"""An Enum containing all existing mime types."""

PATTERN_DB_NAME: re.Pattern = re.compile(r"^[a-z][a-z0-9_$()+/-]*$")
"""The pattern for valid database names."""
PATTERN_USER_ID: re.Pattern = re.compile(r"^org\.couchdb\.user:.*")
"""The pattern for valid user IDs."""

VALID_AUTH_METHODS: Set[str] = {"basic", "cookie"}
"""The valid auth method arguments. Possible values are `\"basic\"` or `\"cookie\"`."""
VALID_SCHEMES: Set[str] = {"http", "https", "socks5"}
"""The valid TCP schemes. Possible values are `\"http\"` or `\"https\"` or `\"socks5\"`."""


def _handler(x: Any) -> str:
    if isinstance(x, (Generator, map, list, set, tuple)):
        return "[%s]" % ",".join(f"\"{_handler(_)}\"" for _ in x)
    elif isinstance(x, dict):
        return str({key: _handler(val) for key, val in x.items()})
    elif isinstance(x, bool):
        return str(x).lower()
    return str(x)


def basic_auth(
        user: str,
        password: str
) -> str:
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
) -> Optional[str]:
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
        path: str = None,
        port: int = None,
        **kwargs,
) -> Url:
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
    Url : An instance of `Url`.
    """
    return Url(
        scheme=scheme,
        host=host,
        port=port,
        path=path,
        query=build_query(**kwargs),
    )


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
    return parse_url(proxy).scheme in VALID_SCHEMES


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


def check_response(response: requests.Response) -> None:
    """
    Check if a request yields a successful response.

    Parameters
    ----------
    response : requests.Response
        A `requests.Response` object.
    Returns
    -------
    None
    Raises
    ------
    One of the following exceptions:

    - couchdb3.error.CouchDBError
    - ConnectionError
    - TimeoutError
    - requests.exceptions.ConnectionError
    - requests.exceptions.HTTPError

    """
    try:
        response.raise_for_status()
    except (
            ConnectionError,
            TimeoutError,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
    ) as err:
        if response.status_code in exceptions.STATUS_CODE_ERROR_MAPPING:
            _ = exceptions.STATUS_CODE_ERROR_MAPPING[response.status_code]
            if _:
                raise _(response.text)
            else:
                return None
        raise err


def extract_url_data(url: str) -> Dict:
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
    parsed = parse_url(url)
    return {
        "scheme": parsed.scheme,
        "user": parsed.auth.split(":")[0] if hasattr(parsed.auth, "split") else None,
        "password": parsed.auth.split(":")[1] if hasattr(parsed.auth, "split") else None,
        "host": parsed.host,
        "port": parsed.port,
        "path": parsed.path
    }


def partitioned_db_resource_parser(
        resource: str = None,
        partition: str = None,
) -> Optional[str]:
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
