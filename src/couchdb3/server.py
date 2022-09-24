#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from typing import Dict, List, Tuple, Union

from .base import Base
from .database import Database
from .exceptions import ConflictError, CouchDBError, NotFoundError, ProxySchemeComplianceError, UserIDComplianceError
from .utils import user_name_to_id, validate_proxy, validate_user_id, DEFAULT_TIMEOUT


__all__ = [
    "Server"
]


class Server(Base):
    """
    Abstract Couchdb client
    """
    def __init__(
            self,
            url: str,
            *,
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
        super(Server, self).__init__(
            url=url,
            port=port,
            user=user,
            password=password,
            disable_ssl_verification=disable_ssl_verification,
            auth_method=auth_method,
            timeout=timeout,
            session=session,
        )

    def __getitem__(self, item) -> Database:
        return self.get(item, check=True)

    def __repr__(self) -> str:
        """
        Close the session on delete.

        Returns
        -------
        str
        """
        return f"{super(Server, self).__repr__()}: {self.url}"

    def active_tasks(
            self,
    ) -> List[Dict]:
        """
        List of running tasks, including the task type, name, status and process ID. The result is a JSON array of the
        currently running tasks, with each task being described with a single object. Depending on operation type set
        of response object fields might be different.

        Returns
        -------
        List[Dict]
        """
        return self._get(
            resource="_active_tasks"
        ).json()

    def check_user(
            self,
            username: str,
            password: str
    ) -> bool:
        """
        Checks the username/password combination by creating a `Server` instance and performing a `Server.check`
        request.

        Parameters
        ----------
        username : str
            The CouchDB user's name.
        password : str
            The CouchDB user's password.

        Returns
        -------
        bool : A boolean indicating if the username/password combination is valid.
        """
        return Server(
            url=self.url,
            user=username,
            password=password
        ).check()

    def save_user(
            self,
            name: str,
            *,
            user_id: str = None,
            derived_key: str = None,
            roles: List[str] = None,
            password: str = None,
            password_sha: str = None,
            password_scheme: str = None,
            salt: str = None,
            iterations: int = None,
            rev: str = None
    ) -> Tuple[bool, str, str]:
        """
        Create or update a user. In case of a `ConflictError`, a `HEAD` request to `/_users/<user_id>` will be sent to
        obtain the latest revision.

        Parameters
        ----------
        name : str
            User’s name aka login. Immutable e.g. you cannot rename an existing user - you have to create new one.
        user_id : str
            The user’s login with the special prefix `org.couchdb.user:`.
        derived_key : str
            PBKDF2 key derived from salt/iterations.
        roles : List[str]
            List of user roles. CouchDB doesn’t provide any built-in roles, so you’re free to define your own depending
            on your needs. However, you cannot set system roles like `_admin` there. Also, only administrators may
            assign roles to users - by default all users have no roles.
        password : str
            A plaintext password can be provided, but will be replaced by hashed fields before the document is actually
            stored.
        password_sha : str
            Hashed password with salt. Used for `simple` password_scheme.
        password_scheme : str
             Password hashing scheme. May be `simple` or `pbkdf2`.
        salt : str
            Hash salt. Used for both `simple` and `pbkdf2` `password_scheme` options.
        iterations : int
            Number of iterations to derive key, used for `pbkdf2` `password_scheme`.
        rev : str
            The user's current revision. Needed when updating an existing user.

        Returns
        -------
        Tuple[bool, str, str]: A tuple consisting of the following elements.

          - the success status (`bool`)
          - the user ID ( `str`)
          - the current revision ( `str`)
        """
        if user_id and validate_user_id(user_id=user_id) is False:
            raise UserIDComplianceError(
                "User ID does not comply with the CouchDB requirements. "
                "See https://docs.couchdb.org/en/main/intro/security.html#why-the-org-couchdb-user-prefix."
            )
        user_id = user_id or user_name_to_id(name)
        body = {
            "_id": user_id,
            "_rev": rev,
            "derived_key": derived_key,
            "name": name,
            "roles": roles or [],
            "password": password,
            "password_sha": password_sha,
            "password_scheme": password_scheme,
            "salt": salt,
            "iterations": iterations,
            "type": "user"
        }
        try:
            response = self._put(
                resource=f"_users/{user_id}",
                body=body
            )
        except ConflictError:
            body.update({"_rev": self.rev(f"_users/{user_id}")})
            response = self._put(
                resource=f"_users/{user_id}",
                body=body
            )
        data = response.json()
        return data["ok"], data["id"], data["rev"]

    def all_dbs(
            self,
            *,
            descending: bool = False,
            endkey: str = None,
            limit: int = None,
            skip: int = 0,
            startkey: str = None,
    ) -> List[str]:
        """
        Get all database names.

        Parameters
        ----------
        descending : bool
            Return the databases in descending order by key. Default `False`.
        endkey : str
            Stop returning databases when the specified key is reached. Default `None`.
        limit : int
            Limit the number of the returned databases to the specified number. Default `None`.
        skip : int
            Skip this number of databases before starting to return the results. Default `0`.
        startkey : str
            Return databases starting with the specified key. Default `None`.

        Returns
        -------
        List[str] : A list of database names.
        """
        return self._get(
            "_all_dbs",
            query_kwargs={
                "descending": descending,
                "endkey": endkey,
                "limit": limit,
                "skip": skip,
                "startkey": startkey,
            }
        ).json()

    def create(
            self,
            name: str,
            q: int = None,
            n: int = None,
            partitioned: bool = False,
    ) -> Database:
        """
        Create a database.

        Parameters
        ----------
        name : str
            The database's name.
        q : int
            Shards, aka the number of range partitions. Default `None` (i.e. server default will be used: `8`, unless
            overridden in the `cluster config`).
        n : int
            Replicas. The number of copies of the database in the cluster. Default `None` (i.e. server default will be
            used: `3`, unless overridden in the `cluster config`).
        partitioned : bool
            Whether to create a partitioned database. Default `False`.

        Returns
        -------
        couchdb3.database.Database
        """
        self._put(
            resource=name,
            query_kwargs={
                "q": q,
                "n": n,
                "partitioned": partitioned
            }
        )
        return self.get(name=name)

    def dbs_info(
            self,
            keys: List[str]
    ) -> List[Dict]:
        """
        Returns information of a list of the specified databases in the CouchDB instance.

        Parameters
        ----------
        keys : List[str]
            List of database names to be requested

        Returns
        -------
        List[Dict] : A list dictionaries containing the corresponding database info.
        """
        return self._post(
            resource="_dbs_info",
            body={
                "keys": keys
            }
        ).json()

    def get(
            self,
            name: str,
            check: bool = False
    ) -> Database:
        """
        Get a database by name.

        Parameters
        ----------
        name : str
            The name of the database.
        check : bool
            If `True`, raise an exception if database `name` cannot be found in the server. Default `False`.

        Returns
        -------
        couchdb3.database.Database

        """
        db = Database(
            name=name,
            url=self.url,
            user=self._user,
            password=self._password,
            disable_ssl_verification=not self.session.verify,
            auth_method=self.auth_method,
            session=self.session,
        )
        try:
            db._head()
        except (NotFoundError, requests.exceptions.RequestException) as error:
            if check is True:
                raise error
        except CouchDBError as error:
            raise error
        return db

    def delete(
            self,
            resource: str = None
    ) -> bool:
        """
        Delete a database.

        Parameters
        ----------
        resource : str
            The database's name.

        Returns
        -------
        bool: `True` upon successful deletion.
        """
        self._delete(resource=resource)
        return True

    def replicate(
            self,
            source: Union[Dict, str],
            target: Union[Dict, str],
            replication_id: str = None,
            cancel: bool = None,
            continuous: bool = None,
            create_target: bool = None,
            create_target_params: Dict = None,
            doc_ids: List[str] = None,
            filter_func: str = None,
            selector: Dict = None,
            source_proxy: str = None,
            target_proxy: str = None
    ) -> Dict:
        """
        Request, configure, or stop, a replication operation. For more info, please refer to
        [the official documentation](https://docs.couchdb.org/en/main/api/server/common.html#replicate).

        Parameters
        ----------
        source : Union[Dict, str]
            Fully qualified source database URL or an object which contains the full URL of the source database with
            additional parameters like headers. Eg:

                "source_db_name"

            or

                "http://example.com/source_db_name"

            or

                {“url”:”url in here”, “headers”: {“header1”:”value1”, …}}

            For backwards compatibility, CouchDB 3.x will
            auto-convert bare database names by prepending the address and port CouchDB is listening on, to form a
            complete URL. This behaviour is deprecated in 3.x and will be removed in CouchDB 4.0.
        target : Union[Dict, str]
            Fully qualified target database URL or an object which contains the full URL of the source database with
            additional parameters like headers. Eg:

                "target_db_name"

            or

                "http://example.com/target_db_name"

            or

                {“url”:”url in here”, “headers”: {“header1”:”value1”, …}}

            For backwards compatibility, CouchDB 3.x will
            auto-convert bare database names by prepending the address and port CouchDB is listening on, to form a
            complete URL. This behaviour is deprecated in 3.x and will be removed in CouchDB 4.0.

            For backwards compatibility, CouchDB 3.x will
            auto-convert bare database names by prepending the address and port CouchDB is listening on, to form a
            complete URL. This behaviour is deprecated in 3.x and will be removed in CouchDB 4.0.
        replication_id : str
            The ID of the replication document.
        cancel : bool
            Cancels the replication.
        continuous : bool
            Configure the replication to be continuous.
        create_target : bool
            Creates the target database. Required administrator’s privileges on target server.
        create_target_params : Dict
            An object that contains parameters to be used when creating the target database. Can include the standard
            `q` and `n` parameters.
        doc_ids : List[str]
            Array of document IDs to be synchronized. `doc_ids`, `filter` and `selector` are mutually exclusive.
        filter_func : str
             The name of a [filter function](https://docs.couchdb.org/en/main/ddocs/ddocs.html#filterfun).
             `doc_ids`, `filter` and `selector` are mutually exclusive.
        selector : Dict
            A [selector](https://docs.couchdb.org/en/main/api/database/find.html#find-selectors) to filter documents
            for synchronization. Has the same behavior as the
            [selector objects](https://docs.couchdb.org/en/main/replication/replicator.html#selectorobj) in replication
            documents. `doc_ids`, `filter` and `selector` are mutually exclusive.
        source_proxy : str
            Address of a proxy server through which replication from the source should occur (protocol can be `"http”`
            or `“socks5”`).
        target_proxy : str
            Address of a proxy server through which replication to the target should occur (protocol can be `"http”`
            or `“socks5”`).

        Returns
        -------
        Dict : A dictionary with the following keys.

          - history (`list`) - Replication history
          - ok (`bool`) - Replication status
          - replication_id_version (`int`) – Replication protocol version
          - session_id (`str`) – Unique session ID
          - source_last_seq (`int`) – Last sequence number read from source database
        """
        if (
                source_proxy and validate_proxy(source_proxy) is False
        ) or (
                target_proxy and validate_proxy(target_proxy) is False
        ):
            raise ProxySchemeComplianceError("Proxy has invalid scheme.")
        if sum(bool(_) for _ in [doc_ids, filter_func, selector]) > 1:
            raise CouchDBError("Arguments \"doc_ids\", \"filter_func\" and \"selector\" are mutually exclusive.")
        return self._post(
            resource="_replicator",
            body={
                "_id": replication_id,
                "source": source,
                "target": target,
                "cancel": cancel,
                "continuous": continuous,
                "create_target": create_target,
                "create_target_params": create_target_params,
                "doc_ids": doc_ids,
                "filter_func": filter_func,
                "selector": selector,
                "source_proxy": source_proxy,
                "target_proxy": target_proxy
            }
        ).json()

    def up(self) -> bool:
        """
        Check if the server is up.

        Returns
        -------
        bool : `True` if the server is up.
        """
        try:
            self._get(resource="_up")
            return True
        except (CouchDBError, requests.exceptions.RequestException):
            return False
