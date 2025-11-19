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
    assert response.status_code in [200, 404]  # Accept 404 if no data
    
    if response.status_code == 200:
        data = response.json()
        assert "stations" in data
        assert isinstance(data["stations"], list)
        
        # If there are stations, verify structure
        if len(data["stations"]) > 0:
            station = data["stations"][0]
            assert "id" in station
            assert "name" in station
            assert "lat" in station
            assert "lng" in station
            assert "value" in station  # PM2.5 value
            assert "timestamp" in station


def test_stations_summary_endpoint():
    """Test stations summary with all monitors."""
    response = client.get("/stations/summary/all")
    assert response.status_code in [200]
    
    if response.status_code == 200:
        data = response.json()
        assert "total" in data
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # If there is data, verify structure
        if len(data["data"]) > 0:
            station = data["data"][0]
            assert "id" in station
            assert "name" in station
            assert "lat" in station
            assert "lng" in station
            assert "monitors" in station
            assert isinstance(station["monitors"], list)
            
            # Verify monitor structure
            if len(station["monitors"]) > 0:
                monitor = station["monitors"][0]
                assert "type" in monitor
                assert "unit" in monitor
                assert "promedio" in monitor
                assert "minimo" in monitor
                assert "maximo" in monitor
                assert "ultima_medicion" in monitor

def test_predict_xgboost_endpoint_allowed_station():
    """
    Verifica la ejecución exitosa del servicio de predicción XGBoost (POST /predict/).
    Usa la estación 2 y el payload JSON requerido.
    """
    station_id = 2
    
    payload = {
        "station_id": station_id,
        "horizons": [1, 3, 6, 12] 
    }
    
    
    response = client.post(
        "/predict/",
        json=payload
    )
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert "success" in data
    assert data["success"] is True
    assert data["station_id"] == station_id
    assert "predictions" in data
    assert isinstance(data["predictions"], list)
    assert len(data["predictions"]) == 4
    
    
    first_prediction = data["predictions"][0]
    assert "horizon" in first_prediction
    assert "predicted_pm25" in first_prediction
    assert "timestamp" in first_prediction

def test_station_detail_endpoint():
    """Test detail for a specific station."""
    # First get a valid station
    stations_response = client.get("/stations/")
    
    if stations_response.status_code == 200:
        stations_data = stations_response.json()
        
        if len(stations_data["stations"]) > 0:
            station_id = stations_data["stations"][0]["id"]
            
            # Test detail endpoint
            response = client.get(f"/stations/{station_id}")
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                data = response.json()
                assert "station_id" in data
                assert "total_sensors" in data
                assert "sensors" in data
                assert isinstance(data["sensors"], list)
                
                # Verify sensor structure
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
    assert response.status_code in [200, 404]  # Accept 404 if no data
    
    if response.status_code == 200:
        data = response.json()
        assert "success" in data
        assert "total" in data
        assert "reports" in data
        assert isinstance(data["reports"], list)
        
        # If there are reports, verify structure
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
            
            # Verify that status is valid
            valid_statuses = ["Bueno", "Moderado", "Alto", "Muy Alto", "Peligroso"]
            assert report["status"] in valid_statuses


def test_reports_summary_endpoint():
    """Test reports summary statistics."""
    response = client.get("/reports/summary")
    assert response.status_code in [200, 404]  # Accept 404 if no data
    
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
        
        # Verify that values are numeric
        assert isinstance(summary["total_stations"], int)
        assert isinstance(summary["avg_pm25"], (int, float))
        assert isinstance(summary["min_pm25"], (int, float))
        assert isinstance(summary["max_pm25"], (int, float))
        
        # Verify that status_distribution is a dict
        assert isinstance(summary["status_distribution"], dict)