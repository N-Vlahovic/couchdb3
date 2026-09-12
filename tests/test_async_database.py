#!/usr/bin/env python3

import atexit
import random
import string
import unittest

from couchdb3.aio import AsyncPartition, AsyncServer
from couchdb3.document import AttachmentDocument, Document
from couchdb3.sync import Server
from couchdb3.utils import MimeTypeEnum
from couchdb3.view import ViewResult, ViewRow
from tests.credentials import (
    ATTACHMENT_PATH_HTML,
    ATTACHMENT_PATH_JSON,
    ATTACHMENT_PATH_PDF,
    ATTACHMENT_PATH_PNG,
    ATTACHMENT_PATH_TXT,
    COUCHDB0_URL,
    COUCHDB_PASSWORD,
    COUCHDB_USER,
    DOCUMENT_VIEW,
)

DB_NAME: str = "test-async-" + "".join(random.choices(string.ascii_lowercase, k=5))
DB_NAME_PARTITIONED: str = f"{DB_NAME}-partitioned"

DDOC_ID: str = "document-design"
P_ID: str = "p0"
VIEW_ID: str = "document-view"

# Sync client for atexit cleanup only
_SYNC_CLIENT: Server = Server(url=COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD)


class TestAsyncDatabase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = AsyncServer(url=COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD)
        all_dbs = await self.server.all_dbs()
        if DB_NAME in all_dbs:
            self.db = await self.server.get(DB_NAME)
        else:
            self.db = await self.server.create(DB_NAME)
        if DB_NAME_PARTITIONED in all_dbs:
            self.db_partitioned = await self.server.get(DB_NAME_PARTITIONED)
        else:
            self.db_partitioned = await self.server.create(DB_NAME_PARTITIONED, partitioned=True)

    async def asyncTearDown(self):
        await self.server.aclose()

    async def test_all_docs(self):
        docs = [{"_id": f"test-async-all-docs-{i}", "name": f"Document {i}"} for i in range(5)]
        await self.db.bulk_docs(docs=docs)
        result = await self.db.all_docs(keys=[d["_id"] for d in docs])
        self.assertIsInstance(result, ViewResult)
        self.assertEqual(len(result.rows), 5)
        result = await self.db.all_docs(keys=[d["_id"] for d in docs], include_docs=True)
        for row in result.rows:
            self.assertIsInstance(row, ViewRow)
            self.assertIsInstance(row.doc, Document)

    async def test_bulk_docs(self):
        docs = [{"_id": f"test-async-bulk-{i}", "name": f"Document {i}"} for i in range(5)]
        results = await self.db.bulk_docs(docs=docs)
        self.assertIsInstance(results, list)
        for doc, res in zip(docs, results):
            self.assertEqual(doc["_id"], res["id"])
            self.assertIsInstance(res["rev"], str)
            self.assertTrue(res["ok"])

    async def test_bulk_get(self):
        docs = [{"_id": f"test-async-bulk-get-{i}", "name": f"Document {i}"} for i in range(5)]
        await self.db.bulk_docs(docs=docs)
        results = await self.db.bulk_get(docs=[{"id": d["_id"]} for d in docs])
        self.assertIsInstance(results, list)
        for res in results:
            self.assertIn("id", res)
            self.assertIn("docs", res)

    async def test_compact(self):
        result = await self.db.compact()
        self.assertTrue(result)

    async def test_create(self):
        docid = "test-async-create"
        _id, ok, _rev = await self.db.create({"_id": docid, "type": "test"})
        self.assertEqual(_id, docid)
        self.assertTrue(ok)
        self.assertIsInstance(_rev, str)

    async def test_delete(self):
        docid = "test-async-delete"
        await self.db.save({"_id": docid})
        rev = await self.db.rev(docid)
        self.assertTrue(await self.db.delete(docid=docid, rev=rev))

    async def test_delete_attachment(self):
        docid = "test-async-delete-attachment"
        await self.db.save({"_id": docid})
        content_type = MimeTypeEnum.mime_type_json.value
        attname = "test-att.json"
        rev = await self.db.rev(docid)
        await self.db.put_attachment(
            docid=docid,
            attname=attname,
            content=b'{"hello": "world"}',
            content_type=content_type,
            rev=rev,
        )
        rev = await self.db.rev(docid)
        self.assertTrue(await self.db.delete_attachment(docid=docid, attname=attname, rev=rev))

    async def test_find(self):
        await self.db.save_index(index={"fields": ["type"]}, name="async-type-idx")
        docs = [{"_id": f"test-async-find-{i}", "type": "async-find-test"} for i in range(3)]
        await self.db.bulk_docs(docs=docs)
        result = await self.db.find({"type": {"$eq": "async-find-test"}}, fields=["_id", "type"])
        self.assertIn("docs", result)
        self.assertIsInstance(result["docs"], list)

    async def test_get(self):
        docid = "test-async-get"
        await self.db.save({"_id": docid, "name": "hello"})
        doc = await self.db.get(docid)
        self.assertIsInstance(doc, Document)
        self.assertEqual(doc.id, docid)
        missing = await self.db.get("nonexistent-doc-async")
        self.assertIsNone(missing)

    async def test_get_attachment(self):
        docid = "test-async-get-attachment"
        attname = "hello.txt"
        content = b"hello async world"
        await self.db.save({"_id": docid})
        rev = await self.db.rev(docid)
        await self.db.put_attachment(
            docid=docid,
            attname=attname,
            content=content,
            content_type="text/plain",
            rev=rev,
        )
        att = await self.db.get_attachment(docid=docid, attname=attname)
        self.assertIsInstance(att, AttachmentDocument)
        self.assertEqual(att.content, content)

    async def test_indexes(self):
        result = await self.db.indexes()
        self.assertIsInstance(result, dict)
        self.assertIn("indexes", result)

    async def test_put_attachment_from_path(self):
        docid = "test-async-put-attachment-path"
        await self.db.save({"_id": docid})
        for path in [
            ATTACHMENT_PATH_TXT,
            ATTACHMENT_PATH_JSON,
            ATTACHMENT_PATH_PNG,
            ATTACHMENT_PATH_HTML,
            ATTACHMENT_PATH_PDF,
        ]:
            rev = await self.db.rev(docid)
            attname = path.split("/")[-1]
            _id, ok, _rev = await self.db.put_attachment(
                docid=docid, attname=attname, path=path, rev=rev
            )
            self.assertEqual(_id, docid)
            self.assertTrue(ok)

    async def test_put_design(self):
        db = await self.server.get(DB_NAME)
        rev = await db.rev(f"_design/{DDOC_ID}")
        _id, ok, _rev = await db.put_design(
            DDOC_ID,
            rev=rev,
            views={VIEW_ID: {"map": DOCUMENT_VIEW}},
        )
        self.assertIsInstance(_id, str)
        self.assertTrue(ok)
        self.assertIsInstance(_rev, str)

    async def test_save(self):
        doc = {"_id": "test-async-save", "name": "hello async"}
        _id, ok, _rev = await self.db.save(doc)
        self.assertEqual(_id, doc["_id"])
        self.assertTrue(ok)
        self.assertIsInstance(_rev, str)
        # Update
        doc["_rev"] = _rev
        doc["name"] = "updated async"
        _id2, ok2, _rev2 = await self.db.save(doc)
        self.assertEqual(_id2, _id)
        self.assertTrue(ok2)
        self.assertNotEqual(_rev2, _rev)

    async def test_save_index(self):
        result, _id, name = await self.db.save_index(
            index={"fields": ["name"]},
            name="async-name-idx",
            index_type="json",
        )
        self.assertIn(result, ["created", "exists"])
        self.assertIsInstance(_id, str)
        self.assertIsInstance(name, str)

    async def test_security(self):
        from couchdb3.document import SecurityDocument

        sec = await self.db.security()
        self.assertIsInstance(sec, SecurityDocument)

    async def test_view(self):
        docid = "test-async-view-doc"
        db = await self.server.get(DB_NAME)
        if not await db.rev(f"_design/{DDOC_ID}"):
            await db.put_design(DDOC_ID, views={VIEW_ID: {"map": DOCUMENT_VIEW}})
        if not await db.rev(docid):
            await db.save({"_id": docid, "type": "document"})
        result = await db.view(DDOC_ID, VIEW_ID)
        self.assertIsInstance(result, ViewResult)


