from prompt_model import prompt_model, GOOGLE_GEMINI_MODELS
import sqlite3
from pathlib import Path
import sys
import math
import time
import random
import re

# if str(Path.cwd()).endswith("week2"):
#     DB_PATH = Path.cwd().parent / "week1" / "data" / "jobs.db"
# else:
#     DB_PATH = Path.cwd() / "week1" / "data" / "jobs.db"

if str(Path.cwd()).endswith("week2"):
    DB_PATH = Path.cwd() / "data" / "jobs_d1.db"
else:
    DB_PATH = Path.cwd() / "week2" / "data" / "jobs_d1.db"

AVG_TOKENS_PER_ROW = 400  # average tokens consumed per job description
SAFETY_MARGIN = 0.9  # stay at 90% of any limit to avoid hitting it

OLLAMA_HARDWARE_INPUT_TPS = {
    "phi3": 20,  # ~3.8B params
    "deepseek-r1:1.5b": 80,  # ~1.5B params — smallest, fastest
    "llama3.1": 10,  # ~8B params
    "gemma3:4b": 15,  # ~4B params
    "deepseek-r1:7b": 10,  # ~7B params
}

OLLAMA_HARDWARE_EVAL_TPS = {
    "phi3": 40,
    "deepseek-r1:1.5b": 125,
    "llama3.1": 18,
    "gemma3:4b": 35,
    "deepseek-r1:7b": 20,
}

OLLAMA_DEFAULT_TPS = 20  # used if a model isn't in the table above

MAX_BATCH_ATTEMPTS = 3

rate_limit_path = "rate_limits.txt"


def get_rate_params(model: str):
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

        return sleep_per_request, batch_size, rpm

    else:
        # Ollama — hypothetical rate limit derived from hardware speed,
        # looked up per-model since each model generates at a different TPS
        hardware_input_tps = OLLAMA_HARDWARE_INPUT_TPS.get(model, OLLAMA_DEFAULT_TPS)
        hardware_eval_tps = OLLAMA_HARDWARE_EVAL_TPS.get(model, OLLAMA_DEFAULT_TPS)

        time_per_row = AVG_TOKENS_PER_ROW / (
            (hardware_input_tps + hardware_eval_tps) / 2
        )
        rows_per_minute = 60 / time_per_row
        hypothetical_rpm = max(1, math.floor(rows_per_minute * SAFETY_MARGIN))

        sleep_per_request = time_per_row / SAFETY_MARGIN
        batch_size = hypothetical_rpm
        return sleep_per_request, batch_size, hypothetical_rpm


def read_rate_limits(model: str):

    limits = {}
    with open(rate_limit_path, "r") as r:
        for line in r:
            line = line.strip()

            parts = line.split()

            model_name = parts[0]

            if model_name == model:
                rpm = int(parts[1])
                tpm = int(parts[2])
                rpd = int(parts[3])
                limits[model] = {"rpm": rpm, "tpm": tpm, "rpd": rpd}

    return limits


def _parse_batch_response(response_text: str, expected_ids):
    """
    Parses the model's batch response into {source_id: tech_stack}.

    Expects one line per job: "<source_id>: <comma-separated tags>"

    Returns (results_dict, missing_ids). missing_ids is a list of
    expected_ids that weren't found in the response — used to decide
    whether to retry.
    """
    results = {}
    expected_set = set(str(i) for i in expected_ids)

    for line in response_text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^(\S+?):\s*(.*)$", line)
        if not match:
            continue
        line_id, tags = match.group(1), match.group(2).strip()
        if line_id in expected_set:
            results[line_id] = tags

    missing_ids = [i for i in expected_ids if str(i) not in results]
    return results, missing_ids


