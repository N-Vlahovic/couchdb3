#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Dict, List, Optional, Union

from .base import DictBase


__all__ = [
    "extract_document_id_and_rev",
    "Document",
    "SecurityDocumentElement",
    "SecurityDocument"
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


class SecurityDocumentElement(DictBase):
    """CouchDB Security Document Element (representing either `"admins"` or `"members"`) - a wrapper around Python 
    dictionaries."""

    def add_name(self, name: str) -> None:
        self.names = sorted(set(self.names).union({name}))

    def add_role(self, role: str) -> None:
        self.roles = sorted(set(self.roles).union({role}))

    @property
    def names(self) -> List[str]:
        """
        Returns
        -------
        List[str] : The document's names.
        """
        return self.get("names", [])

    @names.setter
    def names(self, value) -> None:
        self.update({
            "names": value
        })
    
    @property
    def roles(self) -> List[str]:
        """
        Returns
        -------
        List[str] : The document's roles.
        """
        return self.get("roles", [])

    @roles.setter
    def roles(self, value) -> None:
        self.update({
            "roles": value
        })


class SecurityDocument(DictBase):
    """CouchDB Security Document - a wrapper around Python dictionaries."""
    
    def __init__(
            self,
            *args,
            **kwargs
    ) -> None:
        super(SecurityDocument, self).__init__(*args, **kwargs)
        self.admins = SecurityDocumentElement(**self.get("admins", {}))
        self.members = SecurityDocumentElement(**self.get("members", {}))
    
    @property
    def admins(self) -> SecurityDocumentElement:
        """
        Returns
        -------
        SecurityDocument : The document's admins.
        """
        return self.get("admins", SecurityDocument())
    
    @admins.setter
    def admins(self, value: SecurityDocumentElement) -> None:
        self.update({
            "admins": value
        })

    @property
    def members(self) -> SecurityDocumentElement:
        """
        Returns
        -------
        SecurityDocument : The document's members.
        """
        return self.get("members", SecurityDocument())

    @members.setter
    def members(self, value: SecurityDocumentElement) -> None:
        self.update({
            "members": value
        })

    