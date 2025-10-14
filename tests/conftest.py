""""
Shared fixtures for all tests.
Uses the real database configured in CI.
"""
import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="session")
def db_engine():
    """
    Create a database engine for the test session.
    Uses DATABASE_URL from environment (set in CI).
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set")
    
    engine = create_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Create a new database session for each test.
    """
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def test_station_id(db_engine):
    """
    Get a real station ID from the seeded database for testing.
    """
    with db_engine.connect() as conn:
        result = conn.execute(text("SELECT id FROM stations LIMIT 1"))
        station = result.fetchone()
        if station:
            return station[0]
    pytest.skip("No stations in database")
