#!/usr/bin/env python3

import atexit
import unittest

from couchdb3.document import Document
from couchdb3.sync import Database, Partition, Server
from couchdb3.view import ViewResult
from tests.credentials import (
    COUCHDB0_URL,
    COUCHDB_PASSWORD,
    COUCHDB_USER,
    DOCUMENT_VIEW,
)

CLIENT: Server = Server(COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD)
DB_NAME: str = "tmp-test-partitioned-db"
DB: Database = (
    CLIENT.get(DB_NAME) if DB_NAME in CLIENT else CLIENT.create(DB_NAME, partitioned=True)
)

PARTITION_ID: str = "partition-test"
DDOC_ID: str = "partition-design"


class TestPartitionedDatabase(unittest.TestCase):
    def test_create(self):
        for i in range(2):
            docid = f"partition-{i}:test-doc-id"
            doc = {"name": "Hello", "type": "document", "_id": docid}
            _id, success, _rev = DB.create(doc)
            self.assertIsInstance(_id, str)
            self.assertIsInstance(success, bool)
            self.assertIsInstance(_rev, str)
            self.assertEqual(_id, docid)

    def test_put_design(self):
        for ddoc, partitioned in [
            ("document-design-unpartitioned", False),
            ("document-design-partitioned", True),
        ]:
            _id, ok, _rev = DB.put_design(
                ddoc=ddoc,
                rev=DB.rev(f"_design/{ddoc}"),
                views={"document-view": {"map": DOCUMENT_VIEW}},
                options={"partitioned": partitioned},
            )
            self.assertEqual(_id, f"_design/{ddoc}")
            self.assertEqual(ok, True)
            self.assertIsInstance(_rev, str)

    def test_put_design_partitioned_flag_persists(self):
        ddoc = "document-design-flag"
        DB.put_design(
            ddoc=ddoc,
            rev=DB.rev(f"_design/{ddoc}"),
            views={"document-view": {"map": DOCUMENT_VIEW}},
            partitioned=True,
        )
        saved = DB.get(f"_design/{ddoc}")
        self.assertIsInstance(saved, Document)
        self.assertEqual(saved["options"]["partitioned"], True)


class TestPartition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.partition: Partition = DB.get_partition(PARTITION_ID)

    def test_type(self):
        self.assertIsInstance(self.partition, Partition)

    def test_save_and_get(self):
        docid = "partition-save-doc"
        _id, ok, _rev = self.partition.save(
            {"_id": docid, "type": "document", "name": "partition-save"}
        )
        self.assertEqual(_id, f"{PARTITION_ID}:{docid}")
        self.assertTrue(ok)
        self.assertIsInstance(_rev, str)

        doc = self.partition.get(docid)
        self.assertIsInstance(doc, Document)
        self.assertIn(PARTITION_ID, doc.id)

    def test_get_returns_none_for_missing(self):
        self.assertIsNone(self.partition.get("partition-missing-doc"))

    def test_rev(self):
        docid = "partition-rev-doc"
        self.partition.save({"_id": docid, "type": "document"})
        rev = self.partition.rev(docid)
        self.assertIsInstance(rev, str)
        self.assertTrue(rev.startswith("1-"))

    def test_contains(self):
        docid = "partition-contains-doc"
        self.partition.save({"_id": docid, "type": "document"})
        self.assertIn(docid, self.partition)
        self.assertNotIn("partition-missing-doc", self.partition)

    def test_delete(self):
        docid = "partition-delete-doc"
        self.partition.save({"_id": docid, "type": "document"})
        self.assertTrue(self.partition.delete(docid=docid, rev=self.partition.rev(docid)))
        self.assertNotIn(docid, self.partition)

    def test_all_docs(self):
        for i in range(3):
            self.partition.save({"_id": f"partition-all-docs-{i}", "type": "document"})
        result = self.partition.all_docs()
        self.assertIsInstance(result, ViewResult)
        ids = [row.id for row in result.rows]
        for i in range(3):
            self.assertIn(f"{PARTITION_ID}:partition-all-docs-{i}", ids)

    def test_bulk_docs_and_bulk_get(self):
        docs = [{"_id": f"partition-bulk-{i}", "type": "document"} for i in range(3)]
        original_ids = [doc["_id"] for doc in docs]
        results = self.partition.bulk_docs(docs)
        self.assertEqual(len(results), 3)
        for orig_id, res in zip(original_ids, results):
            self.assertEqual(f"{PARTITION_ID}:{orig_id}", res["id"])
            self.assertTrue(res["ok"])

        fetched = self.partition.bulk_get(docs=[{"id": _id} for _id in original_ids])
        self.assertEqual(len(fetched), 3)
        for item in fetched:
            self.assertIn("id", item)
            self.assertIn("docs", item)
            self.assertIn("ok", item["docs"][0])

    def test_find(self):
        self.partition.save({"_id": "partition-find-doc", "type": "partition-find"})
        result = self.partition.find({"type": {"$eq": "partition-find"}})
        self.assertIn("docs", result)
        self.assertIsInstance(result["docs"], list)

    def test_info(self):
        info = self.partition.info()
        self.assertIsInstance(info, dict)

    def test_view(self):
        ddoc = DDOC_ID
        DB.put_design(
            ddoc=ddoc,
            rev=DB.rev(f"_design/{ddoc}"),
            views={"document-view": {"map": DOCUMENT_VIEW}},
            partitioned=True,
        )
        self.partition.save({"_id": "partition-view-doc", "type": "document"})
        result = self.partition.view(ddoc, "document-view")
        self.assertIsInstance(result, ViewResult)
        ids = [row.id for row in result.rows]
        self.assertIn(f"{PARTITION_ID}:partition-view-doc", ids)


@atexit.register
def rm_test_db() -> None:
    """
    Removing temporary test database.
    """
    CLIENT.delete(DB_NAME)


if __name__ == "__main__":
    unittest.main()
