#!/usr/bin/env python3
"""
Synchronous CouchDB client subpackage.

    from couchdb3.sync import Server, Database, Partition

Shared types (Document, ViewResult, ViewRow, exceptions, utils) are not
re-exported here — import them from ``couchdb3`` directly.
"""

from .database import Database as Database
from .database import Partition as Partition
from .server import Server as Server

__all__ = [
    "Database",
    "Partition",
    "Server",
]
