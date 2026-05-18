from pydantic import BaseModel
from typing import Optional

class PlotAnalysisRequest(BaseModel):
    """Schema representing an AI plot analysis request."""
    image_base64: str
    plot_type: str
    context: Optional[str] = ""

class PlotAnalysisResponse(BaseModel):
    """Schema representing an AI plot analysis response."""
    success: bool
    analysis: str
    error: Optional[str] = None
