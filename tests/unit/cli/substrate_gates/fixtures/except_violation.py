# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture: file with silent except-pass violations — must be detected by Gate 4."""


def bare_except() -> None:
    try:
        pass
    except:
        pass


def except_exception() -> None:
    try:
        pass
    except Exception:  # noqa: BLE001
        pass


def except_base_exception() -> None:
    try:
        pass
    except BaseException:  # noqa: BLE001
        pass


def except_tuple() -> None:
    try:
        pass
    except (Exception, ValueError):  # noqa: BLE001
        pass
