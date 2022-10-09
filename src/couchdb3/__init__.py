__doc__ = """# CouchDB3

*CouchDB3* is a wrapper around the CouchDB API. For more detailed information, please refer to 
[the documentation](https://n-vlahovic.github.io/couchdb3/).

## Disclaimer

Big parts of the documentation (and thus docstrings) have been copied from CouchDB's API's great 
[official documentation](https://docs.couchdb.org/en/main/api/index.html).


## Requirements  

- Python version `>= 3.7`
- CouchDB version `3.x`

## Installation
Installing via PyPi
```bash
pip install couchdb3
```

Installing via Github
```bash
python -m pip install git+https://github.com/n-Vlahovic/couchdb3.git
```

Installing from source
```bash
git clone https://github.com/n-Vlahovic/couchdb3
python -m pip install -e couchdb3
```

## Quickstart

### Connecting to a database server

```python
import couchdb3

client = couchdb3.Server(
    "http://user:password@127.0.0.1:5984"
)

# Checking if the server is up
print(client.up())
# True
```

user and password can also be passed into the Server constructor as keyword parameters, e.g.

```python
client = couchdb3.Server(
    "127.0.0.1:5984:",  # Scheme omitted - will assume http protocol
    user="user",
    password="password"
)
```

Both approaches are equivalent, i.e. in both cases the instance's `scheme,host,port,user,password` will be identical.

Further, clients can be used with context managers:
```python
with couchdb3.Server("http://user:password@127.0.0.1:5984") as client:
    # Do stuff
    ...
```

### Getting or creating a database
```python
dbname = "mydb"
db = client.get(dbname) if dbname in client else client.create(dbname)
print(db)
# Database: mydb
```

### Creating a document
```python
mydoc = {
    "_id": "mydoc-id",
    "name": "Hello",
    "type": "World"
}
print(db.save(mydoc))
# ('mydoc-id', True, '1-24fa3b3fd2691da9649dd6abe3cafc7e')
```
Note: `Database.save` requires the document to have an id (i.e. a key `_id`), 
`Database.create` does not.

### Updating a document
To update an existing document, retrieving the revision is paramount.
In the example below, `dbdoc` contains the key `_rev` and the builtin `dict.update` function is used to update the 
document before saving it.
```python
mydoc = {
    "_id": "mydoc-id",
    "name": "Hello World",
    "type": "Hello World"
}
dbdoc = db.get(mydoc["_id"])
dbdoc.update(mydoc)
print(db.save(dbdoc))
# ('mydoc-id', True, '2-374aa8f0236b9120242ca64935e2e8f1')
```
Alternatively, one can use `Database.rev` to fetch the latest revision and overwrite the document
```python
mydoc = {
    "_id": "mydoc-id",
    "_rev": db.rev("mydoc-id"),
    "name": "Hello World",
    "type": "Hello World"
}
print(db.save(mydoc))
# ('mydoc-id', True, '3-d56b14b7ffb87960b51d03269990a30d')
```

### Deleting a document
To delete a document, the `docid` and `rev` are needed
```python
docid = "mydoc-id"
print(db.delete(docid=docid, rev=db.rev(docid)))  # Fetch the revision on the go
# True
```

### Working with partitions
For a partitioned database, the `couchdb3.Partition` class offers a wrapper around partitions (acting similarly 
to collections in Mongo). 

```python
from couchdb3 import Server, Database, Partition


client: Server = Server(...)
db: Database = client["some-db"]
partition: Partition = db.get_partition("partition_id")
```

Partition instances append the partition's ID the document IDs (`partition-id:doc-id`) for a simpler user interaction, 
e.g.
```python
doc_id = "test-id"
print(doc_id in partition)  # no need to append the partition's ID
rev = partition.rev(doc_id)
partition.save({
    "_id": doc_id,  # no need to append the partition's ID
    "_rev": rev,
    ...
})
```

The partition ID will only be appended provided document IDs do not start with `partition-id`, e.g. the following will 
work and be equivalent to the previous example
```python
doc_id = "partition_id:test-id"
print(doc_id in partition)
rev = partition.rev(doc_id)
partition.save({
    "_id": doc_id,
    "_rev": rev,
    ...
})
```
"""
from . import exceptions
from . import utils
from .database import Database, Partition
from .document import Document
from .server import Server
from .view import ViewResult, ViewRow
