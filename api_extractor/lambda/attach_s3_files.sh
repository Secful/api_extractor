#!/bin/bash
set -e

source lambda-config.sh

echo "Attaching S3 file system to Lambda function..."

# Check if FILE_SYSTEM_ID is set
if [ -z "$FILE_SYSTEM_ID" ]; then
    echo "ERROR: S3 Files configuration not found. Run 'bash scripts/setup_s3_files.sh' first."
    exit 1
fi

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Construct file system ARN
# For S3 Files, the ARN format is: arn:aws:s3files:region:account-id:file-system/filesystem-id
FILE_SYSTEM_ARN="arn:aws:s3files:${AWS_REGION}:${ACCOUNT_ID}:file-system/${FILE_SYSTEM_ID}"

echo "Attaching file system $FILE_SYSTEM_ID to Lambda..."
echo "File system ARN: $FILE_SYSTEM_ARN"

# Attach file system to Lambda
aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --region "$AWS_REGION" \
    --file-system-configs \
        Arn="$FILE_SYSTEM_ARN",LocalMountPath=/mnt/s3

echo "Waiting for Lambda to update..."
aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$AWS_REGION"

echo ""
echo "S3 file system attached to Lambda at /mnt/s3"
echo "File System ID: $FILE_SYSTEM_ID"
