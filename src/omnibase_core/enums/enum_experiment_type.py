# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Experiment-type enumeration for the Shared Experiment Result Contract.

Strongly typed classification of which canonical experiment orchestrator
produced a :class:`~omnibase_core.models.experiment.model_experiment_result.ModelExperimentResult`.
One member per Phase-3 orchestrator of the SEA→canonical migration
(epic OMN-13604):

* ``ENTROPY``         — ``node_entropy_experiment_orchestrator`` (OMN-13614)
* ``MODEL_EVAL``      — ``node_model_eval_orchestrator`` (OMN-13615)
* ``REGRESSION_TEST`` — ``node_regression_test_orchestrator`` (OMN-13616)

.. versionadded:: OMN-13613
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumExperimentType(UtilStrValueHelper, str, Enum):
    """Which canonical experiment orchestrator produced a result."""

    ENTROPY = "entropy"
    MODEL_EVAL = "model_eval"
    REGRESSION_TEST = "regression_test"


__all__ = ["EnumExperimentType"]
