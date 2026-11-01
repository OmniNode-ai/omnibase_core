# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
def resolve(request):
    try:
        resolution = HandlerVocabulary().handle(request)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    return resolution
