output "endpoint_name" {
  description = "Name of the SageMaker endpoint."
  value       = aws_sagemaker_endpoint.inference.name
}

output "endpoint_arn" {
  description = "ARN of the SageMaker endpoint."
  value       = aws_sagemaker_endpoint.inference.arn
}

output "inference_component_name" {
  description = "Name of the SageMaker inference component."
  value       = aws_sagemaker_inference_component.inference.name
}

output "inference_component_arn" {
  description = "ARN of the SageMaker inference component."
  value       = aws_sagemaker_inference_component.inference.arn
}

output "model_name" {
  description = "Name of the SageMaker model."
  value       = aws_sagemaker_model.inference.name
}

output "execution_role_arn" {
  description = "ARN of the SageMaker execution IAM role."
  value       = aws_iam_role.sagemaker_execution.arn
}

output "log_group_name" {
  description = "CloudWatch log group name for the SageMaker endpoint."
  value       = aws_cloudwatch_log_group.endpoint.name
}

output "inference_component_log_group_name" {
  description = "CloudWatch log group name for the SageMaker inference component container logs."
  value       = aws_cloudwatch_log_group.inference_component.name
}
