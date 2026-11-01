# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
def resolve(container, request):
    try:
        resolution = container.get_service(HandlerVocabulary).handle(request)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    return resolution
