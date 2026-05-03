#!/bin/bash
# Lambda deployment configuration
# IMPORTANT: All AWS operations use credentials from ~/.aws/credentials and ~/.aws/config
# The AWS CLI automatically reads credentials from ~/.aws/ directory
# If you have multiple profiles, set AWS_PROFILE environment variable before running scripts

# Lambda Configuration
export FUNCTION_NAME=api-extractor
export AWS_REGION=eu-north-1

# S3 Configuration
export S3_BUCKET_NAME=my-code-repositories

# Lambda Settings
export LAMBDA_TIMEOUT=300
export LAMBDA_MEMORY=1024

# VPC Configuration (auto-generated)
export VPC_ID=vpc-04c807514c9b47c25
export SUBNET_IDS="subnet-02e4e5dfd1846ff12 subnet-04282b104cb990de2"
export SECURITY_GROUP_ID=sg-0980528a0aeaf965f

# S3 Files Configuration (auto-generated)
export FILE_SYSTEM_ID=fs-07fb9cb984b56d279
export S3FILES_ROLE_ARN=arn:aws:iam::329599622528:role/api-extractor-s3files-role

export ACCESS_POINT_ID=fsap-0a6df2113c56cb2bc
export ACCESS_POINT_ARN=arn:aws:s3files:eu-north-1:329599622528:file-system/fs-07fb9cb984b56d279/access-point/fsap-0a6df2113c56cb2bc
