from fastapi import APIRouter, HTTPException, Cookie, status
from fastapi.responses import StreamingResponse
from src.domains.ai.schemas import (
    PlotAnalysisRequest, PlotAnalysisResponse, 
    AskQuestionRequest, AskQuestionResponse,
    ExportZipRequest, ExportPdfRequest
)
from src.domains.ai.service import analyze_plot_with_groq
from src.domains.ai.memory import redis_memory
from src.domains.ai.rag_service import answer_question_with_rag
from src.domains.ai.exporter import generate_zip_archive, generate_pdf_report

router = APIRouter(prefix="/ai", tags=["AI Agent Diagnostics"])

@router.post("/analyze-plot", response_model=PlotAnalysisResponse)
def analyze_plot_endpoint(request: PlotAnalysisRequest, session_token: str = Cookie(None)):
    """
    POST endpoint that receives base64 plot images and context keywords,
    querying the Llama vision model via Groq API. Requires active session_token.
    """
    if not session_token:
         raise HTTPException(status_code=401, detail="Session expired or invalid. Please reload the page.")
         
    if not request.image_base64:
        raise HTTPException(status_code=400, detail="Missing required image data.")
        
    try:
        analysis = analyze_plot_with_groq(
            image_base64=request.image_base64,
            plot_type=request.plot_type,
            context=request.context
        )
        
        # Save generated diagnostics context directly into Upstash Redis memory
        redis_memory.save_plot_analysis(
            session_token=session_token,
            plot_type=request.plot_type,
            analysis=analysis,
            context=request.context or ""
        )
        redis_memory.register_plot_in_session(session_token, request.plot_type)
        
        return PlotAnalysisResponse(success=True, analysis=analysis)
    except Exception as e:
        return PlotAnalysisResponse(success=False, analysis="", error=str(e))

@router.post("/ask-question", response_model=AskQuestionResponse)
def ask_question_endpoint(request: AskQuestionRequest, session_token: str = Cookie(None)):
    """
    POST endpoint that answers researcher questions about a specific plot
    using retrieved facts and cross-plot RAG session history.
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please reload the page."
        )
        
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )
        
    try:
        answer = answer_question_with_rag(
            session_token=session_token,
            plot_type=request.plot_type,
            question=request.question
        )
        return AskQuestionResponse(success=True, answer=answer)
    except Exception as e:
        return AskQuestionResponse(success=False, answer="", error=str(e))

@router.post("/export-zip")
def export_zip_endpoint(request: ExportZipRequest, session_token: str = Cookie(None)):
    """
    POST endpoint that packages multiple base64 plot images into a downloadable ZIP file.
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please reload the page."
        )
    if not request.plots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No plots provided to package."
        )
    try:
        zip_io = generate_zip_archive(request.plots)
        return StreamingResponse(
            zip_io,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=spectroscopy_plots.zip"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate ZIP archive: {str(e)}"
        )

@router.post("/export-pdf")
def export_pdf_endpoint(request: ExportPdfRequest, session_token: str = Cookie(None)):
    """
    POST endpoint that compiles multiple plots and their visual diagnoses into a styled scientific PDF report.
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please reload the page."
        )
    if not request.plots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No plots provided to compile."
        )
    try:
        pdf_io = generate_pdf_report(
            request.plots, 
            request.diagnoses,
            title=request.title,
            subtitle=request.subtitle
        )
        return StreamingResponse(
            pdf_io,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=spectroscopy_report.pdf"}
        )
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}"
        )


