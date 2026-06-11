# Data Input & Processing Component

## Objective

Build a robust, local data engineering pipeline that successfully extracts raw data from the `0_source` , processes and cleans it into a structured format, and stores it in a relational database (`jobs.db`). By the end of this module, the success metric is a fully functional `main.py` CLI tool that orchestrates a clean database table where the `description` is readable text, not messy HTML code.

```markdown
[SOURCE] -> [EXTRACT] -> [CLEAN/PROCESS] -> [LOAD] -> [DATABASE]
```

The `jobs.db` database will be the final deliverable that will be integrated into Week 3, containing a single table with the following schema:

```bash
source_id | job_title | company | description | tech_stack
```

## General Instructions

- All git commit messages must follow [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
- Format all Python code with `ruff` version **0.15.***
- Ensure you are running python version **3.14**.*
- All packages are allowed, but unused packages must be removed from `pyproject.toml`, with the exception of OS-specific packages of course.
- Ensure all packages are pinned to exact versions to prevent breaking changes.
- Make sure your program and scripts support at least Linux/macOS and Windows. Platform independence will be checked; any platform-dependent code or scripts will be considered incomplete.

## Instructions

1. Create a `.python-version` file add:

```jsx
3.14
```

2. Follow the steps [here](https://docs.astral.sh/uv/getting-started/installation/) to Install `uv`

3. Run `uv python install`, proceed with `uv init`, and `uv venv`, follow the instructions to setup virtual environment, now you can run `python` commands!

4. Use `uv add bs4 ruff pydantic` to add the BeautifulSoup, Ruff linter/formatter, and pydantic package.

5. Create a `.gitignore` file at the root of the project, and add the following files:

```markdown
data/
src/__pycache__/
.ruff_cache/
.venv/
```

## Usage

This project is executed through a CLI-based orchestration pipeline using main.py.

You can run the full end-to-end pipeline or execute individual stages separately.

### Run Full Pipeline

To execute the complete data orchestration (ingestion → processing → loading → profiling):

```bash
python main.py all
```

### Run Individual Pipeline Stages

You can also run each stage independently for testing or debugging purposes:

```bash
python main.py ingest
```

Runs the data ingestion step (extract raw data into Bronze layer).

```bash
python main.py process
```

Runs data transformation and cleaning (Silver layer).

```bash
python main.py load
```

Loads processed data into the final structured layer (Gold layer / database).

```bash
python main.py profile
```

Runs data profiling and validation checks on the dataset.

## Technical Reflections

**1. Why is the pipeline divided into Bronze, Silver, and Gold layers?**

The Bronze, Silver, and Gold architecture follows a common data engineering pattern used in modern data platforms. The Bronze layer stores raw data exactly as it is collected, allowing the original source data to be preserved for auditing and recovery purposes. The Silver layer applies cleaning, validation, and transformation steps to improve data quality, while the Gold layer contains business-ready datasets optimized for analysis and reporting.

Separating these layers improves maintainability and reliability. If transformation logic changes or errors are discovered, the pipeline can be rerun from earlier layers without recollecting source data. This approach is widely used in lakehouse architectures such as those built with Databricks and Delta Lake.

**2. Why use SQLite instead of CSV files throughout the project?**

SQLite provides structured storage, efficient querying, and data integrity features that are difficult to achieve with multiple CSV files. Using SQL queries enables filtering, aggregation, and validation directly within the database, reducing the need for custom file-processing logic.

While large-scale production systems often use databases such as PostgreSQL, SQL Server, or cloud data warehouses, SQLite is an excellent lightweight choice for local development because it requires no separate server installation while still supporting standard SQL operations.

**3. How does CLI-based execution relate to real-world data pipelines?**

Using command-line arguments allows individual pipeline stages to be executed independently. For example, users can run ingestion, transformation, loading, or profiling without executing the entire workflow. This modular design makes testing and troubleshooting easier.

In industry environments, orchestration tools such as Apache Airflow, Azure Data Factory, and GitHub Actions commonly trigger pipeline stages through command-line commands or scripts. Therefore, the CLI approach mirrors how production pipelines are automated and scheduled.

**4. Why is data validation important in the pipeline?**

Data validation ensures that incomplete, missing, or malformed records are identified before they reach downstream processing stages. Without validation, poor-quality data can produce inaccurate analytics, unreliable machine learning models, and incorrect business decisions.

Industry data pipelines typically implement quality checks such as null detection, schema validation, duplicate identification, and completeness monitoring. The validation steps in this project follow the same principle by ensuring only reliable data progresses through the pipeline.

**5. How does version control contribute to data engineering projects?**

Version control allows changes to code, configuration files, and documentation to be tracked over time. Developers can collaborate safely, review modifications through pull requests, and revert to previous versions when issues occur.

In professional environments, Git-based workflows are standard practice. Branching strategies, code reviews, and pull requests help maintain code quality and reduce the risk of introducing errors into production data pipelines.

**6. How does dependency management with uv improve reproducibility?**

Dependency management ensures that all developers and environments use consistent package versions. The uv.lock file records exact dependency versions, making it possible to recreate the same environment across different machines.

This mirrors industry practices where reproducibility is critical for deployment and collaboration. Consistent environments reduce "works on my machine" issues and improve reliability throughout development and production workflows.