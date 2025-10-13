"""Collection TypedDict definitions.

Type-safe dict[str, Any]ionary definitions for collection creation parameters.
"""

from .typed_dict_collection_create_kwargs import TypedDictCollectionCreateKwargs
from .typed_dict_collection_from_items_kwargs import TypedDictCollectionFromItemsKwargs

__all__ = [
    "TypedDictCollectionCreateKwargs",
    "TypedDictCollectionFromItemsKwargs",
]
