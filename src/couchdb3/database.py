#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import requests

from .base import Base
from .document import Document, AttachmentDocument, extract_document_id_and_rev, SecurityDocument, \
    SecurityDocumentElement
from .exceptions import CouchDBError, NameComplianceError
from .utils import validate_db_name, content_type_getter, DEFAULT_TIMEOUT, partitioned_db_resource_parser
from .view import ViewResult


__all__ = [
    "Database",
    "Partition",
]


class Database(Base):
    """
    Abstract Couchdb database
    """
    def __init__(
            self,
            name: str,
            *,
            url: str = None,
            port: int = None,
            user: str = None,
            password: str = None,
            disable_ssl_verification: bool = False,
            auth_method: str = None,
            timeout: int = DEFAULT_TIMEOUT,
            session: requests.Session = None,
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
            Controls whether to verify the server’s TLS certificate. Set to `True` when connecting to a server with
            self-signed TLS certificates. Default `False`.
        auth_method : str
            Authentication method. Choices are `cookie` or `basic`. Default is `couchdb3.utils.DEFAULT_AUTH_METHOD`.
        timeout : int
            The default timeout for requests. Default c.f. `couchdb3.utils.DEFAULT_TIMEOUT`.
        session: requests.Session
            A specific session to use. Optional - if not provided, a new session will be initialized.
        """
        super(Database, self).__init__(
            url=url,
            session=session,
            port=port,
            user=user,
            password=password,
            disable_ssl_verification=disable_ssl_verification,
            auth_method=auth_method,
            timeout=timeout
        )
        if validate_db_name(name=name) is False:
            raise NameComplianceError(
                "Database name does not comply with the CouchDB requirements. "
                "See https://docs.couchdb.org/en/latest/api/database/common.html#put--db."
            )
        self.name = name
        self.root = name

    def __getitem__(self, item) -> Document:
        return self.get(docid=item, check=True)

    def __repr__(self) -> str:
        """
        Basic repr.

        Returns
        -------
        str : The instance's representation.
        """
        return f"{super(Database, self).__repr__()}: {self.name}"

    def all_docs(
            self,
            partition: str = None,
            keys: Iterable[str] = None,
            **kwargs
    ) -> ViewResult:
        """
        Executes the built-in _all_docs view, returning all the documents in the database (or partition).

        Parameters
        ----------
        partition : str
            Filter using the partition's name (only valid for partitioned databases). Default is `None`.
        keys : Iterable[str]
            Return only documents where the key matches one of the keys specified in the argument. Default is `None`.
        kwargs
            Further `couchdb3.database.Database.view` parameters.

        Returns
        -------
        ViewResult
        """
        return self.view(
            f"_partition/{partition}/_all_docs" if partition else "_all_docs",
            keys=keys,
            **kwargs
        )

    def bulk_docs(
            self,
            docs: List[Union[Dict, Document]],
            new_edits: bool = True
    ) -> List[Dict]:
        """
        The bulk document API allows you to create and update multiple documents at the same time within a single
        request. The basic operation is similar to creating or updating a single document, except that you batch the
        document structure and information.

        When creating new documents the document ID (`_id`) is optional.

        For updating existing documents, you must provide the document ID, revision information (`_rev`), and new
        document values.

        In case of batch deleting documents all fields as document ID, revision information and deletion status
        (`_deleted`) are required.

        Parameters
        ----------
        docs : List[Union[Dict, Document]]
             List of documents objects
        new_edits : bool
            If `False`, prevents the database from assigning them new revision IDs. Default `True`.

        Returns
        -------
        List[Dict] : A list of dictionaries containing the following keys.

          - `id` the document's id
          - `ok` operation status
          - `rev` the document's revision
        """
        return self._post(
            resource="_bulk_docs",
            body={
                "docs": docs,
                "new_edits": new_edits
            }
        ).json()

    def bulk_get(
            self,
            docs: List[Union[Dict, Document]],
            revs: bool = False,
    ) -> List[Dict]:
        """
        This method can be called to query several documents in bulk. It is well suited for fetching a specific
        revision of documents, as replicators do for example, or for getting revision history.

        Parameters
        ----------
        docs : List[Union[Dict, Document]]
            List of document objects, with `id`, and optionally `rev` and `atts_since`.
        revs : bool
             Give the revisions history.

        Returns
        -------
        List[Dict] : An array of results for each requested document/rev pair.

          - `id` key lists the requested
          document ID,
          - `docs` contains a single-item array of objects, each of which has either an `error` key and value describing
          the error, or `ok` key and associated value of the requested document, with the additional _revisions property
          that lists the parent revisions if `revs=true`.
        """
        return self._post(
            resource="_bulk_get",
            body={
                "docs": [extract_document_id_and_rev(_) for _ in docs]
            },
            query_kwargs={
                "revs": revs
            }
        ).json().get("results", [])

    def compact(
            self,
            ddoc: str = None
    ) -> bool:
        """
        Request compaction of the database. For more info, please refer to
        [the official documentation](https://docs.couchdb.org/en/main/api/database/compact.html#db-compact).

        If the `ddoc` parameter is provided, it will compacts the view indexes associated with the specified design
        document.

        Parameters
        ----------
        ddoc : str
            A design document name.

        Returns
        -------
        bool: `True` upon compaction request successfully sent.
        """
        resource = "_compact"
        if ddoc:
            resource += f"/{ddoc}"
        return self._post(
            resource=resource
        ).json().get("ok")

    def copy(
            self,
            docid: str,
            destid: str,
            rev: str = None,
            destrev: str = None
    ) -> Tuple[str, bool, str]:
        """
        Copy an existing document to a new or existing document. Copying a document is only possible within the same
        database. For more info, please refer to
        [the official documentation](https://docs.couchdb.org/en/main/api/document/common.html#copy--db-docid).

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
        Tuple[str, bool, str] : A tuple consisting of the id, success message & revision.
        """
        destination = destid
        if destrev:
            destination += f"?rev={destrev}"
        data = self._request(
            method="COPY",
            resource=docid,
            headers={
                "Destination": destination,
            },
            query_kwargs={
                "rev": rev
            }
        ).json()
        return data["id"], data["ok"], data["rev"]

    def create(
            self,
            doc: Union[Dict, Document],
            *,
            batch: bool = None
    ) -> Tuple[str, bool, str]:
        """
        Create a new document.

        Parameters
        ----------
        doc : Union[Dict, couchdb3.document.Document]
            A dictionary or a `couchdb3.document.Document` instance to be created.
        batch : bool
            Stores document in batch mode. Default `None`.

        Returns
        -------
        Tuple[str, bool, str] : A tuple consisting of the id, success message & revision.
        """
        data = self._post(
            body=doc,
            query_kwargs={
                "batch": "ok" if batch is True else None
            }
        ).json()
        return data["id"], data["ok"], data["rev"]

    def delete(
            self,
            docid: str,
            rev: str,
            *,
            batch: bool = None
    ) -> bool:
        """
        Delete a document.

        Parameters
        ----------
        docid : str
            The document's id.
        rev : str
            The document's current revision. If not known, one can use `Database.rev` with the given `docid`.
        batch : bool
            Stores document in batch mode. Default `None`.

        Returns
        -------
        bool : `True` upon successful deletion.
        """
        self._delete(
            resource=docid,
            query_kwargs={
                "rev": rev,
                "batch": "ok" if batch is True else None
            }
        )
        return True

    def delete_attachment(
            self,
            docid: str,
            attname: str,
            rev: str,
            *,
            batch: bool = False
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
            The document's current revision. If not known, one can use `Database.rev` with the given `docid`.
        batch : bool
            Stores document in batch mode. Default `None`.

        Returns
        -------
        bool : `True` upon successful deletion.
        """
        self._delete(
            resource=f"{docid}/{attname}",
            query_kwargs={
                "rev": rev,
                "batch": "ok" if batch is True else None
            }
        )
        return True

    def explain(
            self,
            selector: Dict,
            limit: int = 25,
            skip: int = 0,
            sort: List[Dict] = None,
            fields: List[str] = None,
            use_index: Union[str, List[str]] = None,
            conflicts: bool = False,
            r: int = 1,
            bookmark: str = None,
            update: bool = True,
            stable: bool = None,
            execution_stats: bool = False
    ) -> Dict:
        """
        Shows which index is being used by the query. Parameters are the same as `Database.find`.

        Parameters
        ----------
        selector : Dict
            JSON object describing criteria used to select documents. More information provided in CouchDB's section on
            [selector syntax](https://docs.couchdb.org/en/main/api/database/find.html#find-selectors).
        limit : int
            Maximum number of results returned. Default is `25`.
        skip : int
            Skip the first `n` results, where `n` is the value specified. Default is `0`.
        sort : Dict
             JSON array following CouchDB's [sort syntax]
             (https://docs.couchdb.org/en/main/api/database/find.html#find-sort). Default is `None`.
        fields : List[str]
            Dictionary specifying which fields of each object should be returned. If it is omitted, the entire object
            is returned. More information provided in CouchDB's [section on filtering fields]
            (https://docs.couchdb.org/en/main/api/database/find.html#find-filter).
        use_index : Union[str, List[str]]
            Instruct a query to use a specific index. Specified either as `"<design_document>"` or
            `["<design_document>", "<index_name>"]`. Default is `None`.
        conflicts : bool
            Include conflicted documents if `True`. Intended use is to easily find conflicted documents,
            without an index or view. Default is `False`.
        r : int
            Read quorum needed for the result. This defaults to 1, in which case the document found in the index is
            returned. If set to a higher value, each document is read from at least that many replicas before it is
            returned in the results. This is likely to take more time than using only the document stored locally with
            the index. Default is `None`.
        bookmark : str
            A string that enables you to specify which page of results you require. Used for paging through result
            sets. Every query returns an opaque string under the `bookmark` key that can then be passed back in a query
            to get the next page of results. If any part of the selector query changes between requests, the results
            are undefined. Default is `None`.
        update: bool
            Whether to update the index prior to returning the result. Default is `True`.
        stable : bool
            Whether or not the view results should be returned from a “stable” set of shards. Default is `None`.
        execution_stats : bool
            Include [execution statistics](https://docs.couchdb.org/en/main/api/database/find.html#find-statistics) in
            the query response. Default is `False`.

        Returns
        -------
        Dict: A dictionary containing the following keys.

          - dbname (`str`) – Name of database
          - index (`Dict`) – Index used to fulfill the query
          - selector (`Dict`) – Query selector used
          - opts (`Dict`) – Query options used
          - limit (`int`) – Limit parameter used
          - skip (`int`) – Skip parameter used
          - fields (`List`) – Fields to be returned by the query
          - range (`Dict`) – Range parameters passed to the underlying view

        """
        return self._post(
            resource="_explain",
            body={
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
        ).json()

    def find(
            self,
            selector: Dict,
            limit: int = 25,
            skip: int = 0,
            sort: List[Dict] = None,
            fields: List[str] = None,
            use_index: Union[str, List[str]] = None,
            conflicts: bool = False,
            r: int = 1,
            bookmark: str = None,
            update: bool = True,
            stable: bool = None,
            execution_stats: bool = False,
            partition: str = None,
    ) -> Dict:
        """
        Find documents using a declarative JSON querying syntax.

        Parameters
        ----------
        selector : Dict
            JSON object describing criteria used to select documents. More information provided in CouchDB's section on
            [selector syntax](https://docs.couchdb.org/en/main/api/database/find.html#find-selectors).
        limit : int
            Maximum number of results returned. Default is `25`.
        skip : int
            Skip the first `n` results, where `n` is the value specified. Default is `0`.
        sort : Dict
             JSON array following CouchDB's [sort syntax]
             (https://docs.couchdb.org/en/main/api/database/find.html#find-sort). Default is `None`.
        fields : List[str]
            Dictionary specifying which fields of each object should be returned. If it is omitted, the entire object
            is returned. More information provided in CouchDB's [section on filtering fields]
            (https://docs.couchdb.org/en/main/api/database/find.html#find-filter).
        use_index : Union[str, List[str]]
            Instruct a query to use a specific index. Specified either as `"<design_document>"` or
            `["<design_document>", "<index_name>"]`. Default is `None`.
        conflicts : bool
            Include conflicted documents if `True`. Intended use is to easily find conflicted documents,
            without an index or view. Default is `False`.
        r : int
            Read quorum needed for the result. This defaults to 1, in which case the document found in the index is
            returned. If set to a higher value, each document is read from at least that many replicas before it is
            returned in the results. This is likely to take more time than using only the document stored locally with
            the index. Default is `None`.
        bookmark : str
            A string that enables you to specify which page of results you require. Used for paging through result
            sets. Every query returns an opaque string under the `bookmark` key that can then be passed back in a query
            to get the next page of results. If any part of the selector query changes between requests, the results
            are undefined. Default is `None`.
        update: bool
            Whether to update the index prior to returning the result. Default is `True`.
        stable : bool
            Whether or not the view results should be returned from a “stable” set of shards. Default is `None`.
        execution_stats : bool
            Include [execution statistics](https://docs.couchdb.org/en/main/api/database/find.html#find-statistics) in
            the query response. Default is `False`.
        partition: str
            An optional partition ID. Only valid for partitioned databases. (Default `None`.)

        Returns
        -------
        Dict: A dictionary containing the following keys.

          - `bookmark`
          - `docs`
          - `warning`
        """
        return self._post(
            resource=partitioned_db_resource_parser(
                resource="_find",
                partition=partition,
            ),
            body={
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
        ).json()

    def indexes(
            self,
    ) -> Dict:
        """
        Get a list of all indexes in the database.

        Returns
        -------
        Dict : A dictionary with the following keys.

          - total_rows (`int`) – Number of indexes
          - indexes (`List[Dict]`) – Array of index definitions
        """
        return self._get(resource="_index").json()

    def get(
            self,
            docid: str,
            *,
            attachments: bool = None,
            att_encoding_info: bool = None,
            atts_since: Iterable[str] = None,
            conflicts: bool = None,
            deleted_conflicts: bool = None,
            latest: bool = None,
            local_seq: bool = None,
            meta: bool = None,
            open_revs: Iterable[str] = None,
            rev: str = None,
            revs: bool = None,
            revs_info: bool = None,
            check: bool = False,
            default_value: Any = None,
    ) -> Union[Document, Any]:
        """
        Get a document by id.

        Parameters
        ----------
        docid : str
            The document's id.
        attachments : bool
            Includes attachments bodies in response. Default `None`.
        att_encoding_info : bool
            Includes encoding information in attachment stubs if the particular attachment is compressed.
            Default `None`.
        atts_since : Iterable[str]
            Includes attachments only since specified revisions. Doesn’t includes attachments for specified revisions.
            Default `None`.
        conflicts : bool
            Includes information about conflicts in document. Default `None`.
        deleted_conflicts : bool
            Includes information about deleted conflicted revisions. Default `None`.
        latest : bool
            Forces retrieving latest “leaf” revision, no matter what rev was requested. Default `None`.
        local_seq : bool
            Includes last update sequence for the document. Default `None`.
        meta : bool
            Acts same as specifying all conflicts, deleted_conflicts and revs_info query parameters. Default `None`.
        open_revs : Iterable[str]
            Retrieves documents of specified leaf revisions. Additionally, it accepts value as all to return all leaf
            revisions. Default `None`.
        rev : str
            Retrieves document of specified revision. Default `None`.
        revs : bool
            Includes list of all known document revisions. Default `None`.
        revs_info : bool
            Includes detailed information for all known document revisions. Default `None`.
        check : bool
            If `True`, raise an exception if `docid` cannot be found in the database. Default `False`.
        default_value : Any
            The default value to return if `check=False` and the `docid` is not in the database. Default `None`.

        Returns
        -------
        `couchdb3.document.Document`
        """
        try:
            return Document(**self._get(
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
                    "revs_info": revs_info
                }
            ).json())
        except (CouchDBError, requests.exceptions.RequestException) as error:
            if check is True:
                raise error
            return default_value

    def get_attachment(
            self,
            docid: str,
            attname: str,
            rev: str = None
    ) -> AttachmentDocument:
        """
        Get a document's attachment

        Parameters
        ----------
        docid : str
            The document's id.
        attname : str
            The attachment's name.
        rev : str
            A specific revision.

        Returns
        -------
        AttachmentDocument : A `couchdb3.document.AttachmentDocument` instance.
        """
        response = self._get(
            f"{docid}/{attname}",
            query_kwargs={"rev": rev}
        )
        return AttachmentDocument(
            content=response.content,
            content_encoding=response.headers.get("content-encoding"),
            content_length=response.headers.get("content-length"),
            content_type=response.headers.get("content-type"),
            digest="md5-" + response.headers.get("content-md5"),
        )

    def get_design(
            self,
            ddoc: str,
            **kwargs
    ) -> Document:
        """
        Get a design document.

        Parameters
        ----------
        ddoc: str
            The design document's name.
        kwargs
            Further `Database.get` parameters.

        Returns
        -------
        Document : A `couchdb3.document.Document` object containing the design document's content.
        """
        return self.get(
            docid=f"_design/{ddoc}",
            **kwargs
        )

    def purge(
            self,
            data: Dict
    ) -> Dict:
        """
        Purge permanently the given pairs of `(id,rev)`. When deleting a (revisions of a) document, the document is
        marked as `_deleted=true` as opposed to being completely purged. For more info, please refer to
        [the official documentation](https://docs.couchdb.org/en/main/api/database/misc.html#db-purge).

        Parameters
        ----------
        data : Dict
            A dictionary with document IDs as keys and list of revisions as values.

        Returns
        -------

        """
        return self._post(
            resource="_purge",
            body=data
        ).json()

    def put_attachment(
            self,
            docid: str,
            attname: str,
            path: str = None,
            *,
            content: Any = None,
            rev: str = None,
    ) -> Tuple[str, bool, str]:
        """
        Uploads the supplied content as an attachment to the specified document.
        The appropriate content-type is generated using `couchdb3.utils.content_type_getter`.

        Parameters
        ----------
        docid : str
            The document's id.
        attname : str
            The attachment's name.
        path : str
            The path ot the local file to be uploaded.
            Precisely one of the arguments `path` or `content` must be supplied.
        content : str
            The content to be uploaded.
            Precisely one of the arguments `path` or `content` must be supplied.
        rev : str
            The document's current revision. Must be supplied for existing documents.

        Returns
        -------
        Tuple[str, bool, str] : A tuple consisting of the following elements.

          - the document's id ( `str`)
          - the operation status (`bool`)
          - the revision ( `str`)
        """
        if (not content and not path) or (content and path):
            raise ValueError("Precisely one of the arguments \"attdata\" and  \"attloc\" must be provided.")
        content_type = content_type_getter(data=content, file_name=path)
        resource = f"{docid}/{attname}"
        query_kwargs = {"rev": rev}
        req_kwargs = {
            "headers": {
                "content-type": content_type_getter(data=content, file_name=path)
            }
        }
        if path:
            with open(path, "rb") as file:
                response = self._put(
                    resource=resource,
                    query_kwargs=query_kwargs,
                    data=file,
                    headers={
                        "content-type": content_type
                    }
                )
        else:
            req_kwargs.update({"body": content})
            response = self._put(
                resource=resource,
                query_kwargs=query_kwargs,
                body=content,
                headers={
                    "content-type": content_type
                }
            )
        data = response.json()
        return data["id"], data["ok"], data["rev"]

    def put_design(
            self,
            ddoc: str,
            *,
            rev: str = None,
            language: str = None,
            options: Dict = None,
            filters: Dict = None,
            updates: Dict = None,
            validate_doc_update: str = None,
            views: Dict = None,
            autoupdate: bool = None,
            partitioned: bool = None,
            **kwargs
    ) -> Tuple[str, bool, str]:
        """
        Create or update a named design document. For more info, please refer to
        [the official documentation](https://docs.couchdb.org/en/latest/api/ddoc/common.html#put--db-_design-ddoc).

        Parameters
        ----------
        ddoc : str
            The design document's name.
        rev : str
            The design document's revision in case of an update.
        language : str
            Defines [Query Server](https://docs.couchdb.org/en/latest/query-server/index.html#query-server) to process
            design document functions.
        options : Dict
            View’s default options.
        filters : Dict
            [Filter functions](https://docs.couchdb.org/en/latest/ddocs/ddocs.html#filterfun) definition.
        updates : Dict
            [Update functions](https://docs.couchdb.org/en/latest/ddocs/ddocs.html#updatefun) definition.
        validate_doc_update : str
            [Validate document update](https://docs.couchdb.org/en/latest/ddocs/ddocs.html#vdufun) function source.
        views : Dict
            [View functions](https://docs.couchdb.org/en/latest/ddocs/ddocs.html#viewfun) definition.
        autoupdate : bool
            Indicates whether to automatically build indexes defined in this design document.
        partitioned : bool
            Set to `True` for a partitioned design.
        kwargs
        Further `Database.save` parameters.

        Returns
        -------
        Tuple[str, bool, str] : The document's id ( `str`), the operation status (`bool`) and the revision ( `str`).
        """
        if partitioned:
            options = (options or dict()).update({
                "partitioned": partitioned
            })
        return self.save(
            doc={
                "_id": f"_design/{ddoc}",
                "_rev": rev,
                "language": language,
                "options": options,
                "filters": filters,
                "updates": updates,
                "validate_doc_update": validate_doc_update,
                "views": views,
                "autoupdate": autoupdate
            },
            **kwargs
        )

    def save(
            self,
            doc: Union[Dict, Document],
            batch: bool = None,
            new_edits: bool = None,
            path: str = None
    ) -> Tuple[str, bool, str]:
        """
        Create a new named document, or a new revision of the existing document.

        Parameters
        ----------
        doc : Union[Dict, couchdb3.document.Document]
            A dictionary or a `couchdb3.document.Document` instance containing a valid identifier (`doc["_id"]`)
            as well as revision number (`doc["_rev"]`) if need be.
        batch : bool
            Store document in batch mode. Default `None`.
        new_edits : bool
            Prevents insertion of a conflicting document. If false, a well-formed _rev must be included in the document.
            `new_edits=False` is used by the replicator to insert documents into the target database even if that leads
            to the creation of conflicts.
        path : str
            Database path, e.g `_design`. Default `None`.

        Returns
        -------
        Tuple[str, bool, str] : The document's id ( `str`), the operation status (`bool`) and the revision ( `str`).
        """
        """
        :return: 
        """
        batch = "ok" if batch else None
        data = self._put(
            resource="%s/%s" % (path, doc.get("_id")) if path else doc.get("_id"),
            body=doc,
            query_kwargs={
                "batch": "ok" if batch else None,
                "new_edits": new_edits,
                "rev": doc.get("_rev")
            }
        ).json()
        return data["id"], data["ok"], data["rev"]

    def save_index(
            self,
            index: Dict,
            ddoc: str = None,
            name: str = None,
            index_type: str = "json",
            partitioned: bool = None
    ) -> Tuple[str, str, str]:
        """
        Create a new index on a database.

        Parameters
        ----------
        index : Dict
            Dictionary describing the index to create.
        ddoc : str
            Name of the design document in which the index will be created. By default, each index will be created in
            its own design document. Indexes can be grouped into design documents for efficiency. However, a change to
            one index in a design document will invalidate all other indexes in the same document (similar to views).
        name : str
            Name of the index. If no name is provided, a name will be generated automatically.
        index_type : str
            Can be `json`  or `text`. Defaults to `json`. Geospatial indexes will be supported in the future. Optional
            Text indexes are supported via a third party library
        partitioned : bool
             Determines whether a JSON index is partitioned or global. The default value of `partitioned` is the
             `partitioned` property of the database. To create a global index on a partitioned database, specify `False`
             for the `"partitioned"` field. If you specify `True` for the `"partitioned"` field on an unpartitioned
             database, an error occurs.

        Returns
        -------
        Tuple[str, str, str]: A tuple consisting of the following elements.

          - result (`str`) – Flag to show whether the index was created or one already exists. Can be `"created"` or
          `"exists"`.
          - id (`str`) – Id of the design document the index was created in.
          - name (`str`) – Name of the index created.
        """
        data = self._post(
            resource="_index",
            body={
                "index": index,
                "ddoc": ddoc,
                "name": name,
                "type": index_type,
                "partitioned": partitioned
            }
        ).json()
        return data["result"], data["id"], data["name"]

    def security(
            self
    ) -> SecurityDocument:
        """
        Returns the current security object from the specified database.

        Returns
        -------
        SecurityDocument : A `couchdb3.document.SecurityDocument` object.
        """
        data = self._get(
            resource="_security"
        ).json()
        return SecurityDocument(**data)

    def update_security(
            self,
            admins: Union[Dict, SecurityDocumentElement],
            members: Union[Dict, SecurityDocumentElement],
    ) -> bool:
        """
        Update database security.

        Parameters
        ----------
        admins : Union[Dict, SecurityDocumentElement]
            Object with two fields as `names` and `roles`. [See the official
            documentation](https://docs.couchdb.org/en/main/api/database/security.html#db-security) for more info.
        members : Union[Dict, SecurityDocumentElement]
            Object with two fields as `names` and `roles`. [See the official
            documentation](https://docs.couchdb.org/en/main/api/database/security.html#db-security) for more info.

        Returns
        -------
        bool :  Operation status.
        """
        return self._put(
            resource="_security",
            body={
                "admins": admins,
                "members": members
            }
        ).json()["ok"]

    def view(
            self,
            ddoc: str,
            view: str = None,
            *,
            partition: str = None,
            conflicts: bool = None,
            descending: bool = None,
            endkey: str = None,
            endkey_docid: str = None,
            group: bool = None,
            group_level: int = None,
            include_docs: bool = None,
            attachments: bool = None,
            att_encoding_info: bool = None,
            inclusive_end: bool = None,
            key: str = None,
            keys: Iterable[str] = None,
            limit: int = None,
            reduce: bool = None,
            skip: int = None,
            sort: bool = None,
            stable: bool = None,
            startkey: str = None,
            startkey_docid: str = None,
            update: str = None,
            update_seq: bool = None
    ) -> ViewResult:
        """
        Executes the specified view function from the specified design document, c.f [the official
        documentation](https://docs.couchdb.org/en/main/api/ddoc/views.html#db-design-design-doc-view-view-name).

        Parameters
        ----------
        ddoc : str
            The corresponding design document's id.
        view : str
            The view's id.
        partition: str
            An optional partition ID. Only valid for partitioned databases. (Default `None`.)
        conflicts : bool
            Include conflicts information in response. Ignored if `include_docs` isn’t `True`. Default is `None`.
        descending : bool
            Return the documents in descending order by key. Default is `None`.
        endkey : str
             Stop returning records when the specified key is reached. Default is `None`
        endkey_docid: str
            Stop returning records when the specified document ID is reached. Ignored if `endkey` is not set. Default
            is `None`.
        group: bool
            Group the results using the reduce function to a group or single row. Implies `reduce` is `true` and the
            maximum `group_level`. Default is `None`.
        group_level : int
             Specify the group level to be used. Implies group is true. Default is `None`.
        include_docs : bool
            Include the associated document with each row. Default is `None`.
        attachments : bool
            Include the Base64-encoded content of attachments in the documents that are included if `include_docs` is
            `True`. Ignored if `include_docs` isn’t `True`. Default is `None`.
        att_encoding_info : bool
            Include encoding information in attachment stubs if `include_docs` is `True` and the particular attachment
            is compressed. Ignored if `include_docs` isn’t `True`. Default is `False`.
        inclusive_end : bool
            Specifies whether the specified end key should be included in the result. Default is `None`.
        key : str
            Return only documents that match the specified key. Default is `None`.
        keys: Iterable[str]
            Return only documents where the key matches one of the keys specified in the argument. Default is `None`.
        limit : int
            Limit the number of the returned documents to the specified number.  Default is `None`.
        reduce : bool
            Use the reduction function. Default is `True` when a reduce function is defined. Default is `None`.
        skip : int
            Skip this number of records before starting to return the results. Default is `None`.
        sort : bool
            Sort returned rows (see Sorting Returned Rows). Setting this to `False` offers a performance boost. The
            `total_rows` and `offset` fields are not available when this is set to `False`. Default is `None`.
        stable : bool
            Whether or not the view results should be returned from a stable set of shards. Default is `None`.
        startkey : str
            Return records starting with the specified key. Default is `None`
        startkey_docid : str
            Return records starting with the specified document ID. Ignored if `startkey` is not set. Default is `None`
        update : str
            Whether or not the view in question should be updated prior to responding to the user. Supported values:

            - `true`
            - `false`
            - `lazy`

            Default is `None`.
        update_seq : bool
             Whether to include in the response an `update_seq` value indicating the sequence id of the database the
             view reflects. Default is `False`.

        Returns
        -------
        `view.ViewResult`
        """
        path = partitioned_db_resource_parser(
            resource="_design",
            partition=partition,
        )
        return ViewResult(**self._get(
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
                "update_seq": update_seq
            }
        ).json())

    def get_partition(self, partition_id: str) -> Partition:
        """
        Get a given partition.

        Parameters
        ----------
        partition_id : str
            The partition's ID.

        Returns
        -------
        `Partition`
        """
        return Partition(
            partition_id=partition_id,
            name=self.name,
            url=self.url,
            port=self.port,
            user=self._user,
            password=self._password,
            disable_ssl_verification=not self.session.verify,
            auth_method=self.auth_method,
            session=self.session,
        )


class Partition(Database):
    """
    Abstract Couchdb partition
    """
    def __init__(
            self,
            partition_id: str,
            name: str,
            *,
            url: str = None,
            port: int = None,
            user: str = None,
            password: str = None,
            disable_ssl_verification: bool = False,
            auth_method: str = None,
            timeout: int = DEFAULT_TIMEOUT,
            session: requests.Session = None,
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
            Controls whether to verify the server’s TLS certificate. Set to `True` when connecting to a server with
            self-signed TLS certificates. Default `False`.
        auth_method : str
            Authentication method. Choices are `cookie` or `basic`. Default is `couchdb3.utils.DEFAULT_AUTH_METHOD`.
        timeout : int
            The default timeout for requests. Default c.f. `couchdb3.utils.DEFAULT_TIMEOUT`.
        session: requests.Session
            A specific session to use. Optional - if not provided, a new session will be initialized.
        """
        super(Partition, self).__init__(
            name=name,
            url=url,
            session=session,
            port=port,
            user=user,
            password=password,
            disable_ssl_verification=disable_ssl_verification,
            auth_method=auth_method,
            timeout=timeout
        )
        self.partition_id = partition_id
        # self.root = f"{name}/_partition/{partition_id}"

    def __repr__(self) -> str:
        return f"{super(Partition, self).__repr__()}/{self.partition_id}"

    def all_docs(
            self,
            keys: Iterable[str] = None,
            **kwargs
    ) -> ViewResult:
        """
        Executes the built-in _all_docs view, returning all the documents in the partition.

        Parameters
        ----------
        keys : Iterable[str]
            Return only documents where the key matches one of the keys specified in the argument. Default is `None`.
        kwargs
            Further `couchdb3.database.Database.view` parameters.

        Returns
        -------
        ViewResult
        """
        return super(Partition, self).all_docs(partition=self.partition_id, keys=keys, **kwargs)

    # noinspection PyMethodOverriding
    def info(
            self,
    ) -> Dict:
        """
        Return the partition's info by sending a `GET` request to `/self.root`.

        Returns
        -------
        Dict: A dictionary containing the server's or database's info.
        """
        return super(Partition, self).info(partition=self.partition_id)

    # noinspection PyMethodOverriding
    def find(
            self,
            selector: Dict,
            limit: int = 25,
            skip: int = 0,
            sort: List[Dict] = None,
            fields: List[str] = None,
            use_index: Union[str, List[str]] = None,
            conflicts: bool = False,
            r: int = 1,
            bookmark: str = None,
            update: bool = True,
            stable: bool = None,
            execution_stats: bool = False
    ) -> Dict:
        """
        See `Database.find`.
        """
        return super(Partition, self).find(
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

    # noinspection PyMethodOverriding
    def view(
            self,
            ddoc: str,
            view: str = None,
            *,
            # partition: str = None,
            conflicts: bool = None,
            descending: bool = None,
            endkey: str = None,
            endkey_docid: str = None,
            group: bool = None,
            group_level: int = None,
            include_docs: bool = None,
            attachments: bool = None,
            att_encoding_info: bool = None,
            inclusive_end: bool = None,
            key: str = None,
            keys: Iterable[str] = None,
            limit: int = None,
            reduce: bool = None,
            skip: int = None,
            sort: bool = None,
            stable: bool = None,
            startkey: str = None,
            startkey_docid: str = None,
            update: str = None,
            update_seq: bool = None
    ) -> ViewResult:
        """
        Executes the specified view function from the specified design document, c.f [the official
        documentation](https://docs.couchdb.org/en/main/api/ddoc/views.html#db-design-design-doc-view-view-name).

        Parameters
        ----------
        ddoc : str
            The corresponding design document's id.
        view : str
            The view's id.
        conflicts : bool
            Include conflicts information in response. Ignored if `include_docs` isn’t `True`. Default is `None`.
        descending : bool
            Return the documents in descending order by key. Default is `None`.
        endkey : str
             Stop returning records when the specified key is reached. Default is `None`
        endkey_docid: str
            Stop returning records when the specified document ID is reached. Ignored if `endkey` is not set. Default
            is `None`.
        group: bool
            Group the results using the reduce function to a group or single row. Implies `reduce` is `true` and the
            maximum `group_level`. Default is `None`.
        group_level : int
             Specify the group level to be used. Implies group is true. Default is `None`.
        include_docs : bool
            Include the associated document with each row. Default is `None`.
        attachments : bool
            Include the Base64-encoded content of attachments in the documents that are included if `include_docs` is
            `True`. Ignored if `include_docs` isn’t `True`. Default is `None`.
        att_encoding_info : bool
            Include encoding information in attachment stubs if `include_docs` is `True` and the particular attachment
            is compressed. Ignored if `include_docs` isn’t `True`. Default is `False`.
        inclusive_end : bool
            Specifies whether the specified end key should be included in the result. Default is `None`.
        key : str
            Return only documents that match the specified key. Default is `None`.
        keys: Iterable[str]
            Return only documents where the key matches one of the keys specified in the argument. Default is `None`.
        limit : int
            Limit the number of the returned documents to the specified number.  Default is `None`.
        reduce : bool
            Use the reduction function. Default is `True` when a reduce function is defined. Default is `None`.
        skip : int
            Skip this number of records before starting to return the results. Default is `None`.
        sort : bool
            Sort returned rows (see Sorting Returned Rows). Setting this to `False` offers a performance boost. The
            `total_rows` and `offset` fields are not available when this is set to `False`. Default is `None`.
        stable : bool
            Whether or not the view results should be returned from a stable set of shards. Default is `None`.
        startkey : str
            Return records starting with the specified key. Default is `None`
        startkey_docid : str
            Return records starting with the specified document ID. Ignored if `startkey` is not set. Default is `None`
        update : str
            Whether or not the view in question should be updated prior to responding to the user. Supported values:

            - `true`
            - `false`
            - `lazy`

            Default is `None`.
        update_seq : bool
             Whether to include in the response an `update_seq` value indicating the sequence id of the database the
             view reflects. Default is `False`.

        Returns
        -------
        `view.ViewResult`
        """
        return super(Partition, self).view(
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
            update_seq=update_seq
        )

    def bulk_docs(
            self,
            docs: List[Union[Dict, Document]],
            new_edits: bool = True
    ) -> List[Dict]:
        """
        See `Database.bulk_docs`.

        Note:
        Appends the partition's ID to the documents' ID.
        """
        return super(Partition, self).bulk_docs(
            docs=[self.add_partition_to_doc(doc) for doc in docs],
            new_edits=new_edits,
        )

    def bulk_get(
            self,
            docs: List[Union[Dict, Document]],
            revs: bool = False,
    ) -> List[Dict]:
        """
        See `Database.bulk_get`.

        Note:
        Appends the partition's ID to the documents' ID.
        """
        return super(Partition, self).bulk_get(
            docs=[self.add_partition_to_doc(doc) for doc in docs],
            revs=revs,
        )

    def copy(
            self,
            docid: str,
            destid: str,
            rev: str = None,
            destrev: str = None
    ) -> Tuple[str, bool, str]:
        """
        See `Database.copy`.

        Note:
        Appends the partition's ID to the document's ID.
        """
        return super(Partition, self).copy(
            docid=self.add_partition_to_str(docid),
            destid=self.add_partition_to_str(destid),
            rev=rev,
            destrev=destrev,
        )

    def create(
            self,
            doc: Union[Dict, Document],
            *,
            batch: bool = None
    ) -> Tuple[str, bool, str]:
        """
        See `Database.create`.

        Note:
        Appends the partition's ID to the document's ID.
        """
        return super(Partition, self).create(
            doc=self.add_partition_to_doc(doc),
            batch=batch,
        )

    def delete(
            self,
            docid: str,
            rev: str,
            *,
            batch: bool = None
    ) -> bool:
        """
        See `Database.delete`.

        Note:
        Appends the partition's ID to the document's ID.
        """
        return super(Partition, self).delete(
            docid=self.add_partition_to_str(docid),
            rev=rev,
            batch=batch,
        )

    def delete_attachment(
            self,
            docid: str,
            attname: str,
            rev: str,
            *,
            batch: bool = False
    ) -> bool:
        """
        See `Database.delete_attachment`.

        Note:
        Appends the partition's ID to the document's ID.
        """
        return super(Partition, self).delete_attachment(
            docid=self.add_partition_to_str(docid),
            attname=attname,
            rev=rev,
            batch=batch,
        )

    def get(
            self,
            docid: str,
            *,
            attachments: bool = None,
            att_encoding_info: bool = None,
            atts_since: Iterable[str] = None,
            conflicts: bool = None,
            deleted_conflicts: bool = None,
            latest: bool = None,
            local_seq: bool = None,
            meta: bool = None,
            open_revs: Iterable[str] = None,
            rev: str = None,
            revs: bool = None,
            revs_info: bool = None,
            check: bool = False,
            default_value: Any = None,
    ) -> Union[Document, Any]:
        """
        See `Database.get`.

        Note:
        Appends the partition's ID to the document's ID.
        """
        return super(Partition, self).get(
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

    def get_attachment(
            self,
            docid: str,
            attname: str,
            rev: str = None
    ) -> AttachmentDocument:
        """
        See `Database.get_attachment`.

        Note:
        Appends the partition's ID to the document's ID.
        """
        return super(Partition, self).get_attachment(
            docid=self.add_partition_to_str(docid),
            attname=attname,
            rev=rev,
        )

    def put_attachment(
            self,
            docid: str,
            attname: str,
            path: str = None,
            *,
            content: Any = None,
            rev: str = None,
    ) -> Tuple[str, bool, str]:
        """
        See `Database.put_attachment`.

        Note:
        Appends the partition's ID to the document's ID.
        """
        return super(Partition, self).put_attachment(
            docid=self.add_partition_to_str(docid),
            attname=attname,
            path=path,
            content=content,
            rev=rev,
        )

    def rev(
            self,
            resource: str
    ) -> Optional[str]:
        """
        See `Database.rev`.
        """
        return super(Partition, self).rev(self.add_partition_to_str(resource))

    def save(
            self,
            doc: Union[Dict, Document],
            batch: bool = None,
            new_edits: bool = None,
            path: str = None
    ) -> Tuple[str, bool, str]:
        """
        See `Database.save`.

        Note:
        Appends the partition's ID to the document's ID.
        """
        return super(Partition, self).save(
            doc=self.add_partition_to_doc(doc),
            batch=batch,
            new_edits=new_edits,
            path=path,
        )

    def __contains__(self, item):
        return super(Partition, self).__contains__(self.add_partition_to_str(item))

    def add_partition_to_str(self, string: str) -> str:
        """
        Append the instance's partition ID to a string.
        """
        if string.startswith(self.partition_id):
            return string
        return f"{self.partition_id}:{string}"

    def add_partition_to_doc(self, doc: Union[Document, Dict]) -> Union[Document, Dict]:
        """
        Append the instance's partition ID to the document's ID.
        """
        docid = doc.get("_id")
        if docid is None:
            return doc
        doc["_id"] = self.add_partition_to_str(docid)
        return doc
