import logging
import pandas as pd
from prophet import Prophet

logger = logging.getLogger(__name__)

class ProphetPredictor:
    """Wrapper for Prophet PM2.5 time-series forecasting."""

    def __init__(self):
        self.model = None

    def load(self):
        """Load Prophet model (can be trained or deserialized)."""
        if self.model is None:
            self.model = Prophet()
            logger.info("Prophet model initialized.")
        return self.model

    def predict(self, history_24h: list[dict]) -> float:
        """
        Predict PM2.5 for the next hour based on 24h historical data.
        """
        df = pd.DataFrame(history_24h)
        model = self.load()
        model.fit(df)
        future = model.make_future_dataframe(periods=1, freq="H")
        forecast = model.predict(future)
        next_val = float(forecast["yhat"].iloc[-1])
        logger.info(f"Prophet prediction: {next_val:.2f} µg/m³")
        return max(0.0, next_val)

    def get_info(self):
        return {"model": "Prophet", "framework": "prophet>=1.1.5"}
