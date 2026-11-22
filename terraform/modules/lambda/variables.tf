variable "function_name" {
  type        = string
  description = "Name of the Lambda function."
}

variable "source_dir" {
  type        = string
  description = "Directory containing the Lambda source code."
}

variable "output_zip_path" {
  type        = string
  description = "Output path for the packaged Lambda zip archive."
}

variable "handler" {
  type        = string
  description = "Lambda handler entrypoint."
  default     = "handler.lambda_handler"
}

variable "memory_size" {
  type        = number
  description = "Memory in MB allocated to the Lambda function."
  default     = 128
}

variable "timeout" {
  type        = number
  description = "Execution timeout in seconds."
  default     = 10
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days."
  default     = 7
}

variable "sagemaker_endpoint_arn" {
  type        = string
  description = "ARN of the SageMaker endpoint managed by this Lambda."
}

variable "sagemaker_inference_component_arn" {
  type        = string
  description = "ARN of the SageMaker inference component managed by this Lambda."
}

variable "environment_variables" {
  type        = map(string)
  description = "Environment variables passed to the Lambda function."
  default     = {}
}
