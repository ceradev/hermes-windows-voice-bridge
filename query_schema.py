import sqlite3

db_path = r"C:\Users\cesar\Desktop\Files\Work\Projects\Personal\hermes-windows-voice-bridge\.codegraph\codegraph.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", tables)
    
    for table in tables:
        t_name = table[0]
        print(f"\nSchema for table '{t_name}':")
        cursor.execute(f"PRAGMA table_info({t_name});")
        columns = cursor.fetchall()
        for col in columns:
            print("  ", col)
            
    conn.close()
except Exception as e:
    print("Error:", e)
