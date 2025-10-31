"""
SQLite-based ledger for tracking processed files
"""

import os
import json
import sqlite3
import time
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

# Database path (will be created in same directory as reports)
def _get_db_path():
    """Get absolute path for database file"""
    reports_file = os.getenv("REPORTS_FILE", "./assets/reports/flow_reports.json")
    
    # Convert to absolute path to handle relative paths and os.chdir()
    reports_file = os.path.abspath(reports_file)
    
    # Get directory and ensure it exists
    db_dir = os.path.dirname(reports_file)
    os.makedirs(db_dir, exist_ok=True)
    
    return os.path.join(db_dir, "processed.db")
# Initialize DB_PATH as absolute path
DB_PATH = _get_db_path()


# ============== Database Connection ==============
@contextmanager
def get_db():
    """Context manager for database connections with proper cleanup"""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


# ============== Database Initialization ==============
def init_db():
    """Initialize database with indexed hash table"""
    with get_db() as conn:
        # Create main table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_files (
                file_hash TEXT PRIMARY KEY,
                file_path TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for fast lookups (though PRIMARY KEY already indexes)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_hash 
            ON processed_files(file_hash)
        """)
        
        # Create index on timestamp for cleanup queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_processed_at 
            ON processed_files(processed_at)
        """)
        
        conn.commit()
        print("[DB] Database initialized")

# ============== Ledger Operations ==============
def load_ledger(load_all=False):
    """
    Load processed file hashes from the database.

    Args:
        load_all (bool): 
            - True: loads all hashes into memory (fast for small datasets, memory intensive for large datasets)
            - False: lazy mode; use is_processed() for per-file checks (scales to large datasets)

    Returns:
        set: set of file hashes if load_all=True, else empty set
    """
    init_db()

    if not load_all:
        print("[DB] Lazy mode active. Use is_processed() for per-file lookups.")
        return set()

    # Small dataset: safe to load all hashes
    with get_db() as conn:
        cursor = conn.execute("SELECT file_hash FROM processed_files")
        hashes = {row[0] for row in cursor.fetchall()}
        print(f"[DB] Loaded {len(hashes)} processed file hashes into memory")
        return hashes


def is_processed(file_hash):
    """
    Check if a file hash is already processed (lazy check).

    Args:
        file_hash (str): hash of the file

    Returns:
        bool: True if processed, False otherwise
    """
    init_db()
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM processed_files WHERE file_hash = ? LIMIT 1",
            (file_hash,)
        )
        return cursor.fetchone() is not None


def save_ledger(processed_hashes):
    """
    Save new hashes to the database (idempotent, scales to both small and large datasets).

    Args:
        processed_hashes (set): set of file hashes to save

    Notes:
        - Uses INSERT OR IGNORE to skip duplicates efficiently.
        - Avoids fetching all existing hashes for large datasets.
    """
    init_db()
    with get_db() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO processed_files (file_hash) VALUES (?)",
            [(h,) for h in processed_hashes]
        )
        conn.commit()
        print(f"[DB] Saved {len(processed_hashes)} hashes (duplicates ignored)")


def add_processed_file(file_hash, file_path=None):
    """
    Add a single processed file to the database
    Args:
        file_hash: SHA256 hash string
        file_path: Optional file path for reference
    """
    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO processed_files (file_hash, file_path) VALUES (?, ?)",
                (file_hash, file_path)
            )
            conn.commit()
            print(f"[DB] Added hash: {file_hash[:16]}...")
        except sqlite3.IntegrityError:
            # Hash already exists (PRIMARY KEY constraint)
            print(f"[DB] Hash already exists: {file_hash[:16]}...")

# ============== Utility Functions ==============
def get_stats():
    """Get statistics about processed files"""
    with get_db() as conn:
        # Total count
        cursor = conn.execute("SELECT COUNT(*) FROM processed_files")
        total = cursor.fetchone()[0]
        
        # Oldest entry
        cursor = conn.execute(
            "SELECT processed_at FROM processed_files ORDER BY processed_at ASC LIMIT 1"
        )
        oldest = cursor.fetchone()
        
        # Newest entry
        cursor = conn.execute(
            "SELECT processed_at FROM processed_files ORDER BY processed_at DESC LIMIT 1"
        )
        newest = cursor.fetchone()
        
        return {
            "total_processed": total,
            "oldest_entry": oldest[0] if oldest else None,
            "newest_entry": newest[0] if newest else None,
            "database_path": DB_PATH
        }


def cleanup_old_entries(days=90):
    """
    Remove entries older than specified days (optional maintenance)
    Args:
        days: Number of days to keep (default: 90)
    Returns:
        int: Number of entries deleted
    """
    with get_db() as conn:
        cursor = conn.execute(
            """
            DELETE FROM processed_files 
            WHERE processed_at < datetime('now', '-' || ? || ' days')
            """,
            (days,)
        )
        conn.commit()
        deleted = cursor.rowcount
        print(f"[DB] Cleaned up {deleted} entries older than {days} days")
        return deleted



def should_run_cleanup():
    """
    Check if cleanup should run (once per day)
    Returns:
        bool: True if cleanup should run
    """
    cleanup_marker = os.path.join(os.path.dirname(DB_PATH), ".last_cleanup")
    
    try:
        if os.path.exists(cleanup_marker):
            # Read last cleanup timestamp
            with open(cleanup_marker, 'r') as f:
                last_cleanup = float(f.read().strip())
            
            # Check if 24 hours have passed
            hours_since_cleanup = (time.time() - last_cleanup) / 3600
            if hours_since_cleanup < 24:
                return False
        
        # Update cleanup marker
        with open(cleanup_marker, 'w') as f:
            f.write(str(time.time()))
        return True
        
    except Exception as e:
        print(f"[DB] Cleanup check error: {e}")
        return False


def auto_cleanup(days=90, force=False):
    """
    Automatically cleanup old entries if it's time
    Args:
        days: Number of days to keep (default: 90)
        force: Force cleanup regardless of last run time
    Returns:
        int: Number of entries deleted, or 0 if skipped
    """
    if force or should_run_cleanup():
        return cleanup_old_entries(days)
    return 0


def reset_database():
    """
    CAUTION: Delete all processed file records
    Use only for testing or fresh start
    """
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM processed_files")
        conn.commit()
        deleted = cursor.rowcount
        print(f"[DB] Reset database: Deleted {deleted} records")
        return deleted


# ============== Testing ==============
# if __name__ == "__main__":
#     """Quick test of database functions"""
#     print("Testing SQLite Ledger...")
    
#     # Initialize
#     init_db()
    
#     # Test adding hashes
#     test_hashes = {"abc123def456", "xyz789uvw012", "test_hash_001"}
#     save_ledger(test_hashes)
    
#     # Test loading
#     loaded = load_ledger()
#     print(f"Loaded hashes: {loaded}")
    
#     # Test single lookup
#     print(f"Is 'abc123def456' processed? {is_processed('abc123def456')}")
#     print(f"Is 'nonexistent' processed? {is_processed('nonexistent')}")
    
#     # Show stats
#     stats = get_stats()
#     print(f"\nDatabase Stats:")
#     for key, value in stats.items():
#         print(f"  {key}: {value}")
    
#     print("\n✅ All tests passed!")