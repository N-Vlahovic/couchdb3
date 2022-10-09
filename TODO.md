# Todo

## Authentication
- <s>Add cookie based authentication</s>


## Misc
- <s>Abstract away partition path insertion</s>, e.g.
```python
def resource_parser(resource: str, partition: str = None) -> str:
    return f"_partition/{partition}/{resource}" if partition else resource
```