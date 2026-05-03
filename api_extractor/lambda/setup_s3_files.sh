#!/bin/bash
set -e

source lambda-config.sh

echo "Creating S3 file system for bucket: $S3_BUCKET_NAME"

# Check if bucket exists
if ! aws s3api head-bucket --bucket "$S3_BUCKET_NAME" 2>/dev/null; then
    echo "Creating S3 bucket..."
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "$S3_BUCKET_NAME" --region "$AWS_REGION"
    else
        aws s3api create-bucket \
            --bucket "$S3_BUCKET_NAME" \
            --region "$AWS_REGION" \
            --create-bucket-configuration LocationConstraint="$AWS_REGION"
    fi
fi

# Get bucket ARN
BUCKET_ARN="arn:aws:s3:::${S3_BUCKET_NAME}"
echo "Bucket ARN: $BUCKET_ARN"

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create IAM role for S3 Files (if it doesn't exist)
S3FILES_ROLE_NAME="${FUNCTION_NAME}-s3files-role"
S3FILES_ROLE_ARN=$(aws iam get-role --role-name "$S3FILES_ROLE_NAME" --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$S3FILES_ROLE_ARN" ]; then
    echo "Creating IAM role for S3 Files..."

    # Create trust policy for S3 Files
    cat > /tmp/s3files-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "s3files.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    aws iam create-role \
        --role-name "$S3FILES_ROLE_NAME" \
        --assume-role-policy-document file:///tmp/s3files-trust-policy.json

    # Create and attach S3 access policy
    cat > /tmp/s3files-bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "${BUCKET_ARN}",
        "${BUCKET_ARN}/*"
      ]
    }
  ]
}
EOF

    aws iam put-role-policy \
        --role-name "$S3FILES_ROLE_NAME" \
        --policy-name "${FUNCTION_NAME}-s3files-bucket-access" \
        --policy-document file:///tmp/s3files-bucket-policy.json

    # Get role ARN
    S3FILES_ROLE_ARN=$(aws iam get-role --role-name "$S3FILES_ROLE_NAME" --query 'Role.Arn' --output text)

    echo "Waiting for IAM role to propagate..."
    sleep 10
fi

echo "Using S3 Files IAM role: $S3FILES_ROLE_ARN"

# Create S3 file system
echo "Creating S3 file system..."
FILE_SYSTEM_ID=$(aws s3files create-file-system \
    --region "$AWS_REGION" \
    --bucket "$BUCKET_ARN" \
    --role-arn "$S3FILES_ROLE_ARN" \
    --query 'FileSystemId' \
    --output text)

echo "File system created: $FILE_SYSTEM_ID"

# Get VPC subnets
SUBNET_IDS_ARRAY=($SUBNET_IDS)

# Create mount targets in each subnet
echo "Creating mount targets..."
for SUBNET_ID in "${SUBNET_IDS_ARRAY[@]}"; do
    echo "Creating mount target in subnet: $SUBNET_ID"
    aws s3files create-mount-target \
        --region "$AWS_REGION" \
        --file-system-id "$FILE_SYSTEM_ID" \
        --subnet-id "$SUBNET_ID" || echo "Mount target may already exist"
done

echo "Waiting for mount targets to become available (this can take up to 15 minutes)..."
sleep 30

# Save IDs for later use
echo "export FILE_SYSTEM_ID=$FILE_SYSTEM_ID" >> lambda-config.sh
echo "export S3FILES_ROLE_ARN=$S3FILES_ROLE_ARN" >> lambda-config.sh

echo ""
echo "S3 file system setup complete!"
echo "File System ID: $FILE_SYSTEM_ID"
echo "Bucket: $S3_BUCKET_NAME"
