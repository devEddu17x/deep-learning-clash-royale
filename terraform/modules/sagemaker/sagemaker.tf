resource "aws_sagemaker_model" "inference" {
  execution_role_arn = aws_iam_role.sagemaker_execution.arn

  primary_container {
    image          = "${var.ecr_repository_url}:${var.image_tag}"
    model_data_url = var.model_data_url
    environment    = length(var.container_environment) > 0 ? var.container_environment : null
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_sagemaker_endpoint_configuration" "inference" {
  name_prefix        = "${var.name_prefix}-epc-"
  execution_role_arn = aws_iam_role.sagemaker_execution.arn

  # model_name is intentionally omitted on the variant so Inference Components manage model placement and scale-to-zero.
  production_variants {
    variant_name           = var.variant_name
    instance_type          = var.instance_type
    initial_instance_count = 1

    managed_instance_scaling {
      status             = "ENABLED"
      min_instance_count = 0
      max_instance_count = var.max_instance_count
    }

    routing_config {
      routing_strategy = "LEAST_OUTSTANDING_REQUESTS"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_sagemaker_endpoint" "inference" {
  name                 = "${var.name_prefix}-endpoint"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.inference.name
}

resource "aws_sagemaker_inference_component" "inference" {
  name          = "${var.name_prefix}-ic"
  endpoint_name = aws_sagemaker_endpoint.inference.name
  variant_name  = var.variant_name

  specification {
    model_name = aws_sagemaker_model.inference.name

    compute_resource_requirements {
      min_memory_required_in_mb              = var.min_memory_mb
      max_memory_required_in_mb              = var.max_memory_mb
      number_of_cpu_cores_required           = var.cpu_cores
      number_of_accelerator_devices_required = var.accelerator_devices
    }

    startup_parameters {
      container_startup_health_check_timeout_in_seconds = var.startup_health_check_timeout_seconds
      model_data_download_timeout_in_seconds            = var.model_data_download_timeout_seconds
    }
  }

  runtime_config {
    copy_count = var.initial_copy_count
  }

  lifecycle {
    ignore_changes = [runtime_config[0].copy_count]
  }
}
