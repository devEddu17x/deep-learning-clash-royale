output "repository_name" {
  description = "Name of the inference ECR repository."
  value       = aws_ecr_repository.inference.name
}

output "repository_arn" {
  description = "ARN of the inference ECR repository."
  value       = aws_ecr_repository.inference.arn
}

output "repository_url" {
  description = "URI of the inference ECR repository."
  value       = aws_ecr_repository.inference.repository_url
}
