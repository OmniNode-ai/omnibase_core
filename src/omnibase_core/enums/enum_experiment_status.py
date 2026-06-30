# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Experiment-status enumeration for the Shared Experiment Result Contract.

Strongly typed lifecycle status of a canonical experiment run carried by
:class:`~omnibase_core.models.experiment.model_experiment_result.ModelExperimentResult`.
Shared by all three Phase-3 experiment orchestrators of the SEA→canonical
migration (epic OMN-13604) so every node reports terminal/lifecycle state
through one vocabulary.

.. versionadded:: OMN-13613
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumExperimentStatus(UtilStrValueHelper, str, Enum):
    """Lifecycle status of a canonical experiment run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


__all__ = ["EnumExperimentStatus"]
