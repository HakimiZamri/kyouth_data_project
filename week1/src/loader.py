import sqlite3
import json

def load_all_jsons(input_dir, output_dir):
    
    print("Gold:...")

    conn = sqlite3.connect(output_dir / "jobs.db")
    cursor = conn.cursor()

    cursor.execute(
        """
            CREATE TABLE IF NOT EXISTS jobs (
                source_id TEXT PRIMARY KEY,
                job_title TEXT,
                company TEXT,
                description TEXT,
                texh_stack TEXT
            )
        """
    )
 
    conn.commit()

    seen = set()
    count = 0
    inserted = 0
    skipped = 0

    for silver in input_dir.glob("*.json"):

        count += 1
        filename = silver.stem
        with open(silver, 'r', encoding="utf-8") as file:
            jsonr = json.load(file)

        if jsonr["source_id"] in seen:
            print(f"Skipped (duplicate): {filename}.json")
            skipped += 1
            continue

        seen.add(jsonr["source_id"])

        cursor.execute(
        """
            INSERT OR IGNORE INTO jobs (source_id, job_title, company, description)
            VALUES (?, ?, ?, ?)
        """,
            (jsonr["source_id"], jsonr["job_title"], jsonr["company"], jsonr["description"])
        )
        conn.commit()

        print(f"Inserted: {filename}.json")
        inserted += 1
    
    conn.close()

    print("Gold Summary:")
    print(f"Total: {count} | Inserted: {inserted} | Skipped: {skipped}")