import sqlite3

DB_PATH = "storage/itbot.db"

def main(db_path=DB_PATH):
    """
    Connects to the database, fetches the last 5 discarded signals,
    prints them, and returns them.
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, strategy, symbol, interval, decision, score FROM discarded_signals ORDER BY id DESC LIMIT 5;")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
    return rows

if __name__ == "__main__":
    main()
