# AI Component

A hybrid local/cloud pipeline that automatically tags job postings with a structured tech_stack field, extracted from free-text job descriptions using an LLM (Gemini via Google AI Studio, or a local Ollama model).


## Project Overview


Raw job postings store their requirements as unstructured free text inside a description column — which makes it hard for downstream models or analyses to reliably extract signal like "this job requires Python and AWS." The goal of this project is to automatically tag every job posting with a clean, structured tech_stack field (e.g. "Python, Django, PostgreSQL") derived from that free text, so the dataset becomes far easier to filter, aggregate, and feed into further machine learning models.



Concretely, the system:


Reads job postings from a SQLite database (jobs table) that don't yet have a tech_stack value.

Sends each description to an LLM — either a cloud model via Google AI Studio (Gemini) or a local model via Ollama — with a prompt instructing it to extract just the relevant technologies.

Writes the resulting comma-separated tag string back into the database, row by row.

Paces all of this against real rate limits (for Gemini) or a hardware-derived hypothetical limit (for Ollama), so the pipeline can run unattended on a full dataset without tripping API throttling.



The broader motivation, per the original course brief, is that tagging the raw text up front makes feature extraction easier for any LLM or model downstream — turning a free-text field into something closer to a structured, queryable label.



## Project Setup

### Part 1: Ollama Setup

#### Step 1: Install Ollama

