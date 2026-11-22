import json
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

_sagemaker_client = None


def _get_sagemaker_client():
    global _sagemaker_client
    if _sagemaker_client is None:
        _sagemaker_client = boto3.client("sagemaker")
    return _sagemaker_client


def _build_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    cors_origin = os.environ.get("CORS_ALLOW_ORIGIN", "*")
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": cors_origin,
        },
        "body": json.dumps(body),
    }


def _normalize_component_state(
    description: dict[str, Any], endpoint_name: str, component_name: str
) -> tuple[str, dict[str, Any]]:
    sagemaker_status = description.get("InferenceComponentStatus", "Unknown")
    runtime = description.get("RuntimeConfig") or {}
    current_copies = int(runtime.get("CurrentCopyCount", 0) or 0)
    desired_copies = int(runtime.get("DesiredCopyCount", 0) or 0)

    if sagemaker_status == "Failed":
        normalized = "error"
    elif sagemaker_status == "InService" and current_copies >= 1:
        normalized = "ready"
    elif sagemaker_status in {"Creating", "Updating"} or (
        desired_copies >= 1 and current_copies < desired_copies
    ):
        normalized = "warming_up"
    elif current_copies == 0 and desired_copies == 0 and sagemaker_status != "Deleting":
        normalized = "sleeping"
    else:
        normalized = "error"

    payload = {
        "status": normalized,
        "endpoint_name": endpoint_name,
        "inference_component_name": component_name,
        "sagemaker_status": sagemaker_status,
        "current_copy_count": current_copies,
        "desired_copy_count": desired_copies,
    }
    return normalized, payload


def _handle_status(client: Any, endpoint_name: str, component_name: str) -> dict[str, Any]:
    description = client.describe_inference_component(
        InferenceComponentName=component_name
    )
    _, payload = _normalize_component_state(description, endpoint_name, component_name)
    return _build_response(200, payload)


def _handle_warmup(client: Any, endpoint_name: str, component_name: str) -> dict[str, Any]:
    description = client.describe_inference_component(
        InferenceComponentName=component_name
    )
    normalized, payload = _normalize_component_state(
        description, endpoint_name, component_name
    )

    if normalized in {"ready", "warming_up"}:
        return _build_response(200, payload)

    if normalized == "error":
        return _build_response(503, payload)

    client.update_inference_component_runtime_config(
        InferenceComponentName=component_name,
        DesiredRuntimeConfig={"CopyCount": 1},
    )
    payload["status"] = "warming_up"
    payload["desired_copy_count"] = 1
    return _build_response(202, payload)


def _map_client_error(exc: ClientError) -> dict[str, Any]:
    error = exc.response.get("Error", {})
    code = error.get("Code", "ClientError")
    message = error.get("Message", "SageMaker request failed.")
    if code in {"ConflictException", "ResourceInUse"} or "in progress" in message.lower():
        return _build_response(409, {"error": code, "message": message})
    return _build_response(502, {"error": code, "message": message})


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    endpoint_name = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "")
    component_name = os.environ.get("SAGEMAKER_INFERENCE_COMPONENT_NAME", "")
    if not endpoint_name or not component_name:
        return _build_response(
            500,
            {
                "error": "ConfigurationError",
                "message": "Missing SageMaker environment variables.",
            },
        )

    method = (event.get("httpMethod") or "").upper()
    resource = (event.get("resource") or "").rstrip("/")
    path = (event.get("path") or "").rstrip("/")
    client = _get_sagemaker_client()

    try:
        if method == "GET" and (resource == "/status" or path.endswith("/status")):
            return _handle_status(client, endpoint_name, component_name)
        if method == "POST" and (resource == "/warmup" or path.endswith("/warmup")):
            return _handle_warmup(client, endpoint_name, component_name)
    except ClientError as exc:
        return _map_client_error(exc)

    return _build_response(404, {"error": "NotFound", "message": "Unsupported route."})
