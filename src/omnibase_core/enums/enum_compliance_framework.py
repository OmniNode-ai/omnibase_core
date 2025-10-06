from enum import Enum


class EnumComplianceFramework(str, Enum):
    """Supported compliance frameworks."""

    SOX = "SOX"  # Sarbanes-Oxley Act
    HIPAA = "HIPAA"  # Health Insurance Portability Act
    GDPR = "GDPR"  # General Data Protection Regulation
    PCI_DSS = "PCI_DSS"  # Payment Card Industry Data Security
    FISMA = "FISMA"  # Federal Information Security Management
    ISO27001 = "ISO27001"  # Information Security Management
    NIST = "NIST"  # NIST Cybersecurity Framework
