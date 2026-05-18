import html
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status, Cookie
from typing import List
from pydantic import ValidationError

from src.domains.pca.schemas import PipelineRequest, PipelineResponse
from src.domains.pca.service import process_spectroscopy_pipeline

router = APIRouter(prefix="/api/v1/pca", tags=["Chemometrics PCA/PLS/RAMAN Pipeline"])

@router.post("/process", response_model=PipelineResponse)
async def process_files(
    files: List[UploadFile] = File(..., description="List of spectroscopy files in .csv or .sp format"),
    config: str = Form(
        '{"algorithm": "PCA", "format": "auto", "preprocessing": {"snv": true, "sg_filter": true, "sg_window_length": 15, "sg_polyorder": 2, "sg_deriv": 0, "mean_center": true}}',
        description="JSON string of the pipeline configuration"
    ),
    session_token: str = Cookie(None)
):
    """
    Accepts multiple file uploads (.csv or .sp format), validates and sanitizes them,
    auto-detects the format, and runs the selected chemometrics algorithm (PCA, PLS, or RAMAN).
    Requires active session_token.
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please reload the page."
        )
    # 1. Parse and validate configuration
    try:
        request_config = PipelineRequest.model_validate_json(config)
    except ValidationError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Configuration validation failed: {ve.errors()}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration JSON string: {str(e)}"
        )

    # 2. Basic sanitization and security validations on files
    sanitized_files = []
    for f in files:
        # Secure filename sanitization to prevent directory traversal
        original_name = f.filename
        if not original_name:
            continue
        
        # Strip path and escape special characters for safety (anti-XSS and anti-injection)
        clean_name = html.escape(original_name.split("/")[-1].split("\\")[-1])
        
        # Validate file extensions (allow only .csv or .sp)
        ext = clean_name.split(".")[-1].lower()
        if ext not in {"csv", "sp"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation error: File '{clean_name}' has an invalid extension. Only .csv and .sp are allowed."
            )
        
        try:
            content = await f.read()
            # Enforce maximum size validation (5MB) per file
            if len(content) > 5 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File '{clean_name}' exceeds the 5MB size limit."
                )
            
            sanitized_files.append((clean_name, content))
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read file '{clean_name}': {str(err)}"
            )

    if not sanitized_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were uploaded or filenames were invalid."
        )

    # 3. Process the spectroscopy pipeline
    try:
        result = process_spectroscopy_pipeline(sanitized_files, request_config)
        return PipelineResponse(**result)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except KeyError as ke:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Data structure error: {str(ke)}"
        )
    except Exception as exc:
        # Unhandled exceptions will be captured by Sentry middleware
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline processing failed: {str(exc)}"
        )