Go to [ollama.com](https://ollama.com/) and download the installer for your OS, or use the terminal:

macOS / Linux (one-liner):

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

macos (Homebrew):

```bash
brew install ollama
```

windows:

```bash
irm https://ollama.com/install.ps1 | iex
```

The direct download link for the v0.21.0 Windows installer is:

```
https://github.com/ollama/ollama/releases/download/v0.21.0/OllamaSetup.exe
```

Paste that URL directly into your browser to download it. This bypasses the GitHub releases page which defaults to the latest version.

#### Step 2: Verify the version is 0.21.x

After installation, check the version:

```bash
ollama -v
# Expected: ollama version is 0.21.0
```

If you need a specific version (0.21.0), on macOS you can pin it via Homebrew:

```bash
brew install ollama@0.21.0
```

#### Step 3: Start the Ollama server

```bash
ollama serve
```

Leave this running in a terminal tab, or on macOS you can run Ollama as a background app from the menu bar.

#### Step 4: Verify the server is running

In a new terminal:

```bash
curl 127.0.0.1:11434
# Expected response: Ollama is running
```

#### Step 5: Pull the three models 

Run each command (they download sequentially — sizes shown for reference):

```bash
ollama pull llama3.1        # ~4.9 GB
ollama pull phi3            # ~2.2 GB
ollama pull deepseek-r1:1.5b  # ~1.1 GB
```

These may take a while depending on your internet speed (~8 GB total).

#### Step 6: Verify all models are installed

```bash
ollama ls
```

You should see output like:

```
NAME                ID              SIZE      MODIFIED
deepseek-r1:1.5b    e0979632db5a    1.1 GB    About a minute ago
phi3:latest         4f2222927938    2.2 GB    2 minutes ago
llama3.1:latest     46e0c10c039e    4.9 GB    3 hours ago
```

### Part 2: Google AI Setup

#### Step 1: Get your API Key

1. Go to [aistudio.google.com](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click "Get API Key" (top left or via the menu)
4. Click "Create API key" → copy and save it somewhere safe

#### Step 2: Find the Rate Limits

1. In AI Studio, click on "Get API Key" again
2. You'll see a table listing your keys — look for a "Rate limits" column or link
3. Alternatively, go to: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) and click on "View rate limits" next to your key

For each model, look for these three columns:

RPM — Requests Per Minute
TPM — Tokens Per Minute
RPD — Requests Per Day

#### Step 3: Create the file

Once you have the numbers, create rate_limits.txt like this:

```bash
cat > rate_limits.txt << 'EOF'
gemini-2.5-flash <RPM> <TPM> <RPD>
gemini-2.5-flash-lite <RPM> <TPM> <RPD>
gemini-3-flash-preview <RPM> <TPM> <RPD>
EOF
```

Replace <RPM>, <TPM>, <RPD> with the actual numbers from your dashboard.

### Notes

Create `.env` file to store the secret configuration such as api key. `load_dotenv` from `dotenv` package needed.


---


## API / Function Reference



### `prompt_model.py`



The backend router. Given a model name and a prompt, it decides whether to call Google AI Studio (Gemini) or a local Ollama instance, and returns the raw text response.



#### `prompt_model(model: str, prompt: str) -> str`



**Purpose:** Single entry point for sending a prompt to either a Gemini or Ollama model. Detects which backend to use automatically.



**Inputs:**

| Param | Type | Description |
|---|---|---|
| `model` | `str` | Model name. Must be one of `GOOGLE_GEMINI_MODELS` (`gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-3-flash-preview`) or `OLLAMA_MODELS` (`llama3.1`, `phi3`, `deepseek-r1:1.5b`). |
| `prompt` | `str` | The text prompt to send to the model. |



**Output:** `str` — the model's text response, **or** an error string prefixed with `"Error: ..."` (this function never raises on API/network failures — it returns the error as text instead).



---



#### `_detect_model(model: str) -> str`



**Purpose:** Internal helper that decides whether a model name belongs to Gemini or Ollama.



**Inputs:** `model` (`str`) — model name (case-insensitive).



**Output:** `"gemini"` or `"ollama"`.



---



#### `_prompt_gemini(model: str, prompt: str) -> str`



**Purpose:** Sends a prompt to the Google AI Studio Gemini API and extracts the text reply.



**Inputs:** `model`, `prompt` — same as above.



**Output:** `str` — extracted text from `data["candidates"][0]["content"]["parts"][0]["text"]`, or an error string if the API key is missing, the request fails, or the response shape is unexpected.



---



#### `_prompt_ollama(model: str, prompt: str) -> str`



**Purpose:** Sends a prompt to a local Ollama server (`/api/generate`).



**Inputs:** `model`, `prompt` — same as above.



**Output:** `str` — extracted text from `data["response"]`, or an error string on failure (e.g. Ollama not running).



---



#### `read_rate_limits(model: str) -> dict`



**Purpose:** Reads `rate_limits.txt` and returns the rate limit entry for a given model.



**Inputs:** `model` (`str`) — must match a model name listed in `rate_limits.txt`.



**Output:** `dict` in the form `{model: {"rpm": int, "tpm": int, "rpd": int}}`. Returns an empty dict if the model isn't found in the file.



---



### `tag_data.py`



The tagging pipeline. Reads untagged rows from the `jobs` table, calls `prompt_model()` for each one, and writes the result back to the database.



#### `tag_data(db_url: str)`



**Purpose:** Main entry point. Tags every row in the `jobs` table where `tech_stack` is `NULL` or empty.



**Inputs:** `db_url` (`str` or `Path`) — path to the SQLite database file.



**Output:** None (side effect: updates the `tech_stack` column in place, row by row, committing after each row).



**Behavior:**

1. Connects to the database and confirms the `jobs` table has a `tech_stack` column (adds it via `ALTER TABLE` if missing).

2. Selects all rows where `tech_stack IS NULL OR tech_stack = ''`.

3. For each row, calls `_extract_tech_stack()` to get a tagged string, then `UPDATE`s that row and commits immediately.

4. Paces requests using values from `_get_rate_params()` — sleeping between requests, and pausing 60 seconds after every `batch_size` rows to let the rate-limit window reset.



---



#### `_extract_tech_stack(desc: str, model: str, max_retries: int, rpm: int) -> str`



**Purpose:** Builds the extraction prompt for a single job description and calls `prompt_model()`, retrying on rate-limit errors.



**Inputs:**

| Param | Type | Description |
|---|---|---|
| `desc` | `str` | Raw job description text. |
| `model` | `str` | Model name to use. |
| `max_retries` | `int` | Max retry attempts on a 429 / rate-limit error. |
| `rpm` | `int` | Requests-per-minute limit, used to scale backoff wait time. |



**Output:** `str` — comma-separated tech stack (e.g. `"Python, Django, PostgreSQL"`), or `""` if the description is empty, the model returns nothing technical, or all retries are exhausted.



**Retry logic:** Exponential backoff anchored to the rate window: `wait = (2^attempt) × (60 / rpm) + random_jitter`.



---



#### `_get_rate_params(model: str) -> tuple[float, int, int, int]`



**Purpose:** Calculates safe pacing values from either the published rate limits (Gemini) or a hardware-derived formula (Ollama), rather than hardcoding them.



**Inputs:** `model` (`str`).



**Output:** `(sleep_per_request, max_retries, batch_size, rpm)`

- `sleep_per_request` (`float`) — seconds to wait between individual requests.

- `max_retries` (`int`) — always `3`.

- `batch_size` (`int`) — how many rows to process before a 60s pause.

- `rpm` (`int`) — the requests-per-minute value used (real for Gemini, hypothetical for Ollama).



**Formulas:**



*Gemini (from `rate_limits.txt`):*

```

sleep_per_request = 60 / RPM

rpm_safe_batch     = floor(RPM × 0.8)

tpm_safe_batch     = floor(TPM / AVG_TOKENS_PER_ROW × 0.8)

batch_size         = min(rpm_safe_batch, tpm_safe_batch)

```



*Ollama (no published limit — derived from measured hardware speed):*

```

time_per_row      = AVG_TOKENS_PER_ROW / ((hardware_input_tps + hardware_eval_tps) / 2)

hypothetical_RPM  = floor((60 / time_per_row) × 0.8)

sleep_per_request = time_per_row / 0.8

batch_size        = hypothetical_RPM

```

`hardware_input_tps` and `hardware_input_eval_tps` is looked up per-model from `OLLAMA_HARDWARE_INPUT_TPS` and `OLLAMA_HARDWARE_EVAL_TPS` respectively, measured via:

```bash

ollama run <model> "say hi" --verbose   # see "prompt eval rate: X tokens/s" and "eval rate: X tokens/s"

```



---



## Module interaction



```

tag_data.py

   │

   ├── imports prompt_model, GOOGLE_GEMINI_MODELS  ──→  prompt_model.py

   │                                                       │

   │                                                       ├── _prompt_gemini()  → Google AI Studio API

   │                                                       └── _prompt_ollama()  → local Ollama server

   │

   ├── read_rate_limits() ──→ reads rate_limits.txt

   │

   └── sqlite3 ──→ reads/writes the `jobs` table in the SQLite DB

```

`tag_data.py` never talks to Gemini or Ollama directly — every model call goes through `prompt_model()`, so the tagging logic stays backend-agnostic.


---



## Data / Assumptions


### Database schema


The `jobs` table is expected to contain at minimum:


| Column | Type | Notes |
|---|---|---|
| `source_id` | unique identifier | used as the row key for updates |
| `description` | text | raw job description — the input to tagging |
| `tech_stack` | text | output column; added automatically via `ALTER TABLE` if it doesn't already exist |


### External files


- **`rate_limits.txt`** — plain text, one model per line: `model_name RPM TPM RPD`. Must be in the working directory when `tag_data.py` is run, since the path is relative (`rate_limit_path = "rate_limits.txt"`).

- **`.env`** — holds `GOOGLE_API_KEY`, `GOOGLE_BASE_URL`, `OLLAMA_BASE_URL`, loaded by `prompt_model.py` via `python-dotenv`.



### Assumptions made


- **Input format:** `description` is assumed to be plain text in English. No HTML stripping, no language detection.

- **Average prompt size:** Batch and rate calculations assume `AVG_TOKENS_PER_ROW = 400`. Descriptions significantly longer than this will under-estimate token usage and could risk hitting the TPM limit before the RPM-based pause kicks in.

- **Ollama hardware speed:** `OLLAMA_HARDWARE_TPS` values are manually measured and hardcoded per model. If hardware changes (e.g. different machine, GPU vs CPU), these numbers go stale and must be re-measured.

- **Model output format:** The prompt instructs the model to return only a comma-separated list, with no extra text. The code trusts this and does not validate or reformat the structure — if the model adds a preamble or bullet points despite instructions, that text is stored as-is.

- **One job per API call:** Tagging is strictly one job description per request/response. There is no batch-prompting (multiple jobs sent in a single prompt), which avoids the need to validate response counts against a batch size.

- **Idempotency:** Re-running `tag_data()` only processes rows where `tech_stack` is empty, so it's safe to re-run after an interruption — already-tagged rows are skipped.


### Data flow


```

SQLite (jobs table, tech_stack = NULL)

   │

   ▼

tag_data() selects untagged rows

   │

   ▼

for each row: build prompt → prompt_model() → Gemini or Ollama

   │

   ▼

parse response text → strip → store as tech_stack

   │

   ▼

UPDATE jobs SET tech_stack = ... WHERE source_id = ...  (committed immediately)

```


---


## Testing


### Test scenarios covered during development


| Scenario | How it was triggered | Result |
|---|---|---|
| Missing CLI argument | `python tag_data.py` with no path | Clear usage message, exit code 1 |
| Non-existent DB path | `python tag_data.py wrong_path.db` | `FileNotFoundError` with explicit message |
| Invalid/non-SQLite file | Passed a `.txt` file as the DB path | Caught as `sqlite3.DatabaseError` |
| `jobs` table missing or empty | Pointed at a DB without the expected schema | `ValueError` raised with explanation |
| `tech_stack` column missing | Fresh DB without the column | Column auto-added via `ALTER TABLE` |
| Row with `NULL` description | Manually inserted a row with `description = NULL` | Skipped with a log line, no crash |
| 429 / rate-limit response | Forced by intentionally setting a low RPM | Exponential backoff retry observed in logs, eventually succeeds or gives up after `max_retries` |
| Connection dropped mid-run (`Ctrl+C`) | Manually interrupted during a batch | Already-committed rows remained tagged; script exited cleanly without corrupting the DB |
| `TypeError` on row indexing under `uv run` | Ran via `uv run tag_data.py jobs_d1.db` | Diagnosed as a `row_factory` inconsistency; fixed by accessing columns positionally / via `sqlite3.Row` consistently |
| Connection used after close | Triggered "Cannot operate on a closed database" | Fixed by wrapping all DB work in `try/finally` so `conn.close()` runs exactly once |



### How to reproduce



```bash

# Standard run

python tag_data.py jobs_d1.db



# Run via uv

uv run tag_data.py jobs_d1.db



# Verify results directly

sqlite3 jobs_d1.db "SELECT source_id, tech_stack FROM jobs LIMIT 10;"

```


### Validation method


Correctness was checked manually by:

- Spot-checking several `tech_stack` outputs against their source `description` text to confirm the extracted terms were actually present in the posting.

- Confirming idempotency: running the script twice in a row results in zero API calls on the second run (since all rows already have `tech_stack` populated).

- Confirming that interrupting the script mid-run (`Ctrl+C`) does not roll back already-committed rows, since each row commits independently.


No automated test suite (e.g. `pytest`) was built for this version — testing was manual and exploratory, driven by actually running the script against the real database and observing console output and final column values.


---


## Limitations



- **No automated tests.** All verification was manual; there is no regression suite to catch future breakage.

- **No response validation.** The model's output is trusted as-is. If the model ignores formatting instructions (e.g. adds explanatory text), that gets stored directly in `tech_stack` with no cleanup.

- **No deduplication or normalization of tags.** `"Python"`, `"python"`, and `"Python3"` could all appear as different strings across rows — there is no canonicalization step.

- **Token estimate is a flat constant.** `AVG_TOKENS_PER_ROW = 400` is a rough average, not measured per-row. Very long descriptions could silently push past the TPM limit despite the RPM-based pacing looking safe.

- **Ollama TPS values are static and manual.** They reflect one measurement on one machine at one point in time; performance can vary with system load, model quantization, or hardware changes, and the code has no way to detect that drift.

- **No batching of multiple jobs per request.** Every job is tagged with a separate API call. This is simpler and avoids response-parsing complexity, but means tagging speed is bound entirely by the per-request rate limit — there's no way to get more throughput by packing several jobs into one call.

- **Retry only covers rate-limit (429) errors.** Other transient errors (e.g. a single dropped connection, a 500 from the API) are treated as permanent failures for that row and stored as an empty string, rather than retried.

- **Single-threaded, sequential processing.** Rows are tagged one at a time in a loop; there's no concurrency, so total runtime scales linearly with row count and the per-request sleep time.

- **Accuracy is bounded by model judgment.** Since tagging relies on an LLM's interpretation of free text, the extracted tech stack may miss implied technologies (e.g. a tool referenced by an uncommon abbreviation) or occasionally include a tool that's only tangentially mentioned.


---


## Architecture Reflection


### Design choices


The system is split into two clearly separated layers: `prompt_model.py` handles **how to talk to a model** (Gemini vs Ollama, including auth, error formatting, and response parsing), while `tag_data.py` handles **what to do with the database** (selecting untagged rows, pacing requests, writing results back). This separation means the tagging logic never needs to know which backend is in use — it just calls `prompt_model(model, prompt)` and gets text back. Swapping from Gemini to a local Ollama model is a one-line change (the `model` variable), not a rewrite.


Rate-limit handling was deliberately pulled into its own function, `_get_rate_params()`, rather than hardcoding sleep values. This makes the pacing logic auditable and explainable — every number used to throttle requests traces back to a real published limit (for Gemini) or a measured hardware constant (for Ollama), rather than an arbitrary `time.sleep(0.5)` picked by guesswork.


### Trade-offs


The clearest trade-off is **simplicity over throughput**. Processing one job per API call, sequentially, with deliberate sleeps, is easy to reason about and debug but it's slow. A batch-prompting approach (sending several job descriptions in one request) would tag the database faster, but introduces a new failure mode: the model might return a different number of results than jobs sent, requiring response-count validation and partial-failure handling. Given the goal was getting the tagging mechanism *correct and robust* first, the slower-but-simpler one-at-a-time design was chosen deliberately.


Similarly, error handling favors **graceful degradation over strict correctness**: a single bad row (malformed description, unexpected API response shape) gets skipped with a logged warning rather than crashing the whole run. This trades a small risk of silently incomplete tags for the much larger benefit of not losing hours of progress on a 500-row dataset because of one bad row.


### Improvements


Given more time, the next priorities would be:

1. **Token-aware batching** — measure actual token counts per description (rather than the flat `400` estimate) so the TPM-based batch size reflects real usage.

2. **Concurrent requests** — for Ollama especially, running multiple descriptions through a thread pool (within rate-limit bounds) would meaningfully cut total runtime.

3. **Output normalization** — lowercasing and deduplicating tags, or mapping known synonyms (`"JS"` → `"JavaScript"`) to a canonical form, to make the resulting `tech_stack` column more useful for downstream filtering or aggregation.

4. **A small automated test suite** — even a handful of `pytest` cases using a temporary in-memory SQLite DB and a mocked `prompt_model()` would catch regressions (e.g. the `row_factory` tuple-indexing bug) automatically instead of relying on manual runs.