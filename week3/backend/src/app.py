# backend/src/app.py
import os
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import logging
import uvicorn
import pdfplumber
import io

from week2.find_skill_gaps import find_skill_gaps
from week2.prompt_model import prompt_model


# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env.example"
load_dotenv(env_path)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Resume Helper Chatbot API",
    description="Analyze resumes and find skill gaps using AI",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000",
        # Add any other origins your frontend uses
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    expose_headers=["Content-Type"],
    max_age=600,  # Cache preflight for 10 minutes
)


@app.options("/{path:path}")
async def options_all(path: str):
    """Handle OPTIONS preflight requests for all paths"""
    return JSONResponse(
        content={"message": "OK"},
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Max-Age": "600",
        }
    )


class ChatRequest(BaseModel):
    message: str
    pdf_content: Optional[str] = None
    pdf_name: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    skill_gaps: Optional[list] = None
    pdf_analyzed: bool = False

class SkillGapRequest(BaseModel):
    resume_text: str
    db_path: Optional[str] = None

# Configuration
BASE_DIR = Path(__file__).parent
DEFAULT_RESUME_PATH = BASE_DIR / "week2" / "data" / "resume_d3.txt"
DEFAULT_DB_PATH = BASE_DIR / "week2" / "data" / "jobs_d1.db"

RESUME_PATH = os.getenv("RESUME_PATH", str(DEFAULT_RESUME_PATH))
DB_PATH = os.getenv("DB_PATH", str(DEFAULT_DB_PATH))


def process_user_query(message: str, pdf_content: Optional[str] = None) -> str:
    """Process user messages using Week 2 functionality."""
    try:
        is_gap_query = any(keyword in message.lower() for keyword in [
            'skill gap', 'missing skills', 'what skills am i missing',
            'gaps', 'improve', 'what should i learn', 'skill', 'gap'
        ])
        
        if is_gap_query and pdf_content:
            logger.info("Processing skill gap analysis request...")
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(pdf_content)
                temp_resume_path = f.name
            
            try:
                result = find_skill_gaps(temp_resume_path, DB_PATH)
                
                if result.gaps:
                    gaps_list = "\n".join(f"- {gap}" for gap in result.gaps[:20])
                    response = f"""**Skill Gap Analysis Complete**

I found **{len(result.gaps)} skills** that appear in job postings but are missing from your resume:

{gaps_list}

{f"... and {len(result.gaps) - 20} more" if len(result.gaps) > 20 else ""}

**Recommendations:**
1. Consider adding these skills to your resume (if you have them)
2. Look for courses or projects to learn these technologies
3. Highlight related experience that demonstrates these skills

*Analysis took {result.time} seconds using {result.tokens} tokens.*
"""
                else:
                    response = """**Great News!**

I didn't find any major skill gaps between your resume and current job requirements. Your skills are well-aligned with what employers are looking for!

**Next steps:**
1. Still refine your resume's wording
2. Focus on highlighting achievements
3. Consider adding a projects section
"""
                
                os.unlink(temp_resume_path)
                return response
                
            except Exception as e:
                logger.error(f"Skill gap analysis failed: {e}")
                return f"Sorry, I couldn't analyze the skill gaps. Error: {str(e)}"
        
        elif pdf_content:
            logger.info("Processing resume text analysis...")
            
            prompt = f"""
            You are a resume expert. Analyze the following resume and provide:
            1. A summary of the candidate's profile
            2. Key technical skills identified
            3. Potential areas for improvement
            
            Resume:
            {pdf_content[:3000]}
            """
            
            response_text, _, _ = prompt_model("gemini-2.5-flash", prompt)
            
            if isinstance(response_text, str) and not response_text.startswith("Error:"):
                return f"**Resume Analysis**\n\n{response_text}"
            else:
                return f"Sorry, I couldn't analyze your resume. The AI service returned: {response_text}"
        
        else:
            logger.info("Processing general chat query...")
            
            prompt = f"""
            You are a helpful career assistant focused on resume writing and job searching.
            
            The user asked: {message}
            
            Provide helpful, specific advice. Be encouraging but honest.
            Keep your response under 200 words unless more detail is needed.
            """
            
            response_text, _, _ = prompt_model("gemini-2.5-flash", prompt)
            
            if isinstance(response_text, str) and not response_text.startswith("Error:"):
                return response_text
            else:
                return f"Sorry, I couldn't process your request. Error: {response_text}"
            
    except Exception as e:
        logger.error(f"Error in process_user_query: {str(e)}")
        return f"An error occurred while processing your request: {str(e)}"

def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
            return text
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return f"Error extracting PDF text: {str(e)}"


@app.get("/")
async def root():
    return {
        "message": "Welcome to Resume Helper Chatbot API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "resume-chatbot-backend",
        "week2_available": True,
        "db_path": DB_PATH,
        "resume_path": RESUME_PATH
    }

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Process chat messages with optional PDF content"""
    try:
        logger.info(f"Received chat request: {request.message[:50] if request.message else 'No message'}...")
        
        response_text = process_user_query(
            message=request.message,
            pdf_content=request.pdf_content
        )
        
        skill_gaps = None
        if request.pdf_content:
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(request.pdf_content)
                    temp_path = f.name
                
                result = find_skill_gaps(temp_path, DB_PATH)
                skill_gaps = result.gaps[:10] if result.gaps else []
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Could not extract skill gaps: {e}")
        
        return ChatResponse(
            response=response_text,
            skill_gaps=skill_gaps,
            pdf_analyzed=bool(request.pdf_content)
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", 8001))
    
    if not DEFAULT_RESUME_PATH.exists():
        logger.warning(f"Default resume file not found: {DEFAULT_RESUME_PATH}")
    if not DEFAULT_DB_PATH.exists():
        logger.warning(f"Default database file not found: {DEFAULT_DB_PATH}")
    
    logger.info(f"Starting backend server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)