variable "name_prefix" {
  type        = string
  description = "Prefix used for resource naming."
}

variable "aws_region" {
  type        = string
  description = "AWS region where SageMaker runtime is hosted."
}

variable "rest_api_id" {
  type        = string
  description = "ID of the API Gateway REST API."
}

variable "predict_resource_id" {
  type        = string
  description = "Resource ID of the /predict endpoint."
}

variable "sagemaker_endpoint_name" {
  type        = string
  description = "Name of the target SageMaker endpoint."
}

variable "sagemaker_endpoint_arn" {
  type        = string
  description = "ARN of the target SageMaker endpoint."
}

variable "sagemaker_inference_component_name" {
  type        = string
  description = "Name of the SageMaker inference component injected as header."
}

variable "sagemaker_inference_component_arn" {
  type        = string
  description = "ARN of the SageMaker inference component."
}

variable "cors_allow_origin" {
  type        = string
  description = "Allowed origin returned in CORS response headers."
  default     = "*"
}
