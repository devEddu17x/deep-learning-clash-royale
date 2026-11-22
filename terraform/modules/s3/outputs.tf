output "bucket_id" {
  description = "ID of the model artifacts S3 bucket."
  value       = aws_s3_bucket.model_artifacts.id
}

output "bucket_arn" {
  description = "ARN of the model artifacts S3 bucket."
  value       = aws_s3_bucket.model_artifacts.arn
}

output "bucket_name" {
  description = "Name of the model artifacts S3 bucket."
  value       = aws_s3_bucket.model_artifacts.bucket
}
