import psycopg2
from config import settings

try:
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        dbname=settings.POSTGRES_DB
    )
    print("Database connection successful")
    conn.close()
except Exception as e:
    print(f"Database connection failed: {e}")
