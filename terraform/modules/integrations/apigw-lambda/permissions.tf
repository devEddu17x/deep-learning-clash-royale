locals {
  lambda_routes = {
    warmup = {
      resource_id = var.warmup_resource_id
      http_method = "POST"
    }
    status = {
      resource_id = var.status_resource_id
      http_method = "GET"
    }
  }
}

resource "aws_lambda_permission" "apigw" {
  for_each = local.lambda_routes

  statement_id  = "AllowAPIGatewayInvoke-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.execution_arn}/*/${each.value.http_method}/${each.key}"
}
