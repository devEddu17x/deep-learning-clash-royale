resource "aws_appautoscaling_target" "inference_component" {
  min_capacity       = 0
  max_capacity       = var.max_copy_count
  resource_id        = "inference-component/${aws_sagemaker_inference_component.inference.name}"
  scalable_dimension = "sagemaker:inference-component:DesiredCopyCount"
  service_namespace  = "sagemaker"
}

resource "aws_appautoscaling_policy" "scale_in_to_zero" {
  name               = "${var.name_prefix}-ic-scale-in"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.inference_component.resource_id
  scalable_dimension = aws_appautoscaling_target.inference_component.scalable_dimension
  service_namespace  = aws_appautoscaling_target.inference_component.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = var.autoscaling_target_concurrency
    scale_in_cooldown  = var.scale_in_cooldown_seconds
    scale_out_cooldown = var.scale_out_cooldown_seconds

    predefined_metric_specification {
      predefined_metric_type = "SageMakerInferenceComponentConcurrentRequestsPerCopyHighResolution"
    }
  }
}

resource "aws_appautoscaling_policy" "scale_out_from_zero" {
  name               = "${var.name_prefix}-ic-scale-out-from-zero"
  policy_type        = "StepScaling"
  resource_id        = aws_appautoscaling_target.inference_component.resource_id
  scalable_dimension = aws_appautoscaling_target.inference_component.scalable_dimension
  service_namespace  = aws_appautoscaling_target.inference_component.service_namespace

  step_scaling_policy_configuration {
    adjustment_type         = "ChangeInCapacity"
    cooldown                = 60
    metric_aggregation_type = "Maximum"

    step_adjustment {
      metric_interval_lower_bound = 0
      scaling_adjustment          = 1
    }
  }
}
