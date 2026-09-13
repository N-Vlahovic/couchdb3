#!/usr/bin/env python3
from __future__ import annotations

import mimetypes
from collections.abc import Iterable
from typing import Any

import httpx

from ..document import (
    AttachmentDocument,
    Document,
    SecurityDocument,
    SecurityDocumentElement,
    extract_document_id_and_rev,
)
from ..exceptions import CouchDBError, NameComplianceError
from ..utils import (
    DEFAULT_TIMEOUT,
    partitioned_db_resource_parser,
    rm_nones_from_dict,
    validate_db_name,
)
from ..view import ViewResult
from .async_base import AsyncBase

__all__ = [
    "AsyncDatabase",
    "AsyncPartition",
]


class AsyncDatabase(AsyncBase):
    """
    Async CouchDB database client. Mirrors `Database` with `async def` methods throughout.

    Note: `__getitem__` is not supported on async classes — Python does not allow
    `__getitem__` to be a coroutine. Use `await db.get(docid)` instead.
    """

    def __init__(
        self,
        name: str,
        *,
        url: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        disable_ssl_verification: bool = False,
        auth_method: str | None = None,
        timeout: int | None = DEFAULT_TIMEOUT,
        session: httpx.AsyncClient | None = None,
        _server: Any = None,
    ) -> None:
        """

        Parameters
        ----------
        name : str
            The name of the database.
        url : str
            The url of the CouchDB server formatted as `scheme://user:password@host:port`. For example:

                "http://user:password@127.0.0.1:5984"
                "https://couchdb.example.com"
        port : int
            The port of the CouchDB server. Can also be supplied via the url.
        user : str
            The CouchDB admin username. Can also be supplied via the url.
        password : str
            The CouchDB admin password. Can also be supplied via the url.
        disable_ssl_verification : bool
            Controls whether to verify the server's TLS certificate. Set to `True` when connecting
            to a server with self-signed TLS certificates. Default `False`.
        auth_method : str
            Authentication method. Choices are `cookie` or `basic`.
            Default is `couchdb3.utils.DEFAULT_AUTH_METHOD`.
        timeout : int
            The default timeout for requests. Default c.f. `couchdb3.utils.DEFAULT_TIMEOUT`.
        session : httpx.AsyncClient
            A specific async client to use. Optional — if not provided, a new client will be
            initialized.
        _server : AsyncServer
            The owning `AsyncServer` instance. Set internally by `AsyncServer.get()` to keep
            the server alive for the lifetime of this database object. Not part of the public
            constructor API — pass `None` (default) when constructing an `AsyncDatabase`
            directly.
        """
        super().__init__(
            url=url,
            session=session,
            port=port,
            user=user,
            password=password,
            disable_ssl_verification=disable_ssl_verification,
            auth_method=auth_method,
            timeout=timeout,
        )
        if not validate_db_name(name=name):
            raise NameComplianceError(
                "Database name does not comply with the CouchDB requirements. "
                "See https://docs.couchdb.org/en/latest/api/database/common.html#put--db."
            )
        self.name = name
        self.root = name
        self._server = _server

    @property
    def server(self):
        """
        The `AsyncServer` instance this database was obtained from, or `None` if the database
        was constructed directly (i.e. not via `AsyncServer.get()`).

        Read-only. Setting this attribute raises `AttributeError`.

        Returns
        -------
        AsyncServer | None
        """
        return self._server

    def __repr__(self) -> str:
        """
        Basic repr.

        Returns
        -------
        str : The instance's representation.
        """
        return f"{super().__repr__()}: {self.name}"

    async def all_docs(
        self,
        partition: str | None = None,
        keys: Iterable[str] | None = None,
        **kwargs,
    ) -> ViewResult:
        """
        Executes the built-in _all_docs view, returning all documents in the database
        (or partition).

        Parameters
        ----------
        partition : str
            Filter using the partition's name (only valid for partitioned databases).
            Default is `None`.
        keys : Iterable[str]
            Return only documents where the key matches one of the keys specified.
            Default is `None`.
        kwargs
            Further `AsyncDatabase.view` parameters.

        Returns
        -------
        ViewResult
        """
        return await self.view(
            f"_partition/{partition}/_all_docs" if partition else "_all_docs",
            keys=keys,
            **kwargs,
        )

    async def design_docs(
        self,
        *,
        conflicts: bool | None = None,
        descending: bool | None = None,
        endkey: str | None = None,
        include_docs: bool | None = None,
        keys: Iterable[str] | None = None,
        limit: int | None = None,
        skip: int | None = None,
        startkey: str | None = None,
        update_seq: bool | None = None,
    ) -> ViewResult:
        """
        Executes the built-in `_design_docs` view, returning all the design documents in the database.

        This is a shorthand for `_all_docs` filtered to the `_design/` key range.

        Parameters
        ----------
        conflicts : bool
            Include conflicts information. Ignored if `include_docs` isn't `True`. Default is `None`.
        descending : bool
            Return the documents in descending order by key. Default is `None`.
        endkey : str
            Stop returning records when the specified key is reached. Default is `None`.
        include_docs : bool
            Include the associated document with each row. Default is `None`.
        keys : Iterable[str]
            Return only documents where the key matches one of the keys specified in the argument.
            Default is `None`.
        limit : int
            Limit the number of the returned documents. Default is `None`.
        skip : int
            Skip this number of records before starting to return the results. Default is `None`.
        startkey : str
            Return records starting with the specified key. Default is `None`.
        update_seq : bool
            Whether to include an `update_seq` value indicating the sequence id of the database.
            Default is `None`.

        Returns
        -------
        ViewResult
        """
        return ViewResult(
            **(
                await self._get(
                    resource="_design_docs",
                    query_kwargs=rm_nones_from_dict(
                        {
                            "conflicts": conflicts,
                            "descending": descending,
                            "endkey": endkey,
                            "include_docs": include_docs,
                            "keys": keys,
                            "limit": limit,
                            "skip": skip,
                            "startkey": startkey,
                            "update_seq": update_seq,
                        }
                    ),
                )
            ).json()
        )

    async def bulk_docs(
        self,
        docs: list[dict | Document],
        new_edits: bool = True,
    ) -> list[dict]:
        """
        Create or update multiple documents in a single request.

        Parameters
        ----------
        docs : list[dict | Document]
            List of document objects.
        new_edits : bool
            If `False`, prevents the database from assigning new revision IDs. Default `True`.

        Returns
        -------
        list[dict] : Each item contains `id`, `ok`, and `rev`.
        """
        return (
            await self._post(resource="_bulk_docs", body={"docs": docs, "new_edits": new_edits})
        ).json()

    async def bulk_get(
        self,
        docs: list[dict | Document],
        revs: bool = False,
    ) -> list[dict]:
        """
        Query several documents in bulk.

        Parameters
        ----------
        docs : list[dict | Document]
            List of document objects, with `id`, and optionally `rev` and `atts_since`.
        revs : bool
            Give the revisions history. Default `False`.

        Returns
        -------
        list[dict]
        """
        return (
            (
                await self._post(
                    resource="_bulk_get",
                    body={"docs": [extract_document_id_and_rev(_) for _ in docs]},
                    query_kwargs={"revs": revs},
                )
            )
            .json()
            .get("results", [])
        )

    async def compact(self, ddoc: str | None = None) -> bool:
        """
        Request compaction of the database.

        Parameters
        ----------
        ddoc : str
            A design document name. If provided, compacts the view indexes for that ddoc.

        Returns
        -------
        bool: `True` upon compaction request successfully sent.
        """
        resource = "_compact"
        if ddoc:
            resource += f"/{ddoc}"
        return (await self._post(resource=resource)).json().get("ok")

    async def copy(
        self,
        docid: str,
        destid: str,
        rev: str | None = None,
        destrev: str | None = None,
    ) -> tuple[str, bool, str]:
        """
        Copy an existing document to a new or existing document.

        Parameters
        ----------
        docid : str
            The ID of the document to copy.
        destid : str
            The target document's ID.
        rev : str
            A specific revision of the document to copy.
        destrev : str
            If the target document already exists, its current revision.

        Returns
        -------
        tuple[str, bool, str] : (id, ok, rev)
        """
        destination = destid
        if destrev:
            destination += f"?rev={destrev}"
        data = (
            await self._request(
                method="COPY",
                resource=docid,
                headers={"Destination": destination},
                query_kwargs={"rev": rev},
            )
        ).json()
        return data["id"], data["ok"], data["rev"]

    async def create(
        self,
        doc: dict | Document,
        *,
        batch: bool | None = None,
    ) -> tuple[str, bool, str]:
        """
        Create a new document without specifying an ID.

        Parameters
        ----------
        doc : dict | Document
            A dictionary or Document instance.
        batch : bool
            Stores document in batch mode. Default `None`.

        Returns
        -------
        tuple[str, bool, str] : (id, ok, rev)
        """
        data = (
            await self._post(body=doc, query_kwargs={"batch": "ok" if batch is True else None})
        ).json()
        return data["id"], data["ok"], data["rev"]

    async def delete(self, docid: str, rev: str, *, batch: bool | None = None) -> bool:
        """
        Delete a document.

        Parameters
        ----------
        docid : str
            The document's id.
        rev : str
            The document's current revision.
        batch : bool
            Stores document in batch mode. Default `None`.

        Returns
        -------
        bool : `True` upon successful deletion.
        """
        await self._delete(
            resource=docid,
            query_kwargs={"rev": rev, "batch": "ok" if batch is True else None},
        )
        return True

    async def delete_attachment(
        self, docid: str, attname: str, rev: str, *, batch: bool = False
    ) -> bool:
        """
        Delete an attachment.

        Parameters
        ----------
        docid : str
            The document's id.
        attname : str
            The attachment's name.
        rev : str
            The document's current revision.
        batch : bool
            Stores in batch mode. Default `False`.

        Returns
        -------
        bool : `True` upon successful deletion.
        """
        await self._delete(
            resource=f"{docid}/{attname}",
            query_kwargs={"rev": rev, "batch": "ok" if batch is True else None},
        )
        return True

    async def explain(
        self,
        selector: dict,
        limit: int = 25,
        skip: int = 0,
        sort: list[dict] | None = None,
        fields: list[str] | None = None,
        use_index: str | list[str] | None = None,
        conflicts: bool = False,
        r: int = 1,
        bookmark: str | None = None,
        update: bool = True,
        stable: bool | None = None,
        execution_stats: bool = False,
    ) -> dict:
        """
        Shows which index is being used by the query. Parameters are the same as
        `AsyncDatabase.find`.

        Parameters
        ----------
        selector : dict
            JSON object describing criteria used to select documents.
        limit : int
            Maximum number of results returned. Default is `25`.
        skip : int
            Skip the first `n` results. Default is `0`.
        sort : list[dict]
            JSON array following CouchDB's sort syntax. Default is `None`.
        fields : list[str]
            Fields to return. Default is `None` (entire object).
        use_index : str | list[str]
            Instruct a query to use a specific index. Default is `None`.
        conflicts : bool
            Include conflicted documents. Default is `False`.
        r : int
            Read quorum. Default is `1`.
        bookmark : str
            Paging bookmark. Default is `None`.
        update : bool
            Whether to update the index prior to returning the result. Default is `True`.
        stable : bool
            Whether to use a stable set of shards. Default is `None`.
        execution_stats : bool
            Include execution statistics. Default is `False`.

        Returns
        -------
        dict
        """
        return (
            await self._post(
                resource="_explain",
                body=rm_nones_from_dict(
                    {
                        "selector": selector,
                        "limit": limit,
                        "skip": skip,
                        "sort": sort,
                        "fields": fields,
                        "use_index": use_index,
                        "conflicts": conflicts,
                        "r": r,
                        "bookmark": bookmark,
                        "update": update,
                        "stable": stable,
                        "execution_stats": execution_stats,
                    }
                ),
            )
        ).json()

    async def find(
        self,
        selector: dict,
        limit: int = 25,
        skip: int = 0,
        sort: list[dict] | None = None,
        fields: list[str] | None = None,
        use_index: str | list[str] | None = None,
        conflicts: bool = False,
        r: int = 1,
        bookmark: str | None = None,
        update: bool = True,
        stable: bool | None = None,
        execution_stats: bool = False,
        partition: str | None = None,
    ) -> dict:
        """
        Find documents using a declarative JSON querying syntax.

        Parameters
        ----------
        selector : dict
            JSON object describing criteria used to select documents.
        limit : int
            Maximum number of results returned. Default is `25`.
        skip : int
            Skip the first `n` results. Default is `0`.
        sort : list[dict]
            JSON array following CouchDB's sort syntax. Default is `None`.
        fields : list[str]
            Fields to return. Default is `None` (entire object).
        use_index : str | list[str]
            Instruct a query to use a specific index. Default is `None`.
        conflicts : bool
            Include conflicted documents. Default is `False`.
        r : int
            Read quorum. Default is `1`.
        bookmark : str
            Paging bookmark. Default is `None`.
        update : bool
            Whether to update the index prior to returning the result. Default is `True`.
        stable : bool
            Whether to use a stable set of shards. Default is `None`.
        execution_stats : bool
            Include execution statistics. Default is `False`.
        partition : str
            An optional partition ID. Only valid for partitioned databases. Default `None`.

        Returns
        -------
        dict : Keys are `bookmark`, `docs`, `warning`.
        """
        return (
            await self._post(
                resource=partitioned_db_resource_parser(
                    resource="_find",
                    partition=partition,
                ),
                body=rm_nones_from_dict(
                    {
                        "selector": selector,
                        "limit": limit,
                        "skip": skip,
                        "sort": sort,
                        "fields": fields,
                        "use_index": use_index,
                        "conflicts": conflicts,
                        "r": r,
                        "bookmark": bookmark,
                        "update": update,
                        "stable": stable,
                        "execution_stats": execution_stats,
                    }
                ),
            )
        ).json()

    async def indexes(self) -> dict:
        """
        Get a list of all indexes in the database.

        Returns
        -------
        dict : Keys are `total_rows` and `indexes`.
        """
        return (await self._get(resource="_index")).json()

    async def get(
        self,
        docid: str,
        *,
        attachments: bool | None = None,
        att_encoding_info: bool | None = None,
        atts_since: Iterable[str] | None = None,
        conflicts: bool | None = None,
        deleted_conflicts: bool | None = None,
        latest: bool | None = None,
        local_seq: bool | None = None,
        meta: bool | None = None,
        open_revs: Iterable[str] | None = None,
        rev: str | None = None,
        revs: bool | None = None,
        revs_info: bool | None = None,
        check: bool | None = None,
        default_value: Any | None = None,
    ) -> Document | Any:
        """
        Get a document by id.

        Parameters
        ----------
        docid : str
            The document's id.
        attachments : bool
            Includes attachment bodies in response. Default `None`.
        att_encoding_info : bool
            Includes encoding information in attachment stubs. Default `None`.
        atts_since : Iterable[str]
            Includes attachments only since specified revisions. Default `None`.
        conflicts : bool
            Includes conflict information. Default `None`.
        deleted_conflicts : bool
            Includes deleted conflicted revisions. Default `None`.
        latest : bool
            Forces retrieving the latest leaf revision. Default `None`.
        local_seq : bool
            Includes last update sequence for the document. Default `None`.
        meta : bool
            Equivalent to specifying all conflicts, deleted_conflicts and revs_info.
            Default `None`.
        open_revs : Iterable[str]
            Retrieves documents of specified leaf revisions. Default `None`.
        rev : str
            Retrieves document of specified revision. Default `None`.
        revs : bool
            Includes list of all known document revisions. Default `None`.
        revs_info : bool
            Includes detailed information for all known document revisions. Default `None`.
        check : bool
            If `True`, raise an exception if the document is not found. Default `None`.
        default_value : Any
            Value to return if `check=False` and document is not found. Default `None`.

        Returns
        -------
        Document | Any
        """
        try:
            return Document(
                **(
                    await self._get(
                        resource=docid,
                        query_kwargs={
                            "attachments": attachments,
                            "att_encoding_info": att_encoding_info,
                            "atts_since": atts_since,
                            "conflicts": conflicts,
                            "deleted_conflicts": deleted_conflicts,
                            "latest": latest,
                            "local_seq": local_seq,
                            "meta": meta,
                            "open_revs": open_revs,
                            "rev": rev,
                            "revs": revs,
                            "revs_info": revs_info,
                        },
                    )
                ).json()
            )
        except (CouchDBError, httpx.RequestError):
            if check:
                raise
            return default_value

    async def get_attachment(
        self,
        docid: str,
        attname: str,
        rev: str | None = None,
    ) -> AttachmentDocument:
        """
        Get a document's attachment.

        Parameters
        ----------
        docid : str
            The document's id.
        attname : str
            The attachment's name.
        rev : str
            A specific revision. Default `None`.

        Returns
        -------
        AttachmentDocument
        """
        response = await self._get(f"{docid}/{attname}", query_kwargs={"rev": rev})
        content_md5 = response.headers.get("content-md5")
        digest_value = f"md5-{content_md5}" if content_md5 else None
        return AttachmentDocument(
            content=response.content,
            content_encoding=response.headers.get("content-encoding"),
            content_length=response.headers.get("content-length"),
            content_type=response.headers.get("content-type"),
            digest=digest_value,
        )

    async def get_design(self, ddoc: str, **kwargs) -> Document:
        """
        Get a design document.

        Parameters
        ----------
        ddoc : str
            The design document's name.
        kwargs
            Further `AsyncDatabase.get` parameters.

        Returns
        -------
        Document
        """
        return await self.get(docid=f"_design/{ddoc}", **kwargs)

    async def purge(self, data: dict) -> dict:
        """
        Permanently purge the given `(id, rev)` pairs.

        Parameters
        ----------
        data : dict
            A dictionary with document IDs as keys and list of revisions as values.

        Returns
        -------
        dict
        """
        return (await self._post(resource="_purge", body=data)).json()

    async def put_attachment(
        self,
        docid: str,
        attname: str,
        path: str | None = None,
        *,
        content: bytes | None = None,
        content_type: str | None = None,
        rev: str | None = None,
    ) -> tuple[str, bool, str]:
        """
        Upload content as an attachment to the specified document.

        Parameters
        ----------
        docid : str
            The document's id.
        attname : str
            The attachment's name.
        path : str
            Path to a local file to upload. Mutually exclusive with `content`.
        content : bytes
            Raw bytes to upload. Mutually exclusive with `path`.
        content_type : str
            The attachment's MIME type. Required when `content` is provided.
        rev : str
            The document's current revision. Required for existing documents.

        Returns
        -------
        tuple[str, bool, str] : (id, ok, rev)
        """
        if (not content and not path) or (content and path):
            raise ValueError(
                'Precisely one of the arguments "content" and "path" must be provided.'
            )
        if content and not content_type:
            raise ValueError('Argument "content_type" cannot be empty when "content" is provided.')
        resource = f"{docid}/{attname}"
        query_kwargs = {"rev": rev}
        content_type = content_type if content_type else mimetypes.guess_type(path)[0]
        if path:
            with open(path, "rb") as file:
                content = file.read()
        response = await self._put(
            resource=resource,
            query_kwargs=query_kwargs,
            content=content,
            headers={"content-type": content_type},
        )
        data = response.json()
        return data["id"], data["ok"], data["rev"]

    async def put_design(
        self,
        ddoc: str,
        *,
        rev: str | None = None,
        language: str | None = None,
        options: dict | None = None,
        filters: dict | None = None,
        updates: dict | None = None,
        validate_doc_update: str | None = None,
        views: dict | None = None,
        autoupdate: bool | None = None,
        partitioned: bool | None = None,
        **kwargs,
    ) -> tuple[str, bool, str]:
        """
        Create or update a named design document.

        Parameters
        ----------
        ddoc : str
            The design document's name.
        rev : str
            The design document's revision in case of an update.
        language : str
            Query Server to process design document functions.
        options : dict
            View's default options.
        filters : dict
            Filter functions definition.
        updates : dict
            Update functions definition.
        validate_doc_update : str
            Validate document update function source.
        views : dict
            View functions definition.
        autoupdate : bool
            Indicates whether to automatically build indexes.
        partitioned : bool
            Set to `True` for a partitioned design.
        kwargs
            Further `AsyncDatabase.save` parameters.

        Returns
        -------
        tuple[str, bool, str] : (id, ok, rev)
        """
        if partitioned:
            options = {**(options or {}), "partitioned": partitioned}
        return await self.save(
            doc=rm_nones_from_dict(
                {
                    "_id": f"_design/{ddoc}",
                    "_rev": rev,
                    "language": language,
                    "options": options,
                    "filters": filters,
                    "updates": updates,
                    "validate_doc_update": validate_doc_update,
                    "views": views,
                    "autoupdate": autoupdate,
                }
            ),
            **kwargs,
        )

    async def save(
        self,
        doc: dict | Document,
        batch: bool | None = None,
        new_edits: bool | None = None,
        path: str | None = None,
    ) -> tuple[str, bool, str]:
        """
        Create a new named document, or a new revision of an existing document.

        Parameters
        ----------
        doc : dict | Document
            A dictionary or Document instance with a valid `_id`, and `_rev` if updating.
        batch : bool
            Store document in batch mode. Default `None`.
        new_edits : bool
            Prevents insertion of a conflicting document. Default `None`.
        path : str
            Database path, e.g. `_design`. Default `None`.

        Returns
        -------
        tuple[str, bool, str] : (id, ok, rev)
        """
        batch = "ok" if batch else None
        data = (
            await self._put(
                resource=f"{path}/{doc.get('_id')}" if path else doc.get("_id"),
                body=doc,
                query_kwargs={
                    "batch": "ok" if batch else None,
                    "new_edits": new_edits,
                    "rev": doc.get("_rev"),
                },
            )
        ).json()
        return data["id"], data["ok"], data["rev"]

    async def save_index(
        self,
        index: dict,
        ddoc: str | None = None,
        name: str | None = None,
        index_type: str | None = "json",
        partitioned: bool | None = None,
    ) -> tuple[str, str, str]:
        """
        Create a new index on a database.

        Parameters
        ----------
        index : dict
            Dictionary describing the index to create.
        ddoc : str
            Name of the design document. Default `None` (auto-generated).
        name : str
            Name of the index. Default `None` (auto-generated).
        index_type : str
            `json` or `text`. Default `json`.
        partitioned : bool
            Whether the index is partitioned or global. Default `None`.

        Returns
        -------
        tuple[str, str, str] : (result, id, name)
        """
        data = (
            await self._post(
                resource="_index",
                body=rm_nones_from_dict(
                    {
                        "index": index,
                        "ddoc": ddoc,
                        "name": name,
                        "type": index_type,
                        "partitioned": partitioned,
                    }
                ),
            )
        ).json()
        return data["result"], data["id"], data["name"]

    async def delete_index(self, ddoc: str, name: str, index_type: str = "json") -> bool:
        """
        Delete an index from a database. For more info, please refer to
        [the official documentation](https://docs.couchdb.org/en/main/api/database/find.html#db-index).

        Parameters
        ----------
        ddoc : str
            Name of the design document the index belongs to. A `_design/` prefix is stripped
            automatically.
        name : str
            Name of the index.
        index_type : str
            Can be `json` or `text`. Defaults to `json`.

        Returns
        -------
        bool : `True` upon successful deletion.
        """
        ddoc = ddoc.removeprefix("_design/")
        return (await self._delete(resource=f"_index/{ddoc}/{index_type}/{name}")).json().get("ok")

    async def security(self) -> SecurityDocument:
        """
        Returns the current security object from the specified database.

        Returns
        -------
        SecurityDocument
        """
        data = (await self._get(resource="_security")).json()
        return SecurityDocument(**data)

    async def update_security(
        self,
        admins: dict | SecurityDocumentElement | None = None,
        members: dict | SecurityDocumentElement | None = None,
    ) -> bool:
        """
        Update database security.

        Parameters
        ----------
        admins : dict | SecurityDocumentElement
            Object with `names` and `roles` fields.
        members : dict | SecurityDocumentElement
            Object with `names` and `roles` fields.

        Returns
        -------
        bool : Operation status.
        """
        return (
            await self._put(resource="_security", body={"admins": admins, "members": members})
        ).json()["ok"]

    async def view(
        self,
        ddoc: str,
        view: str | None = None,
        *,
        partition: str | None = None,
        conflicts: bool | None = None,
        descending: bool | None = None,
        endkey: Any | None = None,
        endkey_docid: str | None = None,
        group: bool | None = None,
        group_level: int | None = None,
        include_docs: bool | None = None,
        attachments: bool | None = None,
        att_encoding_info: bool | None = None,
        inclusive_end: bool | None = None,
        key: str | None = None,
        keys: Iterable[str] | None = None,
        limit: int | None = None,
        reduce: bool | None = None,
        skip: int | None = None,
        sort: bool | None = None,
        stable: bool | None = None,
        startkey: Any | None = None,
        startkey_docid: str | None = None,
        update: str | None = None,
        update_seq: bool | None = None,
    ) -> ViewResult:
        """
        Executes the specified view function from the specified design document.

        Parameters
        ----------
        ddoc : str
            The corresponding design document's id.
        view : str
            The view's id.
        partition : str
            An optional partition ID. Only valid for partitioned databases. Default `None`.
        conflicts : bool
            Include conflicts information in response. Default `None`.
        descending : bool
            Return documents in descending order. Default `None`.
        endkey : Any
            Stop returning records at this key. Default `None`.
        endkey_docid : str
            Stop returning records at this document ID. Default `None`.
        group : bool
            Group results using the reduce function. Default `None`.
        group_level : int
            Specify the group level. Default `None`.
        include_docs : bool
            Include the associated document with each row. Default `None`.
        attachments : bool
            Include Base64-encoded attachment content. Default `None`.
        att_encoding_info : bool
            Include encoding information in attachment stubs. Default `None`.
        inclusive_end : bool
            Whether the end key should be included in the result. Default `None`.
        key : str
            Return only documents matching this key. Default `None`.
        keys : Iterable[str]
            Return only documents matching these keys. Default `None`.
        limit : int
            Maximum number of documents to return. Default `None`.
        reduce : bool
            Use the reduction function. Default `None`.
        skip : int
            Skip this number of records. Default `None`.
        sort : bool
            Sort returned rows. Default `None`.
        stable : bool
            Use a stable set of shards. Default `None`.
        startkey : Any
            Return records starting with this key. Default `None`.
        startkey_docid : str
            Return records starting with this document ID. Default `None`.
        update : str
            Whether to update the view prior to responding (`true`, `false`, `lazy`).
            Default `None`.
        update_seq : bool
            Include the `update_seq` value in the response. Default `None`.

        Returns
        -------
        ViewResult
        """
        path = partitioned_db_resource_parser(
            resource="_design",
            partition=partition,
        )
        return ViewResult(
            **(
                await self._get(
                    resource=f"{path}/{ddoc}/_view/{view}" if (ddoc and view) else ddoc,
                    query_kwargs={
                        "conflicts": conflicts,
                        "descending": descending,
                        "endkey": endkey,
                        "endkey_docid": endkey_docid,
                        "group": group,
                        "group_level": group_level,
                        "include_docs": include_docs,
                        "attachments": attachments,
                        "att_encoding_info": att_encoding_info,
                        "inclusive_end": inclusive_end,
                        "key": key,
                        "keys": keys,
                        "limit": limit,
                        "reduce": reduce,
                        "skip": skip,
                        "sorted": sort,
                        "stable": stable,
                        "startkey": startkey,
                        "startkey_docid": startkey_docid,
                        "update": update,
                        "update_seq": update_seq,
                    },
                )
            ).json()
        )

    async def changes(
        self,
        *,
        doc_ids: list[str] | None = None,
        conflicts: bool | None = None,
        descending: bool | None = None,
        feed: str | None = None,
        filter: str | None = None,
        heartbeat: int | None = None,
        include_docs: bool | None = None,
        attachments: bool | None = None,
        att_encoding_info: bool | None = None,
        limit: int | None = None,
        since: str | None = None,
        style: str | None = None,
        timeout: int | None = None,
        view: str | None = None,
        seq_interval: int | None = None,
        selector: dict | None = None,
    ) -> dict:
        """
        Returns a sorted list of changes made to documents in the database. Only the most
        recent change for a given document is included.

        When `doc_ids` is provided the request is sent as ``POST /{db}/_changes`` with
        ``filter=_doc_ids``. When `selector` is provided it is sent as
        ``POST /{db}/_changes`` with ``filter=_selector``. All other cases use
        ``GET /{db}/_changes``.

        .. note::
            ``feed='continuous'`` and ``feed='eventsource'`` are **not** supported by this
            method. Passing either value raises :class:`ValueError`. Streaming feeds will be
            addressed in a future ``changes_stream()`` method.

        Parameters
        ----------
        doc_ids : list[str]
            List of document IDs to filter the changes feed. Triggers a POST request with
            ``filter=_doc_ids``. Mutually exclusive with `selector`.
        conflicts : bool
            Include conflicts information. Only effective when `include_docs` is `True`.
        descending : bool
            Return changes in descending sequence order. Default `False`.
        feed : str
            Feed type. Supported values: ``'normal'`` (default), ``'longpoll'``.
            ``'continuous'`` and ``'eventsource'`` are not supported.
        filter : str
            Name of a filter function (``'design_doc/filter_name'``, ``'_design'``, or
            ``'_view'``). Do not pass ``'_doc_ids'`` or ``'_selector'`` manually — use the
            `doc_ids` / `selector` parameters instead.
        heartbeat : int
            Milliseconds between heartbeat newlines for ``longpoll`` feed.
        include_docs : bool
            Include the associated document with each result. Default `False`.
        attachments : bool
            Include Base64-encoded attachment content when `include_docs` is `True`.
        att_encoding_info : bool
            Include encoding info in attachment stubs when `include_docs` is `True`.
        limit : int
            Maximum number of rows to return.
        since : str
            Return only changes after the given update sequence. Use ``'now'`` to get only
            future changes.
        style : str
            Revision style. ``'main_only'`` (default) or ``'all_docs'``.
        timeout : int
            Maximum milliseconds to wait for a change (``longpoll`` only).
        view : str
            View function to use as a filter (requires ``filter='_view'``).
        seq_interval : int
            Calculate update sequence every N results (reduces server load on large
            sharded databases).
        selector : dict
            Mango selector to filter documents. Triggers a POST request with
            ``filter=_selector``. Mutually exclusive with `doc_ids`.

        Returns
        -------
        dict : A dictionary with the following keys.

          - ``last_seq`` (`str`) — last change update sequence
          - ``pending`` (`int`) — count of remaining items in the feed
          - ``results`` (`list`) — list of change objects, each with ``id``, ``seq``,
            ``changes``, and optionally ``deleted`` / ``doc``

        Raises
        ------
        ValueError
            If ``feed`` is ``'continuous'`` or ``'eventsource'``.
        CouchDBError
            If both `doc_ids` and `selector` are provided.
        """
        if feed in ("continuous", "eventsource"):
            raise ValueError(
                f"feed={feed!r} is not supported by changes(). Use feed='normal' or "
                "'longpoll'. Streaming feeds will be available via changes_stream() "
                "in a future release."
            )
        if doc_ids is not None and selector is not None:
            raise CouchDBError("Arguments 'doc_ids' and 'selector' are mutually exclusive.")
        query_kwargs = {
            "conflicts": conflicts,
            "descending": descending,
            "feed": feed,
            "filter": filter,
            "heartbeat": heartbeat,
            "include_docs": include_docs,
            "attachments": attachments,
            "att_encoding_info": att_encoding_info,
            "limit": limit,
            "since": since,
            "style": style,
            "timeout": timeout,
            "view": view,
            "seq_interval": seq_interval,
        }
        if doc_ids is not None:
            query_kwargs["filter"] = "_doc_ids"
            return (
                await self._post(
                    resource="_changes",
                    body={"doc_ids": doc_ids},
                    query_kwargs=query_kwargs,
                )
            ).json()
        if selector is not None:
            query_kwargs["filter"] = "_selector"
            return (
                await self._post(
                    resource="_changes",
                    body={"selector": selector},
                    query_kwargs=query_kwargs,
                )
            ).json()
        return (await self._get(resource="_changes", query_kwargs=query_kwargs)).json()

    async def get_partition(self, partition_id: str) -> AsyncPartition:
        """
        Get a given partition.

        Parameters
        ----------
        partition_id : str
            The partition's ID.

        Returns
        -------
        AsyncPartition
        """
        return AsyncPartition(
            partition_id=partition_id,
            name=self.name,
            url=self.url,
            port=self.port,
            user=self._user,
            password=self._password,
            disable_ssl_verification=self.disable_ssl_verification,
            auth_method=self.auth_method,
            session=self.session,  # shared — child sets _owns_session=False
            _database=self,
        )


