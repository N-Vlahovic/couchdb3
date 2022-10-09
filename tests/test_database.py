#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import atexit
import datetime
import random
import string

import unittest

from couchdb3.database import Database, Partition
from couchdb3.document import Document, AttachmentDocument
from couchdb3.server import Server
from couchdb3.view import ViewResult, ViewRow
from couchdb3.utils import user_name_to_id

from tests.credentials import ATTACHMENT_PATH_HTML, ATTACHMENT_PATH_JSON, ATTACHMENT_PATH_PNG, ATTACHMENT_PATH_TXT, \
    ATTACHMENT_PATH_ZIP, COUCHDB_USER, COUCHDB_PASSWORD, COUCHDB0_URL, DOCUMENT_VIEW


def get_or_create_db(db_name: str, client: Server, partitioned: bool = False) -> Database:
    return client.get(db_name) if db_name in client else client.create(db_name, partitioned=partitioned)


CLIENT: Server = Server(COUCHDB0_URL, user=COUCHDB_USER, password=COUCHDB_PASSWORD)
DB_NAME: str = "test-" + "".join(random.choices(string.ascii_lowercase, k=5))
DB_NAME_PARTITIONED: str = f"{DB_NAME}-partitioned"
DB: Database = get_or_create_db(DB_NAME, CLIENT)
DB_PARTITIONED: Database = get_or_create_db(DB_NAME_PARTITIONED, CLIENT, True)

DDOC_ID: str = "document-design"
P_ID: str = "p0"
VIEW_ID: str = "document-view"


