#!/usr/bin/env python3

from datetime import UTC, datetime

import httpx

from .. import exceptions, utils
from ..document import DictBase as DictBase

__all__ = ["Base", "DictBase"]


class Base:
    """
    Abstract base class
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
        session: httpx.Client | None = None,
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
            Controls whether to verify the server's TLS certificate. Set to `True` when connecting to a server with
            self-signed TLS certificates. Default `False`.
        auth_method : str
            Authentication method. Choices are `cookie` or `basic`. Default is `couchdb3.utils.DEFAULT_AUTH_METHOD`.
        timeout : int
            The default timeout for requests. Default c.f. `couchdb3.utils.DEFAULT_TIMEOUT`.
        session: httpx.Client
            A specific client to use. Optional - if not provided, a new client will be initialized.
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
        # NOTE: httpx.Client takes verify and headers at construction time, unlike
        # requests.Session where they can be set as mutable attributes post-construction.
        # Track ownership so that child objects sharing a parent's session don't close it.
        if session is not None:
            self.session = session
            self._owns_session = False
        else:
            self.session = httpx.Client(
                verify=disable_ssl_verification is False,
                headers={"Accept": "application/json", "Content-type": "application/json"},
            )
            self._owns_session = True
        self._user = user
        self._password = password
        self._auth = httpx.BasicAuth(user, password) if user and password else None
        self.auth_method = auth_method
        self.timeout = timeout

    def __bool__(self) -> bool:
        """
        Checks if the server/database exists.

        Returns
        -------
        bool: A boolean indicating whether the server/database exists.
        """
        try:
            self._head()
            return True
        except exceptions.CouchDBError:
            return False

    def __contains__(self, resource: str) -> bool:
        """
        Checks if the server/database contains the given resource.

        Parameters
        ----------
        resource : str
            A string identifying the target resource.

        Returns
        -------
            bool: A boolean value indicating whether the server/database contains the given resource.
        """
        try:
            self._head(resource=resource)
            return True
        except exceptions.CouchDBError:
            return False

    def __del__(self) -> None:
        """
        Close the session on delete (only if this instance owns it).

        Returns
        -------
        None
        """
        if getattr(self, "_owns_session", False):
            self.session.close()

    def __enter__(self):
        """
        Enter method to use the class in conjunction with `with ... as ...` statements.

        Returns
        -------
        Base: The given instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Method ran after running `with ... as ...` statements.

        Returns
        -------
        None
        """
        if self._owns_session:
            self.session.close()  # httpx.Client.close() — same interface as requests.Session

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
        str: The instance's url parsed using it's scheme, root and port.
        """
        url = f"{self.scheme}://{self.host}"
        if self.port:
            url += f":{self.port}"
        if self.root:
            url += f"/{self.root}"
        return url

    def _request(
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
        Abstract request

        Parameters
        ----------
        method : str
            The request method.
        resource : str
            The resource to fetch (relative to the host). Default `None`.
        body : Union[Dict, List]
            The request's body. Default `None`.
        query_kwargs : Dict
            A dictionary containing the requests query parameters.
        auth_method : str
            Authentication method. Choices are `cookie` or `basic`. Default is `None`.
        root : str
            A root relative to the server's URL, e.g. `"dbname"`. Default is `None`.
        timeout : int
            The request's timeout. Default c.f. `couchdb3.utils.DEFAULT_TIMEOUT`.
        req_kwargs
            Further `httpx.Client.request` keyword parameters.
        Returns
        -------
        httpx.Response
        """
        auth_method = auth_method or self.auth_method
        root = root if isinstance(root, str) else self.root
        path = ""
        if root:
            path += root
        if body:
            if isinstance(body, dict):
                for k in utils.COUCH_DB_RESERVED_DOC_FIELDS:
                    if k in body and body.get(k) is None:
                        del body[k]
        if resource:
            path += f"/{resource}"
        if auth_method == "basic":
            req_kwargs.update({"auth": self._auth})
        elif auth_method == "cookie":
            if self._is_auth_token_expired() is True:
                self._renew_auth_token()
        response = self.session.request(
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

    def _delete(
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
        DELETE request.

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host). Default `None`.
        timeout : int
            The request's timeout. Default c.f. `couchdb3.utils.DEFAULT_TIMEOUT`.
        query_kwargs : Dict
            A dictionary containing the requests query parameters.
        auth_method : str
            Authentication method. Choices are `cookie` or `basic`. Default is `None`.
        root : str
            A root relative to the server's URL, e.g. `"dbname"`. Default is `None`.
        req_kwargs
            Further `httpx.Client.request` keyword parameters.
        Returns
        -------
        httpx.Response
        """
        return self._request(
            method="DELETE",
            resource=resource,
            timeout=timeout,
            query_kwargs=query_kwargs,
            auth_method=auth_method,
            root=root,
            **req_kwargs,
        )

    def _get(
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
        GET request

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host). Default `None`.
        timeout : int
            The request's timeout. Default c.f. `couchdb3.utils.DEFAULT_TIMEOUT`.
        query_kwargs : Dict
            A dictionary containing the requests query parameters.
        auth_method : str
            Authentication method. Choices are `cookie` or `basic`. Default is `None`.
        root : str
            A root relative to the server's URL, e.g. `"dbname"`. Default is `None`.
        req_kwargs
            Further `httpx.Client.request` keyword parameters.
        Returns
        -------
        httpx.Response
        """
        return self._request(
            method="GET",
            resource=resource,
            timeout=timeout,
            query_kwargs=query_kwargs,
            auth_method=auth_method,
            root=root,
            **req_kwargs,
        )

    def _head(
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
        HEAD request

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host). Default `None`.
        timeout : int
            The request's timeout. Default c.f. `couchdb3.utils.DEFAULT_TIMEOUT`.
        query_kwargs : Dict
            A dictionary containing the requests query parameters.
        auth_method : str
            Authentication method. Choices are `cookie` or `basic`. Default is `None`.
        root : str
            A root relative to the server's URL, e.g. `"dbname"`. Default is `None`.
        req_kwargs
            Further `httpx.Client.request` keyword parameters.
        Returns
        -------
        httpx.Response
        """
        return self._request(
            method="HEAD",
            resource=resource,
            timeout=timeout,
            query_kwargs=query_kwargs,
            auth_method=auth_method,
            root=root,
            **req_kwargs,
        )

    def _post(
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
        POST request

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host). Default `None`.
        body : Dict
            The request's body. Default `None`.
        timeout : int
            The request's timeout. Default c.f. `couchdb3.utils.DEFAULT_TIMEOUT`.
        query_kwargs : Union[Dict, List]
            A dictionary containing the requests query parameters.
        auth_method : str
            Authentication method. Choices are `cookie` or `basic`. Default is `None`.
        root : str
            A root relative to the server's URL, e.g. `"dbname"`. Default is `None`.
        req_kwargs
            Further `httpx.Client.request` keyword parameters.
        Returns
        -------
        httpx.Response
        """
        return self._request(
            method="POST",
            resource=resource,
            body=body,
            timeout=timeout,
            query_kwargs=query_kwargs,
            auth_method=auth_method,
            root=root,
            **req_kwargs,
        )

    def _put(
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
        PUT request

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host). Default `None`.
        body : Union[Dict, List]
            The request's body. Default `None`.
        timeout : int
            The request's timeout. Default c.f. `couchdb3.utils.DEFAULT_TIMEOUT`.
        query_kwargs : Dict
            A dictionary containing the requests query parameters.
        auth_method : str
            Authentication method. Choices are `cookie` or `basic`. Default is `None`.
        root : str
            A root relative to the server's URL, e.g. `"dbname"`. Default is `None`.
        req_kwargs
            Further `httpx.Client.request` keyword parameters.
        Returns
        -------
        httpx.Response
        """
        return self._request(
            method="PUT",
            resource=resource,
            body=body,
            timeout=timeout,
            query_kwargs=query_kwargs,
            auth_method=auth_method,
            root=root,
            **req_kwargs,
        )

    def _is_auth_token_expired(self) -> bool:
        """
        Check if the authentication token is expired.

        Returns
        -------
        bool : `True` if the auth token is expired.
        """
        try:
            # httpx.Client.cookies.jar yields http.cookiejar.Cookie objects which
            # carry the .name and .expires attributes we need.
            expires = next(_.expires for _ in self.session.cookies.jar if _.name == "AuthSession")
            if expires is None:
                return False
            return expires <= datetime.now(UTC).timestamp()
        except StopIteration:
            return True

    def _renew_auth_token(self) -> None:
        """
        Send a `POST` request to the `_session` endpoint to obtain a token.
        Returns
        -------
        None
        """
        self._post(
            resource="_session",
            body={"name": self._user, "password": self._password},
            auth_method="basic",
            root="",
        )

    def check(self, resource: str | None = None) -> bool:
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
            utils.check_response(self._head(resource=resource))
            return True
        except (exceptions.CouchDBError, httpx.RequestError):
            return False

    def info(self, partition: str | None = None) -> dict:
        """
        Return a server's or database's info by sending a `GET` request to `/self.root`.

        Parameters
        ----------
        partition : str
            A specific partition of the database. Only valid for partitioned databases. Default is `None`.

        Returns
        -------
        Dict: A dictionary containing the server's or database's info.
        """
        return self._get(resource=f"_partition/{partition}" if partition else None).json()

    def rev(self, resource: str) -> str | None:
        """
        Safely retrieves a resource's revision by sending a lightweight `HEAD`request and reading the response's
        `"ETag"` header.

        If the provided resource cannot be found, `None` will be returned (instead of raising a
        `couchdb3.exceptions.NotFoundError` error).

        Parameters
        ----------
        resource : str
            The resource to fetch (relative to the host).

        Returns
        -------
        Optional[str] : The resource's current revision.
        """
        rev = None
        try:
            rev = self._head(resource=resource).headers.get("ETag").strip('"')
        except exceptions.NotFoundError:
            pass
        return rev
