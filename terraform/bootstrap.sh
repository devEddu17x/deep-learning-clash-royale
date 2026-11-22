#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-dp-clash-royale}"

if ! command -v aws >/dev/null 2>&1; then
  echo "Error: AWS CLI is not installed or not in PATH." >&2
  exit 1
fi

read -rp "AWS profile: " AWS_PROFILE
if [[ -z "$AWS_PROFILE" ]]; then
  echo "Error: AWS profile is required." >&2
  exit 1
fi

read -rp "AWS region (e.g. us-east-1): " AWS_REGION
if [[ -z "$AWS_REGION" ]]; then
  echo "Error: AWS region is required." >&2
  exit 1
fi

read -rp "Environment (dev/qa/prod): " ENVIRONMENT
case "$ENVIRONMENT" in
  dev|qa|prod) ;;
  *)
    echo "Error: environment must be dev, qa, or prod." >&2
    exit 1
    ;;
esac

ACCOUNT_ID="$(aws sts get-caller-identity \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --query Account \
  --output text)"

if [[ ! "$ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
  echo "Error: could not resolve a valid AWS account ID." >&2
  exit 1
fi

BUCKET_NAME="${PROJECT}-${ENVIRONMENT}-${ACCOUNT_ID}"
STATE_KEY="${PROJECT}/${ENVIRONMENT}/terraform.tfstate"

if aws s3api head-bucket --bucket "$BUCKET_NAME" --profile "$AWS_PROFILE" --region "$AWS_REGION" >/dev/null 2>&1; then
  echo "Bucket ${BUCKET_NAME} already exists. Ensuring configuration..."
else
  echo "Creating bucket ${BUCKET_NAME} in ${AWS_REGION}..."
  if [[ "$AWS_REGION" == "us-east-1" ]]; then
    aws s3api create-bucket \
      --bucket "$BUCKET_NAME" \
      --profile "$AWS_PROFILE" \
      --region "$AWS_REGION" >/dev/null
  else
    aws s3api create-bucket \
      --bucket "$BUCKET_NAME" \
      --profile "$AWS_PROFILE" \
      --region "$AWS_REGION" \
      --create-bucket-configuration "LocationConstraint=${AWS_REGION}" >/dev/null
  fi
fi

aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

aws s3api put-bucket-versioning \
  --bucket "$BUCKET_NAME" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --versioning-configuration "Status=Enabled"

aws s3api put-bucket-encryption \
  --bucket "$BUCKET_NAME" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        },
        "BucketKeyEnabled": true
      }
    ]
  }'

BUCKET_POLICY="$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::${BUCKET_NAME}",
        "arn:aws:s3:::${BUCKET_NAME}/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
EOF
)"

aws s3api put-bucket-policy \
  --bucket "$BUCKET_NAME" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --policy "$BUCKET_POLICY"

aws s3api put-bucket-tagging \
  --bucket "$BUCKET_NAME" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --tagging "{\"TagSet\":[{\"Key\":\"Project\",\"Value\":\"${PROJECT}\"},{\"Key\":\"Environment\",\"Value\":\"${ENVIRONMENT}\"},{\"Key\":\"ManagedBy\",\"Value\":\"Bootstrap\"}]}"

cat <<EOF

Copy into terraform/environments/${ENVIRONMENT}/backend.hcl:

profile = "${AWS_PROFILE}"
bucket = "${BUCKET_NAME}"
encrypt = true
key = "${STATE_KEY}"
region = "${AWS_REGION}"
use_lockfile = true
EOF
