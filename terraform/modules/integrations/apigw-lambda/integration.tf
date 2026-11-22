resource "aws_api_gateway_method" "lambda" {
  for_each = local.lambda_routes

  rest_api_id   = var.rest_api_id
  resource_id   = each.value.resource_id
  http_method   = each.value.http_method
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda" {
  for_each = local.lambda_routes

  rest_api_id             = var.rest_api_id
  resource_id             = each.value.resource_id
  http_method             = aws_api_gateway_method.lambda[each.key].http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = var.lambda_invoke_arn
}

resource "aws_api_gateway_method" "lambda_options" {
  for_each = local.lambda_routes

  rest_api_id   = var.rest_api_id
  resource_id   = each.value.resource_id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_options" {
  for_each = local.lambda_routes

  rest_api_id = var.rest_api_id
  resource_id = each.value.resource_id
  http_method = aws_api_gateway_method.lambda_options[each.key].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

resource "aws_api_gateway_method_response" "lambda_options_200" {
  for_each = local.lambda_routes

  rest_api_id = var.rest_api_id
  resource_id = each.value.resource_id
  http_method = aws_api_gateway_method.lambda_options[each.key].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "lambda_options_200" {
  for_each = local.lambda_routes

  rest_api_id = var.rest_api_id
  resource_id = each.value.resource_id
  http_method = aws_api_gateway_method.lambda_options[each.key].http_method
  status_code = aws_api_gateway_method_response.lambda_options_200[each.key].status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Accept'"
    "method.response.header.Access-Control-Allow-Methods" = "'${each.value.http_method},OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'${var.cors_allow_origin}'"
  }

  depends_on = [aws_api_gateway_integration.lambda_options]
}
