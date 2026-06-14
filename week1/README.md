# Data Input & Processing Component

## Objective

A local data engineering pipeline that extracts raw job listings, cleans and processes them into structured data, and stores them in a SQLite database (`jobs.db`). The final output is a queryable table of job postings with clean, readable descriptions — no raw HTML.

```
[SOURCE] -> [EXTRACT] -> [CLEAN/PROCESS] -> [LOAD] -> [DATABASE]
  0_source    Bronze         Silver           Gold      jobs.db
```

---

## Architecture

This pipeline follows the **Medallion Architecture** a layered data design pattern that progressively refines raw data into a clean, trusted dataset. Each layer has a clear purpose and quality contract.

### Bronze Layer — Raw Ingestion

The Bronze layer is a faithful copy of the source data with minimal transformation. Its purpose is to preserve raw data exactly as it came from the source, making it easy to reprocess from scratch if requirements change later.

In this pipeline, the Bronze layer holds the raw HTML job listing files extracted from `0_source/`.

**What happens here:** `python main.py ingest`

### Silver Layer — Cleaning and Processing

The Silver layer applies business logic and cleaning rules to produce structured, validated records. This is where HTML is stripped into readable text, fields are normalised, and bad records are filtered out.

**What happens here:** `python main.py process`

Key transformations:
- HTML descriptions → clean plain text (via BeautifulSoup)
- Field validation via Pydantic models
- Deduplication and null handling
- Tech stack extraction

### Gold Layer — Serving Layer (Database)

The Gold layer is the final, analytics-ready output: a SQLite database (`jobs.db`) containing a single clean table ready for downstream use in Week 3. This layer is optimised for querying, not for storing raw data.

**What happens here:** `python main.py load`

### Why Medallion Architecture?

| Benefit | Description |
|---|---|
| **Reproducibility** | Raw data is always preserved in Bronze; you can re-derive Silver and Gold at any time |
| **Debuggability** | When something goes wrong, you can inspect each layer to pinpoint where data was lost or corrupted |
| **Separation of concerns** | Ingestion, transformation, and serving logic are decoupled and testable independently |
| **Incremental processing** | Each stage can be run independently, so you don't have to re-ingest when you only change cleaning logic |

---

## Project Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package and environment manager
- Python 3.14 (installed and managed via `uv`)

### Step-by-Step Installation

**1. Install `uv`**

Follow the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/) for your platform. For most systems:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**2. Pin the Python version**

Create a `.python-version` file in the project root:

```
3.14
```

**3. Install Python and initialise the project**

```bash
uv python install   # installs Python 3.14 as specified in .python-version
uv init             # initialises pyproject.toml if not already present
uv venv             # creates a virtual environment at .venv/
```

**4. Activate the virtual environment**

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.venv\Scripts\activate.bat
```

**5. Install dependencies**

```bash
uv add bs4 ruff pydantic
```

All packages are pinned to exact versions in `pyproject.toml` to prevent breaking changes.

**6. Set up `.gitignore`**

```
data/
src/__pycache__/
.ruff_cache/
.venv/
```

### Everyday `uv` Commands

| Command | Purpose |
|---|---|
| `uv add <package>` | Add a new dependency |
| `uv remove <package>` | Remove a dependency |
| `uv sync` | Sync installed packages to match `pyproject.toml` |
| `uv run python main.py all` | Run a command inside the managed environment without activating it |
| `uv lock` | Regenerate the lockfile |

---

## Development Tools

### Ruff — Linter and Formatter

This project uses [Ruff](https://docs.astral.sh/ruff/) (version `0.15.*`) for both linting and formatting Python code. Ruff is extremely fast and replaces tools like `flake8`, `isort`, and `black` in a single binary.

**Check for lint errors:**

```bash
ruff check .
```

**Auto-fix lint errors where possible:**

```bash
ruff check . --fix
```

**Format all Python files:**

```bash
ruff format .
```

**Check formatting without writing changes (useful in CI):**

```bash
ruff format . --check
```

**Recommended workflow before committing:**

```bash
ruff check . --fix && ruff format .
```

Ruff configuration lives in `pyproject.toml` under `[tool.ruff]`. The linter respects your project structure and ignores virtual environments automatically.

### Commit Messages

All commits must follow [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>(<optional scope>): <description>

feat: add HTML stripping to silver layer
fix: handle missing company field in pydantic model
chore: update ruff to 0.15.1
refactor(pipeline): split ingest and process stages
docs: add medallion architecture explanation to README
```

Common types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `ci`

---

## Usage

All pipeline stages are orchestrated through `main.py`.

### Run the full pipeline

```bash
python main.py all
```

Executes ingestion → processing → loading → profiling in sequence.

### Run individual stages

```bash
# Ingest raw data into the Bronze layer
python main.py ingest

# Clean and transform data into the Silver layer
python main.py process

# Load structured data into jobs.db (Gold layer)
python main.py load

# Run data profiling and validation checks
python main.py profile
```

Running stages individually is useful when iterating on a specific part of the pipeline — for example, if you update your cleaning logic in the Silver layer, you can run `python main.py process` and `python main.py load` without re-ingesting.

---

## Database Schema

The final output is a SQLite database at `jobs.db` containing a single table:

