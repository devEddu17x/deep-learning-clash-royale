variable "name_prefix" {
  type        = string
  description = "Prefix used for resource naming."
}

variable "binary_media_types" {
  type        = list(string)
  description = "Media types treated as binary payloads by API Gateway."
  default     = ["multipart/form-data"]
}

variable "cors_allow_origin" {
  type        = string
  description = "Allowed origin returned in CORS response headers."
  default     = "*"
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch access log retention in days."
  default     = 7
}

variable "manage_account_logging_role" {
  type        = bool
  description = "Configure the region-level API Gateway CloudWatch Logs IAM role on the AWS account."
  default     = true
}
