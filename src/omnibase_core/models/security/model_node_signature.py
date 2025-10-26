from typing import Optional
from uuid import UUID

from pydantic import Field

__all__ = [
    "ModelCertificateInfo",
    "ModelNodeSignature",
]

"\nModelNodeSignature: Cryptographic signature for envelope audit trails\n\nThis model represents a single node's cryptographic signature in the envelope\nrouting chain, providing non-repudiation and tamper detection capabilities.\n"
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, validator

from omnibase_core.enums.enum_node_operation import EnumNodeOperation
from omnibase_core.enums.enum_signature_algorithm import EnumSignatureAlgorithm
from omnibase_core.models.security.model_operation_details import ModelOperationDetails
from omnibase_core.models.security.model_signature_metadata import (
    ModelSignatureMetadata,
)

from .model_nodesignature import ModelNodeSignature

logger = logging.getLogger(__name__)


@dataclass
class ModelCertificateInfo:
    """Information extracted from an X.509 certificate."""

    certificate_id: UUID
    subject_dn: str
    issuer_dn: str
    serial_number: str
    not_before: datetime
    not_after: datetime
    public_key_hash: str
    key_usage: list[str]
    extended_key_usage: list[str]
