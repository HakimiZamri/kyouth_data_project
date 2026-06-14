import sqlite3
import json
import os
import sys


def load_all_jsons(input_dir, output_dir):

    if not os.path.exists(input_dir):
        print(f"Warning: Please run process first or create {input_dir}")

    os.makedirs(output_dir, exist_ok=True)

    print("Gold:...")

    conn = sqlite3.connect(output_dir / "jobs.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS jobs (
                    source_id TEXT PRIMARY KEY,
                    job_title TEXT,
                    company TEXT,
                    description TEXT,
                    tech_stack TEXT
                )
            """
        )

        conn.commit()

    except sqlite3.OperationalError as e:
        print(f"Error: Database query failed - {e}")
        sys.exit(1)

    except sqlite3.DatabaseError as e:
        print(f"Error: Database error - {e}")
        sys.exit(1)

    count = 0
    inserted = 0
    skipped = 0

    for silver in input_dir.glob("*.json"):
        count += 1
        filename = silver.stem
        with open(silver, "r", encoding="utf-8") as file:
            jsonr = json.load(file)

        if not jsonr.get("source_id"):
            print("Skipping record: missing source_id")
            continue

        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO jobs (source_id, job_title, company, description)
                VALUES (?, ?, ?, ?)
            """,
                (
                    jsonr.get("source_id"),
                    jsonr.get("job_title"),
                    jsonr.get("company"),
                    jsonr.get("description"),
                ),
            )
            conn.commit()

        except sqlite3.OperationalError as e:
            print(f"Error: Insert failed - {e}")
            sys.exit(1)

        except sqlite3.DatabaseError as e:
            print(f"Error: Database error - {e}")
            sys.exit(1)

        if cursor.rowcount == 0:
            print(f"Skipped (duplicate): {filename}.json")
            skipped += 1
            continue

        print(f"Inserted: {filename}.json")
        inserted += 1

    conn.close()

    print("Gold Summary:")
    print(f"Total: {count} | Inserted: {inserted} | Skipped: {skipped}")
