module "s3" {
  source = "../../modules/s3"

  name_prefix   = local.name_prefix
  account_id    = local.account_id
  force_destroy = var.s3_force_destroy
}

module "ecr" {
  source = "../../modules/ecr"

  name_prefix          = local.name_prefix
  image_tag_mutability = var.ecr_image_tag_mutability
  force_delete         = var.ecr_force_delete
  max_image_count      = var.ecr_max_image_count
}

module "sagemaker" {
  source = "../../modules/sagemaker"

  name_prefix                          = local.name_prefix
  model_bucket_arn                     = module.s3.bucket_arn
  ecr_repository_arn                   = module.ecr.repository_arn
  ecr_repository_url                   = module.ecr.repository_url
  image_tag                            = var.sagemaker_image_tag
  model_data_url                       = var.sagemaker_model_data_url
  container_environment                = var.sagemaker_container_environment
  variant_name                         = var.sagemaker_variant_name
  instance_type                        = var.sagemaker_instance_type
  max_instance_count                   = var.sagemaker_max_instance_count
  initial_copy_count                   = var.sagemaker_initial_copy_count
  max_copy_count                       = var.sagemaker_max_copy_count
  min_memory_mb                        = var.sagemaker_min_memory_mb
  max_memory_mb                        = var.sagemaker_max_memory_mb
  cpu_cores                            = var.sagemaker_cpu_cores
  accelerator_devices                  = var.sagemaker_accelerator_devices
  startup_health_check_timeout_seconds = var.sagemaker_startup_health_check_timeout_seconds
  model_data_download_timeout_seconds  = var.sagemaker_model_data_download_timeout_seconds
  autoscaling_target_concurrency       = var.sagemaker_autoscaling_target_concurrency
  scale_in_cooldown_seconds            = var.sagemaker_scale_in_cooldown_seconds
  scale_out_cooldown_seconds           = var.sagemaker_scale_out_cooldown_seconds
  log_retention_days                   = var.log_retention_days
}

module "lambda_warmup" {
  source = "../../modules/lambda"

  function_name                     = "${local.name_prefix}-warm-up"
  source_dir                        = "${path.module}/../../services/lambda/warm-up"
  output_zip_path                   = "${path.root}/.terraform/build/warm-up.zip"
  memory_size                       = var.warmup_lambda_memory_size
  timeout                           = var.warmup_lambda_timeout
  log_retention_days                = var.log_retention_days
  sagemaker_endpoint_arn            = module.sagemaker.endpoint_arn
  sagemaker_inference_component_arn = module.sagemaker.inference_component_arn

  environment_variables = {
    SAGEMAKER_ENDPOINT_NAME            = module.sagemaker.endpoint_name
    SAGEMAKER_INFERENCE_COMPONENT_NAME = module.sagemaker.inference_component_name
    CORS_ALLOW_ORIGIN                  = var.cors_allow_origin
  }
}

module "api_gateway" {
  source = "../../modules/api-gateway"

  name_prefix                 = local.name_prefix
  binary_media_types          = var.api_binary_media_types
  cors_allow_origin           = var.cors_allow_origin
  log_retention_days          = var.log_retention_days
  manage_account_logging_role = var.api_manage_account_logging_role
}

module "apigw_sagemaker" {
  source = "../../modules/integrations/apigw-sagemaker"

  name_prefix                        = local.name_prefix
  aws_region                         = var.aws_region
  rest_api_id                        = module.api_gateway.rest_api_id
  predict_resource_id                = module.api_gateway.predict_resource_id
  sagemaker_endpoint_name            = module.sagemaker.endpoint_name
  sagemaker_endpoint_arn             = module.sagemaker.endpoint_arn
  sagemaker_inference_component_name = module.sagemaker.inference_component_name
  sagemaker_inference_component_arn  = module.sagemaker.inference_component_arn
  cors_allow_origin                  = var.cors_allow_origin
}

module "apigw_lambda" {
  source = "../../modules/integrations/apigw-lambda"

  rest_api_id          = module.api_gateway.rest_api_id
  execution_arn        = module.api_gateway.execution_arn
  warmup_resource_id   = module.api_gateway.warmup_resource_id
  status_resource_id   = module.api_gateway.status_resource_id
  lambda_function_name = module.lambda_warmup.function_name
  lambda_invoke_arn    = module.lambda_warmup.invoke_arn
  cors_allow_origin    = var.cors_allow_origin
}

module "apigw_deployment" {
  source = "../../modules/integrations/apigw-deployment"

  rest_api_id            = module.api_gateway.rest_api_id
  stage_name             = var.environment
  access_log_group_arn   = module.api_gateway.access_log_group_arn
  throttling_rate_limit  = var.throttling_rate_limit
  throttling_burst_limit = var.throttling_burst_limit

  redeployment_triggers = [
    module.api_gateway.trigger_hash,
    module.apigw_sagemaker.trigger_hash,
    module.apigw_lambda.trigger_hash,
  ]
}
