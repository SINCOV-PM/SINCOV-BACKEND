"""
Unit tests for RMCAB utility functions.
"""
import pytest
from datetime import datetime
import pytz
from app.utils.rmcab_utils import (
    normalize_datetime_string,
    to_dotnet_ticks,
    parse_rmcab_timestamp,
    dumps_list_as_string,
    build_rmcab_params
)


class TestRMCABUtils:
    """Test suite for RMCAB utility functions."""


    def test_normalize_datetime_regular(self):
        """Verifica que las horas normales no se modifiquen."""
        result = normalize_datetime_string("10-10-2025 15:30")
        assert result == "10-10-2025 15:30"

    def test_to_dotnet_ticks_returns_int(self):
        """Confirma que la conversión a ticks devuelva un entero válido."""
        dt_str = "2025-10-10T00:00:00"
        ticks = to_dotnet_ticks(dt_str, "America/Bogota")
        assert isinstance(ticks, int)
        assert ticks > 0

    def test_build_rmcab_params_structure(self):
        """Valida que los parámetros generados tengan la estructura esperada."""
        params = build_rmcab_params(
            station_id=999,
            station_name="Test Station",
            monitor_ids=["S_1", "S_2"],
            from_ticks=123456789,
            to_ticks=987654321,
            granularity_minutes=60
        )

        assert "ListStationId" in params
        assert params["ListStationId"] == "[999]"
        assert "ListMonitorIds" in params
        assert "FDate" in params
        assert "TDate" in params
        assert "ToTB" in params
        assert params["ToTB"] == "60"

    """
    def test_normalize_datetime_24_hour(self):
        # Verifica que 24:00 se convierta en 00:00 del día siguiente.
        result = normalize_datetime_string("10-10-2025 24:00")
        assert result == "11-10-2025 00:00"

    def test_parse_rmcab_timestamp_iso(self):
        # Prueba que se interpreten correctamente timestamps ISO 8601.
        dt = parse_rmcab_timestamp("2025-10-10T12:00:00", "America/Bogota")
        assert isinstance(dt, datetime)
        assert dt.hour == 12

    def test_parse_rmcab_timestamp_dd_mm_yyyy(self):
        # Verifica fechas en formato dd-mm-yyyy HH:MM.
        dt = parse_rmcab_timestamp("10-10-2025 15:30", "America/Bogota")
        assert dt.year == 2025
        assert dt.hour == 15

    def test_parse_rmcab_timestamp_24_hour(self):
        # Verifica que 24:00 se interprete correctamente.
        dt = parse_rmcab_timestamp("10-10-2025 24:00", "America/Bogota")
        assert dt.day == 11
        assert dt.hour == 0

    def test_dumps_list_as_string_compact(self):
        # Verifica que las listas se conviertan a JSON compacto.
        result = dumps_list_as_string([1, 2, 3])
        assert result == "[1,2,3]"
        assert " " not in result
    """