class AsyncPartition(AsyncDatabase):
    """
    Async CouchDB partition client. Mirrors `Partition` with `async def` methods throughout.
    """

    def __init__(
        self,
        partition_id: str,
        name: str,
        *,
        url: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        disable_ssl_verification: bool = False,
        auth_method: str | None = None,
        timeout: int | None = None,
        session: httpx.AsyncClient | None = None,
        _database: Any = None,
    ) -> None:
        """

        Parameters
        ----------
        partition_id : str
            The partition's ID.
        name : str
            The name of the database.
        url : str
            The url of the CouchDB server.
        port : int
            The port of the CouchDB server.
        user : str
            The CouchDB admin username.
        password : str
            The CouchDB admin password.
        disable_ssl_verification : bool
            Controls whether to verify the server's TLS certificate. Default `False`.
        auth_method : str
            Authentication method. Default is `couchdb3.utils.DEFAULT_AUTH_METHOD`.
        timeout : int
            The default timeout for requests. Default `None`.
        session : httpx.AsyncClient
            A specific async client to use. Optional.
        _database : AsyncDatabase
            The owning `AsyncDatabase` instance. Set internally by
            `AsyncDatabase.get_partition()` to keep the database alive for the lifetime of
            this partition object. Not part of the public constructor API — pass `None`
            (default) when constructing an `AsyncPartition` directly.
        """
        super().__init__(
            name=name,
            url=url,
            session=session,
            port=port,
            user=user,
            password=password,
            disable_ssl_verification=disable_ssl_verification,
            auth_method=auth_method,
            timeout=timeout,
        )
        self.partition_id = partition_id
        self._database = _database

    @property
    def database(self):
        """
        The `AsyncDatabase` instance this partition was obtained from, or `None` if the
        partition was constructed directly (i.e. not via `AsyncDatabase.get_partition()`).

        Read-only. Setting this attribute raises `AttributeError`.

        Returns
        -------
        AsyncDatabase | None
        """
        return self._database

    def __repr__(self) -> str:
        return f"{super().__repr__()}/{self.partition_id}"

    async def all_docs(self, keys: Iterable[str] | None = None, **kwargs) -> ViewResult:
        """
        Executes the built-in _all_docs view, returning all documents in the partition.

        Parameters
        ----------
        keys : Iterable[str]
            Return only documents matching these keys. Default `None`.
        kwargs
            Further `AsyncDatabase.view` parameters.

        Returns
        -------
        ViewResult
        """
        return await super().all_docs(partition=self.partition_id, keys=keys, **kwargs)

    async def info(self) -> dict:
        """
        Return the partition's info.

        Returns
        -------
        dict
        """
        return await super().info(partition=self.partition_id)

    async def find(
        self,
        selector: dict,
        limit: int = 25,
        skip: int = 0,
        sort: list[dict] | None = None,
        fields: list[str] | None = None,
        use_index: str | list[str] | None = None,
        conflicts: bool = False,
        r: int = 1,
        bookmark: str | None = None,
        update: bool = True,
        stable: bool | None = None,
        execution_stats: bool = False,
    ) -> dict:
        """
        See `AsyncDatabase.find`.
        """
        return await super().find(
            selector=selector,
            limit=limit,
            skip=skip,
            sort=sort,
            fields=fields,
            use_index=use_index,
            conflicts=conflicts,
            r=r,
            bookmark=bookmark,
            update=update,
            stable=stable,
            execution_stats=execution_stats,
            partition=self.partition_id,
        )

    async def view(
        self,
        ddoc: str,
        view: str | None = None,
        *,
        conflicts: bool | None = None,
        descending: bool | None = None,
        endkey: Any | None = None,
        endkey_docid: str | None = None,
        group: bool | None = None,
        group_level: int | None = None,
        include_docs: bool | None = None,
        attachments: bool | None = None,
        att_encoding_info: bool | None = None,
        inclusive_end: bool | None = None,
        key: str | None = None,
        keys: Iterable[str] | None = None,
        limit: int | None = None,
        reduce: bool | None = None,
        skip: int | None = None,
        sort: bool | None = None,
        stable: bool | None = None,
        startkey: Any | None = None,
        startkey_docid: str | None = None,
        update: str | None = None,
        update_seq: bool | None = None,
    ) -> ViewResult:
        """
        See `AsyncDatabase.view`.
        """
        return await super().view(
            ddoc=ddoc,
            view=view,
            partition=self.partition_id,
            conflicts=conflicts,
            descending=descending,
            endkey=endkey,
            endkey_docid=endkey_docid,
            group=group,
            group_level=group_level,
            include_docs=include_docs,
            attachments=attachments,
            att_encoding_info=att_encoding_info,
            inclusive_end=inclusive_end,
            key=key,
            keys=keys,
            limit=limit,
            reduce=reduce,
            skip=skip,
            sort=sort,
            stable=stable,
            startkey=startkey,
            startkey_docid=startkey_docid,
            update=update,
            update_seq=update_seq,
        )

    async def bulk_docs(self, docs: list[dict | Document], new_edits: bool = True) -> list[dict]:
        """See `AsyncDatabase.bulk_docs`. Prepends partition ID to document IDs."""
        return await super().bulk_docs(
            docs=[self.add_partition_to_doc(doc) for doc in docs],
            new_edits=new_edits,
        )

    async def bulk_get(self, docs: list[dict | Document], revs: bool = False) -> list[dict]:
        """See `AsyncDatabase.bulk_get`. Prepends partition ID to document IDs."""
        return await super().bulk_get(
            docs=[self.add_partition_to_bulk_get_doc(doc) for doc in docs],
            revs=revs,
        )

    async def copy(
        self,
        docid: str,
        destid: str,
        rev: str | None = None,
        destrev: str | None = None,
    ) -> tuple[str, bool, str]:
        """See `AsyncDatabase.copy`. Prepends partition ID to document IDs."""
        return await super().copy(
            docid=self.add_partition_to_str(docid),
            destid=self.add_partition_to_str(destid),
            rev=rev,
            destrev=destrev,
        )

    async def create(
        self, doc: dict | Document, *, batch: bool | None = None
    ) -> tuple[str, bool, str]:
        """See `AsyncDatabase.create`. Prepends partition ID to document ID."""
        return await super().create(
            doc=self.add_partition_to_doc(doc),
            batch=batch,
        )

    async def delete(self, docid: str, rev: str, *, batch: bool | None = None) -> bool:
        """See `AsyncDatabase.delete`. Prepends partition ID to document ID."""
        return await super().delete(
            docid=self.add_partition_to_str(docid),
            rev=rev,
            batch=batch,
        )

    async def delete_attachment(
        self, docid: str, attname: str, rev: str, *, batch: bool = False
    ) -> bool:
        """See `AsyncDatabase.delete_attachment`. Prepends partition ID to document ID."""
        return await super().delete_attachment(
            docid=self.add_partition_to_str(docid),
            attname=attname,
            rev=rev,
            batch=batch,
        )

    async def get(
        self,
        docid: str,
        *,
        attachments: bool | None = None,
        att_encoding_info: bool | None = None,
        atts_since: Iterable[str] | None = None,
        conflicts: bool | None = None,
        deleted_conflicts: bool | None = None,
        latest: bool | None = None,
        local_seq: bool | None = None,
        meta: bool | None = None,
        open_revs: Iterable[str] | None = None,
        rev: str | None = None,
        revs: bool | None = None,
        revs_info: bool | None = None,
        check: bool | None = False,
        default_value: Any | None = None,
    ) -> Document | Any:
        """See `AsyncDatabase.get`. Prepends partition ID to document ID."""
        return await super().get(
            docid=self.add_partition_to_str(docid),
            attachments=attachments,
            att_encoding_info=att_encoding_info,
            atts_since=atts_since,
            conflicts=conflicts,
            deleted_conflicts=deleted_conflicts,
            latest=latest,
            local_seq=local_seq,
            meta=meta,
            open_revs=open_revs,
            rev=rev,
            revs=revs,
            revs_info=revs_info,
            check=check,
            default_value=default_value,
        )

    async def get_attachment(
        self, docid: str, attname: str, rev: str | None = None
    ) -> AttachmentDocument:
        """See `AsyncDatabase.get_attachment`. Prepends partition ID to document ID."""
        return await super().get_attachment(
            docid=self.add_partition_to_str(docid),
            attname=attname,
            rev=rev,
        )

    async def put_attachment(
        self,
        docid: str,
        attname: str,
        path: str | None = None,
        *,
        content: bytes | None = None,
        content_type: str | None = None,
        rev: str | None = None,
    ) -> tuple[str, bool, str]:
        """See `AsyncDatabase.put_attachment`. Prepends partition ID to document ID."""
        return await super().put_attachment(
            docid=self.add_partition_to_str(docid),
            attname=attname,
            content_type=content_type,
            path=path,
            content=content,
            rev=rev,
        )

    async def rev(self, resource: str) -> str | None:
        """See `AsyncDatabase.rev`. Prepends partition ID to the resource."""
        return await super().rev(self.add_partition_to_str(resource))

    async def save(
        self,
        doc: dict | Document,
        batch: bool | None = None,
        new_edits: bool | None = None,
        path: str | None = None,
    ) -> tuple[str, bool, str]:
        """See `AsyncDatabase.save`. Prepends partition ID to document ID."""
        return await super().save(
            doc=self.add_partition_to_doc(doc),
            batch=batch,
            new_edits=new_edits,
            path=path,
        )

    def add_partition_to_str(self, string: str) -> str:
        """Append the instance's partition ID to a string if not already present."""
        if string.startswith(f"{self.partition_id}:"):
            return string
        return f"{self.partition_id}:{string}"

    def add_partition_to_doc(self, doc: Document | dict) -> Document | dict:
        """Append the instance's partition ID to the document's `_id`."""
        docid = doc.get("_id")
        if docid is None:
            return doc
        doc["_id"] = self.add_partition_to_str(docid)
        return doc

    def add_partition_to_bulk_get_doc(self, doc: Document | dict) -> Document | dict:
        """Append the instance's partition ID to a `bulk_get` document's `id` (or `_id`)."""
        key = "_id" if "_id" in doc else "id" if "id" in doc else None
        if key is None:
            return doc
        doc[key] = self.add_partition_to_str(doc[key])
        return doc
