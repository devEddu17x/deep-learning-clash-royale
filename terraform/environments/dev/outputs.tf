output "api_base_url" {
  description = "Base invoke URL of the API Gateway stage."
  value       = module.apigw_deployment.invoke_url
}

output "predict_url" {
  description = "Invoke URL for POST /predict."
  value       = "${module.apigw_deployment.invoke_url}/predict"
}

output "warmup_url" {
  description = "Invoke URL for POST /warmup."
  value       = "${module.apigw_deployment.invoke_url}/warmup"
}

output "status_url" {
  description = "Invoke URL for GET /status."
  value       = "${module.apigw_deployment.invoke_url}/status"
}

output "health_url" {
  description = "Invoke URL for GET /health."
  value       = "${module.apigw_deployment.invoke_url}/health"
}

output "ecr_repository_url" {
  description = "ECR repository URI for the BYOC inference image."
  value       = module.ecr.repository_url
}

output "model_artifacts_bucket" {
  description = "S3 bucket name for model artifacts."
  value       = module.s3.bucket_name
}

output "sagemaker_endpoint_name" {
  description = "Name of the SageMaker endpoint."
  value       = module.sagemaker.endpoint_name
}

output "sagemaker_inference_component_name" {
  description = "Name of the SageMaker inference component."
  value       = module.sagemaker.inference_component_name
}

output "warmup_lambda_name" {
  description = "Name of the warm-up control Lambda function."
  value       = module.lambda_warmup.function_name
}
