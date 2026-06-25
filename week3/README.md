# System Integration: Resume Helper Chatbot

A complete microservices-based system demonstrating frontend-backend integration with Docker containerization.

---

## System Overview

This is a **microservices-based system** where:

| Component | Port | Purpose |
|-----------|------|---------|
| **Frontend Service** | 8000 | Serves HTML/JS, proxies API requests |
| **Backend Service** | 8001 | Processes AI requests, handles business logic |
| **Docker Network** | - | Connects services internally |
| **Browser** | - | User interface client |

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER BROWSER                              │
│                    http://localhost:8000                           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP Requests
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FRONTEND SERVICE (Port 8000)                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  FastAPI Server (app.py)                                   │   │
│  │  - Serves HTML templates (Jinja2)                         │   │
│  │  - Serves static files (CSS/JS)                           │   │
│  │  - Proxies API requests to backend                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Routes:                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  GET  /              → Renders chat interface               │   │
│  │  GET  /health        → Frontend health check                │   │
│  │  POST /api/chat      → Proxies to backend:/chat            │   │
│  │  POST /api/upload-pdf → Proxies to backend:/upload-pdf     │   │
│  │  GET  /api/health    → Proxies to backend:/health          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Internal Network
                                    │ http://backend:8001
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND SERVICE (Port 8001)                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  FastAPI Server (app.py)                                   │   │
│  │  - Processes chat requests                                  │   │
│  │  - Handles PDF extraction                                   │   │
│  │  - Calls Week 2 AI modules                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Routes:                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  GET  /            → API root info                          │   │
│  │  GET  /health      → Backend health check                   │   │
│  │  POST /chat        → Process chat messages                 │   │
│  │  POST /upload-pdf  → Extract text from PDF                 │   │
│  │  POST /skill-gaps  → Run skill gap analysis                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Week 2 Modules (AI Processing)                            │   │
│  │  - find_skill_gaps.py   → Compares resume vs jobs         │   │
│  │  - prompt_model.py      → Interfaces with Gemini/Ollama   │   │
│  │  - tag_data.py          → Tags job descriptions           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ File System Access
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA STORAGE                              │
│                        (./data/ directory)                          │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Data Files:                                                │   │
│  │  - resume_d3.txt      → Sample resume text                  │   │
│  │  - jobs_d1.db         → SQLite database with job listings  │   │
│  │  - .skill_gap_cache.json → Cached analysis results         │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Docker Network Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     Docker Network                         │
│                "resume-network" (bridge)                   │
│                                                            │
│  ┌────────────────┐          ┌────────────────┐           │
│  │   Backend      │          │   Frontend     │           │
│  │   Container    │◄────────►│   Container    │           │
│  │   "backend"    │          │   "frontend"   │           │
│  │    Port 8001   │          │    Port 8000   │           │
│  └────────────────┘          └────────────────┘           │
│         │                           │                      │
│         │                           │                      │
│         ▼                           ▼                      │
│  ┌────────────────┐          ┌────────────────┐           │
│  │   Volume       │          │   Volume       │           │
│  │   "data"       │          │   "src"        │           │
│  │   ./data:/app/ │          │   ./frontend/  │           │
│  └────────────────┘          └────────────────┘           │
└────────────────────────────────────────────────────────────┘
```

---

## 🔗 Component Integration

### Frontend → Backend Communication

The frontend **does NOT** call the backend directly. It uses a **proxy pattern**:

```javascript
// ❌ Wrong - Direct backend call (causes CORS issues)
fetch('http://backend:8001/chat', { ... })

// ✅ Correct - Through frontend proxy
fetch('/api/chat', { ... })  // ← This goes to frontend:8000/api/chat
```

### Proxy Flow

```
Browser
  │
  │ fetch('/api/chat')
  ▼
Frontend (localhost:8000)
  │
  │ Forward to http://backend:8001/chat
  ▼
Backend (localhost:8001)
  │
  │ Process request
  ▼
