from pydantic import BaseModel
from typing import Optional, Dict

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

class AskQuestionRequest(BaseModel):
    """Schema representing a request to ask a question about a plot."""
    plot_type: str
    question: str

class AskQuestionResponse(BaseModel):
    """Schema representing the response for a plot question."""
    success: bool
    answer: str
    error: Optional[str] = None

class ExportZipRequest(BaseModel):
    """Schema representing a request to package all plots in a ZIP file."""
    plots: Dict[str, str]

class ExportPdfRequest(BaseModel):
    """Schema representing a request to generate a diagnostics PDF report."""
    plots: Dict[str, str]
    diagnoses: Dict[str, str]

