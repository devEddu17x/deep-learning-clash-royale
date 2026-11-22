import base64
import binascii
from contextlib import asynccontextmanager
import json
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.predictor import BasePredictor, create_predictor
from app.schemas import HealthResponse, PredictRequest, PredictResponse


async def _parse_multipart_payload(request: Request) -> tuple[list[bytes], int | None]:
    form = await request.form()
    raw_frames = form.getlist("frames")
    if len(raw_frames) != 4:
        raise HTTPException(status_code=400, detail="Expected exactly 4 files in 'frames'.")

    decoded_frames: list[bytes] = []
    for item in raw_frames:
        if not isinstance(item, UploadFile):
            raise HTTPException(status_code=400, detail="Each item in 'frames' must be a file.")
        try:
            content = await item.read()
        finally:
            await item.close()
        if not content:
            raise HTTPException(status_code=400, detail="Frame file cannot be empty.")
        decoded_frames.append(content)

    timestamp_raw = form.get("timestamp_ms")
    timestamp_ms: int | None = None
    if timestamp_raw is not None and timestamp_raw != "":
        try:
            timestamp_ms = int(str(timestamp_raw))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid timestamp_ms integer.") from exc

    return decoded_frames, timestamp_ms


async def _parse_json_payload(request: Request) -> tuple[list[bytes], int | None]:
    try:
        raw_body = await request.body()
        payload_dict = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON request body.") from exc

    try:
        parsed = PredictRequest.model_validate(payload_dict)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail="Payload must contain 4 base64 frames.") from exc

    decoded_frames: list[bytes] = []
    for frame_b64 in parsed.frames:
        if not frame_b64.strip():
            raise HTTPException(status_code=400, detail="Frame string cannot be empty.")
        try:
            decoded = base64.b64decode(frame_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid base64 encoding in frames.") from exc
        if not decoded:
            raise HTTPException(status_code=400, detail="Decoded frame cannot be empty.")
        decoded_frames.append(decoded)

    return decoded_frames, parsed.timestamp_ms


def create_app(predictor: BasePredictor | None = None) -> FastAPI:
    load_on_startup = predictor is None

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        active_predictor = predictor or create_predictor()
        if load_on_startup:
            active_predictor.load()
        application.state.predictor = active_predictor
        yield

    application = FastAPI(
        title="Clash Royale Inference API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.get("/ping", response_model=HealthResponse)
    async def ping(request: Request):
        active_predictor: BasePredictor = request.app.state.predictor
        if not active_predictor.is_ready():
            return JSONResponse(
                status_code=503,
                content=HealthResponse(
                    status="loading",
                    model_version=active_predictor.model_version,
                ).model_dump(),
            )
        return HealthResponse(status="ok", model_version=active_predictor.model_version)

    @application.post("/invocations", response_model=PredictResponse)
    async def invocations(request: Request):
        active_predictor: BasePredictor = request.app.state.predictor
        if not active_predictor.is_ready():
            raise HTTPException(status_code=503, detail="Model is not ready.")

        content_type = (request.headers.get("content-type") or "").lower()
        if content_type.startswith("multipart/form-data"):
            frames, timestamp_ms = await _parse_multipart_payload(request)
        else:
            frames, timestamp_ms = await _parse_json_payload(request)

        start = time.perf_counter()
        recommendation = active_predictor.predict(frames, timestamp_ms)
        inference_ms = round((time.perf_counter() - start) * 1000.0, 3)

        return PredictResponse(
            recommendation=recommendation,
            inference_ms=inference_ms,
            model_version=active_predictor.model_version,
        )

    return application


app = create_app()
