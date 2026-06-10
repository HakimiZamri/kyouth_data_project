import sqlite3

def run_data_profile(db_path):

    if not db_path.exists():
        print(f"Database not found at {db_path.parent}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    total_rec = cursor.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    missing = cursor.execute(""" SELECT COUNT(job_title) as cntjobtle, 
                            COUNT(company) as cntcom,
                            COUNT(description) as cntdesc
                            FROM jobs 
                            WHERE job_title IS NULL
                            AND company IS NULL
                            AND description IS NULL
                             """).fetchone()
    avg_desc = cursor.execute("SELECT CAST(AVG(LENGTH(description)) AS Integer) FROM jobs").fetchone()[0]
    min_desc = cursor.execute("SELECT source_id, job_title, MIN(LENGTH(description)) AS mindesc FROM jobs").fetchone()
    max_desc = cursor.execute("SELECT source_id, job_title, MAX(LENGTH(description)) AS mindesc FROM jobs").fetchone()
    
    print("--- DATA QUALITY REPORT ---")
    print(f"Total Records: {total_rec}")
    print(f"Missing values -> job_title: {missing[0]}, company: {missing[1]}, description: {missing[2]}")
    print(f"Avg Description Length: {avg_desc} chars")
    print(f"Shortest Description: {min_desc[2]} chars -> source_id: {min_desc[0]} | job_title: {min_desc[1]}")
    print(f"Longest Description: {max_desc[2]} chars -> source_id: {max_desc[0]} | job_title: {max_desc[1]}")

    conn.close()