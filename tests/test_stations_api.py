"""
Specific tests for stations API endpoints.
"""
from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)


class TestStationsAPI:
    """Test suite for /stations/ endpoints."""


    def test_get_all_stations(self):
        """Verifica que el endpoint /stations/ devuelva la lista de estaciones."""
        response = client.get("/stations/")
        assert response.status_code == 200
        
        data = response.json()
        assert "stations" in data
        assert isinstance(data["stations"], list)

    def test_stations_summary_aggregates(self):
        """Verifica que el endpoint summary devuelva datos agregados."""
        response = client.get("/stations/summary/all")
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        if len(data["data"]) > 0:
            summary = data["data"][0]
            assert "promedio" in summary or "average" in summary


    """
    def test_stations_have_pm25_data(self):
        # Verifica que las estaciones incluyan mediciones PM2.5 (opcional).
        response = client.get("/stations/")
        assert response.status_code == 200
        
        data = response.json()
        if len(data["stations"]) > 0:
            station = data["stations"][0]
            assert "value" in station
            assert "timestamp" in station

    def test_station_detail_has_sensors(self, test_station_id):
        # Prueba que el detalle de estación incluya sensores (requiere fixture).
        response = client.get(f"/stations/{test_station_id}")
        assert response.status_code == 200
        data = response.json()
        assert "sensors" in data or "total_sensors" in data
    """
