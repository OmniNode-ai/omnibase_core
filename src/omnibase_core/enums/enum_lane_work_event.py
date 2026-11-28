# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The lane work event kinds (OMN-26699, plan section 3.3)."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumLaneWorkEvent(UtilStrValueHelper, str, Enum):
    """Twenty-nine event kinds plus `status_requested`, a read that folds nothing.

    `overlay_pr_needed` (OMN-26698): a red whose remedy is an overlays pull request that must
    merge first; the evidence carries the refusal lines and the node names.
    """

    START = "start"
    WORKER_STARTED = "worker_started"
    CLAIM_CONFIRMED = "claim_confirmed"
    CLAIM_MISSING = "claim_missing"
    CHECK_RED = "check_red"
    CHECK_PENDING = "check_pending"
    CHECK_GREEN = "check_green"
    HEAD_MOVED = "head_moved"
    LOG_READ = "log_read"
    CAUSE_FOUND = "cause_found"
    CAUSE_UNKNOWN = "cause_unknown"
    FIX_COMMITTED = "fix_committed"
    COMMIT_REFUSED = "commit_refused"
    PUSHED = "pushed"
    PUSH_REFUSED = "push_refused"
    PROOF_PASSED = "proof_passed"
    PROOF_FAILED = "proof_failed"
    PROOF_POSTED = "proof_posted"
    PROOF_POST_FAILED = "proof_post_failed"
    HANDOFF_WRITTEN = "handoff_written"
    HANDOFF_FAILED = "handoff_failed"
    DEADLINE_PASSED = "deadline_passed"
    HELP_CAUSE_FOUND = "help_cause_found"
    HELP_RETRY = "help_retry"
    HELP_STOP = "help_stop"
    HELP_FAILED = "help_failed"
    UNCLASSIFIED = "unclassified"
    REPEAT_BOUND_REACHED = "repeat_bound_reached"
    OVERLAY_PR_NEEDED = "overlay_pr_needed"
    STATUS_REQUESTED = "status_requested"
