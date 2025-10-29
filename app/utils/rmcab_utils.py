import json
import re
from datetime import datetime, timezone, timedelta
import pytz


# .NET Epoch: 0001-01-01 00:00:00 UTC
# Ticks since that moment (100 nanoseconds per tick)
DOTNET_EPOCH = datetime(1, 1, 1, tzinfo=timezone.utc)

# Regex to detect dd-mm-YYYY HH:MM format
DT_RE = re.compile(r"(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})")


def normalize_datetime_string(s: str) -> str:
    """
    Converts 'dd-mm-YYYY 24:MM' -> 'dd-mm-YYYY+1 00:MM'.
    If it's a normal hour (00–23), it remains the same.
    If it does not match the pattern, it returns as is.
    
    Args:
        s: Date/time string in dd-mm-YYYY HH:MM format
    
    Returns:
        Normalized string
    
    Example:
        >>> normalize_datetime_string("10-10-2025 24:00")
        "11-10-2025 00:00"
    """
    m = DT_RE.fullmatch(s)
    if not m:
        return s
    
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    h, mi = int(m.group(4)), int(m.group(5))
    
    if h == 24:
        # Move to the next day with 00:MM
        dt = datetime(y, mo, d, 0, mi) + timedelta(days=1)
    else:
        dt = datetime(y, mo, d, h, mi)
    
    return dt.strftime("%d-%m-%Y %H:%M")


def to_dotnet_ticks(dt_str, tz_str="America/Bogota"):
    """
    Converts an ISO date string to .NET ticks.
    
    Args:
        dt_str: Date in ISO format (e.g., "2025-10-10T00:00:00")
        tz_str: Timezone (e.g., "America/Bogota")
    
    Returns:
        int: .NET ticks
    
    Example:
        >>> to_dotnet_ticks("2025-10-10T00:00:00", "America/Bogota")
        638641440000000000
    """
    tz = pytz.timezone(tz_str)
    
    # Parse the date string
    if isinstance(dt_str, str):
        # Try fromisoformat first
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            try:
                # Fallback to manual format
                dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
            except:
                # Alternative format YYYY-MM-DD HH:MM
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    else:
        dt = dt_str
    
    # If it has no timezone, assign the specified one
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    
    # Convert to UTC
    dt_utc = dt.astimezone(timezone.utc)
    
    # Calculate difference from .NET epoch
    delta = dt_utc - DOTNET_EPOCH
    
    # Convert to ticks (1 tick = 100 nanoseconds = 0.1 microseconds)
    ticks = int(delta.total_seconds() * 10_000_000)
    
    return ticks


def ticks_to_iso(ticks, tz_str="America/Bogota"):
    """
    Converts .NET ticks to ISO date string in the specified timezone.
    
    Args:
        ticks: .NET ticks (int)
        tz_str: Timezone (e.g., "America/Bogota")
    
    Returns:
        str: Date in ISO format
    """
    tz = pytz.timezone(tz_str)
    
    # Convert ticks to seconds
    seconds = ticks / 10_000_000
    
    # Create datetime from .NET epoch
    dt_utc = DOTNET_EPOCH + timedelta(seconds=seconds)
    
    # Convert to the specified timezone
    dt_local = dt_utc.astimezone(tz)
    
    return dt_local.isoformat()


def parse_rmcab_timestamp(value, tz_str="America/Bogota"):
    """
    Parses different timestamp formats that RMCAB can return.
    
    Args:
        value: Timestamp value (str, int, float, or datetime)
        tz_str: Timezone to localize naive dates
    
    Returns:
        datetime: Timezone-aware datetime object
    
    Handles:
        - ISO 8601: "2025-10-10T12:00:00" or "2025-10-10T12:00:00Z"
        - dd-mm-YYYY HH:MM format (including 24 hour)
        - .NET ticks (large numbers)
        - Unix timestamps
    """
    tz = pytz.timezone(tz_str)
    
    if value is None:
        return datetime.now(tz)
    
    # If it's already a datetime object
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return tz.localize(value)
        return value
    
    # If it's a string
    if isinstance(value, str):
        # Normalize 24:00 hour if it exists
        if "24:" in value:
            value = normalize_datetime_string(value)
        
        try:
            # Try ISO 8601
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = tz.localize(dt)
            return dt
        except:
            try:
                # dd-mm-YYYY HH:MM format
                dt = datetime.strptime(value, "%d-%m-%Y %H:%M")
                return tz.localize(dt)
            except:
                try:
                    # YYYY-MM-DD HH:MM:SS format
                    dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                    return tz.localize(dt)
                except:
                    try:
                        # YYYY-MM-DD HH:MM format
                        dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
                        return tz.localize(dt)
                    except:
                        # If parsing fails, return now
                        return datetime.now(tz)
    
    # If it's a number (Unix timestamp or .NET ticks)
    if isinstance(value, (int, float)):
        if value > 630000000000000000:  # .NET ticks
            timestamp_str = ticks_to_iso(value, tz_str)
            dt = datetime.fromisoformat(timestamp_str)
            if dt.tzinfo is None:
                dt = tz.localize(dt)
            return dt
        elif value > 1000000000:  # Unix timestamp
            return datetime.fromtimestamp(value, tz=tz)
    
    # Fallback: return now
    return datetime.now(tz)


def dumps_list_as_string(data_list):
    """
    Converts a list to a JSON string without spaces (compact format).
    
    Args:
        data_list: Python list
    
    Returns:
        str: JSON string
    
    Example:
        >>> dumps_list_as_string([1, 2, 3])
        '[1,2,3]'
    """
    return json.dumps(data_list, separators=(',', ':'), ensure_ascii=False)


def build_rmcab_params(station_id, station_name, monitor_ids, 
                       from_ticks, to_ticks, granularity_minutes,
                       report_type="Average", take=0, page_size=0):
    """
    Builds the parameters for the RMCAB API request.
    
    Args:
        station_id: Station ID (int)
        station_name: Station name (str)
        monitor_ids: List of monitor IDs (list)
        from_ticks: Start date in .NET ticks (int)
        to_ticks: End date in .NET ticks (int)
        granularity_minutes: Granularity in minutes (int)
        report_type: Report type (str, default "Average")
        take: Take parameter (int, default 0)
        page_size: Page size (int, default 0)
    
    Returns:
        dict: Dictionary of parameters for requests
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
