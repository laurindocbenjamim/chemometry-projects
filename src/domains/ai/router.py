from fastapi import APIRouter, HTTPException
from src.domains.ai.schemas import PlotAnalysisRequest, PlotAnalysisResponse
from src.domains.ai.service import analyze_plot_with_groq

router = APIRouter(prefix="/ai", tags=["AI Agent Diagnostics"])

@router.post("/analyze-plot", response_model=PlotAnalysisResponse)
def analyze_plot_endpoint(request: PlotAnalysisRequest):
    """
    POST endpoint that receives base64 plot images and context keywords,
    querying the Llama vision model via Groq API.
    """
    if not request.image_base64:
        raise HTTPException(status_code=400, detail="Missing required image data.")
        
    try:
        analysis = analyze_plot_with_groq(
            image_base64=request.image_base64,
            plot_type=request.plot_type,
            context=request.context
        )
        return PlotAnalysisResponse(success=True, analysis=analysis)
    except Exception as e:
        return PlotAnalysisResponse(success=False, analysis="", error=str(e))
