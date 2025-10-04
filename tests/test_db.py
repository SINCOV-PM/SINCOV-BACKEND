from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

def test_database_connection():
    url = os.getenv("DATABASE_URL")
    assert url is not None, "DATABASE_URL not found in environment"

    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    except Exception as e:
        raise AssertionError(f"Database connection failed: {e}")
