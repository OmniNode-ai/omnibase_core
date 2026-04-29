# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture: file with no silent except-pass violations — Gate 4 must pass this clean."""


def may_raise() -> None:
    raise ValueError("fixture")


def narrow_with_body() -> None:
    try:
        may_raise()
    except ValueError:
        print("handled")  # print-ok: fixture


def narrow_pass_allowed() -> None:
    try:
        may_raise()
    except ValueError:  # substrate-allow: intentional no-op in fixture
        pass


def except_exception_with_reraise() -> None:
    try:
        may_raise()
    except Exception as exc:
        raise RuntimeError("wrapped") from exc


def except_exception_with_log() -> None:
    try:
        may_raise()
    except Exception:  # noqa: BLE001
        print("error occurred")  # print-ok: fixture
