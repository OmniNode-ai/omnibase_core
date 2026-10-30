from typing import Any


def plain(values: dict[str, Any]) -> dict[str, Any]:
    return values


def fine(values: dict[str, int]) -> int:
    return 1


def allow_dict_any(fn):
    return fn


def allow_dict_str_any(reason):
    return lambda fn: fn


@allow_dict_any
def decorated(values: dict[str, Any]) -> dict[str, Any]:
    return values


@allow_dict_str_any("reason")
class Decorated:
    field: dict[str, Any]

    def method(self, x: dict[str, Any]) -> None:
        return None


# ONEX_EXCLUDE: dict_str_any
def excluded(
    a: dict[str, Any],
    b: int,
) -> None:
    return None


def beyond_window(
    a: int,
    b: int,
    c: int,
    d: int,
    e: int,
    f: dict[str, Any],
) -> None:
    return None


async def coroutine(x: dict[str, Any]) -> None:
    return None
