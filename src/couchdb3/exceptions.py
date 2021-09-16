#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Dict


__all__ = [
    "CouchDBError",
    "AuthenticationMethodError",
    "NameComplianceError",
    "ProxySchemeComplianceError",
    "UserIDComplianceError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "MethodNotAllowedError",
    "NotAcceptableError",
    "ConflictError",
    "PreconditionFailedError",
    "RequestEntityTooLargeError",
    "UnsupportedMediaTypeError",
    "RequestRangeNotSatisfiableError",
    "ExpectationFailedError",
    "InternalServerError",
    "STATUS_CODE_ERROR_MAPPING"
]


class CouchDBError(Exception):
    """CouchDB Error"""


class AuthenticationMethodError(CouchDBError):
    """Authentication method is not allowed."""


class NameComplianceError(CouchDBError):
    """Database name does not comply with the CouchDB requirements. For more information please refer to [the official
    documentation](https://docs.couchdb.org/en/main/api/database/common.html#put--db)."""


class ProxySchemeComplianceError(CouchDBError):
    """Proxy scheme does not comply with the CouchDB requirements. For more information please refer to [the official
    documentation](https://docs.couchdb.org/en/main/api/server/common.html#replicate)"""


class UserIDComplianceError(CouchDBError):
    """User ID does not comply with the CouchDB requirements. For more information please refer to [the official
    documentation](https://docs.couchdb.org/en/main/intro/security.html#org-couchdb-user)"""


class BadRequestError(CouchDBError):
    """Bad request structure. The error can indicate an error with the request URL, path or headers. Differences in the
    supplied MD5 hash and content also trigger this error, as this may indicate message corruption."""


class UnauthorizedError(CouchDBError):
    """The item requested was not available using the supplied authorization, or authorization was not supplied."""


class ForbiddenError(CouchDBError):
    """The requested item or operation is forbidden."""


class NotFoundError(CouchDBError):
    """The requested content could not be found. The content will include further information, as a JSON object, if
    available. The structure will contain two keys, `error` and `reason`. For example:
    ```
    {"error":"not_found","reason":"no_db_file"}
    ```
    """


class MethodNotAllowedError(CouchDBError):
    """A request was made using an invalid HTTP request type for the URL requested. For example, you have requested a
    `PUT` when a `POST` is required. Errors of this type can also triggered by invalid URL strings."""


class NotAcceptableError(CouchDBError):
    """The requested content type is not supported by the server."""


class ConflictError(CouchDBError):
    """Request resulted in an update conflict."""


class PreconditionFailedError(CouchDBError):
    """The request headers from the client and the capabilities of the server do not match."""


class RequestEntityTooLargeError(CouchDBError):
    """A document exceeds the configured `couchdb3/max_document_size` value or the entire request exceeds the
    `chttpd/max_http_request_size` value"""


class UnsupportedMediaTypeError(CouchDBError):
    """Content type error."""


class RequestRangeNotSatisfiableError(CouchDBError):
    """The range specified in the request header cannot be satisfied by the server."""


class ExpectationFailedError(CouchDBError):
    """When sending documents in bulk, the bulk load operation failed."""


class InternalServerError(CouchDBError):
    """The request was invalid, either because the supplied JSON was invalid, or invalid information was supplied as
    part of the request."""


STATUS_CODE_ERROR_MAPPING: Dict = {
    200: None,
    201: None,
    202: None,
    304: None,
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    405: MethodNotAllowedError,
    406: NotAcceptableError,
    409: ConflictError,
    412: PreconditionFailedError,
    413: RequestEntityTooLargeError,
    415: UnsupportedMediaTypeError,
    416: RequestRangeNotSatisfiableError,
    417: ExpectationFailedError,
    500: InternalServerError
}
