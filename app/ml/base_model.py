from abc import ABC, abstractmethod

class BasePredictor(ABC):
    """
    Abstract base class for all predictors (XGBoost, Prophet, etc.).
    Ensures a consistent interface across ML models.
    """

    @abstractmethod
    def predict(self, features, horizon: int):
        """
        Generate a prediction for a given horizon using the provided features.

        Args:
            features: Input feature data (pandas DataFrame, list, or dict)
            horizon: Prediction horizon (e.g., 1, 3, 6, 12 hours)

        Returns:
            float: Predicted PM2.5 value
        """
        pass

    @abstractmethod
    def get_info(self) -> dict:
        """Return metadata about the model (features, training info, version)."""
        pass
