#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from pathlib import Path
import requests
from typing import Dict, Optional

from couchdb3.exceptions import CouchDBError
from couchdb3.utils import check_response, DEFAULT_TIMEOUT


__all__ = [
    "ATTACHMENT_PATH_HTML",
    "ATTACHMENT_PATH_JSON",
    "ATTACHMENT_PATH_PDF",
    "ATTACHMENT_PATH_PNG",
    "ATTACHMENT_PATH_TXT",
    "ATTACHMENT_PATH_ZIP",
    "COUCHDB_USER",
    "COUCHDB_PASSWORD",
    "COUCHDB0_URL",
    "COUCHDB1_URL",
    "DOCUMENT_VIEW",
    "check_alive"
]


DEFAULT_URL: str = "http://127.0.0.1:5984"


def check_alive(url: str = DEFAULT_URL) -> bool:
    try:
        check_response(requests.get(url, timeout=DEFAULT_TIMEOUT))
        return True
    except (CouchDBError, requests.exceptions.ConnectionError):
        return False


proj_path: str = Path(os.path.dirname(os.path.abspath(__file__))).parent.as_posix()
env_file_path: str = f"{proj_path}/.env"
env_file: Dict
if os.path.isfile(env_file_path):
    with open(env_file_path, "r", encoding="utf-8") as _:
        env_file = {k: v for k, v in map(lambda _: _.strip().split("="), _.readlines())}
else:
    env_file = {}


ATTACHMENT_PATH_HTML: str = f"{proj_path}/tests/attachments/test.html"
ATTACHMENT_PATH_JSON: str = f"{proj_path}/tests/attachments/test.json"
ATTACHMENT_PATH_PNG: str = f"{proj_path}/tests/attachments/test.png"
ATTACHMENT_PATH_TXT: str = f"{proj_path}/tests/attachments/test.txt"
ATTACHMENT_PATH_ZIP: str = f"{proj_path}/tests/attachments/test.zip"
ATTACHMENT_PATH_PDF: str = f"{proj_path}/tests/attachments/test.pdf"


with open(f"{proj_path}/tests/views/document-view.js", "r", encoding="utf-8") as _:
    DOCUMENT_VIEW: str = _.read()


def load_env_var(name: str) -> Optional[str]:
    """
    Load an environment variable.
    Parameters
    ----------
    name : str
        The variable's name.

    Returns
    -------
    Optional[str]
    """
    return os.environ.get(name, env_file.get(name))


COUCHDB_USER: str = load_env_var("COUCHDB_USER") or input("CouchDB username:\n")
COUCHDB_PASSWORD: str = load_env_var("COUCHDB_PASSWORD") or input("CouchDB password:\n")
COUCHDB0_URL: str = DEFAULT_URL if check_alive() else (
        load_env_var("COUCHDB_URL") or load_env_var("COUCHDB0_URL") or input("Please provide a valid CouchDB URL:\n")
)
COUCHDB1_URL: Optional[str] = load_env_var("COUCHDB1_URL") or None
