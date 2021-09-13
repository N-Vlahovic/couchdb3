#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import re
import requests
from typing import Any, Dict, Optional
from urllib import parse

from . import exceptions


__all__ = [
    "basic_auth",
    "build_query",
    "build_url",
    "validate_db_name",
    "validate_proxy",
    "validate_user_id",
    "check_response",
    "content_type_getter",
    "extract_url_data",
    "DEFAULT_TIMEOUT",
    "MIME_TYPES_MAPPING",
    "PATTERN_DB_NAME",
    "PATTERN_USER_ID",
    "PATTERN_URL",
]


DEFAULT_TEXTUAL_MIME_TYPE: str = "text/plain"
DEFAULT_FALLBACK_MIME_TYPE: str = "application/octet-stream"
DEFAULT_TIMEOUT: int = 15
"""The default timeout set in requests."""

MIME_TYPES_MAPPING: Dict = {
    "aac": "audio/aac",
    "abw": "application/x-abiword",
    "arc": "application/x-freearc",
    "avi": "video/x-msvideo",
    "azw": "application/vnd.amazon.ebook",
    "bin": "application/octet-stream",
    "bmp": "image/bmp",
    "bz": "application/x-bzip",
    "bz2": "application/x-bzip2",
    "cda": "application/x-cdf",
    "csh": "application/x-csh",
    "css": "text/css",
    "csv": "text/csv",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "eot": "application/vnd.ms-fontobject",
    "epub": "application/epub+zip",
    "gz": "application/gzip",
    "gif": "image/gif",
    "htm": "text/html",
    "html": "text/html",
    "ico": "image/vnd.microsoft.icon",
    "ics": "text/calendar",
    "jar": "application/java-archive",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "js": "text/javascript",
    "json": "application/json",
    "jsonld": "application/ld+json",
    "mid": "audio/midi audio/x-midi",
    "midi": "audio/midi audio/x-midi",
    "mjs": "text/javascript",
    "mp3": "audio/mpeg",
    "mp4": "video/mp4",
    "mpeg": "video/mpeg",
    "mpkg": "application/vnd.apple.installer+xml",
    "odp": "application/vnd.oasis.opendocument.presentation",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "odt": "application/vnd.oasis.opendocument.text",
    "oga": "audio/ogg",
    "ogv": "video/ogg",
    "ogx": "application/ogg",
    "opus": "audio/opus",
    "otf": "font/otf",
    "png": "image/png",
    "pdf": "application/pdf",
    "php": "application/x-httpd-php",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "rar": "application/vnd.rar",
    "rtf": "application/rtf",
    "sh": "application/x-sh",
    "svg": "image/svg+xml",
    "swf": "application/x-shockwave-flash",
    "tar": "application/x-tar",
    "tif .tiff": "image/tiff",
    "ts": "video/mp2t",
    "ttf": "font/ttf",
    "txt": "text/plain",
    "vsd": "application/vnd.visio",
    "wav": "audio/wav",
    "weba": "audio/webm",
    "webm": "video/webm",
    "webp": "image/webp",
    "woff": "font/woff",
    "woff2": "font/woff2",
    "xhtml": "application/xhtml+xml",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xml": "application/xml",
    "xul": "application/vnd.mozilla.xul+xml",
    "zip": "application/zip",
    "3gp": "video/3gpp",
    "3g2": "video/3gpp2",
    "7z": "application/x-7z-compressed"
}
"""A dictionary mapping file extensions to their appropriate content-type."""

PATTERN_DB_NAME: re.Pattern = re.compile(r"^[a-z][a-z0-9_$()+/-]*$")
"""The pattern for valid database names."""
PATTERN_USER_ID: re.Pattern = re.compile(r"^org\.couchdb\.user:.*")
"""The pattern for valid user IDs."""
PATTERN_URL: re.Pattern = re.compile(r"^(\w+)://((.*):(.*)@|)(\w[\w.-]+\w)(:(\d+)|)/?(.*)$")
"""A pattern for abstract URLs split as `scheme://user:password@host:port/path`."""


def _handler(x: Any) -> str:
    if isinstance(x, (list, set, tuple)):
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
    str : A URL parsed as string.
    """
    url = f"{scheme}://{host}"
    if port:
        url += f":{port}"
    if path:
        path = path.removeprefix("/")
        url += f"/{path}"
    if kwargs:
        url += f"?{build_query(**kwargs)}"
    return url


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
    return bool(PATTERN_DB_NAME.fullmatch(name))


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
    return PATTERN_URL.sub(r"\1", proxy) in {"http", "socks5"}


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


def content_type_getter(
        file_name: str = None,
        data: Any = None
) -> Optional[str]:
    """
    Get the appropriate content-type.

    If the argument `file_name` is provided, the content-type will be determined by matching the file extension against
    keys of `MIME_TYPES_MAPPING`. If no match was found, then `"application/octet-stream"` will be returned.

    Alternatively, if the argument `data` is provided the conent-type returned will be

    - `"application/json"` if `data` is a dictionary or a list
    - `"text/plain"` else

    Parameters
    ----------
    file_name : str
        A file name.
    data : Any
        A Python object.

    Returns
    -------
    str : A valid content-type.
    """
    if file_name:
        for ext, mime_type in MIME_TYPES_MAPPING.items():
            if file_name.endswith(f".{ext}"):
                return mime_type
        return DEFAULT_FALLBACK_MIME_TYPE
    elif data:
        if isinstance(data, (dict, list)):
            return "application/json"
        else:
            return DEFAULT_TEXTUAL_MIME_TYPE


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
    return {
        "scheme": PATTERN_URL.sub(r"\1", url) or None,
        "user": PATTERN_URL.sub(r"\3", url) or None,
        "password": PATTERN_URL.sub(r"\4", url) or None,
        "host": PATTERN_URL.sub(r"\5", url) or None,
        "port": int(PATTERN_URL.sub(r"\7", url) or 0) or None,
        "path": PATTERN_URL.sub(r"\8", url or None)
    }
