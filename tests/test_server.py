#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import atexit
import unittest

from couchdb3.database import Database
from couchdb3.server import Server
from couchdb3.utils import COUCH_DB_RESERVED_DB_NAMES

from tests.credentials import COUCHDB_USER, COUCHDB_PASSWORD, COUCHDB0_URL


TEST_DB_NAME: str = "test-db"
CLIENT: Server = Server(url=COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD)


class TestClient(unittest.TestCase):
    def test_client_init(self):
        self.assertIsInstance(CLIENT, Server)
        self.assertTrue(CLIENT.check())
        self.assertIsInstance(CLIENT.info(), dict)

    def test_active_tasks(self):
        results = CLIENT.active_tasks()
        self.assertIsInstance(results, list)
        for _ in results:
            self.assertIsInstance(_, dict)

    def test_all_dbs(self):
        results = CLIENT.all_dbs()
        self.assertIsInstance(results, list)
        for _ in results:
            self.assertIsInstance(_, str)

    def test_check_user(self):
        self.assertTrue(CLIENT.check_user(username=COUCHDB_USER, password=COUCHDB_PASSWORD))

    def test_create(self):
        db = CLIENT.create(name=TEST_DB_NAME, partitioned=True)
        self.assertIsInstance(db, Database)
        self.assertTrue(db.check())

    def test_dbs_info(self):
        keys = CLIENT.all_dbs()
        results = CLIENT.dbs_info(keys=keys)
        self.assertIsInstance(results, list)
        for _ in results:
            self.assertIsInstance(_, dict)

    def test_delete(self):
        self.assertTrue(CLIENT.delete(TEST_DB_NAME))

    def test_get(self):
        if TEST_DB_NAME not in CLIENT:
            self.assertFalse(CLIENT.get(TEST_DB_NAME).check())
            CLIENT.create(TEST_DB_NAME)
        db = CLIENT[TEST_DB_NAME]
        self.assertIsInstance(db, Database)
        self.assertTrue(db.check())
        CLIENT.delete(TEST_DB_NAME)

    def test_get_special_db(self):
        for _ in COUCH_DB_RESERVED_DB_NAMES:
            if _ in CLIENT:
                self.assertIsInstance(CLIENT.get(_), Database)

    def test_replicate(self):
        if TEST_DB_NAME not in CLIENT:
            CLIENT.create(TEST_DB_NAME)
        target_db = f"{TEST_DB_NAME}-rep"
        result = CLIENT.replicate(
            source=TEST_DB_NAME,
            target=target_db,
            continuous=True,
            create_target=True
        )
        self.assertTrue(result.get("ok"))

    def test_rev(self):
        self.assertIsInstance(CLIENT.rev("_users/_design/_auth"), str)
        self.assertIs(CLIENT.rev("_users/test"), None)

    def test_save_user(self):
        user_id = "org.couchdb.user:john"
        ok, _id, _rev = CLIENT.save_user(
            user_id=user_id,
            name="john",
            password="secret123"
        )
        self.assertEqual(ok, True)
        self.assertEqual(_id, user_id)
        self.assertIsInstance(_rev, str)

    def test_up(self):
        self.assertTrue(CLIENT.up())
        self.assertFalse(Server("http://admin:secret@localhost:1234").up())

    def test_with_context(self):
        with Server(url=COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD) as client:
            self.assertIsInstance(client, Server)


@atexit.register
def rm_test_db() -> None:
    """
    Removing temporary test database.
    """
    for dbname in [
        TEST_DB_NAME,
        f"{TEST_DB_NAME}-rep"
    ]:
        if dbname in CLIENT:
            CLIENT.delete(dbname)


if __name__ == '__main__':
    unittest.main()
