"""
find_skill_gaps.py

Compares a resume against the technical stacks of all tagged job postings
in the database, and returns the skills mentioned across those jobs that
are NOT present in the resume.

Batching:
    The full set of distinct skills (already extracted into the
    tech_stack column by tag_data.py — no re-extraction from raw
    descriptions happens here) is split into batches. Each batch is
    compared against the resume in its own prompt. The final gap list
    is the union of all per-batch gaps, deduplicated and sorted.

Determinism guarantee:
    Each batch result is cached to disk (.skill_gap_cache.json), keyed
    by a hash of (resume content + that batch's exact skill list).
    Re-running with the same resume and same tagged DB hits the cache
    for every batch and makes zero additional API calls, returning the
    exact same result every time. This is necessary because LLM APIs
    can have run-to-run variance even at temperature=0 — caching is
    what actually guarantees identical output across separate process
    runs, not the model call itself.

Usage:
    uv run find_skill_gaps.py [resume.txt] [jobs_d1.db]
    (both arguments are optional; see DEFAULT_RESUME_PATH / DEFAULT_DB_PATH)
"""

import json
import math
import random
import re
import sqlite3
import sys
import time
import hashlib
from pathlib import Path
from typing import List

from pydantic import BaseModel

from .prompt_model import prompt_model, GOOGLE_GEMINI_MODELS
from .tag_data import read_rate_limits
from .config import DATA_DIR, RESUME_PATH, DB_PATH, CACHE_PATH

DEFAULT_RESUME_PATH = Path(RESUME_PATH)
DEFAULT_DB_PATH = Path(DB_PATH)
CACHE_PATH = Path(CACHE_PATH)
DATA_DIR = Path(DATA_DIR)
# DEFAULT_RESUME_PATH = Path.cwd() / "resources_eval" / "resume_d3_eval.txt"
# DEFAULT_DB_PATH = Path.cwd() / "resources_eval" / "jobs_d3_eval.db"
# CURRENT_FILE = Path(__file__).resolve()
# WEEK2_ROOT = CURRENT_FILE.parent.parent  # Goes up: week2 -> backend -> week3
# DATA_DIR = WEEK2_ROOT / "data"  # Now points to week3/data/

# DEFAULT_RESUME_PATH = Path.cwd() / "data" / "resume_d3.txt"
# DEFAULT_DB_PATH = Path.cwd() / "data" / "jobs_d1.db"

# DEFAULT_RESUME_PATH = DATA_DIR / "resume_d3.txt"
# DEFAULT_DB_PATH = DATA_DIR / "jobs_d1.db"

MODEL = "gemini-2.5-flash"
# CACHE_PATH = Path.cwd() / ".skill_gap_cache.json"

# Skill compound terms that contain a "/" but must NOT be split into
# separate skills. Matched case-insensitively as whole phrases.
SLASH_EXCEPTIONS = {"a/b testing", "ci/cd"}

AVG_TOKENS_PER_SKILL = 8  # rough estimate of tokens per skill string,
# used to size batches sensibly
SAFETY_MARGIN = 0.8
MAX_RETRIES = 3


class SkillGapResult(BaseModel):
    gaps: List[str]
    time: float = 0.0
    tokens: int = 0


