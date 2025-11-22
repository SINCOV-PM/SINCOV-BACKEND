import json
from pathlib import Path
from app.db.session import SessionLocal
from app.models.station import Station
from app.models.monitor import Monitor
from sqlalchemy.exc import SQLAlchemyError

def seed_stations_from_json():
    db = SessionLocal()

    # Check if stations are already seeded
    if db.query(Station).count() > 0:
        print("Stations already seeded, skipping.")
        db.close()
        return

    # Absolute path to JSON
    json_path = Path(__file__).resolve().parent.parent / "data" / "stations.json"

    if not json_path.exists():
        print(f"File not found: {json_path}")
        db.close()
        return

    # Load JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    stations = data.get("stations", {})

    for station_id, info in stations.items():
        try:
            station = Station(
                name=info["name"],
                station_rmcab_id=int(station_id),
                latitude=info.get("lat", 0.0),
                longitude=info.get("lon", 0.0),
            )
            db.add(station)
            db.flush()  # Get station.id

            for code, sensor in info["codes"].items():
                monitor = Monitor(
                    station_id=station.id,
                    type=sensor["label"],
                    code=code,
                    unit=sensor["unit"]
                )
                db.add(monitor)

            db.commit()
            print(f"Station '{info['name']}' seeded successfully")

        except SQLAlchemyError as e:
            db.rollback()
            print(f"Failed to seed station '{info['name']}': {str(e)}")

    db.close()
    print("Seeding process completed.")
