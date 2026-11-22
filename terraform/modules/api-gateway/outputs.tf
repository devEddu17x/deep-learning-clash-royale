output "rest_api_id" {
  description = "ID of the API Gateway REST API."
  value       = aws_api_gateway_rest_api.this.id
}

output "root_resource_id" {
  description = "Root resource ID of the API Gateway REST API."
  value       = aws_api_gateway_rest_api.this.root_resource_id
}

output "execution_arn" {
  description = "Execution ARN of the API Gateway REST API."
  value       = aws_api_gateway_rest_api.this.execution_arn
}

output "health_resource_id" {
  description = "Resource ID for /health."
  value       = aws_api_gateway_resource.health.id
}

output "predict_resource_id" {
  description = "Resource ID for /predict."
  value       = aws_api_gateway_resource.predict.id
}

output "warmup_resource_id" {
  description = "Resource ID for /warmup."
  value       = aws_api_gateway_resource.warmup.id
}

output "status_resource_id" {
  description = "Resource ID for /status."
  value       = aws_api_gateway_resource.status.id
}

output "access_log_group_arn" {
  description = "ARN of the CloudWatch access log group."
  value       = aws_cloudwatch_log_group.access_logs.arn
}

output "trigger_hash" {
  description = "Hash of API resources and health routes to trigger redeployment on changes."
  value = sha1(jsonencode([
    aws_api_gateway_rest_api.this.binary_media_types,
    aws_api_gateway_resource.health.id,
    aws_api_gateway_resource.predict.id,
    aws_api_gateway_resource.warmup.id,
    aws_api_gateway_resource.status.id,
    aws_api_gateway_method.health_get.id,
    aws_api_gateway_integration.health_get.id,
    aws_api_gateway_integration_response.health_get_200.id,
    aws_api_gateway_method.health_options.id,
    aws_api_gateway_integration.health_options.id,
    aws_api_gateway_integration_response.health_options_200.id,
    try(aws_api_gateway_account.this[0].cloudwatch_role_arn, ""),
  ]))
}
