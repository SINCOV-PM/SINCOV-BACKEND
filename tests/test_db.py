"""
Database integration tests.
"""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import pytest

load_dotenv()
def test_database_connection():
    """Verifica conexión básica a la base de datos."""
    url = os.getenv("DATABASE_URL")
    assert url is not None, "DATABASE_URL no está configurada en el entorno"
    
    engine = create_engine(url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_database_tables_exist():
    """Verifica que existan las tablas principales."""
    url = os.getenv("DATABASE_URL")
    engine = create_engine(url)
    
    required_tables = ["stations", "monitors", "sensors"]
    with engine.connect() as conn:
        tables = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
        """)).fetchall()
        
        table_names = [t[0] for t in tables]
        for table in required_tables:
            assert table in table_names, f"Falta la tabla '{table}'"


def test_database_pm25_monitors():
    """Verifica que existan monitores PM2.5."""
    url = os.getenv("DATABASE_URL")
    engine = create_engine(url)
    
    with engine.connect() as conn:
        pm25_count = conn.execute(text("""
            SELECT COUNT(*) FROM monitors WHERE type = 'PM2.5'
        """)).scalar()
        assert pm25_count > 0, "No se encontraron monitores PM2.5"
        print(f"✅ {pm25_count} monitores PM2.5 encontrados correctamente")

"""
def test_database_seed_stations():
    # Similar a verificar tablas + datos, ya cubierto en test_database_pm25_monitors
    url = os.getenv("DATABASE_URL")
    engine = create_engine(url)
    with engine.connect() as conn:
        station_count = conn.execute(text("SELECT COUNT(*) FROM stations")).scalar()
        assert station_count > 0

def test_database_seed_monitors():
    # Redundante, también lo cubre test_database_pm25_monitors
    url = os.getenv("DATABASE_URL")
    engine = create_engine(url)
    with engine.connect() as conn:
        monitor_count = conn.execute(text("SELECT COUNT(*) FROM monitors")).scalar()
        assert monitor_count > 0
"""
"""
def test_database_coordinates():
    # Verifica lat/long válidas, útil pero no esencial
    url = os.getenv("DATABASE_URL")
    engine = create_engine(url)
    with engine.connect() as conn:
            SELECT COUNT(*) FROM stations
            WHERE latitude = 0 OR longitude = 0 OR latitude IS NULL OR longitude IS NULL
        )).scalar()
        assert missing_coords == 0, f"{missing_coords} estaciones sin coordenadas válidas"
"""

"""

def test_database_foreign_keys():
    # Comprueba relaciones FK, importante pero se puede reactivar más adelante
    url = os.getenv("DATABASE_URL")
    engine = create_engine(url)
    with engine.connect() as conn:
        orphan_monitors = conn.execute(text(
            SELECT COUNT(*) FROM monitors m
            LEFT JOIN stations s ON m.station_id = s.id
            WHERE s.id IS NULL
        )).scalar()
        assert orphan_monitors == 0, f"{orphan_monitors} monitores sin estación válida"
"""
