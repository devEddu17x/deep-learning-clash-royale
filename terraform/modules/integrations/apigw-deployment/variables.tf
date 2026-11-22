variable "rest_api_id" {
  type        = string
  description = "ID of the API Gateway REST API."
}

variable "stage_name" {
  type        = string
  description = "Name of the API Gateway stage."
}

variable "access_log_group_arn" {
  type        = string
  description = "ARN of the CloudWatch log group for API Gateway access logs."
}

variable "redeployment_triggers" {
  type        = list(string)
  description = "Hashes from API Gateway and integration modules to trigger redeployment."
}

variable "throttling_rate_limit" {
  type        = number
  description = "Steady-state request rate limit per second across the stage."
  default     = 5
}

variable "throttling_burst_limit" {
  type        = number
  description = "Burst request capacity across the stage."
  default     = 10
}
