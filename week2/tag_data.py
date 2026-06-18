import requests
from prompt_model import prompt_model, GOOGLE_GEMINI_MODELS
import sqlite3
from pathlib import Path
import sys
import math
import time
import random

# DB_PATH = Path("week1/data/3_gold/jobs.db")
DB_PATH = Path("data/jobs_d1.db")

AVG_TOKENS_PER_ROW = 400    # average tokens consumed per job description
SAFETY_MARGIN = 0.8    # stay at 80% of any limit to avoid hitting it

OLLAMA_HARDWARE_TPS = {
    "phi3": 55,   # ~3.8B params — fastest of the three
    "deepseek-r1:1.5b": 70,   # ~1.5B params — smallest, fastest
    "llama3.1": 25,   # ~8B params — slowest of the three
}
OLLAMA_DEFAULT_TPS = 30   # used if a model isn't in the table above
 
rate_limit_path = "rate_limits.txt"

def _get_rate_params(model: str):
    """
    Returns (sleep_per_request, max_retries, batch_size, rpm) calculated
    from the rate limits in rate_limits.txt (for Gemini models), or from
    a hypothetical hardware-derived formula (for Ollama models).
    """
    if model in GOOGLE_GEMINI_MODELS:
        limits = read_rate_limits(model)
        if model not in limits:
            raise ValueError(
                f"No rate limit entry found for '{model}' in rate_limits.txt"
            )
        rpm = limits[model]["rpm"]
        tpm = limits[model]["tpm"]
 
        # Sleep so we never exceed RPM
        sleep_per_request = 60 / rpm
 
        # Batch size = stricter of RPM-safe and TPM-safe limits
        rpm_safe_batch = math.floor(rpm * SAFETY_MARGIN)
        tpm_safe_batch = math.floor((tpm / AVG_TOKENS_PER_ROW) * SAFETY_MARGIN)
        batch_size = min(rpm_safe_batch, tpm_safe_batch)
 
        max_retries = 3
        return sleep_per_request, max_retries, batch_size, rpm
 
    else:
        # Ollama — hypothetical rate limit derived from hardware speed,
        # looked up per-model since each model generates at a different TPS
        hardware_tps = OLLAMA_HARDWARE_TPS.get(model, OLLAMA_DEFAULT_TPS)
 
        time_per_row = AVG_TOKENS_PER_ROW / hardware_tps
        rows_per_minute = 60 / time_per_row
        hypothetical_rpm = max(1, math.floor(rows_per_minute * SAFETY_MARGIN))
 
        sleep_per_request = time_per_row / SAFETY_MARGIN
        batch_size = hypothetical_rpm
        max_retries = 3
        return sleep_per_request, max_retries, batch_size, hypothetical_rpm

def read_rate_limits(model: str):

	limits = {}
	with open(rate_limit_path, 'r') as r:
		
		for line in r:
			line = line.strip()

			parts = line.split()

			model_name = parts[0]

			if model_name == model:
				rpm = int(parts[1])
				tpm = int(parts[2])
				rpd = int(parts[3])
				limits[model] = {'rpm': rpm, 'tpm': tpm, 'rpd': rpd}
	
	return limits
 
def _extract_tech_stack(
    desc: str,
    model: str,
    max_retries: int,
    rpm: int,
) -> str:
    """
    Calls prompt_mode.prompt_model() to extract a comma-separated tech
    stack from a job description, retrying on rate-limit errors using
    backoff anchored to the model's RPM window.
    """
    if not isinstance(desc, str) or not desc.strip():
        return ""
 
    prompt = (
        "You are a technical recruiter assistant. "
        "Given the following job description, extract the technical stack "
        "mentioned (programming languages, frameworks, tools, platforms, databases, cloud services, APIs, methodologies, etc.). "
        "Return ONLY a comma-separated list of technologies with no extra explanation, "
        "If there is nothing technical stack in the description, just return empty string with no additional explanation"
        "no bullet points, no numbering, and no preamble. "
        "If nothing technical is mentioned, return an empty string which is ''.\n\n"
        f"Job Description:\n{desc}"
    )
 
    for attempt in range(max_retries):
        
        result = prompt_model(model, prompt)
 
        if not isinstance(result, str):
            return ""
 
        if result.startswith("Error:") and ("429" in result or "Too Many Requests" in result):
            if attempt < max_retries - 1:
                retry_wait = (2 ** attempt) * (60 / rpm) + random.uniform(0, 1)
                print(f"  Rate limited. Waiting {retry_wait:.1f}s "
                      f"(attempt {attempt + 1}/{max_retries})...")
                time.sleep(retry_wait)
                continue
            print(f"  Warning: still rate limited after {max_retries} attempts. Returning empty.")
            return ""
 
        if result.startswith("Error:"):
            print(f"  Warning: {result}. Returning empty.")
            return ""
 
        return result.strip()
 
    return ""

def tag_data(db_url: str):

    model = "llama3.1"
    sleep_per_request, max_retries, batch_size, rpm = _get_rate_params(model)

    conn = sqlite3.connect(db_url)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        cur.execute("PRAGMA table_info(jobs)")
        columns = [row["name"] for row in cur.fetchall()]

        if "tech_stack" not in columns:
            cur.execute("ALTER TABLE jobs ADD COLUMN tech_stack TEXT")
            conn.commit()

        rows = cur.execute("SELECT source_id, description FROM jobs WHERE tech_stack IS NULL OR tech_stack = ''").fetchall()

        if not rows:
            print("There is no rows to tag.")
            conn.close()
            return
        
        rows_in_current_batch = 0

        for i, row in enumerate(rows, start=1):
            source_id = row["source_id"]
            desc = row["description"]
            
            if not desc:
                print("There is no description to tag.")
                return

            tech_stack = _extract_tech_stack(desc, model, max_retries, rpm)

            cur.execute(
                  "UPDATE jobs SET tech_stack = ? WHERE source_id = ?",
                  (tech_stack, source_id),
                         )
            conn.commit()
            print(f"Analyzed Job {source_id}: {tech_stack}")

            rows_in_current_batch += 1

            if rows_in_current_batch >= batch_size and i < len(rows):
                print(f"  Batch of {batch_size} done — waiting 60s for a fresh rate-limit window...")
                time.sleep(60)
                rows_in_current_batch = 0
            else:
                time.sleep(sleep_per_request)

    except sqlite3.OperationalError as e:
        print(f"Error: Insert failed - {e}")
        sys.exit(1)

    except sqlite3.DatabaseError as e:
        print(f"Error: Database error - {e}")
        sys.exit(1)

    finally:
        conn.close()

if __name__ == "__main__":

    if len(sys.argv) >= 2:
        print("Usage: python tag_data.py <path_to_db>")
        print("Example: python tag_data.py jobs_d1.db")
        sys.exit(1)
 
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
 
    try:
        tag_data(db_path)
    except TypeError as e:
        print(f"[TypeError] {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"[FileNotFoundError] {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"[ValueError] {e}")
        sys.exit(1)
    except sqlite3.DatabaseError as e:
        print(f"[DatabaseError] '{db_path}' does not appear to be a valid SQLite database.\nDetail: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted. Progress already committed rows are saved.")
        sys.exit(0)