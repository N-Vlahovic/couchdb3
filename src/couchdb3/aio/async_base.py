#!/usr/bin/env python3

import asyncio
from datetime import UTC, datetime

import httpx

from .. import exceptions, utils

__all__ = ["AsyncBase"]


class AsyncBase:
    """
    Abstract async base class. Mirrors `Base` but uses `httpx.AsyncClient`
    and `async def` methods throughout.

    Lifecycle must be managed via `async with` or explicit `await obj.aclose()`.
    `__del__` is intentionally absent — `await` is not valid inside it.
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
        timeout: int | None = utils.DEFAULT_TIMEOUT,
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
            initialized. When provided, the caller retains ownership and is responsible for closing
            it; this instance will NOT close it on `aclose()`.
        """
        auth_method = auth_method or utils.DEFAULT_AUTH_METHOD
        if utils.validate_auth_method(auth_method=auth_method) is False:
            raise exceptions.AuthenticationMethodError(
                'Invalid authentication method. Possible values are "basic" and "cookie".'
            )
        _ = utils.extract_url_data(url=url)
        user = user or _["user"]
        password = password or _["password"]
        self.scheme = _["scheme"]
        self.host = _["host"]
        self.port = port or _["port"]
        self.root = None
        self.disable_ssl_verification = disable_ssl_verification
        # Track ownership so that child objects sharing a parent's session don't close it.
        if session is not None:
            self.session = session
            self._owns_session = False
        else:
            self.session = httpx.AsyncClient(
                verify=disable_ssl_verification is False,
                headers={"Accept": "application/json", "Content-type": "application/json"},
            )
            self._owns_session = True
        self._user = user
        self._password = password
        self._auth = httpx.BasicAuth(user, password) if user and password else None
        self.auth_method = auth_method
        self.timeout = timeout
        # Lock for cookie auth token renewal — prevents concurrent coroutines from
        # each issuing a renewal POST when the token expires simultaneously.
        self._auth_lock: asyncio.Lock = asyncio.Lock()

    async def __aenter__(self):
        """
        Enter method for use with `async with` statements.

        Returns
        -------
        AsyncBase: The given instance.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit method for use with `async with` statements. Closes the client
        if this instance owns it.

        Returns
        -------
        None
        """
        await self.aclose()

    def __repr__(self) -> str:
        """
        Basic repr.

        Returns
        -------
        str: The instance's representation.
        """
        return self.__class__.__name__

    @property
    def basic(self) -> str:
        return utils.basic_auth(user=self._user, password=self._password)

    @property
    def url(self) -> str:
        """

        Returns
        -------
        str: The instance's url parsed using its scheme, root and port.
        """
        url = f"{self.scheme}://{self.host}"
        if self.port:
            url += f":{self.port}"
        if self.root:
            url += f"/{self.root}"
        return url

    async def aclose(self) -> None:
        """
        Close the underlying async client, but only if this instance owns it.

        Returns
        -------
        None
        """
        if self._owns_session:
            await self.session.aclose()

    def _is_auth_token_expired(self) -> bool:
        """
        Check if the authentication token is expired. Synchronous — reads a
        timestamp only, no I/O.

        Returns
        -------
        bool : `True` if the auth token is expired or absent.
        """
        try:
            expires = next(_.expires for _ in self.session.cookies.jar if _.name == "AuthSession")
            if expires is None:
                return False
            return expires <= datetime.now(UTC).timestamp()
        except StopIteration:
            return True

    async def _renew_auth_token(self) -> None:
        """
        Send a `POST` request to the `_session` endpoint to obtain a fresh cookie token.

        Protected by a double-checked `asyncio.Lock` so that concurrent coroutines
        that simultaneously detect an expired token only issue a single renewal POST.

        Returns
        -------
        None
        """
        async with self._auth_lock:
            # Re-check inside the lock: another coroutine may have already renewed
            # the token while this one was waiting to acquire the lock.
            if self._is_auth_token_expired():
                await self._post(
                    resource="_session",
                    body={"name": self._user, "password": self._password},
                    auth_method="basic",
                    root="",
                )

    async def _request(
        self,
        *,
        method: str,
        resource: str | None = None,
        body: dict | list | None = None,
        query_kwargs: dict | None = None,
        auth_method: str | None = None,
        root: str | None = None,
        timeout: int | None = None,
        **req_kwargs,
    ) -> httpx.Response:
        """
        Abstract async request dispatcher.

        Parameters
        ----------
        method : str
            The HTTP method.
        resource : str
            The resource to fetch (relative to the host). Default `None`.
        body : dict | list
            The request body. Default `None`.
        query_kwargs : dict
            Query parameters to encode into the URL. Default `None`.
        auth_method : str
            Authentication method override. Choices are `cookie` or `basic`. Default `None`.
        root : str
            A root path relative to the server URL, e.g. `"dbname"`. Default `None`.
        timeout : int
            Request-level timeout override. Default `None`.
        req_kwargs
            Further `httpx.AsyncClient.request` keyword parameters.

        Returns
        -------
        httpx.Response
        """
        auth_method = auth_method or self.auth_method
        root = root if isinstance(root, str) else self.root
        path = ""
        if root:
            path += root
        if body and isinstance(body, dict):
            for k in utils.COUCH_DB_RESERVED_DOC_FIELDS:
                if k in body and body.get(k) is None:
                    del body[k]
        if resource:
            path += f"/{resource}"
        if auth_method == "basic":
            req_kwargs.update({"auth": self._auth})
        elif auth_method == "cookie":
            if self._is_auth_token_expired():
                await self._renew_auth_token()
        response = await self.session.request(
            method=method,
            url=utils.build_url(
                scheme=self.scheme,
                host=self.host,
                path=path,
                port=self.port,
                **(query_kwargs or {}),
            ),
            json=body,
            timeout=timeout or self.timeout,
            **req_kwargs,
        )
        utils.check_response(response=response)
        return response

    async def _delete(
        self,
        resource: str | None = None,
        *,
        timeout: int = utils.DEFAULT_TIMEOUT,
        query_kwargs: dict | None = None,
        auth_method: str | None = None,
        root: str | None = None,
        **req_kwargs,
    ) -> httpx.Response:
        """
        Async DELETE request.

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host). Default `None`.
        timeout : int
            The request's timeout. Default c.f. `couchdb3.utils.DEFAULT_TIMEOUT`.
        query_kwargs : dict
            Query parameters. Default `None`.
        auth_method : str
            Authentication method override. Default `None`.
        root : str
            Root path override. Default `None`.
        req_kwargs
            Further `httpx.AsyncClient.request` keyword parameters.

        Returns
        -------
        httpx.Response
        """
        return await self._request(
            method="DELETE",
            resource=resource,
            timeout=timeout,
            query_kwargs=query_kwargs,
            auth_method=auth_method,
            root=root,
            **req_kwargs,
        )

    async def _get(
        self,
        resource: str | None = None,
        *,
        timeout: int = utils.DEFAULT_TIMEOUT,
        query_kwargs: dict | None = None,
        auth_method: str | None = None,
        root: str | None = None,
        **req_kwargs,
    ) -> httpx.Response:
        """
        Async GET request.

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host). Default `None`.
        timeout : int
            The request's timeout. Default c.f. `couchdb3.utils.DEFAULT_TIMEOUT`.
        query_kwargs : dict
            Query parameters. Default `None`.
        auth_method : str
            Authentication method override. Default `None`.
        root : str
            Root path override. Default `None`.
        req_kwargs
            Further `httpx.AsyncClient.request` keyword parameters.

        Returns
        -------
        httpx.Response
        """
        return await self._request(
            method="GET",
            resource=resource,
            timeout=timeout,
            query_kwargs=query_kwargs,
            auth_method=auth_method,
            root=root,
            **req_kwargs,
        )

    async def _head(
        self,
        resource: str | None = None,
        *,
        timeout: int | None = None,
        query_kwargs: dict | None = None,
        auth_method: str | None = None,
        root: str | None = None,
        **req_kwargs,
    ) -> httpx.Response:
        """
        Async HEAD request.

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host). Default `None`.
        timeout : int
            The request's timeout. Default `None`.
        query_kwargs : dict
            Query parameters. Default `None`.
        auth_method : str
            Authentication method override. Default `None`.
        root : str
            Root path override. Default `None`.
        req_kwargs
            Further `httpx.AsyncClient.request` keyword parameters.

        Returns
        -------
        httpx.Response
        """
        return await self._request(
            method="HEAD",
            resource=resource,
            timeout=timeout,
            query_kwargs=query_kwargs,
            auth_method=auth_method,
            root=root,
            **req_kwargs,
        )

    async def _post(
        self,
        resource: str | None = None,
        *,
        body: dict | list | None = None,
        timeout: int | None = None,
        query_kwargs: dict | None = None,
        auth_method: str | None = None,
        root: str | None = None,
        **req_kwargs,
    ) -> httpx.Response:
        """
        Async POST request.

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host). Default `None`.
        body : dict | list
            The request body. Default `None`.
        timeout : int
            The request's timeout. Default `None`.
        query_kwargs : dict
            Query parameters. Default `None`.
        auth_method : str
            Authentication method override. Default `None`.
        root : str
            Root path override. Default `None`.
        req_kwargs
            Further `httpx.AsyncClient.request` keyword parameters.

        Returns
        -------
        httpx.Response
        """
        return await self._request(
            method="POST",
            resource=resource,
            body=body,
            timeout=timeout,
            query_kwargs=query_kwargs,
            auth_method=auth_method,
            root=root,
            **req_kwargs,
        )

    async def _put(
        self,
        resource: str | None = None,
        *,
        body: dict | list | None = None,
        timeout: int | None = None,
        query_kwargs: dict | None = None,
        auth_method: str | None = None,
        root: str | None = None,
        **req_kwargs,
    ) -> httpx.Response:
        """
        Async PUT request.

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host). Default `None`.
        body : dict | list
            The request body. Default `None`.
        timeout : int
            The request's timeout. Default `None`.
        query_kwargs : dict
            Query parameters. Default `None`.
        auth_method : str
            Authentication method override. Default `None`.
        root : str
            Root path override. Default `None`.
        req_kwargs
            Further `httpx.AsyncClient.request` keyword parameters.

        Returns
        -------
        httpx.Response
        """
        return await self._request(
            method="PUT",
            resource=resource,
            body=body,
            timeout=timeout,
            query_kwargs=query_kwargs,
            auth_method=auth_method,
            root=root,
            **req_kwargs,
        )

    async def check(self, resource: str | None = None) -> bool:
        """
        Check the server or database by sending a `HEAD` request to `/self.root`.

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host). Default `None`.

        Returns
        -------
        bool: `True` if the server is up or the database exists.
        """
        try:
            utils.check_response(await self._head(resource=resource))
            return True
        except (exceptions.CouchDBError, httpx.RequestError):
            return False

    async def info(self, partition: str | None = None) -> dict:
        """
        Return a server's or database's info by sending a `GET` request to `/self.root`.

        Parameters
        ----------
        partition : str
            A specific partition of the database. Only valid for partitioned databases.
            Default is `None`.

        Returns
        -------
        dict: A dictionary containing the server's or database's info.
        """
        return (await self._get(resource=f"_partition/{partition}" if partition else None)).json()

    async def rev(self, resource: str) -> str | None:
        """
        Safely retrieves a resource's revision via a lightweight `HEAD` request,
        reading the `"ETag"` response header.

        Returns `None` if the resource is not found, rather than raising
        `couchdb3.exceptions.NotFoundError`.

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host).

        Returns
        -------
        str | None : The resource's current revision.
        """
        rev = None
        try:
            rev = (await self._head(resource=resource)).headers.get("ETag").strip('"')
        except exceptions.NotFoundError:
            pass
        return rev
