"""
Integration tests for API endpoints.
"""
from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)


def test_predict():
    response = client.post("/predict/", json={"features": [22.5, 60, 1012]})
    assert response.status_code == 200
    assert "prediction" in response.json()

def test_reports_endpoint():
    """Prueba general del endpoint de reportes."""
    response = client.get("/reports")
    assert response.status_code == 200
    data = response.json()
    assert "reports" in data or "data" in data

def test_stations_summary_endpoint():
    """Verifica el resumen de estaciones."""
    response = client.get("/stations/summary/all")
    assert response.status_code in [200]
    data = response.json()
    assert "total" in data or "data" in data

# ============================================================================
# STATIONS ENDPOINTS
# ============================================================================

def test_stations_endpoint():
    """Verifica que el endpoint de estaciones funcione correctamente."""
    response = client.get("/stations/")
    assert response.status_code in [200]
    
    if response.status_code == 200:
        data = response.json()
        assert "stations" in data
        assert isinstance(data["stations"], list)
        
        # Si hay estaciones, verificar estructura
        if len(data["stations"]) > 0:
            station = data["stations"][0]
            assert "id" in station
            assert "name" in station
            assert "lat" in station
            assert "lng" in station
            assert "value" in station  # PM2.5 value
            assert "timestamp" in station


def test_stations_summary_endpoint():
    """Verifica el resumen de estaciones con todos los monitores."""
    response = client.get("/stations/summary/all")
    assert response.status_code in [200]
    
    if response.status_code == 200:
        data = response.json()
        assert "total" in data
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # Si hay datos, verificar estructura
        if len(data["data"]) > 0:
            station = data["data"][0]
            assert "id" in station
            assert "name" in station
            assert "lat" in station
            assert "lng" in station
            assert "monitors" in station
            assert isinstance(station["monitors"], list)
            
            # Verificar estructura de monitores
            if len(station["monitors"]) > 0:
                monitor = station["monitors"][0]
                assert "type" in monitor
                assert "unit" in monitor
                assert "promedio" in monitor
                assert "minimo" in monitor
                assert "maximo" in monitor
                assert "ultima_medicion" in monitor


def test_station_detail_endpoint():
    """Verifica el detalle de una estación específica."""
    # Primero obtener una estación válida
    stations_response = client.get("/stations/")
    
    if stations_response.status_code == 200:
        stations_data = stations_response.json()
        
        if len(stations_data["stations"]) > 0:
            station_id = stations_data["stations"][0]["id"]
            
            # Probar el endpoint de detalle
            response = client.get(f"/stations/{station_id}")
            assert response.status_code in [200]
            
            if response.status_code == 200:
                data = response.json()
                assert "station_id" in data
                assert "total_sensors" in data
                assert "sensors" in data
                assert isinstance(data["sensors"], list)
                
                # Verificar estructura de sensores
                if len(data["sensors"]) > 0:
                    sensor = data["sensors"][0]
                    assert "id" in sensor
                    assert "monitor_id" in sensor
                    assert "type" in sensor
                    assert "unit" in sensor
                    assert "value" in sensor
                    assert "timestamp" in sensor


# ============================================================================
# REPORTS ENDPOINTS
# ============================================================================

def test_reports_endpoint():
    """Verifica el endpoint principal de reportes."""
    response = client.get("/reports/")
    assert response.status_code in [200]
    
    if response.status_code == 200:
        data = response.json()
        assert "success" in data
        assert "total" in data
        assert "reports" in data
        assert isinstance(data["reports"], list)
        
        # Si hay reportes, verificar estructura
        if len(data["reports"]) > 0:
            report = data["reports"][0]
            assert "station_id" in report
            assert "station_name" in report
            assert "lat" in report
            assert "lng" in report
            assert "pm25_value" in report
            assert "status" in report
            assert "timestamp" in report
            assert "date" in report
            
            # Verificar que el status sea válido
            valid_statuses = ["Bueno", "Moderado", "Alto", "Muy Alto", "Peligroso"]
            assert report["status"] in valid_statuses


def test_reports_summary_endpoint():
    """Verifica el resumen estadístico de reportes."""
    response = client.get("/reports/summary")
    assert response.status_code in [200]
    
    if response.status_code == 200:
        data = response.json()
        assert "success" in data
        assert "data" in data
        
        summary = data["data"]
        assert "total_stations" in summary
        assert "avg_pm25" in summary
        assert "min_pm25" in summary
        assert "max_pm25" in summary
        assert "status_distribution" in summary
        
        # Verificar que los valores sean numéricos
        assert isinstance(summary["total_stations"], int)
        assert isinstance(summary["avg_pm25"], (int, float))
        assert isinstance(summary["min_pm25"], (int, float))
        assert isinstance(summary["max_pm25"], (int, float))
        
        # Verificar que status_distribution sea un dict
        assert isinstance(summary["status_distribution"], dict)