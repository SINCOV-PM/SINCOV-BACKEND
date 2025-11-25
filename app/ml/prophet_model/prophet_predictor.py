import logging
import pandas as pd
from prophet import Prophet

from app.ml.base_model import BasePredictor

logger = logging.getLogger(__name__)


class ProphetPredictor(BasePredictor):
    """Prophet predictor: ONLY supports 24h ahead forecast."""

    def __init__(self):
        pass  # ❗ No guardamos modelo persistente

    def load(self):
        """Always return a new Prophet model."""
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=False,
            yearly_seasonality=False,
            changepoint_prior_scale=0.5,
        )
        logger.info("Prophet model initialized.")
        return model

    def predict(self, history_24h: list[dict], horizon: int = 24) -> float:
        if horizon != 24:
            raise ValueError("ProphetPredictor ONLY supports horizon = 24 hours.")

        df = pd.DataFrame(history_24h)
        if df.empty:
            raise ValueError("Prophet history cannot be empty.")

        # Always instantiate a fresh Prophet
        model = self.load()

        # Prophet cannot receive timezone-aware timestamps
        df["ds"] = pd.to_datetime(df["ds"]).dt.tz_localize(None)

        model.fit(df)

        # 24 periods ahead
        future = model.make_future_dataframe(periods=24, freq="h")
        forecast = model.predict(future)

        yhat_24 = float(forecast["yhat"].iloc[-1])
        logger.info(f"Prophet 24h prediction: {yhat_24:.2f} µg/m³")

        return max(0.0, yhat_24)

    def get_info(self):
        return {
            "model": "Prophet",
            "framework": "prophet>=1.1.5",
            "valid_horizons": [24],
            "input_required": "24h PM2.5 historical data",
        }
