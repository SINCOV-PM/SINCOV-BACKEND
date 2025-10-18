from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

def test_database_seed_data():

    """Validates that the database is active and stations are properly seeded."""
    url = os.getenv("DATABASE_URL")
    assert url is not None, "DATABASE_URL not found in environment"

    engine = create_engine(url)

    try:
        with engine.connect() as conn:
            # Basic connection test
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1, "Basic DB connection test failed"

            # Check existence of 'stations' table
            tables = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public'
            """)).fetchall()
            table_names = [t[0] for t in tables]
            assert "stations" in table_names, "Table 'stations' does not exist"

            # Check that stations are inserted
            station_count = conn.execute(text("SELECT COUNT(*) FROM stations")).scalar()
            assert station_count > 0, f"No stations found in database (found {station_count})"

            # Check that there are monitors per station
            monitor_count = conn.execute(text("SELECT COUNT(*) FROM monitors")).scalar()
            assert monitor_count > 0, "No monitors found (seed may have failed)"

            # Check that coordinates are not null
            missing_coords = conn.execute(text("""
                SELECT COUNT(*) FROM stations
                WHERE latitude = 0 OR longitude = 0
            """)).scalar()
            assert missing_coords == 0, f"{missing_coords} stations missing coordinates"

            print(f" Seed data verified successfully: {station_count} stations, {monitor_count} monitors")

    except Exception as e:
        raise AssertionError(f"Database validation failed: {e}")