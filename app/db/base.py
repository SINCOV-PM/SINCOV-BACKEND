from app.db.base_class import Base

# Import all models here for Alembic
from app.models.station import Station
from app.models.monitor import Monitor
from app.models.sensor import Sensor
from app.models.report import Report
from app.models.predict import Prediction
from app.models.subscription import Subscription
from app.models.alert import Alert

