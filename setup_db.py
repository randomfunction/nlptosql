import sqlite3
import os
import requests
import sys

DB_FILE = "Chinook_Sqlite.sqlite"
DB_URL = "https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"

def download_db():
    if os.path.exists(DB_FILE):
        print(f"Database {DB_FILE} already exists.")
        return

    print(f"Downloading {DB_FILE} from {DB_URL}...")
    try:
        response = requests.get(DB_URL)
        response.raise_for_status()
        with open(DB_FILE, "wb") as f:
            f.write(response.content)
        print("Download complete.")
    except Exception as e:
        print(f"Error downloading database: {e}")
        sys.exit(1)

def get_schema_info():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("\nDatabase Schema Summary:")
    print("-" * 30)
    
    total_tables = 0
    for table in tables:
        table_name = table[0]
        if table_name.startswith("sqlite_"):
            continue
            
        total_tables += 1
        # Get column info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        print(f"Table: {table_name}")
        print(f"  Columns: {len(columns)}")
        print(f"  Rows:    {row_count}")
        print(f"  Schema:  {', '.join([col[1] for col in columns])}")
        print("-" * 30)
        
    print(f"\nTotal Tables: {total_tables}")
    conn.close()

if __name__ == "__main__":
    download_db()
    get_schema_info()
