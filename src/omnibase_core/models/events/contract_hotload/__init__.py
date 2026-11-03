# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract hot-loading record family (OMN-21226, plan task H1).

Frozen, ``extra="forbid"`` records for the registry, the replies, the prune
protocol and the runtime. They sit beside ``contract_registration``. Import each
model from its own module.

Categories and the models in them:
    request: ``ModelContractLoadRequest``
    registry state: ``ModelContractHotloadAccepted``, ``ModelContractHotloadRemoved``
    replies: ``ModelContractLoadReply``
    prune: ``ModelPruneRequest`` (with ``ModelPruneCandidate``,
        ``ModelPartitionEndOffset``), ``ModelPruneCompletion`` (with
        ``ModelPruneTopicResult``)
    registry records: ``ModelContractRevision``, ``ModelRegistryWatermark``
    runtime events: ``ModelContractHotloadApplied``
    runtime state: ``ModelRuntimeHotloadState`` (with ``ModelHotloadObservedEntry``,
        ``ModelHotloadServedEntry``)

``content_hash`` on every record is the canonical content hash that
``ModelNodeAnnouncement.canonical_content_hash`` states: SHA-256 of the contract
file's bytes with line endings normalised to ``\\n``, as 64 lowercase hexadecimal
characters. It is the form omnibase_infra's ``util_contract_content_hash`` states;
core names it without importing infra.

The topics these records travel on are declared in the registry's and the
runtime's contract files, not here.
"""
