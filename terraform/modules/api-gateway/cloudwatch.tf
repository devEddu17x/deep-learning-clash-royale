resource "aws_cloudwatch_log_group" "access_logs" {
  name              = "/aws/apigateway/${var.name_prefix}-api"
  retention_in_days = var.log_retention_days
}

data "aws_iam_policy_document" "apigw_cloudwatch_assume" {
  count = var.manage_account_logging_role ? 1 : 0

  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apigw_cloudwatch" {
  count = var.manage_account_logging_role ? 1 : 0

  name               = "${var.name_prefix}-apigw-cloudwatch-role"
  assume_role_policy = data.aws_iam_policy_document.apigw_cloudwatch_assume[0].json
}

resource "aws_iam_role_policy_attachment" "apigw_cloudwatch" {
  count = var.manage_account_logging_role ? 1 : 0

  role       = aws_iam_role.apigw_cloudwatch[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

resource "aws_api_gateway_account" "this" {
  count = var.manage_account_logging_role ? 1 : 0

  cloudwatch_role_arn = aws_iam_role.apigw_cloudwatch[0].arn

  depends_on = [aws_iam_role_policy_attachment.apigw_cloudwatch]
}
