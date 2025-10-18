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
    assert response.status_code in [200, 404]
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
    assert response.status_code in [200, 404]
    data = response.json()
    assert "total" in data or "data" in data

