import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import logging
import uvicorn

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env.example"
load_dotenv(env_path)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resolve paths relative to this file
BASE_DIR = Path(__file__).resolve().parent

# Initialize FastAPI app
app = FastAPI(
    title="Resume Helper Chatbot - Frontend",
    description="Chat interface for resume analysis",
    version="1.0.0"
)

# Mount static files (create the directory if it doesn't exist)
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)  # Create if doesn't exist
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")  # Fixed port
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 8000))

logger.info(f"Frontend running on port {FRONTEND_PORT}")
logger.info(f"Backend URL: {BACKEND_URL}")


@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    """
    Render the main chat page
    """
    return templates.TemplateResponse(
        request,
        "chat_page.html",
        {
            "backend_url": BACKEND_URL,  # Pass without /chat
            "title": "Resume Helper Chatbot"
        }
    )

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "service": "frontend",
        "backend_url": BACKEND_URL
    }

@app.post("/api/chat")
async def proxy_chat(request: Request):
    """
    Proxy chat requests to the backend
    This keeps the frontend simple and handles CORS
    """
    try:
        # Get the request body
        body = await request.json()
        
        logger.info(f"Proxying chat request to {BACKEND_URL}/chat")
        
        # Forward to backend
        async with httpx.AsyncClient(timeout=500.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/chat",  # Add /chat here
                json=body
            )
        
        # Return the backend response
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )
        
    except httpx.TimeoutException:
        logger.error("Backend request timed out")
        raise HTTPException(
            status_code=504,
            detail="Backend service timed out. The AI might be taking too long."
        )
    except httpx.ConnectError:
        logger.error(f"Could not connect to backend at {BACKEND_URL}")
        raise HTTPException(
            status_code=503,
            detail=f"Backend service is not available at {BACKEND_URL}"
        )
    except Exception as e:
        logger.error(f"Proxy error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-pdf")
async def proxy_upload_pdf(request: Request):
    """
    Proxy PDF upload to backend
    """
    try:
        # Get the form data
        form = await request.form()
        file = form.get('file')
        
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        content = await file.read()
        
        # Forward to backend
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {'file': (file.filename, content, file.content_type)}
            response = await client.post(
                f"{BACKEND_URL}/upload-pdf",
                files=files
            )
        
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )
        
    except Exception as e:
        logger.error(f"PDF upload proxy error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def proxy_health():
    """
    Check backend health
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/health")
            return JSONResponse(content=response.json())
    except Exception as e:
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503
        )

if __name__ == "__main__":
    
    host = os.getenv("FRONTEND_HOST", "127.0.0.1")
    port = int(os.getenv("FRONTEND_PORT", 8000))
    
    logger.info(f"Starting frontend server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)