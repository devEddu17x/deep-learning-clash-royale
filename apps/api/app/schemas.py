from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    frames: list[str] = Field(min_length=4, max_length=4)
    timestamp_ms: int | None = None


class PredictResponse(BaseModel):
    recommendation: str
    inference_ms: float
    model_version: str


class HealthResponse(BaseModel):
    status: str
    model_version: str
