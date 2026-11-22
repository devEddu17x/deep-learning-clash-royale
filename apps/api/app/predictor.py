from abc import ABC, abstractmethod
import os
from pathlib import Path


class BasePredictor(ABC):
    @property
    @abstractmethod
    def model_version(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def load(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_ready(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def predict(self, frames: list[bytes], timestamp_ms: int | None) -> str:
        raise NotImplementedError


class PlaceholderPredictor(BasePredictor):
    """Fallback predictor that validates the 4-frame input contract until a trained model is wired."""

    def __init__(
        self,
        model_dir: str | None = None,
        version: str | None = None,
        default_recommendation: str | None = None,
    ) -> None:
        self._model_dir = Path(model_dir or os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
        self._version = version or os.environ.get("MODEL_VERSION", "placeholder-v0")
        self._default_recommendation = default_recommendation or os.environ.get(
            "PLACEHOLDER_RECOMMENDATION", "wait"
        )
        self._ready = False
        self._artifact_count = 0

    @property
    def model_version(self) -> str:
        return self._version

    def load(self) -> None:
        if self._model_dir.exists() and self._model_dir.is_dir():
            self._artifact_count = sum(1 for item in self._model_dir.rglob("*") if item.is_file())
        else:
            self._artifact_count = 0
        self._ready = True

    def is_ready(self) -> bool:
        return self._ready

    def predict(self, frames: list[bytes], timestamp_ms: int | None) -> str:
        if len(frames) != 4 or any(len(frame) == 0 for frame in frames):
            raise ValueError("Expected exactly 4 non-empty image frames.")
        return self._default_recommendation


def create_predictor() -> BasePredictor:
    return PlaceholderPredictor()
