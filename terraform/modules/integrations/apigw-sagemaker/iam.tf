data "aws_iam_policy_document" "apigw_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apigw_sagemaker" {
  name               = "${var.name_prefix}-apigw-sagemaker-role"
  assume_role_policy = data.aws_iam_policy_document.apigw_assume.json
}

data "aws_iam_policy_document" "apigw_sagemaker" {
  statement {
    sid     = "InvokeSageMakerEndpoint"
    actions = ["sagemaker:InvokeEndpoint"]
    resources = [
      var.sagemaker_endpoint_arn,
      var.sagemaker_inference_component_arn,
    ]
  }
}

resource "aws_iam_role_policy" "apigw_sagemaker" {
  name   = "${var.name_prefix}-apigw-sagemaker-policy"
  role   = aws_iam_role.apigw_sagemaker.id
  policy = data.aws_iam_policy_document.apigw_sagemaker.json
}
