# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pure workflow policy: shared GitHub quota requires an exact exception."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator

import yaml
from pydantic import ValidationError
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_shared_token_allowlist import (
    ModelSharedTokenAllowlist,
)
from omnibase_core.models.validation.model_shared_token_policy_request import (
    ModelSharedTokenPolicyRequest,
)
from omnibase_core.models.validation.model_shared_token_policy_result import (
    ModelSharedTokenPolicyResult,
)
from omnibase_core.models.validation.model_shared_token_use import ModelSharedTokenUse
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

# Aliases are treated conservatively until an operator establishes separate identity.
_SHARED_SECRETS = frozenset({"CROSS_REPO_PAT", "OMNI_GITHUB_TOKEN"})
_INHERITED_BINDING = "SECRETS_INHERIT"
_EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}", re.DOTALL)
_SECRET = re.compile(
    r"(?<![\w.-])secrets\s*(?:\.\s*([\w-]+)|\[\s*'([^']+)'\s*\])", re.IGNORECASE
)
_CONTEXT = re.compile(r"(?<![\w.-])secrets\b", re.IGNORECASE)


def _pointer(parts: tuple[str, ...]) -> str:
    return "/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in parts)


def _scalars(
    node: Node, parts: tuple[str, ...] = (), ancestors: frozenset[int] = frozenset()
) -> Iterator[tuple[str, str]]:
    """Expand aliases at every use; reject cycles, merge keys and duplicate keys."""
    if id(node) in ancestors:
        raise ModelOnexError(
            message="recursive YAML alias",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    ancestors = ancestors | {id(node)}
    if isinstance(node, ScalarNode):
        yield _pointer(parts), node.value
    elif isinstance(node, SequenceNode):
        for index, value in enumerate(node.value):
            yield from _scalars(value, (*parts, str(index)), ancestors)
    elif isinstance(node, MappingNode):
        keys: set[str] = set()
        for key, value in node.value:
            if (
                not isinstance(key, ScalarNode)
                or key.value in keys
                or key.value == "<<"
            ):
                raise ModelOnexError(
                    message="non-scalar, duplicate or merged YAML key",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            keys.add(key.value)
            # Secrets in a key cannot be a valid Actions binding.
            if _EXPRESSION.search(key.value):
                raise ModelOnexError(
                    message="expression in a YAML mapping key",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            yield from _scalars(value, (*parts, key.value), ancestors)


class HandlerSharedTokenPolicyCompute:
    """Typed COMPUTE handler used by the event-bus runtime and reusable gate."""

    def handle(
        self, request: ModelSharedTokenPolicyRequest
    ) -> ModelSharedTokenPolicyResult:
        """Compare parsed expression uses with exact, counted exceptions."""
        errors: list[str] = []
        observed: list[ModelSharedTokenUse] = []
        try:
            allowlist = ModelSharedTokenAllowlist.model_validate(
                load_yaml_mapping_no_duplicates(
                    request.allowlist, source="shared-token policy"
                )
            )
        except (yaml.YAMLError, ValidationError, ValueError, ModelOnexError):
            # Source text may contain credentials accidentally; never echo parser inputs.
            return ModelSharedTokenPolicyResult(
                errors=("invalid shared-token allowlist",)
            )

        for workflow, source in sorted(request.workflows.items()):
            try:
                tree = yaml.compose(source)
                if not isinstance(tree, MappingNode):
                    raise ModelOnexError(
                        message="workflow must be a mapping",
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    )
                for location, text in _scalars(tree):
                    counts: Counter[str] = Counter()
                    if (
                        location.startswith("/jobs/")
                        and location.endswith("/secrets")
                        and text == "inherit"
                    ):
                        counts[_INHERITED_BINDING] += 1
                    for expression in _EXPRESSION.findall(text):
                        matches = list(_SECRET.finditer(expression))
                        # Computed indexes and exporting all secrets can conceal this token.
                        if _CONTEXT.search(_SECRET.sub("", expression)):
                            errors.append(
                                f"{workflow}:{location}: dynamic or whole secrets context"
                            )
                        counts.update(
                            name
                            for match in matches
                            if (name := (match[1] or match[2]).upper())
                            in _SHARED_SECRETS
                        )
                    observed.extend(
                        ModelSharedTokenUse(
                            workflow=workflow,
                            location=location,
                            reference=secret,
                            count=count,
                        )
                        for secret, count in sorted(counts.items())
                    )
            except (yaml.YAMLError, ValueError, RecursionError, ModelOnexError):
                errors.append(f"{workflow}: invalid or unsupported workflow YAML")

        def key(use: ModelSharedTokenUse) -> tuple[str, str, str, int]:
            return use.workflow, use.location, use.reference.upper(), use.count

        allowed = [key(entry) for entry in allowlist.entries]
        if len(allowed) != len(set(allowed)):
            errors.append("duplicate shared-token exception")
        for entry in allowlist.entries:
            if entry.reference.upper() not in _SHARED_SECRETS | {_INHERITED_BINDING}:
                errors.append("exception names an unsupported secret")
        actual = {key(use) for use in observed}
        for allowed_key in allowed:
            if allowed_key not in actual:
                errors.append(
                    f"stale shared-token exception: {allowed_key[0]}:{allowed_key[1]}"
                )
        return ModelSharedTokenPolicyResult(
            uses=tuple(observed),
            violations=tuple(use for use in observed if key(use) not in allowed),
            errors=tuple(errors),
        )
