import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

# Resolve paths relative to this file, not the working directory at launch
# (same TemplateNotFound fix from week_2).
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Resume Helper Chatbot - Frontend")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/chat")


@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse(
        request,
        "chat_page.html",
        {"backend_url": BACKEND_URL},
    )