def _get_rate_params(model: str):
    """
    Returns (sleep_per_request, batch_size, rpm), derived from
    rate_limits.txt for Gemini models.

    batch_size here means: how many distinct skills to pack into a single
    comparison prompt. Derived the same way as tag_data.py's batch size —
    the stricter of an RPM-safe and TPM-safe limit — just using a much
    smaller per-item token estimate, since a skill string like "Python"
    is far shorter than a full job description.
    """
    if model in GOOGLE_GEMINI_MODELS:
        try:
            limits = read_rate_limits(model)
        except FileNotFoundError:
            # rate_limits.txt missing — fall back to a conservative default
            # rather than crashing.
            return 12.0, 50, 5

        if model not in limits:
            return 12.0, 50, 5

        rpm = limits[model]["rpm"]
        tpm = limits[model]["tpm"]

        sleep_per_request = 60 / rpm

        rpm_safe_calls = math.floor(rpm * SAFETY_MARGIN)
        tpm_safe_skills_per_call = math.floor(
            (tpm / AVG_TOKENS_PER_SKILL) * SAFETY_MARGIN / max(1, rpm_safe_calls)
        )
        # Batch size is capped at a sane upper bound too, so a single
        # prompt never becomes unreasonably long.
        batch_size = max(1, min(tpm_safe_skills_per_call, 100))

        return sleep_per_request, batch_size, rpm

    # Non-Gemini / unknown model — conservative fallback.
    return 12.0, 50, 5


def _split_skill_string(raw: str) -> List[str]:
    """
    Splits a comma-separated tech_stack string into individual skills,
    lowercased and trimmed.

    Each skill is then further split on "/" UNLESS it matches one of the
    SLASH_EXCEPTIONS (e.g. "A/B testing", "CI/CD"), which are kept intact.

    E.g. "AWS/Azure/GCP" -> ["aws", "azure", "gcp"]
         "A/B testing"   -> ["a/b testing"]
         "CI/CD"         -> ["ci/cd"]
    """
    if not raw or not isinstance(raw, str):
        return []

    skills = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue

        part_lower = part.lower()
        if part_lower in SLASH_EXCEPTIONS:
            skills.append(part_lower)
            continue

        if "/" in part:
            sub_parts = [p.strip().lower() for p in part.split("/") if p.strip()]
            skills.extend(sub_parts)
        else:
            skills.append(part_lower)

    return skills


def _normalize_skill_list(skills: List[str]) -> List[str]:
    """
    Deduplicates and sorts a list of lowercase skill strings.
    """
    cleaned = sorted(set(s.strip().lower() for s in skills if s and s.strip()))
    return cleaned


def _cache_key(resume_text: str, skill_batch: List[str]) -> str:
    """
    Builds a stable hash key from the resume content and one batch's
    exact skill list, so each batch is cached independently. If the
    resume changes, or the overall skill set (and therefore the
    batching) changes, the keys no longer match and the cache misses
    correctly rather than returning stale results.
    """
    payload = resume_text.strip() + "||" + "||".join(skill_batch)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError, OSError:
        # Corrupted or unreadable cache file — treat as empty rather than crash.
        return {}


def _save_cache(cache: dict):
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except OSError:
        # If we can't write the cache, that's fine — just means this run's
        # result won't be reusable next time. Not a fatal error.
        pass


def _build_gap_prompt(resume_text: str, skill_batch: List[str]) -> str:
    skills_block = ", ".join(skill_batch)

    prompt = (
        "You are a technical recruiter assistant.\n\n"
        "You are given:\n"
        "1. A resume (plain text).\n"
        "2. A list of distinct technical skills required across a set of "
        "job postings.\n\n"
        "Task: Identify which skills from the job-postings list are NOT "
        "present in the resume, even if expressed with different wording, "
        'abbreviations, or casing (e.g. if the resume mentions "C/C++", '
        'then "c" and "c++" both count as already present — do not '
        "list either of them as a gap).\n\n"
        "Output rules:\n"
        "- Return ONLY a comma-separated list of the missing skills, "
        "exactly as they appear in the input skills list (same spelling, "
        "same casing as given).\n"
        "- Do not include skills that are present in the resume under any "
        "reasonable equivalent phrasing.\n"
        "- Ignore certifications, even if technology-related.\n"
        "- Ignore non-technical skills (e.g. leadership, management, "
        "communication).\n"
        "- Do not add any other text: no headers, no explanations, no "
        "bullet points, no numbering, no preamble.\n"
        "- If there are no missing skills, return an empty response.\n\n"
        f"Resume:\n{resume_text}\n\n"
        f"Job posting skills:\n{skills_block}"
    )
    return prompt


