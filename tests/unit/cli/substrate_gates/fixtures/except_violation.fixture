# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture: file with silent except-pass violations — must be detected by Gate 4."""


def may_raise() -> None:
    raise ValueError("fixture")


def bare_except() -> None:
    try:
        may_raise()
    except:
        pass  # violation fixture: intentionally silent


def except_exception() -> None:
    try:
        may_raise()
    except Exception:  # noqa: BLE001
        pass  # violation fixture: intentionally silent


def except_base_exception() -> None:
    try:
        may_raise()
    except BaseException:  # noqa: BLE001
        pass  # violation fixture: intentionally silent


def except_tuple() -> None:
    try:
        may_raise()
    except (Exception, ValueError):  # noqa: BLE001
        pass  # violation fixture: intentionally silent
