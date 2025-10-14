"""
Canonical model for rendered template output.
"""

from pydantic import BaseModel


class ModelRenderedTemplate(BaseModel):
    """
    Canonical model for rendered template output.
    """

    content: str
