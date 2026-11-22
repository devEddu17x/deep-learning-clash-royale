output "integration_role_arn" {
  description = "ARN of the IAM role used by API Gateway to invoke SageMaker."
  value       = aws_iam_role.apigw_sagemaker.arn
}

output "trigger_hash" {
  description = "Hash of /predict methods and integrations to trigger redeployment on changes."
  value = sha1(jsonencode([
    aws_api_gateway_method.predict_post.id,
    aws_api_gateway_integration.predict_post.id,
    aws_api_gateway_integration.predict_post.uri,
    aws_api_gateway_integration.predict_post.request_parameters,
    aws_api_gateway_integration_response.predict_post_200.id,
    [for key in sort(keys(aws_api_gateway_integration_response.predict_post_errors)) : aws_api_gateway_integration_response.predict_post_errors[key].id],
    aws_api_gateway_method.predict_options.id,
    aws_api_gateway_integration.predict_options.id,
    aws_api_gateway_integration_response.predict_options_200.id,
  ]))
}
