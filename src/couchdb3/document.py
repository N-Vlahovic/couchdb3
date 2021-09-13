#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Dict, Optional, Union

from .base import DictBase


__all__ = [
    "extract_document_id_and_rev",
    "Document"
]


def extract_document_id_and_rev(
        doc: Union[Dict, Document],
        rev: bool = True
) -> Dict:
    """
    Extract id and revision from an abstract document.

    Parameters
    ----------
    doc : Union[Dict, Document]
    rev : bool
        Include documents revision.

    Returns
    -------
    Dict : A dictionary containing the (optional) keys `id` and `rev`.
    """
    res = {}
    i = doc.get("_id", doc.get("id"))
    r = doc.get("_rev", doc.get("rev"))
    if i:
        res.update({
            "id": i
        })
    if r and rev is True:
        res.update({
            "rev": r
        })
    return res


class Document(DictBase):
    """CouchDB Document - a wrapper around Python dictionaries."""

    @property
    def id(self) -> Optional[str]:
        """
        Returns
        -------
        str : The document's id.
        """
        return self.get("_id")

    @property
    def rev(self) -> Optional[str]:
        """
        Returns
        -------
        str : The document's revision.
        """
        return self.get("_rev")
