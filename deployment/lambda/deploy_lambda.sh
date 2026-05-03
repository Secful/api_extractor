#!/bin/bash
set -e

# Load configuration
source lambda-config.sh

echo "Deploying Lambda function: $FUNCTION_NAME"

# Create IAM role if it doesn't exist
ROLE_NAME="${FUNCTION_NAME}-role"
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$ROLE_ARN" ]; then
    echo "Creating IAM role..."

    # Create trust policy
    cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json

    # Attach basic Lambda execution policy
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

    # Attach VPC execution policy (for VPC access)
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"

    # Create and attach S3 and S3 Files access policy
    cat > /tmp/s3-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${S3_BUCKET_NAME}",
        "arn:aws:s3:::${S3_BUCKET_NAME}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3files:ClientMount",
        "s3files:ClientWrite"
      ],
      "Resource": "*"
    }
  ]
}
EOF

    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "${FUNCTION_NAME}-s3-read" \
        --policy-document file:///tmp/s3-policy.json

    # Get role ARN
    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)

    echo "Waiting for IAM role to propagate..."
    sleep 10
fi

echo "Using IAM role: $ROLE_ARN"

# Get VPC configuration from lambda-config.sh
if [ -z "$SUBNET_IDS" ] || [ -z "$SECURITY_GROUP_ID" ]; then
    echo "ERROR: VPC configuration not found. Run 'bash scripts/setup_vpc.sh' first."
    exit 1
fi

# Convert space-separated subnet IDs to comma-separated
SUBNET_IDS_COMMA=$(echo "$SUBNET_IDS" | tr ' ' ',')

# Check if function exists
FUNCTION_EXISTS=$(aws lambda get-function --function-name "$FUNCTION_NAME" 2>/dev/null || echo "")

if [ -z "$FUNCTION_EXISTS" ]; then
    echo "Creating Lambda function..."
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime python3.11 \
        --architectures arm64 \
        --role "$ROLE_ARN" \
        --handler lambda_handler.lambda_handler \
        --zip-file fileb://build/lambda-function.zip \
        --timeout "$LAMBDA_TIMEOUT" \
        --memory-size "$LAMBDA_MEMORY" \
        --vpc-config "SubnetIds=$SUBNET_IDS_COMMA,SecurityGroupIds=$SECURITY_GROUP_ID" \
        --environment "Variables={S3_MOUNT_PATH=/mnt/s3,LOG_LEVEL=INFO,S3_BUCKET_NAME=$S3_BUCKET_NAME}" \
        --description "API Extractor - Extract OpenAPI specs from source code"
else
    echo "Updating Lambda function code..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file fileb://build/lambda-function.zip

    echo "Updating Lambda function configuration..."
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --timeout "$LAMBDA_TIMEOUT" \
        --memory-size "$LAMBDA_MEMORY" \
        --vpc-config "SubnetIds=$SUBNET_IDS_COMMA,SecurityGroupIds=$SECURITY_GROUP_ID" \
        --environment "Variables={S3_MOUNT_PATH=/mnt/s3,LOG_LEVEL=INFO,S3_BUCKET_NAME=$S3_BUCKET_NAME}"
fi

echo "Lambda function deployed successfully!"
aws lambda get-function --function-name "$FUNCTION_NAME" --query 'Configuration.[FunctionName,State,LastModified]' --output table
