variable "name_prefix" {
  type        = string
  description = "Prefix used for resource naming."
}

variable "account_id" {
  type        = string
  description = "AWS account ID to guarantee globally unique bucket names."
}

variable "force_destroy" {
  type        = bool
  description = "Allow destroying a non-empty bucket."
  default     = false
}
