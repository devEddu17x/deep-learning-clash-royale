variable "aws_profile" {
  type        = string
  description = "AWS CLI profile used to provision resources."
}

variable "aws_region" {
  type        = string
  description = "AWS region where resources are deployed."
}

variable "project_name" {
  type        = string
  description = "Project name used for resource naming and tags."
}

variable "environment" {
  type        = string
  description = "Deployment environment name."
}

variable "s3_force_destroy" {
  type        = bool
  description = "Allow destroying the model artifacts S3 bucket when non-empty."
  default     = true
}

variable "ecr_image_tag_mutability" {
  type        = string
  description = "Tag mutability setting for the ECR repository."
  default     = "MUTABLE"
}

variable "ecr_force_delete" {
  type        = bool
  description = "Allow deleting the ECR repository even when it contains images."
  default     = true
}

variable "ecr_max_image_count" {
  type        = number
  description = "Maximum number of images retained in ECR."
  default     = 5
}

variable "sagemaker_image_tag" {
  type        = string
  description = "Docker image tag deployed to SageMaker."
  default     = "latest"
}

variable "sagemaker_model_data_url" {
  type        = string
  description = "Optional S3 URI of the model artifact archive."
  default     = null
}

variable "sagemaker_container_environment" {
  type        = map(string)
  description = "Environment variables passed to the SageMaker inference container."
  default     = {}
}

variable "sagemaker_variant_name" {
  type        = string
  description = "SageMaker production variant name."
  default     = "primary"
}

variable "sagemaker_instance_type" {
  type        = string
  description = "SageMaker GPU instance type."
  default     = "ml.g5.xlarge"
}

variable "sagemaker_max_instance_count" {
  type        = number
  description = "Maximum number of GPU instances managed by SageMaker scaling."
  default     = 2
}

variable "sagemaker_initial_copy_count" {
  type        = number
  description = "Initial copy count for the SageMaker inference component."
  default     = 1
}

variable "sagemaker_max_copy_count" {
  type        = number
  description = "Maximum copy count for inference component auto scaling."
  default     = 1
}

variable "sagemaker_min_memory_mb" {
  type        = number
  description = "Minimum host memory in MB allocated to the inference component."
  default     = 1024
}

variable "sagemaker_max_memory_mb" {
  type        = number
  description = "Maximum host memory in MB allocated to the inference component."
  default     = null
}

variable "sagemaker_cpu_cores" {
  type        = number
  description = "Number of CPU cores allocated to the inference component."
  default     = null
}

variable "sagemaker_accelerator_devices" {
  type        = number
  description = "Number of GPU accelerator devices allocated to the inference component."
  default     = 1
}

variable "sagemaker_startup_health_check_timeout_seconds" {
  type        = number
  description = "Container startup health check timeout in seconds."
  default     = 600
}

variable "sagemaker_model_data_download_timeout_seconds" {
  type        = number
  description = "Timeout in seconds for downloading model artifacts from S3."
  default     = 600
}

variable "sagemaker_autoscaling_target_concurrency" {
  type        = number
  description = "Target concurrent requests per copy for auto scaling."
  default     = 3
}

variable "sagemaker_scale_in_cooldown_seconds" {
  type        = number
  description = "Cooldown period in seconds before scaling in to zero."
  default     = 300
}

variable "sagemaker_scale_out_cooldown_seconds" {
  type        = number
  description = "Cooldown period in seconds between scale-out actions."
  default     = 60
}

variable "warmup_lambda_memory_size" {
  type        = number
  description = "Memory in MB allocated to the warm-up Lambda function."
  default     = 128
}

variable "warmup_lambda_timeout" {
  type        = number
  description = "Timeout in seconds for the warm-up Lambda function."
  default     = 10
}

variable "api_binary_media_types" {
  type        = list(string)
  description = "Media types treated as binary payloads by API Gateway."
  default     = ["multipart/form-data"]
}

variable "cors_allow_origin" {
  type        = string
  description = "Allowed origin returned in CORS headers."
  default     = "*"
}

variable "throttling_rate_limit" {
  type        = number
  description = "Steady-state request rate limit per second across the API stage."
  default     = 5
}

variable "throttling_burst_limit" {
  type        = number
  description = "Burst request capacity across the API stage."
  default     = 10
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days."
  default     = 7
}

variable "api_manage_account_logging_role" {
  type        = bool
  description = "Configure the region-level API Gateway CloudWatch Logs role; set false if another environment in the same account and region already manages it."
  default     = true
}
