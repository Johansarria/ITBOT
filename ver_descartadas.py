import sqlite3

DB_PATH = "storage/itbot.db"

with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, strategy, symbol, interval, decision, score FROM discarded_signals ORDER BY id DESC LIMIT 5;")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