Response returns through the same path
```

### Service Communication Matrix

| From → To | Connection Type | URL | Port |
|-----------|----------------|-----|------|
| Browser → Frontend | HTTP (Browser) | `http://localhost:8000` | 8000 |
| Frontend → Backend | HTTP (Internal) | `http://backend:8001` | 8001 |
| Browser → Backend | ❌ Blocked by CORS | - | - |
| Frontend → Data | Volume Mount | `./data:/app/data` | - |
| Backend → Data | Volume Mount | `./data:/app/data` | - |

---

## Data Flow

### Complete Request-Response Flow

```
┌──────────────┐
│   User Types │
│   "What gaps?"│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Browser    │
│  (JS Client) │
└──────┬───────┘
       │ fetch('/api/chat')
       ▼
┌──────────────┐
│  Frontend    │
│   (Port 8000) │
└──────┬───────┘
       │ POST http://backend:8001/chat
       ▼
┌──────────────┐
│  Backend     │
│   (Port 8001) │
└──────┬───────┘
       │ ProcessUserQuery()
       ▼
┌──────────────┐
│ Week 2 Module│
│ Skill Gaps   │
└──────┬───────┘
       │ Read files
       ▼
┌──────────────┐
│   Data Files │
│ /app/data/   │
└──────┬───────┘
       │ Return results
       ▼
┌──────────────┐
│  Response    │
│   JSON       │
└──────┬───────┘
       │ Return through chain
       ▼
┌──────────────┐
│   Display    │
│   to User    │
└──────────────┘
```

---

## Prerequisites

### Required Software

| Software | Version | Purpose | Check Command |
|----------|---------|---------|---------------|
| **Python** | 3.14+ | Runtime | `python --version` |
| **UV** | Latest | Package Manager | `uv --version` |
| **Docker** | 24.0+ | Container Runtime | `docker --version` |
| **Docker Compose** | 2.0+ | Service Orchestration | `docker compose version` |
| **Git** | Latest | Version Control | `git --version` |

### Required Accounts
- **Google Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

### Required Files
```
./data/resume_d3.txt     # Sample resume text
./data/jobs_d1.db        # SQLite database with jobs
```

---

##  Quick Start

### Option 1: Docker (Recommended - One Command)

```bash
# 1. Clone repository
git clone <your-repo>
cd week3

# 2. Configure environment
cp .env.example .env
# Add your GOOGLE_API_KEY to .env

# 3. Build and start everything
docker compose up --build

# 4. Open browser
# http://localhost:8000
```

### Option 2: Local Development (Manual)

```bash
# Terminal 1 - Start Backend
cd backend
uv sync
uv run python src/app.py

# Terminal 2 - Start Frontend
cd frontend
uv sync
uv run python src/app.py

# Open browser
# http://localhost:8000
```

---

## Project Setup

**install Docker Desktop on Windows, follow these steps:**

Download the Docker Desktop installer:

