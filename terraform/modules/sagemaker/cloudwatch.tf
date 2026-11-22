resource "aws_cloudwatch_log_group" "endpoint" {
  name              = "/aws/sagemaker/Endpoints/${var.name_prefix}-endpoint"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "inference_component" {
  name              = "/aws/sagemaker/InferenceComponents/${var.name_prefix}-ic"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_metric_alarm" "no_capacity_scale_out" {
  alarm_name          = "${var.name_prefix}-ic-no-capacity"
  alarm_description   = "Scales the inference component from 0 to 1 copy when an invocation arrives with zero capacity."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  metric_name         = "NoCapacityInvocationFailures"
  namespace           = "AWS/SageMaker"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    InferenceComponentName = aws_sagemaker_inference_component.inference.name
  }

  alarm_actions = [aws_appautoscaling_policy.scale_out_from_zero.arn]
}
