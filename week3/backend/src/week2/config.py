import os
from pathlib import Path

def get_data_dir() -> Path:
    """Get the data directory path (backend only)"""
    
    # Check environment variable
    env_data_dir = os.getenv("DATA_DIR")
    if env_data_dir:
        return Path(env_data_dir)
    
    # Check relative paths
    current_file = Path(__file__).resolve()
    possible_paths = [
        current_file.parent / "data",              # week2/data
        current_file.parent.parent / "data",       # backend/data
        current_file.parent.parent.parent / "data", # week3/data
        Path.cwd() / "data",
        Path("/app/data"),  # Docker
    ]
    
    for path in possible_paths:
        if path.exists() and path.is_dir():
            print(f"Found data directory: {path}")
            return path
    
    # Default
    default_path = Path.cwd() / "data"
    default_path.mkdir(parents=True, exist_ok=True)
    return default_path

# Data directory
DATA_DIR = get_data_dir()

# File paths
RESUME_PATH = os.getenv("RESUME_PATH", str(DATA_DIR / "resume_d3.txt"))
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "jobs_d1.db"))
CACHE_PATH = os.getenv("CACHE_PATH", str(DATA_DIR / ".skill_gap_cache.json"))

print(f"Data directory: {DATA_DIR}")
print(f"Resume file: {RESUME_PATH}")
print(f"Database file: {DB_PATH}")