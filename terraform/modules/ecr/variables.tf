variable "name_prefix" {
  type        = string
  description = "Prefix used for resource naming."
}

variable "image_tag_mutability" {
  type        = string
  description = "Tag mutability setting for the ECR repository."
  default     = "MUTABLE"
}

variable "force_delete" {
  type        = bool
  description = "Allow deleting the repository even when it contains images."
  default     = false
}

variable "max_image_count" {
  type        = number
  description = "Maximum number of images to retain in ECR."
  default     = 5
}
