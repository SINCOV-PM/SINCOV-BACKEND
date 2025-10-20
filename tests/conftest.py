import pytest
import os
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic.command import upgrade
from fastapi.testclient import TestClient
from app.main import app
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Set up the test database with migrations before running all tests.
    This fixture runs once per test session.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Run Alembic migrations
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    try:
        upgrade(alembic_cfg, "head")
        print("Database migrations completed successfully")
    except Exception as e:
        print(f"Migration error: {e}")
        raise

    yield

    # Teardown code runs after all tests complete (optional)
    # You can add cleanup code here if needed


@pytest.fixture
def client():
    """
    Provides a TestClient for making HTTP requests to the FastAPI app.
    This fixture is available to all tests.
    """
    return TestClient(app)


@pytest.fixture
def db_session():
    """
    Provides a database connection for direct database queries in tests.
    Useful for verifying data was inserted correctly.
    """
    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        yield conn


@pytest.fixture
def verify_tables_exist():
    """
    Verify that all required tables exist in the database.
    Returns a function that can be called to check table existence.
    """
    def check_tables(required_tables):
        database_url = os.getenv("DATABASE_URL")
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public'
            """))
            existing_tables = [row[0] for row in result.fetchall()]
            
            missing_tables = set(required_tables) - set(existing_tables)
            if missing_tables:
                raise AssertionError(f"Missing tables: {missing_tables}")
            
            return True
    
    return check_tables