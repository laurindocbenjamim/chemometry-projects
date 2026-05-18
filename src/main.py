import os
import sys
import uvicorn

# Inject project root dynamically into system paths to handle direct script execution
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from src.config.config import settings
from src.shared.sentry import init_sentry
from src.domains.pca.router import router as pca_router
from src.domains.ai.router import router as ai_router

# 1. Initialize Sentry tracking
init_sentry()

app = FastAPI(
    title=settings.APP_NAME,
    description="Chemometrics backend pipeline supporting PCA, PLS, and RAMAN baseline correction.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 2. Add CORS Middleware for decoupled frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Global Exception Handler for clean JSON response
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "error": f"Internal Server Error: {str(exc)}"}
    )

# 4. Include Domain Routers
app.include_router(pca_router)
app.include_router(ai_router)

# 5. Serve Frontend static files (HTML, CSS, JS) from 'public' directory
public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
if os.path.exists(public_dir):
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="static")
else:
    # Print a helpful warning if public directory doesn't exist yet
    print(f"Warning: Static files public directory not found at {public_dir}")

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
