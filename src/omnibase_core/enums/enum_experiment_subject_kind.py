# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Subject kind of an experiment: what the experiment is about (OMN-21634)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumExperimentSubjectKind(UtilStrValueHelper, str, Enum):
    """Discriminator for the subject an experiment evaluates.

    The first two values are the existing ones and keep their spelling; the
    rest are added without changing them.

    Attributes:
        DELEGATION_WORKFLOW: A delegation workflow.
        LANE_PROCESS: A lane process.
        MODEL: A model.
        PROTOTYPE_R1: The R1 prototype (verified team status).
        PROTOTYPE_R2: The R2 prototype (verified full result relay).
        PROTOTYPE_R3: The R3 prototype (approval-ready action packet).
        RETROSPECTIVE: The weekly retrospective itself.
    """

    DELEGATION_WORKFLOW = "delegation_workflow"
    LANE_PROCESS = "lane_process"
    MODEL = "model"
    PROTOTYPE_R1 = "prototype_r1"
    PROTOTYPE_R2 = "prototype_r2"
    PROTOTYPE_R3 = "prototype_r3"
    RETROSPECTIVE = "retrospective"
