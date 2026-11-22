import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent))

if "boto3" not in sys.modules:
    boto3_stub = types.ModuleType("boto3")
    boto3_stub.client = MagicMock()
    sys.modules["boto3"] = boto3_stub

if "botocore" not in sys.modules:
    class _ClientError(Exception):
        def __init__(self, error_response, operation_name):
            super().__init__(error_response.get("Error", {}).get("Message", operation_name))
            self.response = error_response
            self.operation_name = operation_name

    botocore_stub = types.ModuleType("botocore")
    exceptions_stub = types.ModuleType("botocore.exceptions")
    exceptions_stub.ClientError = _ClientError
    botocore_stub.exceptions = exceptions_stub
    sys.modules["botocore"] = botocore_stub
    sys.modules["botocore.exceptions"] = exceptions_stub

from botocore.exceptions import ClientError
import handler


class WarmUpHandlerTests(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        handler._sagemaker_client = self.mock_client
        os.environ["SAGEMAKER_ENDPOINT_NAME"] = "dp-clash-royale-dev-endpoint"
        os.environ["SAGEMAKER_INFERENCE_COMPONENT_NAME"] = "dp-clash-royale-dev-ic"
        os.environ["CORS_ALLOW_ORIGIN"] = "*"

    def tearDown(self):
        handler._sagemaker_client = None

    def test_status_sleeping(self):
        self.mock_client.describe_inference_component.return_value = {
            "InferenceComponentStatus": "InService",
            "RuntimeConfig": {"CurrentCopyCount": 0, "DesiredCopyCount": 0},
        }
        response = handler.lambda_handler({"httpMethod": "GET", "resource": "/status"}, None)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["Access-Control-Allow-Origin"], "*")
        body = json.loads(response["body"])
        self.assertEqual(body["status"], "sleeping")
        self.assertEqual(body["current_copy_count"], 0)

    def test_status_warming_up(self):
        self.mock_client.describe_inference_component.return_value = {
            "InferenceComponentStatus": "Updating",
            "RuntimeConfig": {"CurrentCopyCount": 0, "DesiredCopyCount": 1},
        }
        response = handler.lambda_handler({"httpMethod": "GET", "path": "/dev/status"}, None)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["status"], "warming_up")
        self.assertEqual(body["desired_copy_count"], 1)

    def test_status_ready(self):
        self.mock_client.describe_inference_component.return_value = {
            "InferenceComponentStatus": "InService",
            "RuntimeConfig": {"CurrentCopyCount": 1, "DesiredCopyCount": 1},
        }
        response = handler.lambda_handler({"httpMethod": "GET", "resource": "/status"}, None)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["status"], "ready")

    def test_status_error(self):
        self.mock_client.describe_inference_component.return_value = {
            "InferenceComponentStatus": "Failed",
            "RuntimeConfig": {"CurrentCopyCount": 0, "DesiredCopyCount": 1},
        }
        response = handler.lambda_handler({"httpMethod": "GET", "resource": "/status"}, None)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["status"], "error")

    def test_warmup_scales_from_zero(self):
        self.mock_client.describe_inference_component.return_value = {
            "InferenceComponentStatus": "InService",
            "RuntimeConfig": {"CurrentCopyCount": 0, "DesiredCopyCount": 0},
        }
        response = handler.lambda_handler({"httpMethod": "POST", "resource": "/warmup"}, None)
        self.assertEqual(response["statusCode"], 202)
        body = json.loads(response["body"])
        self.assertEqual(body["status"], "warming_up")
        self.assertEqual(body["desired_copy_count"], 1)
        self.mock_client.update_inference_component_runtime_config.assert_called_once_with(
            InferenceComponentName="dp-clash-royale-dev-ic",
            DesiredRuntimeConfig={"CopyCount": 1},
        )

    def test_warmup_idempotent_when_ready(self):
        self.mock_client.describe_inference_component.return_value = {
            "InferenceComponentStatus": "InService",
            "RuntimeConfig": {"CurrentCopyCount": 1, "DesiredCopyCount": 1},
        }
        response = handler.lambda_handler({"httpMethod": "POST", "resource": "/warmup"}, None)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["status"], "ready")
        self.mock_client.update_inference_component_runtime_config.assert_not_called()

    def test_warmup_idempotent_when_already_warming_up(self):
        self.mock_client.describe_inference_component.return_value = {
            "InferenceComponentStatus": "Updating",
            "RuntimeConfig": {"CurrentCopyCount": 0, "DesiredCopyCount": 1},
        }
        response = handler.lambda_handler({"httpMethod": "POST", "resource": "/warmup"}, None)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["status"], "warming_up")
        self.mock_client.update_inference_component_runtime_config.assert_not_called()

    def test_warmup_returns_503_on_failed_state(self):
        self.mock_client.describe_inference_component.return_value = {
            "InferenceComponentStatus": "Failed",
            "RuntimeConfig": {"CurrentCopyCount": 0, "DesiredCopyCount": 0},
        }
        response = handler.lambda_handler({"httpMethod": "POST", "resource": "/warmup"}, None)
        self.assertEqual(response["statusCode"], 503)

    def test_warmup_returns_409_on_conflict(self):
        self.mock_client.describe_inference_component.return_value = {
            "InferenceComponentStatus": "InService",
            "RuntimeConfig": {"CurrentCopyCount": 0, "DesiredCopyCount": 0},
        }
        self.mock_client.update_inference_component_runtime_config.side_effect = ClientError(
            {"Error": {"Code": "ConflictException", "Message": "Update in progress."}},
            "UpdateInferenceComponentRuntimeConfig",
        )
        response = handler.lambda_handler({"httpMethod": "POST", "resource": "/warmup"}, None)
        self.assertEqual(response["statusCode"], 409)

    def test_unknown_route_returns_404(self):
        response = handler.lambda_handler({"httpMethod": "GET", "resource": "/unknown"}, None)
        self.assertEqual(response["statusCode"], 404)

    def test_missing_env_returns_500(self):
        os.environ["SAGEMAKER_ENDPOINT_NAME"] = ""
        response = handler.lambda_handler({"httpMethod": "GET", "resource": "/status"}, None)
        self.assertEqual(response["statusCode"], 500)


if __name__ == "__main__":
    unittest.main()
