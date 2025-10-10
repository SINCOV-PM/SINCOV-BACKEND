# app/utils/rmcab_utils.py
import json
from datetime import datetime, timezone
import pytz


# Epoch de .NET: 0001-01-01 00:00:00 UTC
# Ticks desde ese momento (100 nanosegundos por tick)
DOTNET_EPOCH = datetime(1, 1, 1, tzinfo=timezone.utc)


def to_dotnet_ticks(dt_str, tz_str="America/Bogota"):
    """
    Convierte una fecha ISO string a .NET ticks.
    
    Args:
        dt_str: Fecha en formato ISO (ej: "2025-10-10T00:00:00")
        tz_str: Timezone (ej: "America/Bogota")
    
    Returns:
        int: .NET ticks
    
    Ejemplo:
        >>> to_dotnet_ticks("2025-10-10T00:00:00", "America/Bogota")
        638641440000000000
    """
    tz = pytz.timezone(tz_str)
    
    # Parse la fecha string
    if isinstance(dt_str, str):
        # Intentar con fromisoformat primero
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            # Fallback a formato manual
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
    else:
        dt = dt_str
    
    # Si no tiene timezone, asignar la especificada
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    
    # Convertir a UTC
    dt_utc = dt.astimezone(timezone.utc)
    
    # Calcular diferencia desde epoch de .NET
    delta = dt_utc - DOTNET_EPOCH
    
    # Convertir a ticks (1 tick = 100 nanosegundos = 0.1 microsegundos)
    ticks = int(delta.total_seconds() * 10_000_000)
    
    return ticks


def ticks_to_iso(ticks, tz_str="America/Bogota"):
    """
    Convierte .NET ticks a fecha ISO string en timezone especificado.
    
    Args:
        ticks: .NET ticks (int)
        tz_str: Timezone (ej: "America/Bogota")
    
    Returns:
        str: Fecha en formato ISO
    """
    tz = pytz.timezone(tz_str)
    
    # Convertir ticks a segundos
    seconds = ticks / 10_000_000
    
    # Crear datetime desde epoch de .NET
    dt_utc = DOTNET_EPOCH + datetime.timedelta(seconds=seconds)
    
    # Convertir al timezone especificado
    dt_local = dt_utc.astimezone(tz)
    
    return dt_local.isoformat()


def dumps_list_as_string(data_list):
    """
    Convierte una lista a JSON string sin espacios (formato compacto).
    
    Args:
        data_list: Lista de Python
    
    Returns:
        str: JSON string
    
    Ejemplo:
        >>> dumps_list_as_string([1, 2, 3])
        '[1,2,3]'
    """
    return json.dumps(data_list, separators=(',', ':'))


def build_rmcab_params(station_id, station_name, monitor_ids, 
                       from_ticks, to_ticks, granularity_minutes,
                       report_type="Average", take=0, page_size=0):
    """
    Construye los parámetros para la API de RMCAB.
    
    Args:
        station_id: ID de la estación (int)
        station_name: Nombre de la estación (str)
        monitor_ids: Lista de IDs de monitores (list)
        from_ticks: Fecha inicio en .NET ticks (int)
        to_ticks: Fecha fin en .NET ticks (int)
        granularity_minutes: Granularidad en minutos (int)
        report_type: Tipo de reporte (str, default "Average")
        take: Parámetro take (int, default 0)
        page_size: Tamaño de página (int, default 0)
    
    Returns:
        dict: Diccionario de parámetros para requests
    """
    tb_str = str(granularity_minutes)
    tb_list = [tb_str]
    
    params = {
        "ListStationId": f"[{station_id}]",
        "ListMonitorIds": dumps_list_as_string(monitor_ids),
        "FDate": str(from_ticks),
        "TDate": str(to_ticks),
        "TB": dumps_list_as_string(tb_list),
        "ToTB": str(granularity_minutes),
        "ReportType": report_type,
        "first": "true",
        "take": str(take),
        "skip": "0",
        "page": "1",
        "pageSize": str(page_size)
    }
    
    if station_name:
        names_list = [station_name]
        params["ListStationsNames"] = dumps_list_as_string(names_list)
    
    return params