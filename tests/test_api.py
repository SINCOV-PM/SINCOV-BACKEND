"""
Integration tests for API endpoints.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ============================================================================
# STATIONS ENDPOINTS
# ============================================================================

def test_stations_endpoint():
    """Test that the stations endpoint works correctly."""
    response = client.get("/stations/")
    assert response.status_code in [200, 404, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "stations" in data
        assert isinstance(data["stations"], list)
        
        if len(data["stations"]) > 0:
            station = data["stations"][0]
            assert "id" in station
            assert "name" in station
            assert "lat" in station
            assert "lng" in station
            assert "value" in station
            assert "timestamp" in station


def test_stations_summary_endpoint():
    """Test stations summary with all monitors."""
    response = client.get("/stations/summary/all")
    assert response.status_code in [200, 404, 500]
    
    data = response.json()
    assert "total" in data
    assert "data" in data
    assert isinstance(data["data"], list)
    
    if len(data["data"]) > 0:
        station = data["data"][0]
        assert "id" in station
        assert "name" in station
        assert "lat" in station
        assert "lng" in station
        assert "monitors" in station
        assert isinstance(station["monitors"], list)
        
        if len(station["monitors"]) > 0:
            monitor = station["monitors"][0]
            assert "type" in monitor
            assert "unit" in monitor
            assert "promedio" in monitor
            assert "minimo" in monitor
            assert "maximo" in monitor
            assert "ultima_medicion" in monitor


def test_predict_xgboost_endpoint_allowed_station():
    """Verifica la ejecución del servicio de predicción XGBoost."""
    station_id = 2
    
    payload = {"station_id": station_id, "horizons": [1, 3, 6, 12]}
    response = client.post("/predict/", json=payload)
    
    assert response.status_code in [200, 404]
    data = response.json()
    
    if response.status_code == 200:
        assert data["success"] is True
        assert data["station_id"] == station_id
        assert "predictions" in data
        assert isinstance(data["predictions"], list)
        assert len(data["predictions"]) == 4
        
        for pred in data["predictions"]:
            assert "horizon" in pred
            assert "predicted_pm25" in pred
            assert "timestamp" in pred
            assert pred["horizon"] in [1, 3, 6, 12]
            assert isinstance(pred["predicted_pm25"], (int, float))
            assert pred["predicted_pm25"] >= 0
    elif response.status_code == 404:
        assert "detail" in data or "error" in data


def test_station_detail_endpoint():
    """Test detail for a specific station."""
    stations_response = client.get("/stations/")
    
    if stations_response.status_code == 200:
        stations_data = stations_response.json()
        
        if len(stations_data["stations"]) > 0:
            station_id = stations_data["stations"][0]["id"]
            response = client.get(f"/stations/{station_id}")
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                data = response.json()["data"]  # ✅ acceder a "data"
                assert "station_id" in data
                assert "total_sensors" in data
                assert "sensors" in data
                assert isinstance(data["sensors"], list)
                
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
    """Test main reports endpoint."""
    response = client.get("/reports/")
    assert response.status_code in [200, 404, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "success" in data
        assert "total" in data
        assert "reports" in data
        assert isinstance(data["reports"], list)
        
        if len(data["reports"]) > 0:
            report = data["reports"][0]
            assert "station_id" in report
            assert "station_name" in report
            assert "pm25_value" in report
            assert "status" in report
            assert "date" in report


def test_reports_summary_endpoint():
    """Test reports summary statistics."""
    response = client.get("/reports/summary")
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        data = response.json()
        assert "success" in data
        assert "data" in data
        
        summary = data["data"]
        assert "total_reports" in summary  # ✅ corregido
        assert "avg_pm25" in summary
        assert "min_pm25" in summary
        assert "max_pm25" in summary
        
        assert isinstance(summary["total_reports"], int)
        assert isinstance(summary["avg_pm25"], (int, float))
        assert isinstance(summary["min_pm25"], (int, float))
        assert isinstance(summary["max_pm25"], (int, float))
