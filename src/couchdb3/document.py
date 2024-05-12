#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Dict, List, Optional, Union

from .base import DictBase


__all__ = [
    "extract_document_id_and_rev",
    "Document",
    "AttachmentDocument",
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

    @id.setter
    def id(self, value: str) -> None:
        self.update({"_id": value})

    @property
    def rev(self) -> Optional[str]:
        """
        Returns
        -------
        str : The document's revision.
        """
        return self.get("_rev")

    @rev.setter
    def rev(self, value: str) -> None:
        self.update({"_rev": value})


class AttachmentDocument(DictBase):
    """CouchDB Attachment Document - a wrapper around Python dictionaries."""

    def __init__(
            self,
            *args,
            **kwargs
    ) -> None:
        super(AttachmentDocument, self).__init__(*args, **kwargs)
        self.content = self.get("content")
        self.content_encoding = self.get("content_encoding")
        self.content_length = self.get("content_length")
        self.content_type = self.get("content_type")
        self.digest = self.get("digest")

    @property
    def content(self) -> bytes:
        """
        Returns
        -------
        bytes : The attachment's content.
        """
        return self.get("content")

    @content.setter
    def content(self, value: bytes) -> None:
        self.update({
            "content": value
        })

    @property
    def content_encoding(self) -> str:
        """
        Returns
        -------
        str : The attachment's content encoding.
        """
        return self.get("content_encoding")

    @content_encoding.setter
    def content_encoding(self, value: str) -> None:
        self.update({
            "content_encoding": value
        })

    @property
    def content_length(self) -> int:
        """
        Returns
        -------
        int : The attachment's content length.
        """
        return self.get("content_length")

    @content_length.setter
    def content_length(self, value: int) -> None:
        self.update({
            "content_length": int(value)
        })

    @property
    def content_type(self) -> str:
        """
        Returns
        -------
        str : The attachment's content type.
        """
        return self.get("content_type")

    @content_type.setter
    def content_type(self, value: str) -> None:
        self.update({
            "content_type": value
        })

    @property
    def digest(self) -> str:
        """
        Returns
        -------
        str : The attachment's content digest.
        """
        return self.get("digest")

    @digest.setter
    def digest(self, value: str) -> None:
        self.update({
            "digest": value
        })


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

    