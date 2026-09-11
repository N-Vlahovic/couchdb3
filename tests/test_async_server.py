#!/usr/bin/env python3

import asyncio
import atexit
import unittest

from couchdb3.async_database import AsyncDatabase
from couchdb3.async_server import AsyncServer
from couchdb3.server import Server
from couchdb3.utils import COUCH_DB_RESERVED_DB_NAMES
from tests.credentials import COUCHDB0_URL, COUCHDB_PASSWORD, COUCHDB_USER

TEST_DB_NAME: str = "test-async-db"

# Sync client for atexit cleanup only
_SYNC_CLIENT: Server = Server(
    url=COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD
)


class TestAsyncClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncServer(
            url=COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_client_init(self):
        self.assertIsInstance(self.client, AsyncServer)
        self.assertTrue(await self.client.check())
        self.assertIsInstance(await self.client.info(), dict)

    async def test_active_tasks(self):
        results = await self.client.active_tasks()
        self.assertIsInstance(results, list)
        for _ in results:
            self.assertIsInstance(_, dict)

    async def test_all_dbs(self):
        results = await self.client.all_dbs()
        self.assertIsInstance(results, list)
        for _ in results:
            self.assertIsInstance(_, str)

    async def test_check_user(self):
        self.assertTrue(
            await self.client.check_user(
                username=COUCHDB_USER, password=COUCHDB_PASSWORD
            )
        )

    async def test_create(self):
        db = await self.client.create(name=TEST_DB_NAME, partitioned=True)
        self.assertIsInstance(db, AsyncDatabase)
        self.assertTrue(await db.check())

    async def test_dbs_info(self):
        keys = await self.client.all_dbs()
        results = await self.client.dbs_info(keys=keys)
        self.assertIsInstance(results, list)
        for _ in results:
            self.assertIsInstance(_, dict)

    async def test_delete(self):
        if TEST_DB_NAME not in (await self.client.all_dbs()):
            await self.client.create(TEST_DB_NAME)
        self.assertTrue(await self.client.delete(TEST_DB_NAME))

    async def test_get(self):
        if TEST_DB_NAME not in (await self.client.all_dbs()):
            await self.client.create(TEST_DB_NAME)
        db = await self.client.get(TEST_DB_NAME)
        self.assertIsInstance(db, AsyncDatabase)
        self.assertTrue(await db.check())
        await self.client.delete(TEST_DB_NAME)

    async def test_get_special_db(self):
        all_dbs = await self.client.all_dbs()
        for name in COUCH_DB_RESERVED_DB_NAMES:
            if name in all_dbs:
                db = await self.client.get(name)
                self.assertIsInstance(db, AsyncDatabase)

    async def test_replicate(self):
        if TEST_DB_NAME not in (await self.client.all_dbs()):
            await self.client.create(TEST_DB_NAME)
        db = await self.client.get(TEST_DB_NAME)
        target_db = f"{self.client.url}/{TEST_DB_NAME}-rep"
        result = await self.client.replicate(
            source=db.url,
            target=target_db,
            continuous=True,
            create_target=True,
        )
        self.assertTrue(result.get("ok"))

    async def test_rev(self):
        self.assertIsInstance(
            await self.client.rev("_users/_design/_auth"), str
        )
        self.assertIsNone(await self.client.rev("_users/test"))

    async def test_save_user(self):
        user_id = "org.couchdb.user:john-async"
        ok, _id, _rev = await self.client.save_user(
            user_id=user_id, name="john-async", password="secret123"
        )
        self.assertEqual(ok, True)
        self.assertEqual(_id, user_id)
        self.assertIsInstance(_rev, str)

    async def test_up(self):
        self.assertTrue(await self.client.up())
        async with AsyncServer("http://admin:secret@localhost:1234") as bad:
            self.assertFalse(await bad.up())

    async def test_context_manager(self):
        async with AsyncServer(
            url=COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD
        ) as client:
            self.assertIsInstance(client, AsyncServer)
            self.assertTrue(await client.up())


@atexit.register
def rm_test_dbs() -> None:
    """Remove temporary async test databases using the sync client."""
    for dbname in [TEST_DB_NAME, f"{TEST_DB_NAME}-rep"]:
        if dbname in _SYNC_CLIENT:
            _SYNC_CLIENT.delete(dbname)


if __name__ == "__main__":
    unittest.main()
