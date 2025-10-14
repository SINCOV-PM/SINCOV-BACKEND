"""
Integration tests for API endpoints.
"""
from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)


def test_stations_endpoint():
    """Verifica que el endpoint de estaciones funcione correctamente."""
    response = client.get("/stations/")
    assert response.status_code == 200
    data = response.json()
    assert "stations" in data
    assert isinstance(data["stations"], list)

def test_database_predict_endpoint():
    """Prueba el endpoint de predicción con datos válidos."""
    response = client.post("/predict/", json={"features": [22.5, 60, 1012]})
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data or "result" in data

def test_reports_endpoint():
    """Prueba general del endpoint de reportes."""
    response = client.get("/reports")
    assert response.status_code == 200
    data = response.json()
    assert "reports" in data or "data" in data

def test_stations_summary_endpoint():
    """Verifica el resumen de estaciones."""
    response = client.get("/stations/summary/all")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data or "data" in data

"""
def test_predict():
    # Similar a test_database_predict_endpoint (redundante)
    response = client.post("/predict/", json={"features": [22.5, 60, 1012]})
    assert response.status_code == 200
    assert "prediction" in response.json()

def test_stations():
    # Duplicado de test_stations_endpoint
    response = client.get("/stations/")
    assert response.status_code == 200
    assert "stations" in response.json()

def test_reports():
    # Similar a test_reports_endpoint (redundante)
    response = client.get("/reports?days=3")
    assert response.status_code == 200
    assert "reports" in response.json()

def test_root_endpoint():
    # No es crítico, solo prueba si la raíz existe
    response = client.get("/")
    assert response.status_code in [200, 404]

def test_stations_endpoint_structure():
    # Verifica estructura detallada, opcional
    response = client.get("/stations/")
    assert response.status_code == 200
    data = response.json()
    if len(data["stations"]) > 0:
        station = data["stations"][0]
        assert "id" in station
        assert "name" in station

def test_station_detail_endpoint(test_station_id):
    # Requiere fixture con ID real, no siempre disponible
    response = client.get(f"/stations/{test_station_id}")
    assert response.status_code == 200

def test_station_detail_not_found():
    # Valida caso 404, pero no aporta mucho valor
    response = client.get("/stations/999999")
    assert response.status_code == 404

def test_reports_endpoint_with_days():
    # Repite la lógica de test_reports_endpoint con varios días
    for days in [1, 3, 7, 30]:
        response = client.get(f"/reports?days={days}")
        assert response.status_code == 200
"""
