#!/bin/bash
set -e

# Load configuration
source lambda-config.sh

echo "Cleaning up Lambda resources..."

# Delete Function URL
echo "Deleting Function URL..."
aws lambda delete-function-url-config --function-name "$FUNCTION_NAME" 2>/dev/null || echo "Function URL not found"

# Delete Lambda function
echo "Deleting Lambda function..."
aws lambda delete-function --function-name "$FUNCTION_NAME" 2>/dev/null || echo "Function not found"

# Detach policies from role
echo "Cleaning up IAM role..."
ROLE_NAME="${FUNCTION_NAME}-role"
aws iam detach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>/dev/null || true

aws iam detach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole" 2>/dev/null || true

aws iam delete-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "${FUNCTION_NAME}-s3-read" 2>/dev/null || true

# Delete role
aws iam delete-role --role-name "$ROLE_NAME" 2>/dev/null || echo "Role not found"

echo "Cleanup complete!"
echo "Note: S3 bucket '$S3_BUCKET_NAME' was not deleted (contains data)"
echo "Note: VPC resources were not deleted (run cleanup_vpc.sh separately if needed)"
