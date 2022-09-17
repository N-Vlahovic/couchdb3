# How to contribute

Hello, happy that you're reading this as this projects highly welcomes new contributors.

Below, you'll find a few notes on how to

 - get started
 - check the requirements
 - test
 - submit changes
 - adhere to the coding conventions


## Getting started
Firstly, a rough explanation of the file structure is provided below.

To get started, clone the project into a directory of your choice - say `~/couchdb3`.

Next, you'll need an (virtual) environment: I like to use `venv` but `pipenv`or other alternatives work just as well.

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

- Python `>=3.7`
- CouchDB `3.x.x`
- Python packages `requests setuptools>=42 wheel`

### Python Interpreter
A Python version `>=3.7` is required for this project: 
The reason being able to use the following statement
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
Next, you'll want to install the requirements:
The package itself only requires `requests` (c.f `setup.py`).
However, you'll want to install the packages `setuptools>=42` and `wheel` for packaging purposes.
In addition, other packages will be installed when invoking certain `make` commands.
For example `make build ` installs the package `build`,
`make deploy-test` installs `twine`
and `make html` installs `pdoc3`.


## Testing


### CouchDB Server Setup

There are many ways to get started with CouchDB: you can check out 
[their download section](http://couchdb.apache.org/#download), 
[their official docker image](https://hub.docker.com/_/couchdb),
check out cloud service providers or also your package manager.

I created a small [CouchDB Docker Setup](https://github.com/n-vlahovic/couchdb-docker-setup) 
which sets up CouchDB locally using Docker. It was designed to run two standalone servers in order to test replication.

To use this setup, clone the repository and execute the build command 
(c.f. [README.md](https://github.com/n-vlahovic/couchdb-docker-setup/blob/master/README.md) ).

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
which executes `python -m unittest discover -s tests -t tests`.


## Submitting changes
To submit changes, simply create a new branch following the format 
`username/<optional_date-><description>` 
where `<description>` denotes a short description of the new branch 
(e.g. `n-vlahovic/2022-09-get_attachment_bug_fix`).
Then, push your updates into that branch and open a new pull request for review.

## Coding conventions
The code style is fairly straightforward:
Use annotations whenever possible, ideally using the builtin module 
[typing](https://docs.python.org/3/library/typing.html).

Further, the docstrings type used is [numpydoc](https://numpydoc.readthedocs.io/en/latest/format.html).

Here is a simple example
```python
from typing import Dict, List, Optional, Tuple


CONST: List[int] = [1, 2, 3]
"""CONST is a list of integers"""


def foo(
    data: Dict
) -> Tuple[Optional[str], str]:
    """
    My function foo.
    
    Parameters
    ----------
    data : Dict
        A simple dictionary which must contain the key `name`.
    
    Returns
    -------
    Tuple[Optional[str], str] : A tuple consisting of 
    
    - the id
    - the name
    """
    return data.get("_id"), data["name"]

```

## File structure
```
├── archive  # .gitignore (created automatically when building)
├── contributing.md
├── dist  # .gitignore (created automatically when building)
├── docs  # Automatically created when running "make html"
│   ├── base.html
│   ├── database.html
│   ├── document.html
│   ├── exceptions.html
│   ├── index.html
│   ├── server.html
│   ├── utils.html
│   └── view.html
├── LICENSE
├── Makefile
├── pyproject.toml
├── README.md
├── scripts  # Scripts called in Makefile
│   ├── build.sh
│   ├── deploy.sh
│   ├── deploy-test.sh
│   ├── html.sh
│   └── test.sh
├── setup.py
├── src
│   ├── couchdb3  # Module location
│   │   ├── base.py
│   │   ├── database.py
│   │   ├── document.py
│   │   ├── exceptions.py
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── utils.py
│   │   └── view.py
│   └── __init__.py
└── tests
    ├── attachments
    │   ├── test.html
    │   ├── test.json
    │   ├── test.png
    │   └── test.txt
    ├── credentials.py
    ├── __init__.py
    ├── test_database.py
    ├── test_partitioned_database.py
    ├── test_server.py
    ├── test_utils.py
    └── views
        └── document-view.js

```