| Column | Type | Description |
|---|---|---|
| `source_id` | TEXT | Unique identifier from the source listing |
| `job_title` | TEXT | Title of the job role |
| `company` | TEXT | Name of the hiring company |
| `description` | TEXT | Clean, readable plain-text job description |
| `tech_stack` | TEXT | Comma-separated technologies mentioned in the listing |

The `description` field contains plain text — all HTML tags have been stripped during the Silver layer processing step.


## Technical Reflections


### Day 1: The Extractor (Medallion & Lakehouses)

Why is it useful to keep the original raw HTML files instead of directly inserting processed data into the database? What problems become easier to debug or recover from?


Answer: Keeping raw .mhtml files in 1_bronze/ means the source of truth is always preserved exactly as it arrived, untouched. If a bug is introduced in the Silver cleaning step (say, BeautifulSoup strips content it shouldn't), you don't need to re-scrape or re-download anything; you simply fix the logic and reprocess from Bronze. This mirrors how industry data lakes work: cloud object stores like AWS S3 or Azure Data Lake hold immutable raw files, while downstream layers are derived and fully reproducible from them. The raw layer also makes debugging far easier when a job description ends up malformed in the database, you can trace it back to the original HTML and confirm whether the issue was in the source data or introduced during transformation.
Industry Parallel: This is the core principle behind the Lambda Architecture and modern Lakehouse platforms like Databricks or Delta Lake. Raw files are append-only and never overwritten. Every transformation is a derivation, not a mutation. This "keep everything" philosophy might feel wasteful locally, but at scale it's what allows teams to replay months of data when business logic changes without any dependency on external APIs or re-extraction.



### Day 2: Treatment Plant (ETL vs ELT & Scale)

Why do cloud systems prefer loading raw data first before cleaning it (ELT)? What problems happen when processing files sequentially, and how does distributed processing help?


Answer: Cloud warehouses like Snowflake and BigQuery have massive, elastic compute built in. So it's cheaper and faster to load raw data first and let the warehouse do the transformation using SQL at scale (ELT), rather than spinning up external compute to clean data before loading (ETL). The raw data also lands in the warehouse sooner, meaning analysts can start exploring it before transformation pipelines are even finished. In our local pipeline, we process .mhtml files one at a time in a Python loop, this is sequential processing, and it means one slow or broken file can block everything behind it. At enterprise scale with thousands of files, this becomes a serious bottleneck.
Distributed Processing: Tools like Apache Spark solve this by partitioning data across a cluster of machines and processing chunks in parallel. Instead of File 1 → File 2 → File 3 in sequence, Spark sends groups of files to different worker nodes simultaneously. A job that takes hours sequentially might take minutes distributed. It also provides fault tolerance if one worker node crashes mid-job, Spark reassigns that partition to another node and retries automatically, without restarting the entire pipeline from scratch.



### Day 3: The Blueprint & The Vault (Storage & Contracts)

What should happen if an important field like job_title disappears? Why fail early instead of silently inserting nulls into the DB? How does INSERT OR IGNORE help prevent duplicate records?


Answer: If job_title goes missing whether because a source changed its HTML structure or a Pydantic model didn't catch a schema drift — the pipeline should raise an explicit error and halt rather than inserting a null into the database. A silent null is dangerous because it propagates downstream invisibly: dashboards show blank job titles, analytics on role distributions become skewed, and by the time someone notices, hundreds of corrupted records may have already been written. Failing early (a "fail fast" strategy) surfaces the problem immediately at the load step, before bad data contaminates the Gold layer. This is the principle behind Data Contracts upstream producers agree to deliver fields in a specific shape, and if that contract is violated, the pipeline stops and alerts rather than silently degrading data quality.
Idempotency with INSERT OR IGNORE: Running python main.py load twice should produce the same database state, not duplicate rows. INSERT OR IGNORE achieves this by skipping any insert where the primary key (source_id) already exists. This is critical for idempotent pipelines — a core reliability property in production systems. Without it, every pipeline re-run would double the row count, and downstream queries would return inflated results. In production, tools like dbt handle this more sophisticatedly with MERGE statements (upserts), but INSERT OR IGNORE is the right local equivalent for a Silver-to-Gold load.



### Day 4: The QA Inspector & Orchestrator (Orchestration & DAGs)

What happens if processor.py crashes halfway? How are automated orchestration tools more reliable than manual retries with Python scripts?


Answer: If processor.py crashes halfway through processing 500 files, our current main.py all approach has no recovery mechanism — the next run starts over from the beginning, reprocessing files already completed and potentially leaving partially written Silver files in an inconsistent state. There's also no automatic retry, no alerting, and no visibility into which file caused the crash. Manual intervention is required every time. This is manageable locally with a small dataset, but it's completely unacceptable in a production pipeline running on a schedule overnight.
Orchestration Tools (Airflow / DAGs): Tools like Apache Airflow model pipelines as DAGs (Directed Acyclic Graphs) — each stage (ingest, process, load, profile) becomes a node, and dependencies between stages are declared explicitly. Airflow tracks the state of every task run (success, failed, running, skipped), so if process fails, it knows load cannot proceed. It retries failed tasks automatically (configurable: 3 retries with 5-minute intervals), sends alerts via email or Slack, and provides a web UI to inspect logs per task per run. Critically, it supports partial reruns — if ingest and process succeeded but load failed, you can rerun just load without touching the earlier stages. This is the operational reliability gap between a script and a proper orchestration system.


