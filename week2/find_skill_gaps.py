import sqlite3
import re
from typing import List, Set, Optional
from pydantic import BaseModel
from pathlib import Path
import sys

input_file_path = Path("data/resume_d3.txt")
db_url = Path("data/jobs_d1.db")

class SkillGapResult(BaseModel):
    gaps: List[str]


# Exceptions that should not be split by '/'
EXCEPTIONS = {"a/b testing", "ci/cd"}


def _split_skill(skill: str) -> List[str]:

    skill = skill.strip()
    if not skill:
        return []
    lower_skill = skill.lower()
    if lower_skill in EXCEPTIONS:
        return [lower_skill]
    # Split by '/', trim, and filter out empty
    parts = [p.strip().lower() for p in skill.split('/') if p.strip()]
    return parts


def _preprocess_resume(text: str) -> str:

    # Use placeholders to protect exceptions
    text = text.replace("A/B testing", "ABTESTING_PLACEHOLDER")
    text = text.replace("CI/CD", "CICD_PLACEHOLDER")
    # Replace remaining '/' with space
    text = text.replace('/', ' ')
    # Restore exceptions (lowercased)
    text = text.replace("ABTESTING_PLACEHOLDER", "a/b testing")
    text = text.replace("CICD_PLACEHOLDER", "ci/cd")
    return text.lower()


def _is_skill_present(skill: str, text: str) -> bool:

    pattern = r'(?<![a-zA-Z0-9])' + re.escape(skill) + r'(?![a-zA-Z0-9])'
    return bool(re.search(pattern, text))


def _get_required_skills(db_url: str) -> Optional[Set[str]]:

    try:
        conn = sqlite3.connect(db_url)
        cursor = conn.cursor()

        # Determine which column contains the skills
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [row[1] for row in cursor.fetchall()]
        skill_col = None
        for col in columns:
            if col.lower() == "tech_stack":
                skill_col = col
                break
        if skill_col is None:
            # Fallback: try common names
            for col in "tech_stack":
                try:
                    cursor.execute(f"SELECT {col} FROM jobs LIMIT 1")
                    skill_col = col
                    break
                except sqlite3.OperationalError:
                    continue
        if skill_col is None:
            conn.close()
            return None

        cursor.execute(f"SELECT {skill_col} FROM jobs")
        rows = cursor.fetchall()
        conn.close()

        skills_set = set()
        for row in rows:
            val = row[0]
            if val is None:
                continue
            # If the value is a comma-separated list, split by comma first
            for item in val.split(','):
                item = item.strip()
                if not item:
                    continue
                # Further split by '/' if applicable
                for sub_skill in _split_skill(item):
                    if sub_skill:
                        skills_set.add(sub_skill)
        return skills_set
    except Exception:
        return None


def find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult:

    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            resume_text = f.read()
    except Exception:
        return SkillGapResult(gaps=[])

    # Preprocess resume once
    processed_resume = _preprocess_resume(resume_text)

    # Get required skills from database
    required_skills = _get_required_skills(db_url)
    if required_skills is None:
        return SkillGapResult(gaps=[])

    gaps = []
    for skill in required_skills:
        if not _is_skill_present(skill, processed_resume):
            gaps.append(skill)  # already lowercased

    # Remove duplicates and sort
    gaps = sorted(set(gaps))
    return SkillGapResult(gaps=gaps)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print("Usage: python find_skill_gaps.py")
        sys.exit(1)

    skill_gaps = find_skill_gaps(input_file_path, db_url)
    print(skill_gaps)