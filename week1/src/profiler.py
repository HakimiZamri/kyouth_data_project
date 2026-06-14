import sqlite3
import sys


def run_data_profile(db_path):

    if not db_path.exists():
        print(f"Database not found at {db_path.parent}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        total_rec = cursor.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        missing_job_title = cursor.execute(
            "SELECT COUNT(*) FROM jobs WHERE job_title IS NULL"
        ).fetchone()
        missing_company = cursor.execute(
            "SELECT COUNT(*) FROM jobs WHERE company IS NULL"
        ).fetchone()
        missing_desc = cursor.execute(
            "SELECT COUNT(*) FROM jobs WHERE description IS NULL"
        ).fetchone()
        avg_desc = cursor.execute(
            "SELECT CAST(AVG(LENGTH(description)) AS Integer) FROM jobs"
        ).fetchone()[0]
        min_desc = cursor.execute(
            "SELECT source_id, job_title, MIN(LENGTH(description)) FROM jobs"
        ).fetchone()
        max_desc = cursor.execute(
            "SELECT source_id, job_title, MAX(LENGTH(description)) FROM jobs"
        ).fetchone()

    except sqlite3.OperationalError as e:
        print(f"Error: Database query failed — {e}")
        sys.exit(1)

    except sqlite3.DatabaseError as e:
        print(f"Error: Database error — {e}")
        sys.exit(1)

    try:
        print("--- DATA QUALITY REPORT ---")
        print(f"Total Records: {total_rec}")
        print(
            f"Missing values -> job_title: {missing_job_title[0]}, company: {missing_company[0]}, description: {missing_desc[0]}"
        )
        print(f"Avg Description Length: {avg_desc} chars")
        print(
            f"Shortest Description: {min_desc[2]} chars -> source_id: {min_desc[0]} | job_title: {min_desc[1]}"
        )
        print(
            f"Longest Description: {max_desc[2]} chars -> source_id: {max_desc[0]} | job_title: {max_desc[1]}"
        )

    except sqlite3.ProgrammingError as e:
        print(f"Programming error - {e}")
        sys.exit(1)

    conn.close()