def _parse_gap_response(text: str) -> List[str]:
    if not text or not isinstance(text, str):
        return []
    # Model is asked for a comma-separated list; split defensively in case
    # it adds stray newlines or bullet characters despite instructions.
    cleaned = text.strip().strip("-•\n ")
    if not cleaned:
        return []
    parts = re.split(r"[,\n]", cleaned)
    return [p.strip() for p in parts if p.strip()]


def _call_model_for_batch_gaps(
    resume_text: str, skill_batch: List[str], rpm: int, sleep_per_request: float
):
    """
    Sends one batch of skills + the resume to the model, retrying on
    rate-limit errors. Returns (gap_list, prompt_tokens, output_tokens)
    for this single batch. On unrecoverable failure, returns ([], 0, 0)
    rather than raising.
    """
    prompt = _build_gap_prompt(resume_text, skill_batch)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            text, prompt_tokens, output_tokens = prompt_model(MODEL, prompt)
        except Exception as e:
            # prompt_model() is documented to not raise, but guard anyway —
            # no error from a dependency should ever crash this script.
            print(f"  Warning: unexpected exception calling model: {e}")
            text, prompt_tokens, output_tokens = f"Error: {e}", None, None

        if not isinstance(text, str):
            text = ""

        if text.startswith("Error:"):
            is_rate_limited = "429" in text or "Too Many Requests" in text
            if is_rate_limited and attempt < MAX_RETRIES:
                retry_wait = (2 ** (attempt - 1)) * (60 / rpm) + random.uniform(0, 1)
                print(
                    f"  Rate limited. Waiting {retry_wait:.1f}s "
                    f"(attempt {attempt}/{MAX_RETRIES})..."
                )
                time.sleep(retry_wait)
                continue
            # Non-retryable error, or out of retries — fail fast rather
            # than burning remaining attempts on something retrying can't fix.
            print(f"  Warning: model call failed: {text}")
            return [], (prompt_tokens or 0), (output_tokens or 0)

        gaps = _parse_gap_response(text)
        return gaps, (prompt_tokens or 0), (output_tokens or 0)

    return [], 0, 0


