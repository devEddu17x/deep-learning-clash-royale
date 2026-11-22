variable "name_prefix" {
  type        = string
  description = "Prefix used for resource naming."
}

variable "model_bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket containing model artifacts."
}

variable "ecr_repository_arn" {
  type        = string
  description = "ARN of the ECR repository hosting the inference container."
}

variable "ecr_repository_url" {
  type        = string
  description = "URI of the ECR repository hosting the inference container."
}

variable "image_tag" {
  type        = string
  description = "Container image tag to deploy."
  default     = "latest"
}

variable "model_data_url" {
  type        = string
  description = "Optional S3 URI for the model artifact archive."
  default     = null
}

variable "container_environment" {
  type        = map(string)
  description = "Environment variables passed to the inference container."
  default     = {}
}

variable "variant_name" {
  type        = string
  description = "Production variant name."
  default     = "primary"
}

variable "instance_type" {
  type        = string
  description = "SageMaker GPU instance type."
  default     = "ml.g5.xlarge"
}

variable "max_instance_count" {
  type        = number
  description = "Maximum number of instances managed by SageMaker scaling."
  default     = 2
}

variable "initial_copy_count" {
  type        = number
  description = "Initial number of inference component copies."
  default     = 1
}

variable "max_copy_count" {
  type        = number
  description = "Maximum number of inference component copies for auto scaling."
  default     = 1
}

variable "min_memory_mb" {
  type        = number
  description = "Minimum host memory in MB allocated to the inference component."
  default     = 1024
}

variable "max_memory_mb" {
  type        = number
  description = "Maximum host memory in MB allocated to the inference component."
  default     = null
}

variable "cpu_cores" {
  type        = number
  description = "Number of CPU cores required by the inference component."
  default     = null
}

variable "accelerator_devices" {
  type        = number
  description = "Number of GPU accelerator devices required by the inference component."
  default     = 1
}

variable "startup_health_check_timeout_seconds" {
  type        = number
  description = "Container startup health check timeout in seconds."
  default     = 600
}

variable "model_data_download_timeout_seconds" {
  type        = number
  description = "Timeout in seconds for downloading model artifacts from S3."
  default     = 600
}

variable "autoscaling_target_concurrency" {
  type        = number
  description = "Target concurrent requests per copy before scaling out."
  default     = 3
}

variable "scale_in_cooldown_seconds" {
  type        = number
  description = "Cooldown period in seconds before scaling in to zero."
  default     = 300
}

variable "scale_out_cooldown_seconds" {
  type        = number
  description = "Cooldown period in seconds between scale-out actions."
  default     = 60
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days."
  default     = 7
}
