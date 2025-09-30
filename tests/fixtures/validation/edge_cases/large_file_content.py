#!/usr/bin/env python3
"""Large file for performance testing."""


from pydantic import BaseModel


class ModelLargeData(BaseModel):
    """Large data model for performance testing."""

    field_0001: str
    field_0002: str
    field_0003: str
    field_0004: str
    field_0005: str
    field_0006: str
    field_0007: str
    field_0008: str
    field_0009: str
    field_0010: str
    field_0011: str
    field_0012: str
    field_0013: str
    field_0014: str
    field_0015: str
    field_0016: str
    field_0017: str
    field_0018: str
    field_0019: str
    field_0020: str


def process_large_data(data: dict[str, str]) -> dict[str, str]:
    """Function that processes large amounts of data."""
    result = {}

    # Simulate large processing logic
    for key, value in data.items():
        processed_value = f"processed_{value}"
        result[f"output_{key}"] = processed_value

    return result


# Large data structure for testing
LARGE_CONFIG = {
    "setting_0001": "value_0001",
    "setting_0002": "value_0002",
    "setting_0003": "value_0003",
    "setting_0004": "value_0004",
    "setting_0005": "value_0005",
    "setting_0006": "value_0006",
    "setting_0007": "value_0007",
    "setting_0008": "value_0008",
    "setting_0009": "value_0009",
    "setting_0010": "value_0010",
    "setting_0011": "value_0011",
    "setting_0012": "value_0012",
    "setting_0013": "value_0013",
    "setting_0014": "value_0014",
    "setting_0015": "value_0015",
    "setting_0016": "value_0016",
    "setting_0017": "value_0017",
    "setting_0018": "value_0018",
    "setting_0019": "value_0019",
    "setting_0020": "value_0020",
}
