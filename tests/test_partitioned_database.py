#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import atexit
import datetime

import unittest

from couchdb3.database import Database
from couchdb3.document import Document
from couchdb3.server import Server
from couchdb3.view import ViewResult, ViewRow
from couchdb3.utils import content_type_getter, user_name_to_id

from tests.credentials import ATTACHMENT_PATH_HTML, ATTACHMENT_PATH_JSON, ATTACHMENT_PATH_PNG, ATTACHMENT_PATH_TXT, \
    COUCHDB_USER, COUCHDB_PASSWORD, COUCHDB0_URL, DOCUMENT_VIEW


CLIENT: Server = Server(COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD)
DB_NAME: str = "tmp-test-partitioned-db"
DB: Database = CLIENT.get(DB_NAME) if DB_NAME in CLIENT else CLIENT.create(DB_NAME, partitioned=True)


class TestPartitionedDatabase(unittest.TestCase):
    def test_create(self):
        docid = "partition-0:test-doc-id"
        doc = {
            "name": "Hello",
            "type": "document",
            "_id": docid
        }
        _id, success, _rev = DB.create(doc)
        self.assertIsInstance(_id, str)
        self.assertIsInstance(success, bool)
        self.assertIsInstance(_rev, str)
        self.assertEqual(_id, docid)

    def test_put_design(self):
        ddoc = "document-design"
        _id, ok, _rev = DB.put_design(
            ddoc=ddoc,
            rev=DB.rev(f"_design/{ddoc}"),
            views={
                "document-view": {
                    "map": DOCUMENT_VIEW
                }
            },
            options={
                "partitioned": False
            }
        )
        self.assertEqual(_id, f"_design/{ddoc}")
        self.assertEqual(ok, True)
        self.assertIsInstance(_rev, str)
        breakpoint()


@atexit.register
def rm_test_db() -> None:
    """
    Removing temporary test database.
    """
    CLIENT.delete(DB_NAME)


if __name__ == '__main__':
    unittest.main()