class TestAsyncPartition(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = AsyncServer(url=COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD)
        all_dbs = await self.server.all_dbs()
        if DB_NAME_PARTITIONED not in all_dbs:
            await self.server.create(DB_NAME_PARTITIONED, partitioned=True)
        self.db = await self.server.get(DB_NAME_PARTITIONED)
        self.partition = await self.db.get_partition(P_ID)

    async def asyncTearDown(self):
        await self.server.aclose()

    async def test_partition_info(self):
        info = await self.partition.info()
        self.assertIsInstance(info, dict)

    async def test_partition_save_get(self):
        docid = "test-async-partition-doc"
        await self.partition.save({"_id": docid, "type": "partition-test"})
        doc = await self.partition.get(docid)
        self.assertIsInstance(doc, Document)
        self.assertIn(P_ID, doc.id)

    async def test_partition_all_docs(self):
        result = await self.partition.all_docs()
        self.assertIsInstance(result, ViewResult)

    async def test_partition_find(self):
        result = await self.partition.find({"type": {"$eq": "partition-test"}})
        self.assertIn("docs", result)

    async def test_partition_type(self):
        self.assertIsInstance(self.partition, AsyncPartition)


class TestAsyncDatabaseChanges(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = AsyncServer(url=COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD)
        all_dbs = await self.server.all_dbs()
        if DB_NAME in all_dbs:
            self.db = await self.server.get(DB_NAME)
        else:
            self.db = await self.server.create(DB_NAME)

    async def asyncTearDown(self):
        await self.server.aclose()

    async def test_changes_normal(self):
        docs = [
            {"_id": f"test-async-changes-doc-{i}", "type": "async-changes-test"} for i in range(3)
        ]
        await self.db.bulk_docs(docs=docs)
        result = await self.db.changes()
        self.assertIsInstance(result, dict)
        self.assertIn("results", result)
        self.assertIn("last_seq", result)
        self.assertIsInstance(result["results"], list)

    async def test_changes_since(self):
        before = await self.db.changes(since="now")
        last_seq = before["last_seq"]
        new_doc = {"_id": "test-async-changes-since-doc", "type": "async-changes-since"}
        await self.db.create(new_doc)
        result = await self.db.changes(since=last_seq)
        ids = [r["id"] for r in result["results"]]
        self.assertIn("test-async-changes-since-doc", ids)

    async def test_changes_doc_ids(self):
        target_id = "test-async-changes-doc-ids-doc"
        await self.db.create({"_id": target_id, "type": "async-changes-doc-ids"})
        result = await self.db.changes(doc_ids=[target_id])
        self.assertIsInstance(result, dict)
        self.assertIn("results", result)
        ids = [r["id"] for r in result["results"]]
        self.assertIn(target_id, ids)

    async def test_changes_include_docs(self):
        doc_id = "test-async-changes-include-docs-doc"
        if not await self.db.get(doc_id):
            await self.db.create({"_id": doc_id, "type": "async-changes-include-docs"})
        result = await self.db.changes(doc_ids=[doc_id], include_docs=True)
        self.assertIsInstance(result, dict)
        for row in result["results"]:
            if row["id"] == doc_id:
                self.assertIn("doc", row)
                break
        else:
            self.fail(f"Doc '{doc_id}' not found in changes results")

    async def test_changes_selector(self):
        await self.db.create(
            {"_id": "test-async-changes-selector-doc", "type": "async-changes-selector-unique"}
        )
        result = await self.db.changes(selector={"type": {"$eq": "async-changes-selector-unique"}})
        self.assertIsInstance(result, dict)
        self.assertIn("results", result)

    async def test_changes_invalid_feed_raises(self):
        with self.assertRaises(ValueError):
            await self.db.changes(feed="continuous")
        with self.assertRaises(ValueError):
            await self.db.changes(feed="eventsource")

    async def test_changes_mutual_exclusion_raises(self):
        from couchdb3.exceptions import CouchDBError

        with self.assertRaises(CouchDBError):
            await self.db.changes(doc_ids=["a"], selector={"type": "x"})


class TestAsyncDatabaseServerRef(unittest.IsolatedAsyncioTestCase):
    """Tests for the db.server and partition.database back-references (Option C lifetime fix)."""

    async def asyncSetUp(self):
        self.server = AsyncServer(url=COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD)
        all_dbs = await self.server.all_dbs()
        if DB_NAME in all_dbs:
            self.db = await self.server.get(DB_NAME)
        else:
            self.db = await self.server.create(DB_NAME)
        if DB_NAME_PARTITIONED in all_dbs:
            self.db_partitioned = await self.server.get(DB_NAME_PARTITIONED)
        else:
            self.db_partitioned = await self.server.create(DB_NAME_PARTITIONED, partitioned=True)

    async def asyncTearDown(self):
        await self.server.aclose()

    async def test_db_server_is_set(self):
        self.assertIs(self.db.server, self.server)

    async def test_db_server_is_none_when_standalone(self):
        from couchdb3.aio import AsyncDatabase

        db = AsyncDatabase(
            name=DB_NAME, url=COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD
        )
        self.assertIsNone(db.server)
        await db.aclose()

    async def test_db_server_is_readonly(self):
        with self.assertRaises(AttributeError):
            self.db.server = None

    async def test_partition_database_is_set(self):
        partition = await self.db_partitioned.get_partition(P_ID)
        self.assertIs(partition.database, self.db_partitioned)

    async def test_partition_database_is_none_when_standalone(self):
        from couchdb3.aio import AsyncPartition

        p = AsyncPartition(
            partition_id=P_ID,
            name=DB_NAME_PARTITIONED,
            url=COUCHDB0_URL,
            user=COUCHDB_USER,
            password=COUCHDB_PASSWORD,
        )
        self.assertIsNone(p.database)
        await p.aclose()

    async def test_partition_database_is_readonly(self):
        partition = await self.db_partitioned.get_partition(P_ID)
        with self.assertRaises(AttributeError):
            partition.database = None

    async def test_one_liner_does_not_raise(self):
        # The original bug: temporary AsyncServer GC'd before chained await executes.
        # db.server holds a strong ref, keeping the AsyncServer (and its httpx.AsyncClient) alive.
        async with AsyncServer(
            url=COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD
        ) as server:
            db = await server.get(DB_NAME)
            result = await db.changes(limit=1)
            self.assertIn("results", result)


@atexit.register
def rm_test_dbs() -> None:
    """Remove temporary async database test DBs using the sync client."""
    for dbname in [DB_NAME, DB_NAME_PARTITIONED]:
        if dbname in _SYNC_CLIENT:
            _SYNC_CLIENT.delete(dbname)


if __name__ == "__main__":
    unittest.main()