- For x86_64: [Docker Desktop for Windows - x86_64](https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe?utm_source=docker&utm_medium=webreferral&utm_campaign=docs-driven-download-win-amd64&_gl=1*98l6o2*_gcl_au*MTU2MjE4MTUxMC4xNzgyMjE0MTYx*_ga*MTcyNDM4MTAwNS4xNzgyMjE0MTYx*_ga_XJWPQMJYHQ*czE3ODIyMTQxNjEkbzEkZzEkdDE3ODIyMTQzMDckajIzJGwwJGgw)
- For ARM: [Docker Desktop for Windows - Arm (Early Access)](https://desktop.docker.com/win/main/arm64/Docker%20Desktop%20Installer.exe?utm_source=docker&utm_medium=webreferral&utm_campaign=docs-driven-download-win-arm64&_gl=1*98l6o2*_gcl_au*MTU2MjE4MTUxMC4xNzgyMjE0MTYx*_ga*MTcyNDM4MTAwNS4xNzgyMjE0MTYx*_ga_XJWPQMJYHQ*czE3ODIyMTQxNjEkbzEkZzEkdDE3ODIyMTQzMDckajIzJGwwJGgw)

Run the installer:

Double-click Docker Desktop Installer.exe to start the installation.
Choose the installation mode:
Per-user: Installs to %LOCALAPPDATA%\Programs\DockerDesktop (no admin required).
All users: Installs to C:\Program Files\Docker\Docker (requires admin privileges).
During installation, select your preferred backend (WSL 2 or Hyper-V) if prompted.

Follow the installation wizard to complete the setup.

Once installed, start Docker Desktop from the Windows Start menu.

You can also install from the command line:

Per-user installation (no admin required):

```bash
"Docker Desktop Installer.exe" install --user
```

All-users installation (run as administrator):

```bash
"Docker Desktop Installer.exe" install
```

### Note:

Windows containers are only supported in all-users installation mode.
If your administrator account is different from your user account, add your user to the docker-users group for elevated features.

### Running Locally

Install dependencies:
```bash
pip install fastapi "uvicorn[standard]" jinja2
```

Run the server from the **project root** (`frontend/`), not from inside `src/`:
```bash
uvicorn --app-dir src main:app --host 0.0.0.0 --port 8000
```

Then visit `http://localhost:8000` (or `http://127.0.0.1:8000`).

> **Note on paths:** `main.py` loads its HTML templates using a path built relative to the file itself (`Path(__file__).resolve().parent`), not relative to your terminal's current directory. This means the server will find `index.html` correctly no matter which folder you launch `uvicorn` from. If you ever see a `TemplateNotFound` error, check the working directory you ran the command from first.

## Detailed Project Structure

```
week3/
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── docker-compose.yml           # Service orchestration
├── README.md                    # This file
│
├── backend/                     # Backend Service (Port 8001)
│   ├── Dockerfile               # Container configuration
│   ├── .dockerignore            # Docker ignore rules
│   ├── pyproject.toml           # Python dependencies
│   ├── uv.lock                  # Locked dependencies
│   └── src/
│       ├── app.py               # Main FastAPI application
│       └── week2/               # Week 2 Integration
│           ├── __init__.py      # Package initialization
│           ├── find_skill_gaps.py
│           ├── prompt_model.py
│           ├── tag_data.py
│           ├── rate_limits.txt
│           └── data/            # Data directory
│               ├── resume_d3.txt
│               └── jobs_d1.db
│
├── frontend/                    # Frontend Service (Port 8000)
│   ├── Dockerfile               # Container configuration
│   ├── .dockerignore            # Docker ignore rules
│   ├── pyproject.toml           # Python dependencies
│   ├── uv.lock                  # Locked dependencies
│   └── src/
│       ├── app.py               # Main FastAPI application
│       ├── static/              # Static assets
│       │   ├── css/
│       │   │   └── chat.css     # Styling
│       │   └── js/
│       │       └── chat.js      # Client logic
│       └── templates/
│           └── chat_page.html   # HTML template

```

---

## Docker Integration

### Service Dependencies

```yaml
Frontend depends_on:
  Backend (condition: service_healthy)
  
This means:
1. Backend starts first
2. Health check must pass
3. Then Frontend starts
4. If Backend fails, Frontend won't start
```

### Volume Mounts

| Mount Point | Purpose | Write Permission |
|-------------|---------|------------------|
| `./backend/src:/app/src` | Live code updates | ✅ Yes |
| `./frontend/src:/app/src` | Live code updates | ✅ Yes |
| `./data:/app/data` | Persistent data | ✅ Yes |
| `backend-cache:/app/cache` | Skill gap cache | ✅ Yes |

---

## Configuration Files

### `.env.example` - Environment Variables

```env
# =============================================================
# BACKEND CONFIGURATION
# =============================================================
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8001
DATA_DIR=/app/data

# Google API (REQUIRED)
GOOGLE_API_KEY=your-actual-api-key
GOOGLE_BASE_URL=https://generativelanguage.googleapis.com/v1beta/models

# Ollama (Optional)
OLLAMA_BASE_URL=http://host.docker.internal:11434

# File Paths
RESUME_PATH=./data/resume_d3.txt
DB_PATH=./data/jobs_d1.db
CACHE_PATH=./data/.skill_gap_cache.json

# =============================================================
# FRONTEND CONFIGURATION
# =============================================================
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=8000
BACKEND_URL=http://backend:8001  # ← Docker internal URL

# =============================================================
# SHARED
# =============================================================
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

### `docker-compose.yml` - Service Definitions

```yaml
services:
  backend:
    build:
      context: .                  # Build from week3/
      dockerfile: backend/Dockerfile
    container_name: resume-backend
    ports:
      - "8001:8001"               # Host:Container
    env_file:
      - .env.example
    environment:
      - BACKEND_HOST=0.0.0.0
      - BACKEND_PORT=8001
      - DATA_DIR=/app/data
      - BACKEND_URL=http://backend:8001
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
    volumes:
      - ./backend/src:/app/src    # Mount for live updates
      - ./data:/app/data
      - backend-cache:/app/cache
    networks:
      - resume-network
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"  # Windows compatibility
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    container_name: resume-frontend
    ports:
      - "8000:8000"
    env_file:
      - .env.example
    environment:
      - FRONTEND_HOST=0.0.0.0
      - FRONTEND_PORT=8000
      - BACKEND_URL=http://backend:8001  # ← Uses internal URL
    volumes:
      - ./frontend/src:/app/src
    networks:
      - resume-network
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

networks:
  resume-network:
    name: resume-network
    driver: bridge

volumes:
  backend-cache:
    name: resume-backend-cache
```

### Dockerfile Integration

#### Backend Dockerfile
```dockerfile
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev

COPY backend/src/ ./src/

RUN mkdir -p /app/data /app/cache && chmod 777 /app/data /app/cache

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uv", "run", "python", "-m", "src.app"]
```

#### Frontend Dockerfile
```dockerfile
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY frontend/pyproject.toml frontend/uv.lock ./
RUN uv sync --no-dev

COPY frontend/src/ ./src/

RUN mkdir -p ./src/static

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "python", "-m", "src.app"]
```

---

## Integration Points

### 1. Frontend to Backend Proxy

#### `frontend/src/app.py`
```python
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

