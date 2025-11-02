from pydantic import BaseModel, Field
from typing import List, Literal

#
class PMRequest(BaseModel):
    
    features: List[float]


# ===== NUEVOS SCHEMAS PARA SERIES TEMPORALES =====

# Tipo de rango temporal soportado
TimeRange = Literal["1h", "3h", "6h", "12h", "24h", "48h"]

# Método de predicción utilizado
PredictionMethod = Literal["backend_pkl", "backend_spark", "mock"]


class PredictionRequest(BaseModel):
    """
    Solicitud de predicción de serie temporal.
    
    Attributes:
        station_id: ID de la estación de monitoreo
        time_range: Rango temporal de predicción (1h, 3h, 6h, 12h, 24h, 48h)
        start_time: Timestamp de inicio (opcional, por defecto: ahora)
    
    Example:
        {
            "station_id": 1,
            "time_range": "6h",
            "start_time": "2025-11-01T14:00:00Z"
        }
    """
    station_id: int = Field(..., description="ID de la estación", ge=1)
    time_range: TimeRange = Field(..., description="Rango temporal de predicción")
    start_time: str | None = Field(None, description="Timestamp de inicio (ISO 8601)")


class PredictionPoint(BaseModel):
    """
    Punto individual de predicción.
    
    Attributes:
        timestamp: Momento de la predicción
        predicted_pm25: Valor predicho de PM2.5 en μg/m³
        error_percentage: Porcentaje de error/incertidumbre
    
    Example:
        {
            "timestamp": "2025-11-01T15:00:00Z",
            "predicted_pm25": 32.5,
            "error_percentage": 8.2
        }
    """
    timestamp: str = Field(..., description="Timestamp de la predicción (ISO 8601)")
    predicted_pm25: float = Field(..., description="Valor predicho de PM2.5 (μg/m³)", ge=0)
    error_percentage: float = Field(..., description="Porcentaje de error", ge=0, le=100)


class PredictionResponse(BaseModel):
    """
    Respuesta completa de predicción.
    
    Attributes:
        success: Indica si la predicción fue exitosa
        station_id: ID de la estación predicha
        station_name: Nombre de la estación
        time_range: Rango temporal usado
        method: Método de predicción utilizado
        predictions: Lista de predicciones horarias
        generated_at: Timestamp de generación (ISO 8601)
    
    Example:
        {
            "success": true,
            "station_id": 1,
            "station_name": "Carvajal - Sevillana",
            "time_range": "6h",
            "method": "backend_pkl",
            "predictions": [
                {
                    "timestamp": "2025-11-01T15:00:00Z",
                    "predicted_pm25": 32.5,
                    "error_percentage": 8.2
                },
                ...
            ],
            "generated_at": "2025-11-01T14:30:00Z"
        }
    """
    success: bool = Field(..., description="Indica si la predicción fue exitosa")
    station_id: int = Field(..., description="ID de la estación")
    station_name: str = Field(..., description="Nombre de la estación")
    time_range: TimeRange = Field(..., description="Rango temporal usado")
    method: PredictionMethod = Field(..., description="Método de predicción utilizado")
    predictions: List[PredictionPoint] = Field(..., description="Lista de predicciones horarias")
    generated_at: str = Field(..., description="Timestamp de generación (ISO 8601)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "station_id": 1,
                "station_name": "Carvajal - Sevillana",
                "time_range": "6h",
                "method": "backend_pkl",
                "predictions": [
                    {
                        "timestamp": "2025-11-01T15:00:00Z",
                        "predicted_pm25": 32.5,
                        "error_percentage": 8.2
                    },
                    {
                        "timestamp": "2025-11-01T16:00:00Z",
                        "predicted_pm25": 34.1,
                        "error_percentage": 9.5
                    }
                ],
                "generated_at": "2025-11-01T14:30:00Z"
            }
        }