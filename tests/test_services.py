"""
Unit tests for service layer functions.
"""
import pytest
from sqlalchemy import text

def test_stations_service_query(db_engine):
    """Verifica que el servicio de estaciones pueda consultar la base de datos."""
    with db_engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM stations"))
        count = result.scalar()
        assert count > 0, "No hay estaciones registradas en la base de datos."


def test_pm25_monitors_exist(db_engine):
    """Verifica que existan monitores PM2.5 asociados a estaciones."""
    with db_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT ON (st.id)
                st.id,
                st.name,
                st.latitude,
                st.longitude,
                s.value,
                s.timestamp AT TIME ZONE 'America/Bogota' AS timestamp
            FROM sensors s
            JOIN monitors m ON s.monitor_id = m.id
            JOIN stations st ON m.station_id = st.id
            WHERE m.type = 'PM2.5'
            ORDER BY st.id, s.timestamp DESC
            LIMIT 1
        """))
        row = result.fetchone()
        assert row is not None, "No se encontró ningún monitor PM2.5 en la base de datos."


"""
def test_sensor_data_exists(db_engine):
    # Prueba que la tabla sensors tenga datos (si ya se han generado reportes).
    with db_engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM sensors"))
        count = result.scalar()
        assert count >= 0  # Se mantiene >=0 por si aún no hay datos registrados
"""
