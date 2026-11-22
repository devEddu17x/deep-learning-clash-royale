variable "rest_api_id" {
  type        = string
  description = "ID of the API Gateway REST API."
}

variable "execution_arn" {
  type        = string
  description = "Execution ARN of the API Gateway REST API."
}

variable "warmup_resource_id" {
  type        = string
  description = "Resource ID for /warmup."
}

variable "status_resource_id" {
  type        = string
  description = "Resource ID for /status."
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the warm-up control Lambda function."
}

variable "lambda_invoke_arn" {
  type        = string
  description = "Invoke ARN of the warm-up control Lambda function."
}

variable "cors_allow_origin" {
  type        = string
  description = "Allowed origin returned in CORS response headers."
  default     = "*"
}
