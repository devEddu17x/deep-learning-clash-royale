import base64
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app, create_app
from app.predictor import BasePredictor


class _NotReadyPredictor(BasePredictor):
    @property
    def model_version(self) -> str:
        return "not-ready-v0"

    def load(self) -> None:
        pass

    def is_ready(self) -> bool:
        return False

    def predict(self, frames: list[bytes], timestamp_ms: int | None) -> str:
        raise AssertionError("predict should not be called while not ready")


def _sample_frames_b64(count: int = 4) -> list[str]:
    return [base64.b64encode(f"frame-{index}".encode()).decode() for index in range(count)]


def test_ping_ready():
    with TestClient(app) as client:
        response = client.get("/ping")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_version"] == "placeholder-v0"


def test_ping_not_ready_returns_503():
    unready_app = create_app(predictor=_NotReadyPredictor())
    with TestClient(unready_app) as client:
        response = client.get("/ping")
    assert response.status_code == 503
    assert response.json()["status"] == "loading"


def test_invocations_json_success():
    with TestClient(app) as client:
        response = client.post(
            "/invocations",
            json={"frames": _sample_frames_b64(4), "timestamp_ms": 1732280000000},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"] == "wait"
    assert isinstance(body["inference_ms"], float)
    assert body["inference_ms"] >= 0.0
    assert body["model_version"] == "placeholder-v0"


def test_invocations_multipart_success():
    files = [
        ("frames", (f"frame_{idx}.jpg", f"jpeg-bytes-{idx}".encode(), "image/jpeg"))
        for idx in range(4)
    ]
    with TestClient(app) as client:
        response = client.post(
            "/invocations",
            files=files,
            data={"timestamp_ms": "1732280000000"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"] == "wait"
    assert body["model_version"] == "placeholder-v0"


def test_invocations_wrong_frame_count_returns_400():
    with TestClient(app) as client:
        too_few = client.post("/invocations", json={"frames": _sample_frames_b64(3)})
        too_many = client.post("/invocations", json={"frames": _sample_frames_b64(5)})
    assert too_few.status_code == 400
    assert too_many.status_code == 400


def test_invocations_invalid_base64_returns_400():
    frames = _sample_frames_b64(3) + ["not-valid-base64!!!"]
    with TestClient(app) as client:
        response = client.post("/invocations", json={"frames": frames})
    assert response.status_code == 400


def test_invocations_malformed_json_returns_400():
    with TestClient(app) as client:
        response = client.post(
            "/invocations",
            content="{not-json",
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 400
