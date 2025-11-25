import json
import re
from datetime import datetime, timezone, timedelta
import pytz

# .NET Epoch
DOTNET_EPOCH = datetime(1, 1, 1, tzinfo=timezone.utc)

# Regex fecha dd-mm-YYYY HH:MM
DT_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{4}) (\d{2}):(\d{2})$")


# ---------------------------------------------------------------
# NORMALIZAR 24:00 → 00:00 del día siguiente
# ---------------------------------------------------------------
def normalize_datetime_string(s: str) -> str:
    m = DT_RE.fullmatch(s)
    if not m:
        return s

    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    h, mi = int(m.group(4)), int(m.group(5))

    if h == 24:
        dt = datetime(y, mo, d, 0, mi) + timedelta(days=1)
        return dt.strftime("%d-%m-%Y %H:%M")

    return s


# ---------------------------------------------------------------
# CONVERTIR ISO → ticks .NET
# ---------------------------------------------------------------
def to_dotnet_ticks(dt_str, tz_str="America/Bogota"):
    tz = pytz.timezone(tz_str)

    if isinstance(dt_str, str):
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except:
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
            except:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    else:
        dt = dt_str

    if dt.tzinfo is None:
        dt = tz.localize(dt)

    dt_utc = dt.astimezone(timezone.utc)
    delta = dt_utc - DOTNET_EPOCH
    return int(delta.total_seconds() * 10_000_000)


# ---------------------------------------------------------------
# ticks → ISO
# ---------------------------------------------------------------
def ticks_to_iso(ticks, tz_str="America/Bogota"):
    tz = pytz.timezone(tz_str)
    seconds = ticks / 10_000_000
    dt_utc = DOTNET_EPOCH + timedelta(seconds=seconds)
    return dt_utc.astimezone(tz).isoformat()


# ---------------------------------------------------------------
# PARSEAR TIMESTAMP DEL RMCAB
# ---------------------------------------------------------------
def parse_rmcab_timestamp(value, tz_str="America/Bogota"):
    tz = pytz.timezone(tz_str)

    if value is None:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else tz.localize(value)

    if isinstance(value, str):
        value = normalize_datetime_string(value)

        # ISO 8601
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else tz.localize(dt)
        except:
            pass

        # dd-mm-YYYY HH:MM
        try:
            dt = datetime.strptime(value, "%d-%m-%Y %H:%M")
            return tz.localize(dt)
        except:
            pass

        # YYYY-MM-DD HH:MM:SS
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return tz.localize(dt)
        except:
            pass

        return None  # NO usar datetime.now()

    if isinstance(value, (int, float)):
        if value > 630000000000000000:  # ticks .NET
            dt = datetime.fromisoformat(ticks_to_iso(value, tz_str))
            return dt if dt.tzinfo else tz.localize(dt)

        if value > 1000000000:  # Unix
            return datetime.fromtimestamp(value, tz=tz)

    return None


# ---------------------------------------------------------------
# JSON compact list
# ---------------------------------------------------------------
def dumps_list_as_string(data_list):
    return json.dumps(data_list, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------
# parámetros API
# ---------------------------------------------------------------
def build_rmcab_params(
    station_id,
    station_name,
    monitor_ids,
    from_ticks,
    to_ticks,
    granularity_minutes,
    report_type="Average",
    take=None,
    page_size=None,
):
    if take is None:
        take = granularity_minutes

    if page_size is None:
        page_size = granularity_minutes

    tb = dumps_list_as_string([str(granularity_minutes)])

    params = {
        "ListStationId": f"[{station_id}]",
        "ListMonitorIds": dumps_list_as_string(monitor_ids),
        "FDate": str(from_ticks),
        "TDate": str(to_ticks),
        "TB": tb,
        "ToTB": str(granularity_minutes),
        "ReportType": report_type,
        "first": "true",
        "take": str(take),
        "skip": "0",
        "page": "1",
        "pageSize": str(page_size),
    }

    if station_name:
        params["ListStationsNames"] = dumps_list_as_string([station_name])

    return params