# Initialize FastAPI app
app = FastAPI(
    title="Resume Helper Chatbot - Frontend",
    description="Chat interface for resume analysis",
    version="1.0.0"
)

# Mount static files
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup templates
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 8000))

logger.info(f"Frontend running on port {FRONTEND_PORT}")
logger.info(f"Backend URL: {BACKEND_URL}")

@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Render the main chat page"""
    return templates.TemplateResponse(
        request,
        "chat_page.html",
        {
            "backend_url": BACKEND_URL,
            "title": "Resume Helper Chatbot"
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "frontend",
        "backend_url": BACKEND_URL
    }

@app.post("/api/chat")
async def proxy_chat(request: Request):
    """Proxy chat requests to the backend"""
    try:
        body = await request.json()
        logger.info(f"Proxying chat request to {BACKEND_URL}/chat")
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/chat",
                json=body
            )
        
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

@app.get("/api/health")
async def proxy_health():
    """Check backend health"""
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
```

### 2. Frontend JavaScript Integration

#### `frontend/src/static/js/chat.js` (Key Part)
```javascript
// The frontend calls its own proxy endpoint
chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = messageInput.value.trim();
    if (!message && !attachedPdfText) {
        setStatus("Type a message or attach a PDF first.", true);
        return;
    }

    const payload = {
        message: message || "Please analyze my resume",
        pdf_content: attachedPdfText,
        pdf_name: attachedPdfName,
    };

    try {
        // ✅ CORRECT: Use frontend proxy
        const response = await fetch('/api/chat', {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        // ❌ NOT: Direct backend call
        // const response = await fetch('http://backend:8001/chat', ...)

        if (!response.ok) {
            throw new Error(`Backend returned ${response.status}`);
        }

        const data = await response.json();
        appendBubble(data.response, "bot");
    } catch (err) {
        console.error("Error:", err);
        appendBubble(`Error: ${err.message}`, "error");
    }
});
```

### 3. Backend Week 2 Integration

#### `backend/src/app.py` (Key Part)
```python
from week2.find_skill_gaps import find_skill_gaps
from week2.prompt_model import prompt_model

def process_user_query(message: str, pdf_content: Optional[str] = None) -> str:
    """Uses Week 2 modules to process requests"""
    try:
        is_gap_query = any(keyword in message.lower() for keyword in [
            'skill gap', 'missing skills', 'what skills am i missing',
            'gaps', 'improve', 'what should i learn', 'skill', 'gap'
        ])
        
        if is_gap_query and pdf_content:
            # Call Week 2 function
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(pdf_content)
                temp_resume_path = f.name
            
            result = find_skill_gaps(temp_resume_path, DB_PATH)
            return format_gap_response(result)
        else:
            # Call Week 2 prompt function
            response_text, _, _ = prompt_model("gemini-2.5-flash", prompt)
            return response_text
    except Exception as e:
        return f"Error: {str(e)}"
```

### 4. Data Volume Integration

#### Backend config for data
```python
# backend/src/week2/config.py
def get_data_dir() -> Path:
    """Get the data directory path"""
    env_data_dir = os.getenv("DATA_DIR")
    if env_data_dir:
        return Path(env_data_dir)  # /app/data in Docker
    
    # Fallback for local development
    current_file = Path(__file__).resolve()
    possible_paths = [
        current_file.parent / "data",
        current_file.parent.parent / "data",
        Path.cwd() / "data",
    ]
    
    for path in possible_paths:
        if path.exists() and path.is_dir():
            return path
    
    default_path = Path.cwd() / "data"
    default_path.mkdir(parents=True, exist_ok=True)
    return default_path

DATA_DIR = get_data_dir()
```

---

## Request/Response Flow in Detail

### 1. User Sends Message

```
User: "What skills am I missing?"
   │
   ▼
Browser sends fetch('/api/chat')
   │
   ▼
Frontend receives /api/chat
   │
   ▼
Frontend forwards to backend:8001/chat
   │
   ▼
Backend receives /chat
   │
   ▼
Backend calls process_user_query()
   │
   ▼
process_user_query calls find_skill_gaps()
   │
   ▼
find_skill_gaps reads /app/data/jobs_d1.db
   │
   ▼
find_skill_gaps calls prompt_model()
   │
   ▼
prompt_model calls Google Gemini API
   │
   ▼
Gemini API returns analysis
   │
   ▼
Backend formats response
   │
   ▼
Response travels back through the chain
   │
   ▼
Browser displays the response
```

### 2. PDF Upload Flow

```
User Uploads: resume.pdf
   │
   ▼
Browser sends file to /api/upload-pdf
   │
   ▼
Frontend forwards to backend:8001/upload-pdf
   │
   ▼
Backend reads PDF with pdfplumber
   │
   ▼
Backend extracts text
   │
   ▼
Backend stores text in memory
   │
   ▼
Returns extracted text to frontend
   │
   ▼
Frontend returns to browser
   │
   ▼
Browser stores for next message
```

---

## API Endpoints

### Frontend Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Render chat interface |
| GET | `/health` | Frontend health check |
| POST | `/api/chat` | Proxy to backend `/chat` |
| POST | `/api/upload-pdf` | Proxy to backend `/upload-pdf` |
| GET | `/api/health` | Proxy to backend `/health` |

### Backend Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | API root info |
| GET | `/health` | Backend health check |
| POST | `/chat` | Process chat messages |
| POST | `/upload-pdf` | Extract text from PDF |
| POST | `/skill-gaps` | Run skill gap analysis |

---

## Testing the Integration

### Test 1: Frontend Health Check
```bash
curl http://localhost:8000/health
```
Expected:
```json
{"status":"healthy","service":"frontend","backend_url":"http://backend:8001"}
```

### Test 2: Backend Health Check
```bash
curl http://localhost:8001/health
```
Expected:
```json
{"status":"healthy","service":"resume-chatbot-backend","week2_available":true}
```

### Test 3: Backend API Direct
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```

### Test 4: Frontend Proxy
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```

### Test 5: Full Integration Flow
```bash
# From frontend container
docker compose exec frontend curl http://backend:8001/health

# From host
curl http://localhost:8000/api/health
```

---

## Troubleshooting Integration Issues

### Issue 1: Frontend Can't Connect to Backend (DNS)

**Symptom:** `Could not resolve host: backend`
**Cause:** Docker DNS resolution failing on Windows
**Fix:** Use `host.docker.internal` in `.env`:
```env
BACKEND_URL=http://host.docker.internal:8001
```

### Issue 2: CORS Errors

**Symptom:** Browser console shows CORS errors
**Cause:** Frontend trying to call backend directly
**Fix:** Use frontend proxy `/api/chat` instead:
```javascript
// ❌ Wrong
fetch('http://backend:8001/chat')
// ✅ Correct
fetch('/api/chat')
```

### Issue 3: Module Not Found

**Symptom:** `ModuleNotFoundError: No module named 'week2'`
**Cause:** Wrong import path
**Fix:** Make sure folder name matches import:
```python
# If folder is week2:
from week2.find_skill_gaps import find_skill_gaps
# If folder is week_2:
from week_2.find_skill_gaps import find_skill_gaps
```

### Issue 4: Timeout

**Symptom:** `504 Backend service timed out`
**Cause:** AI processing too slow
**Fix:** Increase timeout in frontend:
```python
async with httpx.AsyncClient(timeout=180.0) as client:  # 3 minutes
```

### Issue 5: Data Files Not Found

**Symptom:** `FileNotFoundError: resume_d3.txt`
**Cause:** Wrong DATA_DIR or missing files
**Fix:** Check files in data directory:
```bash
ls -la data/
# Should show: resume_d3.txt, jobs_d1.db
```

### Issue 6: Permission Denied (Linux/Mac)

**Symptom:** `Permission denied` when accessing data
**Cause:** File permissions on mounted volume
**Fix:**
```bash
sudo chown -R $USER:$USER ./data
chmod 755 ./data
```

### Issue 7: Windows Path Issues

**Symptom:** `Could not find a part of the path`
**Cause:** Windows path separators in Docker
**Fix:** Use forward slashes in `docker-compose.yml`:
```yaml
volumes:
  - ./backend/src:/app/src  # ✅ Correct
  # - .\backend\src:/app/src  # ❌ Wrong
```

---

## Integration Testing Matrix

| Test Point | Command | Expected |
|------------|---------|----------|
| Frontend running | `curl http://localhost:8000/health` | 200 OK |
| Backend running | `curl http://localhost:8001/health` | 200 OK |
| Frontend → Backend | `docker compose exec frontend curl http://backend:8001/health` | 200 OK |
| Backend → Data | `docker compose exec backend ls /app/data` | Shows files |
| Frontend proxy | `curl http://localhost:8000/api/health` | 200 OK |
| Chat endpoint | `curl -X POST http://localhost:8000/api/chat -d '{"message":"Hello"}'` | Response |

---

## Docker Commands Cheat Sheet

```bash
# ============================================================
# BUILD AND RUN
# ============================================================

# Build and start all services
docker compose up --build

# Start in background
docker compose up -d

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v

# Rebuild without cache
docker compose build --no-cache

# ============================================================
# VIEW AND MONITOR
# ============================================================

# View all running containers
docker compose ps

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f backend
docker compose logs -f frontend

# View last 50 lines
docker compose logs --tail=50 backend

# View resource usage
docker stats

# ============================================================
# CONTAINER ACCESS
# ============================================================

# Enter backend container
docker compose exec backend bash

# Enter frontend container
docker compose exec frontend bash

# Run command in container
docker compose exec backend curl http://localhost:8001/health

# ============================================================
# NETWORK AND VOLUMES
# ============================================================

# List networks
docker network ls

# Inspect network
docker network inspect resume-network

# List volumes
docker volume ls

# Remove network
docker network rm resume-network

# ============================================================
# CLEAN UP
# ============================================================

# Remove everything
docker compose down --rmi all -v

# Clean unused resources
docker system prune -f

# Clean everything (including volumes)
docker system prune -a -f --volumes
```

---

## Summary

### How Components Connect

```
User → Frontend (8000) → Backend (8001) → Data/ → Response
         ↓                    ↓
       UI Serves         AI Processes
       Proxies API       Week 2 Modules
       Static Files      Gemini/Ollama
```

### Key Files to Understand

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Service orchestration |
| `frontend/src/app.py` | Frontend server with proxy |
| `backend/src/app.py` | Backend API server |
| `backend/src/week2/` | AI processing logic |
| `.env.example` | Environment configuration |

---