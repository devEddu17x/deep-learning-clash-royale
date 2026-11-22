locals {
  predict_error_responses = {
    "400" = "4(0[0-9]|1[0-9]|2[0-8]|[3-9][0-9])"
    "429" = "429"
    "503" = "503"
    "500" = "5(0[0-24-9]|[1-9][0-9])"
  }
}

resource "aws_api_gateway_method" "predict_post" {
  rest_api_id   = var.rest_api_id
  resource_id   = var.predict_resource_id
  http_method   = "POST"
  authorization = "NONE"

  request_parameters = {
    "method.request.header.Content-Type" = false
    "method.request.header.Accept"       = false
  }
}

resource "aws_api_gateway_integration" "predict_post" {
  rest_api_id             = var.rest_api_id
  resource_id             = var.predict_resource_id
  http_method             = aws_api_gateway_method.predict_post.http_method
  type                    = "AWS"
  integration_http_method = "POST"
  credentials             = aws_iam_role.apigw_sagemaker.arn
  uri                     = "arn:aws:apigateway:${var.aws_region}:runtime.sagemaker:path//endpoints/${var.sagemaker_endpoint_name}/invocations"
  passthrough_behavior    = "WHEN_NO_TEMPLATES"

  request_parameters = {
    "integration.request.header.Content-Type"                         = "method.request.header.Content-Type"
    "integration.request.header.Accept"                               = "method.request.header.Accept"
    "integration.request.header.X-Amzn-SageMaker-Inference-Component" = "'${var.sagemaker_inference_component_name}'"
  }

  depends_on = [aws_iam_role_policy.apigw_sagemaker]
}

resource "aws_api_gateway_method_response" "predict_post_200" {
  rest_api_id = var.rest_api_id
  resource_id = var.predict_resource_id
  http_method = aws_api_gateway_method.predict_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_integration_response" "predict_post_200" {
  rest_api_id = var.rest_api_id
  resource_id = var.predict_resource_id
  http_method = aws_api_gateway_method.predict_post.http_method
  status_code = aws_api_gateway_method_response.predict_post_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'${var.cors_allow_origin}'"
  }

  depends_on = [aws_api_gateway_integration.predict_post]
}

resource "aws_api_gateway_method_response" "predict_post_errors" {
  for_each = local.predict_error_responses

  rest_api_id = var.rest_api_id
  resource_id = var.predict_resource_id
  http_method = aws_api_gateway_method.predict_post.http_method
  status_code = each.key

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_integration_response" "predict_post_errors" {
  for_each = local.predict_error_responses

  rest_api_id       = var.rest_api_id
  resource_id       = var.predict_resource_id
  http_method       = aws_api_gateway_method.predict_post.http_method
  status_code       = aws_api_gateway_method_response.predict_post_errors[each.key].status_code
  selection_pattern = each.value

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'${var.cors_allow_origin}'"
  }

  depends_on = [aws_api_gateway_integration.predict_post]
}

resource "aws_api_gateway_method" "predict_options" {
  rest_api_id   = var.rest_api_id
  resource_id   = var.predict_resource_id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "predict_options" {
  rest_api_id = var.rest_api_id
  resource_id = var.predict_resource_id
  http_method = aws_api_gateway_method.predict_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

resource "aws_api_gateway_method_response" "predict_options_200" {
  rest_api_id = var.rest_api_id
  resource_id = var.predict_resource_id
  http_method = aws_api_gateway_method.predict_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "predict_options_200" {
  rest_api_id = var.rest_api_id
  resource_id = var.predict_resource_id
  http_method = aws_api_gateway_method.predict_options.http_method
  status_code = aws_api_gateway_method_response.predict_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Accept'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'${var.cors_allow_origin}'"
  }

  depends_on = [aws_api_gateway_integration.predict_options]
}
