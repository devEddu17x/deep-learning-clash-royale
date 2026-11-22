output "invoke_url" {
  description = "Base invoke URL of the API Gateway stage."
  value       = aws_api_gateway_stage.this.invoke_url
}

output "stage_arn" {
  description = "ARN of the API Gateway stage."
  value       = aws_api_gateway_stage.this.arn
}

output "deployment_id" {
  description = "ID of the active API Gateway deployment."
  value       = aws_api_gateway_deployment.this.id
}
