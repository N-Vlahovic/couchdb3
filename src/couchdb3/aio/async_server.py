#!/usr/bin/env python3

import httpx

from ..exceptions import (
    ConflictError,
    CouchDBError,
    NotFoundError,
    ProxySchemeComplianceError,
    UserIDComplianceError,
)
from ..utils import (
    DEFAULT_TIMEOUT,
    rm_nones_from_dict,
    user_name_to_id,
    validate_proxy,
    validate_user_id,
)
from .async_base import AsyncBase
from .async_database import AsyncDatabase

__all__ = ["AsyncServer"]


class AsyncServer(AsyncBase):
    """
    Async CouchDB server client. Mirrors `Server` with `async def` methods throughout.

    Use as an async context manager (recommended) or manage the lifecycle manually
    via `await client.aclose()`.

    Note: `__getitem__` is not supported on async classes — Python does not allow
    `__getitem__` to be a coroutine. Use `await client.get(name)` instead.

    Examples
    --------
    >>> async with AsyncServer("http://user:password@127.0.0.1:5984") as client:
    ...     print(await client.up())
    True
    """

    def __init__(
        self,
        url: str,
        *,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        disable_ssl_verification: bool = False,
        auth_method: str | None = None,
        timeout: int | None = DEFAULT_TIMEOUT,
        session: httpx.AsyncClient | None = None,
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
        """
        super().__init__(
            url=url,
            port=port,
            user=user,
            password=password,
            disable_ssl_verification=disable_ssl_verification,
            auth_method=auth_method,
            timeout=timeout,
            session=session,
        )

    def __repr__(self) -> str:
        """
        Returns
        -------
        str
        """
        return f"{super().__repr__()}: {self.url}"

    async def active_tasks(self) -> list[dict]:
        """
        List of running tasks, including the task type, name, status and process ID.

        Returns
        -------
        list[dict]
        """
        return (await self._get(resource="_active_tasks")).json()

    async def check_user(self, username: str, password: str) -> bool:
        """
        Checks the username/password combination by creating a temporary `AsyncServer`
        instance and performing a `check` request.

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
        async with AsyncServer(url=self.url, user=username, password=password) as client:
            return await client.check()

    async def save_user(
        self,
        name: str,
        *,
        user_id: str | None = None,
        derived_key: str | None = None,
        roles: list[str] | None = None,
        password: str | None = None,
        password_sha: str | None = None,
        password_scheme: str | None = None,
        salt: str | None = None,
        iterations: int | None = None,
        rev: str | None = None,
    ) -> tuple[bool, str, str]:
        """
        Create or update a user. In case of a `ConflictError`, a `HEAD` request to
        `/_users/<user_id>` will be sent to obtain the latest revision.

        Parameters
        ----------
        name : str
            User's name aka login. Immutable — you cannot rename an existing user.
        user_id : str
            The user's login with the special prefix `org.couchdb.user:`.
        derived_key : str
            PBKDF2 key derived from salt/iterations.
        roles : list[str]
            List of user roles.
        password : str
            A plaintext password — will be replaced by hashed fields before storage.
        password_sha : str
            Hashed password with salt. Used for `simple` password_scheme.
        password_scheme : str
            Password hashing scheme. May be `simple` or `pbkdf2`.
        salt : str
            Hash salt.
        iterations : int
            Number of iterations to derive key, used for `pbkdf2` password_scheme.
        rev : str
            The user's current revision. Needed when updating an existing user.

        Returns
        -------
        tuple[bool, str, str] : (success, user_id, revision)
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
            "type": "user",
        }
        try:
            response = await self._put(resource=f"_users/{user_id}", body=body)
        except ConflictError:
            body.update({"_rev": await self.rev(f"_users/{user_id}")})
            response = await self._put(resource=f"_users/{user_id}", body=body)
        data = response.json()
        return data["ok"], data["id"], data["rev"]

    async def all_dbs(
        self,
        *,
        descending: bool = False,
        endkey: str | None = None,
        limit: int | None = None,
        skip: int = 0,
        startkey: str | None = None,
    ) -> list[str]:
        """
        Get all database names.

        Parameters
        ----------
        descending : bool
            Return the databases in descending order by key. Default `False`.
        endkey : str
            Stop returning databases when the specified key is reached. Default `None`.
        limit : int
            Limit the number of the returned databases. Default `None`.
        skip : int
            Skip this number of databases before starting to return results. Default `0`.
        startkey : str
            Return databases starting with the specified key. Default `None`.

        Returns
        -------
        list[str] : A list of database names.
        """
        return (
            await self._get(
                "_all_dbs",
                query_kwargs={
                    "descending": descending,
                    "endkey": endkey,
                    "limit": limit,
                    "skip": skip,
                    "startkey": startkey,
                },
            )
        ).json()

    async def create(
        self,
        name: str,
        q: int | None = None,
        n: int | None = None,
        partitioned: bool = False,
    ) -> AsyncDatabase:
        """
        Create a database.

        Parameters
        ----------
        name : str
            The database's name.
        q : int
            Shards. Default `None` (server default: `8`).
        n : int
            Replicas. Default `None` (server default: `3`).
        partitioned : bool
            Whether to create a partitioned database. Default `False`.

        Returns
        -------
        AsyncDatabase
        """
        await self._put(resource=name, query_kwargs={"q": q, "n": n, "partitioned": partitioned})
        return await self.get(name=name)

    async def dbs_info(self, keys: list[str]) -> list[dict]:
        """
        Returns information about a list of specified databases.

        Parameters
        ----------
        keys : list[str]
            List of database names to be requested.

        Returns
        -------
        list[dict]
        """
        return (await self._post(resource="_dbs_info", body={"keys": keys})).json()

    async def get(self, name: str, check: bool = False) -> AsyncDatabase:
        """
        Get a database by name.

        Parameters
        ----------
        name : str
            The name of the database.
        check : bool
            If `True`, raise an exception if the database cannot be found. Default `False`.

        Returns
        -------
        AsyncDatabase
        """
        db = AsyncDatabase(
            name=name,
            url=self.url,
            user=self._user,
            password=self._password,
            disable_ssl_verification=self.disable_ssl_verification,
            auth_method=self.auth_method,
            session=self.session,  # shared — child sets _owns_session=False
        )
        try:
            await db._head()
        except (NotFoundError, httpx.RequestError):
            if check is True:
                raise
        except CouchDBError:
            raise
        return db

    async def delete(self, resource: str | None = None) -> bool:
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
        await self._delete(resource=resource)
        return True

    async def replicate(
        self,
        source: dict | str,
        target: dict | str,
        replication_id: str | None = None,
        cancel: bool | None = None,
        continuous: bool | None = None,
        create_target: bool | None = None,
        create_target_params: dict | None = None,
        doc_ids: list[str] | None = None,
        filter_func: str | None = None,
        selector: dict | None = None,
        source_proxy: str | None = None,
        target_proxy: str | None = None,
    ) -> dict:
        """
        Request, configure, or stop, a replication operation. For more info, please refer to
        [the official documentation](https://docs.couchdb.org/en/main/api/server/common.html#replicate).

        Parameters
        ----------
        source : dict | str
            Fully qualified source database URL or an object with URL and headers.
        target : dict | str
            Fully qualified target database URL or an object with URL and headers.
        replication_id : str
            The ID of the replication document.
        cancel : bool
            Cancels the replication.
        continuous : bool
            Configure the replication to be continuous.
        create_target : bool
            Creates the target database.
        create_target_params : dict
            Parameters for creating the target database (`q`, `n`).
        doc_ids : list[str]
            Document IDs to synchronize. Mutually exclusive with `filter_func` and `selector`.
        filter_func : str
            Name of a filter function. Mutually exclusive with `doc_ids` and `selector`.
        selector : dict
            Selector to filter documents. Mutually exclusive with `doc_ids` and `filter_func`.
        source_proxy : str
            Proxy for replication from source (`http` or `socks5`).
        target_proxy : str
            Proxy for replication to target (`http` or `socks5`).

        Returns
        -------
        dict
        """
        if (source_proxy and validate_proxy(source_proxy) is False) or (
            target_proxy and validate_proxy(target_proxy) is False
        ):
            raise ProxySchemeComplianceError("Proxy has invalid scheme.")
        if sum(bool(_) for _ in [doc_ids, filter_func, selector]) > 1:
            raise CouchDBError(
                'Arguments "doc_ids", "filter_func" and "selector" are mutually exclusive.'
            )
        return (
            await self._post(
                resource="_replicator",
                body=rm_nones_from_dict(
                    {
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
                        "target_proxy": target_proxy,
                    }
                ),
            )
        ).json()

    async def membership(self) -> dict:
        """
        Displays the nodes that are part of the cluster.

        Returns
        -------
        dict : A dictionary with the following keys.

          - ``all_nodes`` (`list[str]`) — all nodes this node knows about
          - ``cluster_nodes`` (`list[str]`) — nodes that are part of the cluster
        """
        return (await self._get(resource="_membership")).json()

    async def cluster_setup(
        self,
        *,
        ensure_dbs_exist: list[str] | None = None,
    ) -> dict:
        """
        Returns the status of the node or cluster, per the cluster setup wizard.

        Parameters
        ----------
        ensure_dbs_exist : list[str]
            List of system databases to ensure exist on the node/cluster.
            Defaults to ``["_users", "_replicator"]``.

        Returns
        -------
        dict : A dictionary with a single key ``state`` whose value is one of
        ``'cluster_disabled'``, ``'single_node_disabled'``, ``'single_node_enabled'``,
        ``'cluster_enabled'``, or ``'cluster_finished'``.
        """
        return (
            await self._get(
                resource="_cluster_setup",
                query_kwargs={"ensure_dbs_exist": ensure_dbs_exist},
            )
        ).json()

    async def setup_cluster(
        self,
        action: str,
        *,
        bind_address: str | None = None,
        username: str | None = None,
        password: str | None = None,
        port: int | None = None,
        node_count: int | None = None,
        remote_node: str | None = None,
        remote_current_user: str | None = None,
        remote_current_password: str | None = None,
        host: str | None = None,
        ensure_dbs_exist: list[str] | None = None,
    ) -> dict:
        """
        Configure a node as a single (standalone) node, as part of a cluster, or finalise
        a cluster. This is a **destructive** operation — do not run against a shared or
        production CouchDB instance during testing.

        Parameters
        ----------
        action : str
            One of ``'enable_single_node'``, ``'enable_cluster'``, ``'add_node'``, or
            ``'finish_cluster'``.
        bind_address : str
            IP address to bind the current node. Use ``'0.0.0.0'`` to bind all interfaces.
            (``enable_cluster`` and ``enable_single_node`` only)
        username : str
            Server-level administrator username to create, or the remote server's
            administrator username (``add_node``).
        password : str
            Server-level administrator password to create, or the remote server's password
            (``add_node``).
        port : int
            TCP port for this node (``enable_cluster`` / ``enable_single_node``) or the
            remote node's port (``add_node``).
        node_count : int
            Total number of nodes to join into the cluster. Determines ``n`` (max 3).
            (``enable_cluster`` only)
        remote_node : str
            IP address of the remote node. (``enable_cluster`` only)
        remote_current_user : str
            Username of the admin on the remote node. (``enable_cluster`` only)
        remote_current_password : str
            Password of the admin on the remote node. (``enable_cluster`` only)
        host : str
            Remote node IP to add to the cluster. (``add_node`` only)
        ensure_dbs_exist : list[str]
            List of system databases to ensure exist. Defaults to
            ``["_users", "_replicator"]``.

        Returns
        -------
        dict : ``{"ok": true}`` on success.
        """
        return (
            await self._post(
                resource="_cluster_setup",
                body=rm_nones_from_dict(
                    {
                        "action": action,
                        "bind_address": bind_address,
                        "username": username,
                        "password": password,
                        "port": port,
                        "node_count": node_count,
                        "remote_node": remote_node,
                        "remote_current_user": remote_current_user,
                        "remote_current_password": remote_current_password,
                        "host": host,
                        "ensure_dbs_exist": ensure_dbs_exist,
                    }
                ),
            )
        ).json()

    async def node_config(
        self,
        node: str = "_local",
        section: str | None = None,
        key: str | None = None,
    ) -> dict | str:
        """
        Returns CouchDB node configuration.

        - No `section` / `key` → full configuration tree (`dict`)
        - `section` only → configuration section (`dict`)
        - `section` + `key` → single configuration value (`str` or primitive)

        The literal string ``'_local'`` (default) is an alias for the local node name.

        Parameters
        ----------
        node : str
            Node name. Default ``'_local'``.
        section : str
            Configuration section name (e.g. ``'log'``, ``'couchdb'``).
        key : str
            Configuration key within the section (e.g. ``'level'``).

        Returns
        -------
        dict | str
        """
        resource = f"_node/{node}/_config"
        if section:
            resource = f"{resource}/{section}"
            if key:
                resource = f"{resource}/{key}"
        return (await self._get(resource=resource)).json()

    async def set_node_config(
        self,
        section: str,
        key: str,
        value: str,
        node: str = "_local",
    ) -> str:
        """
        Updates a single configuration value on a node. Returns the **old** value.

        Parameters
        ----------
        section : str
            Configuration section name.
        key : str
            Configuration key name.
        value : str
            New value (must be a valid JSON string).
        node : str
            Node name. Default ``'_local'``.

        Returns
        -------
        str : The previous value of the configuration key.
        """
        return (
            await self._put(
                resource=f"_node/{node}/_config/{section}/{key}",
                body=value,
            )
        ).json()

    async def delete_node_config(
        self,
        section: str,
        key: str,
        node: str = "_local",
    ) -> str:
        """
        Deletes a single configuration value from a node. Returns the **old** value.

        Parameters
        ----------
        section : str
            Configuration section name.
        key : str
            Configuration key name.
        node : str
            Node name. Default ``'_local'``.

        Returns
        -------
        str : The deleted value.
        """
        return (
            await self._delete(
                resource=f"_node/{node}/_config/{section}/{key}",
            )
        ).json()

    async def reload_node_config(self, node: str = "_local") -> bool:
        """
        Reloads the configuration from disk. Flushes any in-memory configuration changes
        that have not been written to disk.

        Parameters
        ----------
        node : str
            Node name. Default ``'_local'``.

        Returns
        -------
        bool : ``True`` on success.
        """
        return (
            (
                await self._post(
                    resource=f"_node/{node}/_config/_reload",
                    body={},
                )
            )
            .json()
            .get("ok", False)
        )

    async def node_stats(self, node: str = "_local") -> dict:
        """
        Returns statistics for the specified node.

        Parameters
        ----------
        node : str
            Node name. Default ``'_local'``.

        Returns
        -------
        dict
        """
        return (await self._get(resource=f"_node/{node}/_stats")).json()

    async def node_system(self, node: str = "_local") -> dict:
        """
        Returns system-level statistics for the specified node.

        Parameters
        ----------
        node : str
            Node name. Default ``'_local'``.

        Returns
        -------
        dict
        """
        return (await self._get(resource=f"_node/{node}/_system")).json()

    async def up(self, raise_exception: bool = False) -> bool:
        """
        Check if the server is up.

        Parameters
        ----------
        raise_exception : bool
            If `True`, exceptions will be raised instead of returning `False`.

        Returns
        -------
        bool : `True` if the server is up.
        """
        try:
            response = await self._get(resource="_up")
            return "status" in response.json() and response.json()["status"] == "ok"
        except Exception:
            if raise_exception:
                raise
            return False
