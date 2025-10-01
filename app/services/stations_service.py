import os
import asyncio
import logging

logger = logging.getLogger(__name__)

async def get_stations():
    
    
    use_real_data = os.getenv("USE_REAL_DATA", "false").lower() == "true"
    
    if not use_real_data:
        logger.error("USE_REAL_DATA debe estar en 'true'")
        raise ValueError("Configure USE_REAL_DATA=true en .env")
    
    try:
        from app.services.rmcab_client import rmcab_client
        
        stations = await rmcab_client.get_stations_data()
        
        if not stations or len(stations) == 0:
            raise ValueError("No se pudieron capturar datos de ninguna estación")
        
        logger.info(f"Successfully obtained {len(stations)} stations from RMCAB")
        return stations
        
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error al capturar datos: {e}")
        raise ValueError(f"Error al capturar datos de RMCAB: {str(e)}")

def get_stations_sync():
    
    try:
        return asyncio.run(get_stations())
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        raise ValueError(f"Error interno: {str(e)}")