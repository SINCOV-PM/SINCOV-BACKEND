from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context
import os
import sys
from dotenv import load_dotenv
from app.db.base import Base
from app.db.seed_data import seed_stations_from_json

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("No DATABASE_URL set for alembic migrations")

# Alembic base configuration
config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata from your models
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        
        # Uncomment the following lines to clear data before seeding
        # from app.models.station import Station
        # from app.models.monitor import Monitor
        # from app.db.session import SessionLocal
        # db = SessionLocal()
            
        # db.query(Monitor).delete()
        # db.query(Station).delete()
        # db.commit()
        
        if "revision" not in sys.argv:
            seed_stations_from_json()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