def find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult:
    """
    Reads the resume at input_file_path and the `jobs` table at db_url,
    and returns the skills mentioned across tagged jobs that are missing
    from the resume.

    Handles all errors gracefully: missing files, missing DB, missing
    table/columns, model/API failures, and malformed cache data all
    result in a best-effort SkillGapResult rather than a crash.
    """
    start_time = time.time()

    # --- Read resume ---------------------------------------------------- #
    try:
        
        encodings = ['utf-8', 'windows-1252', 'latin-1', 'cp1252']
        resume_text = None
        
        for encoding in encodings:
            try:
                with open(input_file_path, "r", encoding=encoding) as f:
                    resume_text = f.read()
                print(f"Successfully read file with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
        
        if resume_text is None:
            # Last resort: ignore errors
            with open(input_file_path, "r", encoding='utf-8', errors='ignore') as f:
                resume_text = f.read()
            print("⚠️ Read file with errors='ignore'")
            
    except (FileNotFoundError, OSError) as e:
        print(f"Warning: could not read resume file '{input_file_path}': {e}")
        return SkillGapResult(
            gaps=[], time=round(time.time() - start_time, 2), tokens=0
        )

    if not resume_text.strip():
        print(f"Warning: resume file '{input_file_path}' is empty.")
        return SkillGapResult(
            gaps=[], time=round(time.time() - start_time, 2), tokens=0
        )

    # --- Read tagged tech_stack values from DB --------------------------- #
    conn = None
    try:
        conn = sqlite3.connect(db_url)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("PRAGMA table_info(jobs)")
        columns = [row["name"] for row in cur.fetchall()]

        if "tech_stack" not in columns:
            print(
                f"Warning: 'tech_stack' column not found in '{db_url}'. "
                "Has the database been tagged yet?"
            )
            return SkillGapResult(
                gaps=[], time=round(time.time() - start_time, 2), tokens=0
            )

        rows = cur.execute(
            "SELECT tech_stack FROM jobs WHERE tech_stack IS NOT NULL AND tech_stack != ''"
        ).fetchall()

    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        print(f"Warning: database error reading '{db_url}': {e}")
        return SkillGapResult(
            gaps=[], time=round(time.time() - start_time, 2), tokens=0
        )
    except Exception as e:
        print(f"Warning: unexpected error reading database: {e}")
        return SkillGapResult(
            gaps=[], time=round(time.time() - start_time, 2), tokens=0
        )
    finally:
        if conn is not None:
            conn.close()

    if not rows:
        print("Warning: no tagged rows found in the jobs table.")
        return SkillGapResult(
            gaps=[], time=round(time.time() - start_time, 2), tokens=0
        )

    # --- Build the deterministic, deduplicated skill list straight from
    #     the already-tagged tech_stack column — no LLM re-extraction. ---- #
    all_skills = []
    for row in rows:
        all_skills.extend(_split_skill_string(row["tech_stack"]))
    job_skills = _normalize_skill_list(all_skills)

    if not job_skills:
        return SkillGapResult(
            gaps=[], time=round(time.time() - start_time, 2), tokens=0
        )

    # --- Split the skill list into batches --------------------------------#
    sleep_per_request, batch_size, rpm = _get_rate_params(MODEL)

    batches = [
        job_skills[i : i + batch_size] for i in range(0, len(job_skills), batch_size)
    ]

    print(
        f"Comparing {len(job_skills)} distinct skills against the resume "
        f"in {len(batches)} batch(es) of up to {batch_size}..."
    )

    cache = _load_cache()
    all_gaps = set()
    total_tokens = 0

    for batch_num, skill_batch in enumerate(batches):
        key = _cache_key(resume_text, skill_batch)

        if key in cache:
            cached = cache[key]
            all_gaps.update(cached.get("gaps", []))
            total_tokens += cached.get("tokens", 0)
            print(
                f"  [Batch {batch_num}] cache hit — {len(cached.get('gaps', []))} gap(s)."
            )
            continue

        gaps_raw, prompt_tokens, output_tokens = _call_model_for_batch_gaps(
            resume_text, skill_batch, rpm, sleep_per_request
        )
        batch_gaps = _normalize_skill_list(gaps_raw)
        batch_tokens = prompt_tokens + output_tokens

        all_gaps.update(batch_gaps)
        total_tokens += batch_tokens

        cache[key] = {"gaps": batch_gaps, "tokens": batch_tokens}
        _save_cache(cache)

        print(f"  [Batch {batch_num}] {len(batch_gaps)} gap(s), {batch_tokens} tokens.")

        if batch_num < len(batches) - 1:
            time.sleep(sleep_per_request)

    gaps = _normalize_skill_list(list(all_gaps))
    elapsed = round(time.time() - start_time, 2)

    return SkillGapResult(gaps=gaps, time=elapsed, tokens=total_tokens)


if __name__ == "__main__":
    # Both arguments optional, defaulting to resume.txt / data/jobs_d1.db,
    # matching the example invocation `uv run find_skill_gaps.py` with no args.
    resume_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RESUME_PATH
    db_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DB_PATH

    try:
        result = find_skill_gaps(resume_path, db_path)
        print(f"gaps={result.gaps} time={result.time} tokens={result.tokens}")
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
    except Exception as e:
        # Final safety net — per spec, this script must NEVER crash with a
        # stack trace, no matter what goes wrong.
        print(f"Error: unexpected failure: {type(e).__name__}: {e}")
        print("gaps=[] time=0 tokens=0")
        sys.exit(0)
