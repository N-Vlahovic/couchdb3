#!/usr/bin/env python3
"""
Asynchronous CouchDB client subpackage.

    from couchdb3.aio import AsyncServer, AsyncDatabase, AsyncPartition

Shared types (Document, ViewResult, ViewRow, exceptions, utils) are not
re-exported here — import them from ``couchdb3`` directly.
"""

from .async_database import AsyncDatabase as AsyncDatabase
from .async_database import AsyncPartition as AsyncPartition
from .async_server import AsyncServer as AsyncServer

__all__ = [
    "AsyncDatabase",
    "AsyncPartition",
    "AsyncServer",
]
