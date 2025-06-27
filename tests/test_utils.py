#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from urllib import parse

from couchdb3 import utils


class TestUtils(unittest.TestCase):
    def test_build_url(self):
        url0 = "http://127.0.0.1:5984/test/_all_docs?descending=true&skip=10&keys=[\"hello\",\"world\"]"
        url1 = utils.build_url(
            scheme="http",
            host="127.0.0.1",
            port=5984,
            path="test/_all_docs",
            descending=True,
            skip=10,
            keys=["hello", "world"]
        ).url
        self.assertEqual(url0, parse.unquote(url1))

    def test_rm_nones_from_dict(self):
        none_key = 'null'
        data = {
            'hello': 'world',
            'abc': 123,
            'empty string': '',
            none_key: None,
        }
        new_data = utils.rm_nones_from_dict(data)
        self.assertIsInstance(new_data, dict)
        self.assertNotIn(none_key, new_data)

    def test_extract_url_data(self):
        scheme = "http"
        user = "user"
        password = "ABCdef123!"
        host = "127.0.0.1"
        port = 5984
        path = "some-db/some-doc"
        url = f"{scheme}://{user}:{password}@{host}:{port}/{path}"
        data = utils.extract_url_data(url)
        self.assertEqual(scheme, data["scheme"])
        self.assertEqual(user, data["user"])
        self.assertEqual(password, data["password"])
        self.assertEqual(host, data["host"])
        self.assertEqual(port, data["port"])
        self.assertEqual(path, data["path"].lstrip("/"))


if __name__ == '__main__':
    unittest.main()
