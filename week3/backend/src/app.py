import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from week2 import find_skill_gaps

load_dotenv()

app = FastAPI(title="Resume Helper Chatbot - Backend")

# Frontend runs in a separate container/origin, so CORS must be open for it
# to call this API from the browser. Narrow allow_origins for real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to the already-tagged jobs DB (tech_stack column populated by
# week_2/tag_data.py). Resolved from an env var rather than hard-coded so it
# can point at a mounted volume in Docker vs. a local path when running
# without Docker. Defaults to backend/data/jobs_d1.db.
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("JOBS_DB_PATH", str(BASE_DIR / "data" / "jobs_d1.db"))


# Same shape the frontend sends — message, resume_text, filename.
class ChatRequest(BaseModel):
    message: str | None = None
    resume_text: str | None = None
    filename: str | None = None


class ChatResponse(BaseModel):
    reply: str


def _format_gap_reply(result) -> str:
    if not result.gaps:
        return (
            "No skill gaps found — your resume already covers every skill "
            "mentioned across the tagged job postings (or no tagged jobs "
            "were found to compare against)."
        )

    gap_list = "\n".join(f"- {gap}" for gap in result.gaps)
    return (
        f"Found {len(result.gaps)} skill(s) mentioned in job postings that "
        f"don't appear in your resume:\n\n{gap_list}\n\n"
        f"(analysis took {result.time}s, {result.tokens} tokens used)"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    if not payload.resume_text:
        return ChatResponse(
            reply="Please attach a resume PDF — I compare it against the "
            "tagged job postings to find skill gaps."
        )

    result = find_skill_gaps(payload.resume_text, DB_PATH)
    return ChatResponse(reply=_format_gap_reply(result))


@app.get("/health")
async def health():
    return {"status": "ok"}