class TestDatabase(unittest.TestCase):
    def test_all_docs(self):
        docs = [{
            "_id": f"test-all-docs-doc-{_}",
            "name": f"Document {_}",
        } for _ in range(10)]
        DB.bulk_docs(docs=docs)
        result = DB.all_docs(keys=[_["_id"] for _ in docs][:5])
        self.assertIsInstance(result, ViewResult)
        self.assertListEqual(
            [_["_id"] for _ in docs][:5],
            [_.id for _ in result.rows]
        )
        result = DB.all_docs(
            keys=map(lambda _: _["_id"], docs),
            include_docs=True
        )
        for _ in result.rows:
            self.assertIsInstance(_, ViewRow)
            self.assertTrue(_.doc)

    def test___contains__(self):
        _id = "test-doc-__contains__"
        doc = {
            "type": "test-doc-__contains__",
            "_id": _id
        }
        DB.create(doc)
        self.assertIn(_id, DB)

    def test_bulk_docs(self):
        docs = [{
            "_id": f"doc-{_}",
            "name": f"Document {_}",
        } for _ in range(10)]
        results = DB.bulk_docs(docs=docs)
        for doc, res in zip(docs, results):
            self.assertEqual(doc["_id"], res["id"])
            self.assertIsInstance(res["rev"], str)
            self.assertIsInstance(res["ok"], bool)

    def test_bulk_get(self):
        docs = [{
            "_id": f"doc-{_}",
            "name": f"Document {_}",
        } for _ in range(10)]
        DB.bulk_docs(docs=docs)
        results = DB.bulk_get(docs=[{"id": _["_id"]} for _ in docs])
        for doc, res in zip(docs, results):
            self.assertEqual(doc["_id"], res["id"])
            for _ in res["docs"]:
                self.assertIsInstance(_["ok"], dict)

    def test_compact(self):
        DB.compact()
        self.assertTrue(DB.info().get("compact_running"))

    def test_copy(self):
        docid = "doc-id-test-copy"
        doc = {
            "_id": docid,
            "name": "Test Copy"
        }
        destid = f"{docid}-copy"
        DB.save(doc=doc)
        _id, ok, _rev = DB.copy(docid=docid, destid=destid)
        self.assertTrue(ok)
        self.assertEqual(_id, destid)

    def test_create(self):
        doc0 = {
            "name": "Hello",
            "type": "test-doc"
        }
        doc1 = doc0 | {"_id": "test-doc-id"}
        for _ in (doc0, doc1):
            _id, success, _rev = DB.create(_)
            self.assertIsInstance(_id, str)
            self.assertIsInstance(success, bool)
            self.assertIsInstance(_rev, str)
            if _.get("_id"):
                self.assertEqual(_id, _.get("_id"))

    def test_delete(self):
        doc = {
            "type": "test-doc-delete",
            "_id": "test-doc-delete"
        }
        DB.create(doc)
        result = DB.delete(
            docid=doc.get("_id"),
            rev=DB.rev(doc.get("_id"))
        )
        self.assertEqual(result, True)

    def test_explain(self):
        DB.save_index(
            index={
                "fields": ["year"]
            },
            name="my-index"
        )
        docs = [{
            "_id": f"explain-doc-{title.lower()}",
            "year": year,
            "title": title,
        } for title, year in zip(
            ("Inception", "The Dark Knight", "Fight Club"),
            (2010, 2008, 1999)
        )]
        DB.bulk_docs(docs=docs)
        fields = ["_id", "_rev", "year", "title"]
        limit = 2
        skip = 0
        result = DB.explain(
            selector={
                "year": {
                    "$lt": 2010
                }
            },
            limit=limit,
            skip=skip,
            fields=fields,
            sort=[{"year": "asc"}]
        )
        self.assertEqual(
            DB.name,
            result.get("dbname")
        )
        self.assertEqual(
            fields,
            result.get("fields")
        )
        self.assertEqual(
            limit,
            result.get("limit")
        )
        self.assertEqual(
            skip,
            result.get("skip")
        )

    def test_find(self):
        now = datetime.datetime.now()
        DB.save_index(
            index={
                "fields": ["date", "_id"]
            },
            name="my-index"
        )
        docs = [{
            "_id": f"find-doc-{_}",
            "date": int((now + datetime.timedelta(days=_)).timestamp()),
            "name": f"Find Document {_}",
        } for _ in range(10)]
        DB.bulk_docs(docs=docs)
        result = DB.find(
            selector={
                "_id": {
                    "$regex": "^find-.*"
                },
                "date": {
                    "$gt": int((now + datetime.timedelta(days=1)).timestamp())
                }
            },
            limit=1,
            fields=["name", "date"],
            sort=[{"date": "asc"}, {"_id": "asc"}]
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(
            result["docs"][0]["date"],
            int((now + datetime.timedelta(days=2)).timestamp())
        )

    def test_indexes(self):
        result = DB.indexes()
        self.assertIsInstance(result["total_rows"], int)
        self.assertIsInstance(result["indexes"], list)

    def test_get(self):
        docid = "test-doc-get"
        doc = {
            "type": "test-doc-get",
            "_id": docid
        }
        self.assertIs(DB.get(docid), None)
        DB.create(doc)
        dbdoc = DB[docid]
        self.assertIsInstance(dbdoc, Document)
        for key in doc:
            self.assertEqual(doc[key], dbdoc[key])

    def test_delete_attachment(self):
        docid = "test-doc-delete-attachment"
        DB.save({"_id": docid})
        for attname, content in [
            ("test-dict", {"hello": "world", 1: 2, 3: None}),
            ("test-str", "Hello World! 123"),
            ("test-list", ["Hello", "World", 1, 2, 3])
        ]:
            result = DB.put_attachment(
                docid=docid,
                attname=attname,
                content=content,
                rev=DB.rev(docid)
            )
            self.assertTrue(DB.delete_attachment(
                docid=docid,
                attname=attname,
                rev=result[2]
            ))

    def test_get_attachment(self):
        docid = "test-doc-get-attachment"
        DB.save({"_id": docid})
        for attname, path in [
            ("test.html", ATTACHMENT_PATH_HTML),
            ("test.json", ATTACHMENT_PATH_JSON),
            ("test.png", ATTACHMENT_PATH_PNG),
            ("test.txt", ATTACHMENT_PATH_TXT),
            ("test.zip", ATTACHMENT_PATH_ZIP),
        ]:
            DB.put_attachment(
                docid=docid,
                attname=attname,
                path=path,
                rev=DB.rev(docid)
            )
            response = DB.get_attachment(
                docid=docid,
                attname=attname
            )
            self.assertIsInstance(response, AttachmentDocument)
            self.assertIsInstance(response.content, bytes)
            self.assertIsInstance(response.content_length, int)
            self.assertIsInstance(response.digest, str)

    def test_put_design(self):
        for partitioned, db in [
            (False, DB),
            (True, DB_PARTITIONED),
        ]:
            ddoc = DDOC_ID
            _id, ok, _rev = db.put_design(
                ddoc=ddoc,
                rev=db.rev(f"_design/{ddoc}"),
                views={
                    VIEW_ID: {
                        "map": DOCUMENT_VIEW
                    }
                },
                partitioned=partitioned
            )
            self.assertEqual(_id, f"_design/{ddoc}")
            self.assertEqual(ok, True)
            self.assertIsInstance(_rev, str)

    def test_get_design(self):
        for partitioned, db in [
            (None, DB),
            (True, DB_PARTITIONED),
        ]:
            _id = f"_design/{DDOC_ID}"
            if _id not in db:
                db.put_design(
                    ddoc=DDOC_ID,
                    rev=db.rev(_id),
                    views={
                        VIEW_ID: {
                            "map": DOCUMENT_VIEW
                        }
                    },
                    partitioned=partitioned
                )
            result = DB.get_design(ddoc=DDOC_ID)
            self.assertIsInstance(result, Document)

    def test_put_attachment(self):
        docid = "test-doc-put-attachment"
        DB.save({"_id": docid})
        for attname, path in [
            ("test.html", ATTACHMENT_PATH_HTML),
            ("test.json", ATTACHMENT_PATH_JSON),
            ("test.png", ATTACHMENT_PATH_PNG),
            ("test.txt", ATTACHMENT_PATH_TXT),
            ("test.zip", ATTACHMENT_PATH_ZIP),
        ]:
            results = DB.put_attachment(
                docid=docid,
                attname=attname,
                path=path,
                rev=DB.rev(docid)
            )
            self.assertEqual(results[0], docid)
            self.assertEqual(results[1], True)
            self.assertEqual(results[2], DB.rev(docid))

    def test_save(self):
        doc0 = {
            "type": "test-doc-save",
            "_id": "test-doc-save"
        }
        _id, success, _rev = DB.save(doc0)
        self.assertIsInstance(_id, str)
        self.assertIsInstance(success, bool)
        self.assertIsInstance(_rev, str)

    def test_save_index(self):
        res, _id, name = DB.save_index(
            index={
                "partial_filter_selector": {
                    "year": {
                        "$gt": 2010
                    },
                    "limit": 10,
                    "skip": 0
                },
                "fields": [
                    "_id",
                    "_rev",
                    "year",
                    "title"
                ]
            },
            ddoc="example-ddoc",
            name="foo-index",
            index_type="json"
        )
        self.assertTrue(res in {"created", "exists"})
        self.assertEqual(_id, "_design/example-ddoc")
        self.assertEqual(name, "foo-index")

    def test_security(self):
        read_user = "reader-0"
        read_password = "read_password"
        ok, user_id, user_rev = CLIENT.save_user(
            name=read_user,
            password=read_password,
            roles=["reader"],
        )
        self.assertTrue(ok)
        self.assertEqual(user_id, user_name_to_id(read_user))
        self.assertIsInstance(user_rev, str)
        sec = DB.security()
        sec.members.add_name(read_user)
        sec.members.add_role("reader")
        res = DB.update_security(
            admins=sec.admins,
            members=sec.members
        )
        self.assertTrue(res)
        self.assertIsInstance(
            Server(COUCHDB0_URL, user=read_user, password=read_password)[DB.name],
            Database
        )

    def test_view(self):
        for partitioned, db in [
            (None, DB),
            (True, DB_PARTITIONED),
        ]:
            docid = (f"{P_ID}:" if partitioned else "") + "doc-test-view"
            if docid not in db:
                db.save({
                    "type": "document",
                    "name": "",
                    "_id": docid
                })
            _id = f"_design/{DDOC_ID}"
            if _id not in db:
                db.put_design(
                    ddoc=DDOC_ID,
                    rev=db.rev(_id),
                    views={
                        VIEW_ID: {
                            "map": DOCUMENT_VIEW
                        }
                    },
                    partitioned=partitioned,
                )
            result = db.view(
                ddoc=DDOC_ID,
                view=VIEW_ID,
                limit=1,
                partition=P_ID if partitioned else None,
            )
            self.assertEqual(result.rows[0].id, docid)

    def test_partition(self):
        self.assertTrue(DB_PARTITIONED.info()["props"]["partitioned"])
        partition = DB_PARTITIONED.get_partition("p0")
        self.assertIsInstance(partition, Partition)


@atexit.register
def rm_test_db() -> None:
    """
    Removing temporary test database.
    """
    for db_name in (DB_NAME, DB_NAME_PARTITIONED):
        if db_name in CLIENT:
            CLIENT.delete(db_name)


if __name__ == '__main__':
    unittest.main()
