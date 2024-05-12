#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional, Union, Dict, Any, List

from .base import DictBase
from .document import Document


class ViewRow(DictBase):
    """
    View row object.
    """
    def __init__(self, *args, **kwargs) -> None:
        super(ViewRow, self).__init__(*args, **kwargs)
        self.doc = self.get("doc", None)
        self.id = self.get("id", None)
        self.key = self.get("key", None)
        self.value = self.get("value", None)

    @property
    def doc(self) -> Optional[Document]:
        """
        Returns
        -------
        Optional[Document] : The row's document.
        """
        return self._doc

    @doc.setter
    def doc(self, value: Union[Dict, Document]) -> None:
        self._doc = Document(**value) if value else None

    @property
    def id(self) -> str:
        """
        Returns
        -------
        str : The corresponding document's id.
        """
        return self._id

    @id.setter
    def id(self, value: str) -> None:
        self._id = value

    @property
    def key(self) -> str:
        """
        Returns
        -------
        str : The row's key.
        """
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        self._key = value

    @property
    def value(self) -> Optional[Any]:
        """
        Returns
        -------
        Optional[Any] : The row's value.
        """
        return self._value

    @value.setter
    def value(self, value: Any) -> None:
        self._value = value


class ViewResult(DictBase):
    """
    View result object.
    """
    def __init__(self, *args, **kwargs) -> None:
        super(ViewResult, self).__init__(*args, **kwargs)
        self.offset = self.get("offset", 0)
        self.rows = self.get("rows", [])
        self.total_rows = self.get("total_rows", 0)

    @property
    def offset(self) -> int:
        """
        Returns
        -------
        int : The view's offset.
        """
        return self._offset

    @offset.setter
    def offset(self, value: int) -> None:
        self._offset = value

    @property
    def rows(self) -> List[ViewRow]:
        """
        Returns
        -------
        List[couchdb3.database.ViewRow] : The view's rows.
        """
        return self._rows

    @rows.setter
    def rows(self, value: List[ViewRow]) -> None:
        self._rows = [ViewRow(**_) for _ in value]

    @property
    def total_rows(self) -> int:
        """
        Returns
        -------
        int : The view's total number of rows.
        """
        return self._total_rows

    @total_rows.setter
    def total_rows(self, value: int) -> None:
        self._total_rows = value