def tag_data(db_url: Path):

    if not db_url.exists():
        print(f"{db_url} does not exist. Try again.")
        sys.exit(1)

    model = "gemini-2.5-flash"
    sleep_per_request, batch_size, rpm = get_rate_params(model)

    print(f"Model        : {model}")
    print(f"Batch size   : {batch_size} jobs per prompt")
    print(f"Sleep        : {sleep_per_request:.2f}s between batches")
    print()

    conn = sqlite3.connect(db_url)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    total_prompt_tokens = 0
    total_output_tokens = 0

    try:
        start_time = time.time()
        cur.execute("PRAGMA table_info(jobs)")
        columns = [row["name"] for row in cur.fetchall()]

        if "tech_stack" not in columns:
            cur.execute("ALTER TABLE jobs ADD COLUMN tech_stack TEXT")
            conn.commit()

        rows = cur.execute(
            "SELECT source_id, description FROM jobs "
            "WHERE tech_stack IS NULL OR tech_stack = ''"
        ).fetchall()

        if not rows:
            print("There is no rows to tag.")
            return

        # Split rows into chunks of size batch_size
        all_rows = [(row["source_id"], row["description"]) for row in rows]
        batches = [
            all_rows[i : i + batch_size] for i in range(0, len(all_rows), batch_size)
        ]

        print(
            f"Tagging {len(all_rows)} rows in {len(batches)} batches "
            f"of up to {batch_size}..."
        )

        for batch_num, batch_rows in enumerate(batches):
            # Drop rows with no description up front — nothing to tag
            usable_rows = [(source_id, desc) for source_id, desc in batch_rows if desc]
            skipped_rows = [source_id for source_id, desc in batch_rows if not desc]
            for source_id in skipped_rows:
                print(
                    f"  [Batch {batch_num}] id={source_id} has no description — skipping."
                )

            if not usable_rows:
                continue

            expected_ids = [source_id for source_id, _ in usable_rows]
            results = {}

            job_lines = []
            for source_id, desc in batch_rows:
                desc_clean = (desc or "").strip().replace("\n", " ")
                job_lines.append(f"{source_id}. {desc_clean}")

            jobs_block = "\n".join(job_lines)

            for attempt in range(1, MAX_BATCH_ATTEMPTS + 1):
                prompt = (
                    "You are a technical recruiter assistant.\n\n"
                    "Below is a numbered list of job descriptions, each prefixed with its "
                    "job ID. For EVERY job in the list, extract the technical stack "
                    "mentioned (programming languages, frameworks, tools, platforms, "
                    "databases, cloud services, APIs, methodologies).\n\n"
                    "Output rules:\n"
                    "- Return exactly one line per job, in the same order as given.\n"
                    "- Each line must start with the job's ID, followed by a colon, "
                    "followed by a comma-separated list of technologies.\n"
                    "  Example: 91397216: Python, Django, PostgreSQL\n"
                    "- If a job has no technical stack mentioned, still output its ID "
                    "followed by a colon and nothing else.\n"
                    "  Example: 91397216:\n"
                    "- Do not add any other text: no headers, no explanations, no "
                    "numbering beyond the job ID itself, no blank lines.\n\n"
                    f"Jobs:\n{jobs_block}"
                )
                text, prompt_tokens, output_tokens = prompt_model(model, prompt)

                if prompt_tokens is not None:
                    total_prompt_tokens += prompt_tokens
                if output_tokens is not None:
                    total_output_tokens += output_tokens

                if not isinstance(text, str):
                    print(
                        f"  [Batch {batch_num}] Attempt {attempt} failed: "
                        f"non-string response from model."
                    )
                    continue

                if text.startswith("Error:"):
                    if (
                        "429" in text or "Too Many Requests" in text
                    ) and attempt < MAX_BATCH_ATTEMPTS:
                        retry_wait = (2 ** (attempt - 1)) * (60 / rpm) + random.uniform(
                            0, 1
                        )
                        print(
                            f"  [Batch {batch_num}] Rate limited. Waiting "
                            f"{retry_wait:.1f}s (attempt {attempt}/{MAX_BATCH_ATTEMPTS})..."
                        )
                        time.sleep(retry_wait)
                        continue
                    print(f"  [Batch {batch_num}] Attempt {attempt} failed: {text}")
                    continue

                parsed, missing_ids = _parse_batch_response(text, expected_ids)

                if missing_ids:
                    print(
                        f"  [Batch {batch_num}] Attempt {attempt} failed: "
                        f"Mismatch between batch size and response "
                        f"({len(missing_ids)} of {len(expected_ids)} jobs missing)."
                    )
                    if attempt < MAX_BATCH_ATTEMPTS:
                        time.sleep(sleep_per_request)
                        continue
                    # Final attempt — keep whatever we got, leave the rest empty
                    results = parsed
                    break

                results = parsed
                break

            # Write back whatever we have (full or partial results)
            for source_id, _ in usable_rows:
                tech_stack = results.get(str(source_id), "")
                cur.execute(
                    "UPDATE jobs SET tech_stack = ? WHERE source_id = ?",
                    (tech_stack, source_id),
                )
                conn.commit()
                print(f"Analyzed Job {source_id}: {tech_stack}")

            print(
                f"  [Batch {batch_num}] done. "
                f"Tokens so far — prompt: {total_prompt_tokens}, "
                f"output: {total_output_tokens}"
            )

            if batch_num < len(batches) - 1:
                time.sleep(sleep_per_request)

        print()
        print(
            f"Done tagging. Total tokens used — prompt: {total_prompt_tokens}, "
            f"output: {total_output_tokens}, "
            f"combined: {total_prompt_tokens + total_output_tokens}. "
            f"Time taken: {round(time.time() - start_time, 2)}"
        )

    except sqlite3.OperationalError as e:
        print(f"Error: Insert failed - {e}")
        sys.exit(1)

    except sqlite3.DatabaseError as e:
        print(f"Error: Database error - {e}")
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Usage: python tag_data.py <path_to_db>")
        print("Example: python tag_data.py jobs_d1.db")
        print("OR")
        print("Usage: python tag_data.py")
        sys.exit(1)

    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH

    try:
        tag_data(Path(db_path))
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
        print(
            f"[DatabaseError] '{db_path}' does not appear to be a valid SQLite database.\nDetail: {e}"
        )
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted. Progress already committed rows are saved.")
        sys.exit(0)
