# How to contribute

Hello, happy that you're reading this as this project highly welcomes new contributors.

Below, you'll find a few notes on how to

 - get started
 - check the requirements
 - test
 - submit changes
 - adhere to the coding conventions


## Getting started
Firstly, a rough explanation of the file structure is provided below.

To get started, clone the project into a directory of your choice - say `~/couchdb3`.

Next, you'll need an (virtual) environment: I like to use `venv` but `pipenv` or other alternatives work just as well.

### A Few Notes on venv
Creating a new virtual environment can be done with the command
```bash
python3 -m venv /path/to/venv
```
which creates the env at the designated location (relative to your current path).
Activating the env can be done via the command
```bash
source /path/to/venv/bin/activate
```
and deactivating simply with
```bash
deactivate
```

## Requirements

### TL;DR

- Python `>=3.11`
- CouchDB `3.x.x`
- Python package `httpx>=0.27,<1.0`

### Python Interpreter
A Python version `>=3.11` is required as prior versions reached EoL.
Also, new-ish versions are desired to be able to use the following statement
```python
from __future__ import annotations
```
for annotation purposes.

### CouchDB Version
In order to be able to truly test the package, you'll want to have a running CouchDB server.
Of course, it doesn't need to be a server running on your local machine, even though this is the simpler approach when
testing and debugging.

So far, I only ever used CouchDB `v 3.x.x` but neither `v 2.x.x` nor `v 1.x.x`.
Backwards compatibility might be a future topic but as of now `v3` is the only officially supported version.


### Python Packages
The package itself only requires `httpx` (c.f. `setup.py` and `pyproject.toml`).

Dev/build tools (`build`, `pdoc3`, `setuptools`, `twine`) are declared under
`[project.optional-dependencies] dev` in `pyproject.toml` and are installed by certain `make`
commands automatically (e.g. `make build` uses `build`, `make html` uses `pdoc3`).


## Testing


### CouchDB Server Setup

There are many ways to get started with CouchDB: you can check out
[their download section](http://couchdb.apache.org/#download),
[their official docker image](https://hub.docker.com/_/couchdb),
check out cloud service providers or also your package manager.

I created a small [CouchDB Docker Setup](https://github.com/n-vlahovic/couchdb-docker-setup)
which sets up CouchDB locally using Docker. It was designed to run two standalone servers in order to test replication.

To use this setup, clone the repository and execute the build command
(c.f. [README.md](https://github.com/n-vlahovic/couchdb-docker-setup/blob/master/README.md)).

### Unit Tests

The folder `tests` contains several unittests which require a working connection to a server.
The file `tests/credentials.py` handles the credentials by searching for the following environment variables:
- `COUCHDB_USER`
- `COUCHDB_PASSWORD`
- `COUCHDB_URL`

Each variable is searched for as follows:
1. Check if it is contained in `os.environ`
2. Check if there is a `.env` file at the top directory of the project and checks its content
3. Prompt the user for input

The variable `COUCHDB_URL` has one additional step:
0. Check if the default local CouchDB URL (`http://localhost:5984`) points to a running server (by sending a `GET`
request).

To run all tests, one can execute the command
```bash
make test
```
which executes `uv run python3 -m unittest discover -s tests -t tests`.


## Submitting changes
To submit changes, simply create a new branch following the format
`username/<optional_date-><description>`
where `<description>` denotes a short description of the new branch
(e.g. `n-vlahovic/2022-09-get_attachment_bug_fix`).
Then, push your updates into that branch and open a new pull request for review.

## Coding conventions
The code style is fairly straightforward:
use annotations whenever possible, using modern built-in generics (`dict`, `list`, `tuple`, `set`)
rather than the deprecated `typing` equivalents (`Dict`, `List`, `Tuple`, `Set`).

Docstrings follow the [numpydoc](https://numpydoc.readthedocs.io/en/latest/format.html) format.

Here is a simple example:
```python
from __future__ import annotations


CONST: list[int] = [1, 2, 3]
"""CONST is a list of integers"""


def foo(data: dict) -> tuple[str | None, str]:
    """
    My function foo.

    Parameters
    ----------
    data : dict
        A simple dictionary which must contain the key `name`.

    Returns
    -------
    tuple[str | None, str] : A tuple consisting of

    - the id
    - the name
    """
    return data.get("_id"), data["name"]
```

## Linting & formatting

The project uses [ruff](https://docs.astral.sh/ruff/) for both linting and formatting.
Configuration lives in `pyproject.toml` under `[tool.ruff]`.

To check for issues:
```bash
uv run ruff check .
```

To auto-fix all fixable issues:
```bash
uv run ruff check . --fix
```

To format:
```bash
uv run ruff format .
```

Please ensure `uv run ruff check .` reports no errors before submitting a pull request.

## File structure
```
├── archive              # .gitignore (created automatically when building)
├── contributing.md
├── dist                 # .gitignore (created automatically when building)
├── docs                 # Automatically created when running "make html"
├── LICENSE
├── Makefile
├── pyproject.toml
├── README.md
├── scripts              # Scripts called in Makefile
│   ├── build.sh
│   ├── deploy.sh
│   ├── deploy-test.sh
│   ├── html.sh
│   └── test.sh
├── setup.py
├── src
│   ├── couchdb3         # Module location
│   │   ├── aio/         # Async client subpackage
│   │   │   ├── __init__.py
│   │   │   ├── async_base.py
│   │   │   ├── async_database.py
│   │   │   └── async_server.py
│   │   ├── sync/        # Sync client subpackage
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── database.py
│   │   │   └── server.py
│   │   ├── __init__.py  # Flat re-exports (backward compatible)
│   │   ├── document.py  # Shared types (Document, DictBase, etc.)
│   │   ├── exceptions.py
│   │   ├── utils.py
│   │   └── view.py
│   └── __init__.py
└── tests
    ├── attachments
    │   ├── test.html
    │   ├── test.json
    │   ├── test.png
    │   └── test.txt
    ├── credentials.py
    ├── __init__.py
    ├── test_async_database.py
    ├── test_async_server.py
    ├── test_database.py
    ├── test_partitioned_database.py
    ├── test_server.py
    ├── test_utils.py
    └── views
        └── document-view.js
```
