"""ModelContentEncoding: Content encoding options for payload serialization"""

from enum import Enum


class ModelContentEncoding(str, Enum):
    """Content encoding options for payload serialization"""

    JSON = "json"
    JSON_GZIP = "json_gzip"
    AVRO = "avro"
    PROTOBUF = "protobuf"
