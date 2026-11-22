output "trigger_hash" {
  description = "Hash of Lambda routes and integrations to trigger redeployment on changes."
  value = sha1(jsonencode([
    [for key in sort(keys(aws_api_gateway_method.lambda)) : aws_api_gateway_method.lambda[key].id],
    [for key in sort(keys(aws_api_gateway_integration.lambda)) : aws_api_gateway_integration.lambda[key].id],
    [for key in sort(keys(aws_api_gateway_integration.lambda)) : aws_api_gateway_integration.lambda[key].uri],
    [for key in sort(keys(aws_api_gateway_method.lambda_options)) : aws_api_gateway_method.lambda_options[key].id],
    [for key in sort(keys(aws_api_gateway_integration_response.lambda_options_200)) : aws_api_gateway_integration_response.lambda_options_200[key].id],
  ]))
}
